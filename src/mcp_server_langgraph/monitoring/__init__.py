"""Monitoring, SLA tracking, and Cost Monitoring"""

from .sla import SLAMeasurement, SLAMetric, SLAMonitor, SLAReport, SLAStatus, SLATarget, get_sla_monitor, set_sla_monitor


# Cost monitoring (if available)
try:
    pass

    __all__ = [
        "SLAMonitor",
        "SLAMetric",
        "SLAStatus",
        "SLATarget",
        "SLAMeasurement",
        "SLAReport",
        "get_sla_monitor",
        "set_sla_monitor",
        "PRICING_TABLE",
        "calculate_cost",
    ]
except ImportError:
    __all__ = [
        "SLAMonitor",
        "SLAMetric",
        "SLAStatus",
        "SLATarget",
        "SLAMeasurement",
        "SLAReport",
        "get_sla_monitor",
        "set_sla_monitor",
    ]
