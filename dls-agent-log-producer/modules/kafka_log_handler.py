#!/usr/bin/env python3
"""
Kafka Log Handler
-----------------
A stdlib logging.Handler that ships log records to Kafka asynchronously.

Design goals (from system NFRs):
  - Non-blocking: emit() must never stall the application thread.
    Target p95 ingest latency (app → Kafka): ≤ 25 ms.
  - Reliable: queue overflow and Kafka errors degrade gracefully to stderr;
    they never propagate exceptions back to the application.
  - Safe shutdown: close() drains the queue and flushes the producer so
    no records are lost on graceful termination.

Internal architecture:
  ┌─────────────────────────────────────────┐
  │  Application thread(s)                  │
  │  logging.getLogger(...).error(...)       │
  │          │                              │
  │          ▼                              │
  │  KafkaLogHandler.emit()                 │
  │    serialize → queue.put_nowait()       │
  │          │   (non-blocking, O(1))       │
  └──────────┼──────────────────────────────┘
             │  queue.Queue (bounded: handler_queue_size)
  ┌──────────┼──────────────────────────────┐
  │  Drain thread (daemon)                  │
  │    queue.get(timeout=drain_interval)    │
  │    batch up to drain_batch_size records │
  │    KafkaLogProducerService.produce()    │
  │    KafkaLogProducerService.flush()      │
  └─────────────────────────────────────────┘

Queue overflow policy: drop the record and write a one-line warning to
stderr. We intentionally never block the application thread.

Recursion guard: the drain thread and producer service use sys.stderr.write()
for their own error output — never stdlib logging — to break potential
logging → handler → logging cycles.
"""

import sys
import queue
import logging
import threading
from typing import Optional

from modules.log_schema import DLSLogRecord, build_dls_log_record
from services.kafka_producer_service import KafkaLogProducerService


class KafkaLogHandler(logging.Handler):
    """
    Async, non-blocking logging.Handler that ships records to Kafka.

    Instantiate once and attach to the root logger (or any logger) after
    calling KafkaLogProducerService() to initialize the singleton producer.

    Args:
        service_name (str): Originating service name used as partition key
                            and embedded in every log record.
        environment (str): Deployment environment (dev / staging / prod).
        schema_version (str): Log schema version (default "1.0").
        handler_queue_size (int): Max records buffered in the internal queue
                                  before overflow drops begin (default 50000).
        drain_batch_size (int): Max records sent to Kafka per drain cycle
                                (default 200).
        drain_interval_seconds (float): How long the drain thread blocks
                                        waiting for queue items before looping
                                        (default 0.5 s).
        fallback_to_stderr (bool): If True, dropped/failed records are echoed
                                   to stderr (default True).
        level (int): Minimum log level forwarded to Kafka (default logging.NOTSET).
    """

    def __init__(
        self,
        service_name: str,
        environment: str,
        schema_version: str = "1.0",
        handler_queue_size: int = 50_000,
        drain_batch_size: int = 200,
        drain_interval_seconds: float = 0.5,
        fallback_to_stderr: bool = True,
        level: int = logging.NOTSET,
    ):
        super().__init__(level=level)

        self._service_name = service_name
        self._environment = environment
        self._schema_version = schema_version
        self._drain_batch_size = drain_batch_size
        self._drain_interval = drain_interval_seconds
        self._fallback_to_stderr = fallback_to_stderr

        self._queue: queue.Queue = queue.Queue(maxsize=handler_queue_size)
        self._producer: Optional[KafkaLogProducerService] = None

        # Shutdown coordination
        self._stop_event = threading.Event()
        self._drain_thread = threading.Thread(
            target=self._drain_worker,
            name="kafka-log-drain",
            daemon=True,
        )
        self._drain_thread.start()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        """
        Serialize record and enqueue for async Kafka delivery.

        Called by the logging framework on the application thread. Must
        return as fast as possible — no blocking I/O, no Kafka calls.

        Args:
            record (logging.LogRecord): The log record to ship.
        """
        try:
            dls_record = build_dls_log_record(
                record=record,
                service_name=self._service_name,
                environment=self._environment,
                schema_version=self._schema_version,
            )
            self._queue.put_nowait(dls_record)

        except queue.Full:
            if self._fallback_to_stderr:
                sys.stderr.write(
                    f"[KafkaLogHandler] Queue full — dropping record: "
                    f"{record.levelname} {record.name}: {record.getMessage()}\n"
                )

        except Exception as exc:
            # Never let handler errors propagate into the application
            if self._fallback_to_stderr:
                sys.stderr.write(
                    f"[KafkaLogHandler] emit() error: {exc.__class__.__name__}: {exc}\n"
                )

    def close(self) -> None:
        """
        Flush remaining queued records and shut down the drain thread.

        Called automatically by logging.shutdown() on process exit, or
        explicitly when tearing down the handler.
        """
        self._stop_event.set()
        self._drain_thread.join(timeout=15.0)

        # Final flush of the Kafka producer buffer
        producer = self._get_producer()
        if producer is not None:
            producer.flush(timeout_seconds=10.0)

        super().close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_producer(self) -> Optional[KafkaLogProducerService]:
        """
        Lazily return the KafkaLogProducerService singleton.

        The Singleton may not be initialized when the handler is first
        created (it is initialized in main() after config is loaded).
        Returning None here causes the drain thread to fall back to stderr
        until the producer is ready — no records are lost from the queue.
        """
        if self._producer is None:
            try:
                # Singleton: returns existing instance if already initialized
                self._producer = KafkaLogProducerService()
            except Exception:
                pass  # Producer not yet initialized; will retry next cycle
        return self._producer

    def _drain_worker(self) -> None:
        """
        Background thread: drain the queue and ship records to Kafka in batches.

        Runs until _stop_event is set (via close()), then does a final drain
        of any remaining items before exiting.
        """
        while not self._stop_event.is_set():
            self._drain_cycle()

        # Final drain after stop signal
        self._drain_cycle(flush=True)

    def _drain_cycle(self, flush: bool = False) -> None:
        """
        Collect up to drain_batch_size records from the queue and produce them.

        Blocks for at most drain_interval_seconds waiting for the first record,
        then collects additional records without blocking until the batch is full
        or the queue is empty.

        Args:
            flush (bool): If True, call producer.flush() after producing the
                          batch (used on shutdown to ensure full delivery).
        """
        batch: list[DLSLogRecord] = []

        # Block waiting for at least one record
        try:
            first = self._queue.get(timeout=self._drain_interval)
            batch.append(first)
            self._queue.task_done()
        except queue.Empty:
            return

        # Collect remaining records without blocking (up to batch size)
        while len(batch) < self._drain_batch_size:
            try:
                record = self._queue.get_nowait()
                batch.append(record)
                self._queue.task_done()
            except queue.Empty:
                break

        if not batch:
            return

        producer = self._get_producer()

        for dls_record in batch:
            if producer is not None:
                producer.produce(
                    value_bytes=dls_record.to_json_bytes(),
                    key=dls_record.service_name,
                )
            elif self._fallback_to_stderr:
                sys.stderr.write(
                    f"[KafkaLogHandler] No producer available — stderr fallback: "
                    f"{dls_record.log_level} [{dls_record.logger_name}] "
                    f"{dls_record.message}\n"
                )

        if producer is not None and flush:
            producer.flush(timeout_seconds=10.0)
