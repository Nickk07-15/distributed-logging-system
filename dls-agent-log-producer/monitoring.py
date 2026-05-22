#!/usr/bin/env python3
"""
Monitoring stub for dls-agent-log-producer.
Extend with service-specific metrics as needed.
"""

from utils.monitoring_utils import Metrics, Tags
from app_config import cfg, reconfigure_monitors

# Service-level prefix and tags — mirrors the pattern used across all DLS services
_PREFIX = cfg.LOGGER.process_tag
_DEFAULT_TAGS = [f"env:{cfg.LOG_AGENT.environment}"]


class DLSAgentTags(Tags):
    default_tags = _DEFAULT_TAGS


class DLSAgentMetrics(Metrics):
    """
    Service metrics for dls-agent-log-producer.

    Extend _register_metrics() to add counters / histograms as the
    service grows (e.g. records_produced_total, queue_overflow_total).
    """

    def _register_metrics(self) -> None:
        pass  # No metrics registered yet


def init() -> None:
    """
    Initialize monitoring for this service.
    Called once from main() before any business logic runs.
    """
    reconfigure_monitors(_PREFIX, _DEFAULT_TAGS)
    DLSAgentMetrics()
