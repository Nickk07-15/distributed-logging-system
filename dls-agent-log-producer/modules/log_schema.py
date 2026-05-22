#!/usr/bin/env python3
"""
Log Schema Module
-----------------
Defines the canonical log record schema for the distributed logging system
and provides serialization to the wire format sent to Kafka (JSON bytes).

Schema version: 1.0

Wire format (JSON):
{
    "schema_version": "1.0",
    "timestamp":      "2026-01-01T12:00:00.123456Z",  -- ISO 8601 UTC
    "service_name":   "dls-agent-log-producer",
    "environment":    "dev",
    "trace_id":       "abc12345",
    "log_level":      "ERROR",
    "logger_name":    "modules.processor",
    "message":        "Failed to process record",
    "filename":       "processor.py",
    "lineno":         42,
    "process_id":     12345
}
"""

import json
import logging
import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class DLSLogRecord:
    """
    Canonical log record schema for the distributed logging system.

    All fields map directly to a key in the Kafka message value (JSON).
    Downstream consumers (Flink, Elasticsearch) rely on this schema — do
    not remove or rename fields without a corresponding schema migration.

    Attributes:
        schema_version (str): Schema version for forward-compatibility checks.
        timestamp (str): ISO 8601 UTC timestamp with microsecond precision.
        service_name (str): Originating service (maps to Kafka partition key).
        environment (str): Deployment environment (dev / staging / prod).
        trace_id (str): Correlation ID injected by app_config.set_trace().
        log_level (str): Logging level name (DEBUG / INFO / WARNING / ERROR / CRITICAL).
        logger_name (str): Dotted logger name (e.g. "modules.processor").
        message (str): Formatted log message.
        filename (str): Source file that emitted the record.
        lineno (int): Line number within the source file.
        process_id (int): OS process ID.
    """

    schema_version: str
    timestamp: str
    service_name: str
    environment: str
    trace_id: str
    log_level: str
    logger_name: str
    message: str
    filename: str
    lineno: int
    process_id: int

    def to_dict(self) -> dict:
        """Return a plain dict representation of this record."""
        return asdict(self)

    def to_json_bytes(self) -> bytes:
        """
        Serialize to JSON bytes for Kafka wire transport.

        Returns (bytes):
            UTF-8 encoded JSON. Consumers must decode with UTF-8 before parsing.
        """
        return json.dumps(self.to_dict(), ensure_ascii=False).encode("utf-8")


def build_dls_log_record(
    record: logging.LogRecord,
    service_name: str,
    environment: str,
    schema_version: str = "1.0",
) -> DLSLogRecord:
    """
    Convert a stdlib logging.LogRecord into a DLSLogRecord.

    Extracts trace_id from the ContextFilter attribute injected by app_config
    (falls back to empty string if not present).

    Args:
        record (logging.LogRecord): The stdlib log record to convert.
        service_name (str): Originating service name (cfg.LOGGER.process_tag).
        environment (str): Deployment environment (cfg.LOG_AGENT.environment).
        schema_version (str): Schema version string (default: "1.0").

    Returns (DLSLogRecord):
        Populated canonical log record ready for serialization.
    """
    timestamp = datetime.datetime.fromtimestamp(
        record.created, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    return DLSLogRecord(
        schema_version=schema_version,
        timestamp=timestamp,
        service_name=service_name,
        environment=environment,
        trace_id=getattr(record, "trace_id", ""),
        log_level=record.levelname,
        logger_name=record.name,
        message=record.getMessage(),
        filename=record.filename,
        lineno=record.lineno,
        process_id=record.process,
    )
