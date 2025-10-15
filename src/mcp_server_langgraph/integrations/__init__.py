"""
Integration modules for external services (alerting, monitoring, etc.)
"""

from .alerting import AlertingService, AlertSeverity, Alert

__all__ = ["AlertingService", "AlertSeverity", "Alert"]
