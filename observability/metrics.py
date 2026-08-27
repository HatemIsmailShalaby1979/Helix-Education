"""
Observability Metrics Collector.

Provides a simple interface for collecting and exposing metrics for
Prometheus scraping or internal monitoring dashboards.
"""

import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list] = {}

    def increment_counter(self, name: str, value: int = 1):
        """Increments a named counter."""
        self.counters[name] = self.counters.get(name, 0) + value
        logger.debug(f"Counter '{name}' incremented to {self.counters[name]}")

    def set_gauge(self, name: str, value: float):
        """Sets the value of a named gauge."""
        self.gauges[name] = value
        logger.debug(f"Gauge '{name}' set to {value}")

    def observe_histogram(self, name: str, value: float):
        """Records a value in a named histogram."""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

    def get_metrics_summary(self) -> dict:
        """Returns a summary of all current metrics."""
        return {
            "counters": self.counters,
            "gauges": self.gauges,
            "histograms": {
                k: {"count": len(v), "avg": sum(v) / len(v) if v else 0} for k, v in self.histograms.items()
            },
        }


# Global instance for easy access across the application
metrics = MetricsCollector()
