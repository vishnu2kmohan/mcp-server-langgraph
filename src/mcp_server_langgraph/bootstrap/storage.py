"""
Storage Bootstrap Module.

Initializes storage-related services:
- Audit service (unified audit logging)
- Compliance service (GDPR/HIPAA/SOC2 reporting)
- Audit scheduler (FedRAMP AU-9 integrity verification)
- Retention scheduler (FedRAMP AU-11 partition management)
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any


logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from mcp_server_langgraph.audit.service import UnifiedAuditService
    from mcp_server_langgraph.audit.compliance_service import ComplianceService
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.notifications.preferences import PreferencesRepository


@dataclass
class StorageState:
    """
    Storage state after audit/compliance initialization.

    Holds references to audit and compliance services, and schedulers.
    """

    audit_service: "UnifiedAuditService | None" = None
    compliance_service: "ComplianceService | None" = None
    audit_broadcaster: Any = None
    notification_broadcaster: Any = None
    preferences_repository: "PreferencesRepository | None" = None
    audit_scheduler: Any = None
    retention_scheduler: Any = None

    async def cleanup(self) -> None:
        """
        Cleanup storage resources.

        Stops schedulers gracefully.
        """
        if self.retention_scheduler is not None:
            try:
                await self.retention_scheduler.stop()
            except Exception as e:
                logger.debug("Operation failed: %s", e)

        if self.audit_scheduler is not None:
            try:
                self.audit_scheduler.stop()  # sync method
            except Exception as e:
                logger.debug("Operation failed: %s", e)


def create_preferences_repository(
    redis_client: Any = None,
) -> "PreferencesRepository":
    """
    Create a preferences repository based on available Redis client.

    Args:
        redis_client: Optional async Redis client. If provided, uses
            RedisPreferencesRepository for production. If None, uses
            InMemoryPreferencesRepository for development/testing.

    Returns:
        PreferencesRepository instance (Redis-backed or in-memory)
    """
    from mcp_server_langgraph.notifications.preferences import (
        InMemoryPreferencesRepository,
        RedisPreferencesRepository,
    )

    if redis_client is not None:
        logger.info("Using Redis-backed notification preferences repository")
        return RedisPreferencesRepository(redis_client=redis_client)
    else:
        logger.info("Using in-memory notification preferences repository")
        return InMemoryPreferencesRepository()


async def init_storage(settings: "Settings") -> StorageState:
    """
    Initialize storage-related services.

    This includes:
    1. Creating audit repository (Postgres or in-memory)
    2. Creating audit service with broadcaster
    3. Creating compliance service
    4. Starting audit and retention schedulers

    Args:
        settings: Application settings

    Returns:
        StorageState with initialized components

    Example:
        state = await init_storage(settings)
        app.state.audit_service = state.audit_service
    """
    from mcp_server_langgraph.audit.service import UnifiedAuditService
    from mcp_server_langgraph.audit.compliance_service import ComplianceService
    from mcp_server_langgraph.audit.repository import create_audit_repository
    from mcp_server_langgraph.audit.broadcast import AuditEventBroadcaster
    from mcp_server_langgraph.audit.factory import create_audit_scheduler
    from mcp_server_langgraph.audit.retention_scheduler import create_retention_scheduler
    from mcp_server_langgraph.audit.alerts import AuditAlertDetector
    from mcp_server_langgraph.audit.config import load_alerting_config, create_notifiers_from_config
    from mcp_server_langgraph.audit.notifications import NotificationRouter, create_notification_callback
    from mcp_server_langgraph.notifications.broadcast import NotificationBroadcaster
    from mcp_server_langgraph.notifications.preferences import (
        PreferencesRepository,
    )
    from mcp_server_langgraph.api.v1.notification_preferences import set_preferences_repository
    from mcp_server_langgraph.websocket.registry import (
        set_audit_event_broadcaster,
        set_notification_broadcaster,
    )
    from mcp_server_langgraph.api.v1.compliance_reports import set_compliance_service
    from mcp_server_langgraph.middleware.audit import set_audit_service
    from mcp_server_langgraph.observability.telemetry import logger

    audit_service: UnifiedAuditService | None = None
    compliance_service: ComplianceService | None = None
    audit_broadcaster: AuditEventBroadcaster | None = None
    notification_broadcaster: NotificationBroadcaster | None = None
    preferences_repository: PreferencesRepository | None = None
    audit_scheduler: Any = None
    retention_scheduler: Any = None

    try:
        # Create audit repository
        audit_repository = create_audit_repository(database_url=settings.database_url)

        # Create broadcaster for real-time WebSocket streaming
        audit_broadcaster = AuditEventBroadcaster()

        # Create alert notification system (Slack/PagerDuty integration)
        alert_detector = None
        try:
            alerting_config = load_alerting_config()
            notifiers = create_notifiers_from_config(alerting_config)
            if notifiers:
                notification_router = NotificationRouter(notifiers=notifiers)
                notification_callback = create_notification_callback(notification_router)

                alert_detector = AuditAlertDetector(
                    failed_login_threshold=alerting_config.detection.failed_login.threshold,
                    failed_login_window_minutes=alerting_config.detection.failed_login.window_minutes,
                    business_hours_start=alerting_config.detection.after_hours_admin.end_hour,
                    business_hours_end=alerting_config.detection.after_hours_admin.start_hour,
                    bulk_export_threshold_records=alerting_config.detection.bulk_export.threshold_records,
                    alert_callback=notification_callback,
                )
                logger.info(f"Alert notification system initialized with {len(notifiers)} notifier(s)")
            else:
                logger.info("No alert notifiers configured (Slack/PagerDuty webhooks not set)")
        except Exception as alert_config_error:
            logger.warning(f"Failed to initialize alert notifications: {alert_config_error}")

        audit_service = UnifiedAuditService(
            repository=audit_repository,
            integrity_secret=settings.audit_integrity_secret,
            broadcaster=audit_broadcaster,
            alert_detector=alert_detector,
        )
        logger.info("Audit service initialized with WebSocket streaming")

        # Set global accessors for middleware/WebSocket access
        # (Consolidates setter calls from app.py lifespan)
        set_audit_service(audit_service)
        set_audit_event_broadcaster(audit_broadcaster)

        # Create notification broadcaster
        notification_broadcaster = NotificationBroadcaster()
        set_notification_broadcaster(notification_broadcaster)
        logger.info("Notification WebSocket broadcaster initialized")

        # Create notification preferences repository
        # Use Redis when configured, otherwise in-memory for development
        redis_client = None
        if settings.redis_url and "localhost" not in settings.redis_url:
            try:
                import redis.asyncio as aioredis

                redis_client = aioredis.from_url(  # type: ignore[no-untyped-call]
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                logger.debug(f"Redis client created for preferences: {settings.redis_url}")
            except Exception as redis_err:
                logger.warning(f"Failed to create Redis client for preferences: {redis_err}")

        preferences_repository = create_preferences_repository(redis_client=redis_client)
        set_preferences_repository(preferences_repository)

        # Create compliance service
        compliance_service = ComplianceService(audit_service=audit_service)
        set_compliance_service(compliance_service)
        logger.info("Compliance service initialized")

    except Exception as e:
        logger.warning(f"Failed to initialize audit service: {e}")

    # Start audit scheduler if enabled (FedRAMP AU-9)
    if settings.audit_scheduler_enabled and audit_service is not None:
        try:
            audit_scheduler = create_audit_scheduler(
                audit_service=audit_service,
                schedule_hours=settings.audit_scheduler_hours,
            )
            await audit_scheduler.start()
            logger.info(f"Audit integrity scheduler started (every {settings.audit_scheduler_hours} hours)")
        except Exception as e:
            logger.warning(f"Failed to start audit scheduler: {e}")

    # Start retention scheduler if enabled (FedRAMP AU-11)
    if settings.partition_retention_enabled:
        try:
            retention_scheduler = create_retention_scheduler(
                retention_months=settings.partition_retention_months,
                schedule_hours=settings.partition_retention_hours,
            )
            await retention_scheduler.start()
            logger.info(
                f"Partition retention scheduler started "
                f"(retention={settings.partition_retention_months} months, "
                f"interval={settings.partition_retention_hours} hours)"
            )
        except Exception as e:
            logger.warning(f"Failed to start retention scheduler: {e}")

    return StorageState(
        audit_service=audit_service,
        compliance_service=compliance_service,
        audit_broadcaster=audit_broadcaster,
        notification_broadcaster=notification_broadcaster,
        preferences_repository=preferences_repository,
        audit_scheduler=audit_scheduler,
        retention_scheduler=retention_scheduler,
    )
