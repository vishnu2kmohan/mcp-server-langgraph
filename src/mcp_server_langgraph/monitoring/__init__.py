"""Monitoring, SLA tracking, and Cost Monitoring"""

from .sla import SLAMeasurement, SLAMetric, SLAMonitor, SLAReport, SLAStatus, SLATarget, get_sla_monitor, set_sla_monitor

# Cost monitoring - LiteLLM-based (recommended)
from .litellm_cost_callback import get_model_cost_from_litellm

# Legacy pricing (deprecated - use get_model_cost_from_litellm instead)
try:
    from .pricing import PRICING_TABLE, calculate_cost

    __all__ = [
        "PRICING_TABLE",
        "SLAMeasurement",
        "SLAMetric",
        "SLAMonitor",
        "SLAReport",
        "SLAStatus",
        "SLATarget",
        "calculate_cost",  # Deprecated - use get_model_cost_from_litellm
        "get_model_cost_from_litellm",  # Recommended
        "get_sla_monitor",
        "set_sla_monitor",
    ]
except ImportError:
    __all__ = [
        "SLAMeasurement",
        "SLAMetric",
        "SLAMonitor",
        "SLAReport",
        "SLAStatus",
        "SLATarget",
        "get_model_cost_from_litellm",
        "get_sla_monitor",
        "set_sla_monitor",
    ]
