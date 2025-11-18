"""
Integration modules for external services (alerting, monitoring, etc.)
"""

from .alerting import Alert, AlertingService, AlertSeverity


__all__ = ["AlertingService", "AlertSeverity", "Alert"]
