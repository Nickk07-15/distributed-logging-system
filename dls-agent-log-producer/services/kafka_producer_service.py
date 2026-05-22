#!/usr/bin/env python3
"""
Kafka Producer Service
----------------------
Thin singleton wrapper around confluent_kafka.Producer tuned for high-throughput
log record shipping.

Key design decisions vs. the generic KafkaProducerClient in libraries/apache/kafka.py:

1. No per-message flush — the generic client calls producer.flush() after every
   put_record(), which blocks the caller and destroys throughput. This service
   uses fire-and-forget produce() calls; flushing is done explicitly by the
   KafkaLogHandler drain thread on a configurable interval.

2. JSON serialization — the generic client serializes with str(data) (Python
   repr), which is not valid JSON. This service serializes pre-encoded bytes
   directly, keeping deserialization predictable for Flink/Elasticsearch.

3. Singleton — one Producer instance per process. confluent_kafka.Producer is
   thread-safe internally; sharing it avoids per-handler TCP connection overhead.
"""

import sys
import logging
from typing import Optional

from confluent_kafka import Producer, KafkaException

from utils.helpers import Singleton

logger = logging.getLogger(__name__)


class KafkaLogProducerService(metaclass=Singleton):
    """
    Singleton Kafka producer for shipping log records to the logs.raw topic.

    Wraps confluent_kafka.Producer with async (fire-and-forget) produce calls.
    The caller is responsible for periodically calling flush() to drain the
    internal librdkafka send buffer.

    Usage:
        producer = KafkaLogProducerService(cfg=cfg.KAFKA_PRODUCER)
        producer.produce(value_bytes=record.to_json_bytes(), key="my-service")
        producer.flush()  # called by KafkaLogHandler drain thread
    """

    def __init__(self, cfg=None):
        """
        Initialize the Kafka producer.

        Args:
            cfg: KAFKA_PRODUCER config namespace from app_config (required on
                 first call; ignored on subsequent Singleton calls).
        """
        if cfg is None:
            raise ValueError(
                "KafkaLogProducerService requires cfg on first initialization"
            )

        producer_config = {
            "bootstrap.servers": cfg.bootstrap_servers,
            "acks": str(cfg.acks),
            "retries": cfg.retries,
            "queue.buffering.max.messages": cfg.queue_buffering_max_messages,
            "queue.buffering.max.kbytes": cfg.queue_buffering_max_kbytes,
            "batch.num.messages": cfg.batch_num_messages,
            "linger.ms": cfg.linger_ms,
            "on_delivery": self._delivery_report,
        }

        self._topic = cfg.topic
        self._producer = Producer(producer_config)
        logger.info(
            f"KafkaLogProducerService initialized, topic={self._topic}, "
            f"bootstrap={cfg.bootstrap_servers}"
        )

    def produce(self, value_bytes: bytes, key: Optional[str] = None) -> None:
        """
        Enqueue a log record for async delivery. Non-blocking.

        If the internal librdkafka queue is full (queue.buffering.max.messages
        reached), the record is dropped and a warning is written to stderr to
        avoid recursive logging.

        Args:
            value_bytes (bytes): Pre-serialized JSON log record (UTF-8).
            key (str | None): Partition key — typically the service_name so
                              all logs from one service land in one partition.
        """
        try:
            self._producer.produce(
                topic=self._topic,
                value=value_bytes,
                key=key.encode("utf-8") if key else None,
            )
            # Poll to trigger delivery callbacks without blocking
            self._producer.poll(0)

        except KafkaException as error:
            sys.stderr.write(
                f"[KafkaLogProducerService] KafkaException during produce: {error}\n"
            )
        except BufferError:
            # librdkafka internal queue full
            sys.stderr.write(
                "[KafkaLogProducerService] Producer queue full — log record dropped.\n"
            )

    def flush(self, timeout_seconds: float = 5.0) -> int:
        """
        Block until all enqueued messages are delivered or timeout expires.

        Called periodically by the KafkaLogHandler drain thread and on shutdown.

        Args:
            timeout_seconds (float): Max seconds to wait for delivery.

        Returns (int):
            Number of messages still in the queue after flush (0 = fully drained).
        """
        try:
            remaining = self._producer.flush(timeout=timeout_seconds)
            if remaining > 0:
                sys.stderr.write(
                    f"[KafkaLogProducerService] flush() timed out with {remaining} "
                    f"messages still in queue.\n"
                )
            return remaining
        except KafkaException as error:
            sys.stderr.write(
                f"[KafkaLogProducerService] KafkaException during flush: {error}\n"
            )
            return -1

    def _delivery_report(self, err, msg) -> None:
        """
        librdkafka delivery callback. Called from poll()/flush() on the
        producer thread — do NOT use stdlib logging here (recursion risk).

        Args:
            err: KafkaError if delivery failed, None on success.
            msg: The delivered/failed Message object.
        """
        if err is not None:
            sys.stderr.write(
                f"[KafkaLogProducerService] Delivery failed for message "
                f"key={msg.key()}: {err}\n"
            )
