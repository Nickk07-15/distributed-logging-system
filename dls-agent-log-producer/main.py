#!/usr/bin/env python3
"""
dls-agent-log-producer — Entry Point
--------------------------------------
Demonstrates end-to-end usage of the KafkaLogHandler:

  1. Initializes config, trace context, and monitoring.
  2. Creates the KafkaLogProducerService singleton.
  3. Attaches a KafkaLogHandler to the root logger so that every
     logging call in the process is automatically shipped to Kafka.
  4. Runs a simulated workload that emits log records at multiple
     levels to exercise the full pipeline.

In a real integration, steps 1–3 would live in the host service's
main.py / setup sequence; step 4 would be replaced by actual business
logic. The KafkaLogHandler is designed to be a drop-in addition to
any service that already uses stdlib logging.
"""

import time
import random
import logging

import monitoring
from app_config import cfg, print_app_config, reconfigure_logger, set_trace
from modules.kafka_log_handler import KafkaLogHandler
from services.kafka_producer_service import KafkaLogProducerService


logger = logging.getLogger(__name__)


def setup_kafka_log_handler() -> KafkaLogHandler:
    """
    Initialize the Kafka producer singleton and attach a KafkaLogHandler
    to the root logger.

    The handler is added alongside the existing StreamHandler so that logs
    continue to appear on stdout (for local dev / CloudWatch) while also
    being shipped to Kafka.

    Returns (KafkaLogHandler):
        The attached handler instance (useful for explicit close() on shutdown).
    """
    KafkaLogProducerService(cfg=cfg.KAFKA_PRODUCER)

    handler = KafkaLogHandler(
        service_name=cfg.LOGGER.process_tag,
        environment=cfg.LOG_AGENT.environment,
        schema_version=cfg.LOG_AGENT.schema_version,
        handler_queue_size=cfg.LOG_AGENT.handler_queue_size,
        drain_batch_size=cfg.LOG_AGENT.drain_batch_size,
        drain_interval_seconds=cfg.LOG_AGENT.drain_interval_seconds,
        fallback_to_stderr=cfg.LOG_AGENT.fallback_to_stderr,
        level=logging.INFO,
    )

    logging.getLogger().addHandler(handler)
    logger.info("KafkaLogHandler attached to root logger")
    return handler


def simulate_workload(duration_seconds: int = 30) -> None:
    """
    Emit a representative mix of log records to exercise the handler.

    Simulates a service processing records with occasional warnings and
    errors, running for `duration_seconds` before returning.

    Args:
        duration_seconds (int): How long to run the simulation (default 30 s).
    """
    workload_logger = logging.getLogger("simulation.workload")
    error_logger = logging.getLogger("simulation.errors")

    logger.info(f"Starting workload simulation for {duration_seconds}s ...")

    start = time.time()
    processed = 0
    errors = 0

    while time.time() - start < duration_seconds:
        record_id = f"rec-{random.randint(10000, 99999)}"

        workload_logger.info(f"Processing record {record_id}")

        # Simulate occasional slow records
        if random.random() < 0.05:
            latency_ms = random.randint(500, 2000)
            workload_logger.warning(
                f"Slow record {record_id}, processing_time_ms={latency_ms}"
            )

        # Simulate occasional errors
        if random.random() < 0.02:
            error_logger.error(
                f"Failed to process record {record_id}, "
                f"error=TimeoutError, retries_remaining=2"
            )
            errors += 1
        else:
            processed += 1

        time.sleep(0.01)  # 100 records/sec simulation rate

    logger.info(
        f"Workload simulation complete — "
        f"processed={processed}, errors={errors}, "
        f"duration={time.time() - start:.1f}s"
    )


def main() -> None:
    """
    Service entry point.
    """
    logger.info("Starting dls-agent-log-producer ...")
    print_app_config()

    kafka_handler = setup_kafka_log_handler()

    try:
        simulate_workload(duration_seconds=30)
    finally:
        logger.info("Shutting down — flushing Kafka log handler ...")
        kafka_handler.close()
        logger.info("dls-agent-log-producer shut down cleanly.")


if __name__ == "__main__":
    set_trace()
    reconfigure_logger(use_console_logger=True)
    monitoring.init()
    main()
