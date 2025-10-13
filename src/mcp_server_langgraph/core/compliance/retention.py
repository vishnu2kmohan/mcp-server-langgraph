"""
Data Retention Service - GDPR Article 5(1)(e) Storage Limitation

Implements automated data retention policies with configurable cleanup schedules.
Ensures compliance with GDPR data minimization and SOC 2 storage requirements.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.session import SessionStore
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class RetentionPolicy(BaseModel):
    """Data retention policy configuration"""

    data_type: str = Field(..., description="Type of data (sessions, conversations, etc.)")
    retention_days: int = Field(..., description="Number of days to retain data")
    enabled: bool = Field(default=True, description="Whether policy is enabled")
    soft_delete: bool = Field(default=False, description="Soft delete before permanent deletion")
    notify_before: bool = Field(default=False, description="Notify before deletion")


class RetentionResult(BaseModel):
    """Result of retention policy execution"""

    policy_name: str
    execution_timestamp: str
    deleted_count: int = 0
    archived_count: int = 0
    errors: List[str] = Field(default_factory=list)
    dry_run: bool = False


class DataRetentionService:
    """
    Service for enforcing data retention policies

    Features:
    - Configurable retention periods per data type
    - Scheduled cleanup execution
    - Dry-run mode for testing
    - Audit logging of all deletions
    - Metrics tracking
    """

    def __init__(
        self,
        config_path: str = "config/retention_policies.yaml",
        session_store: Optional[SessionStore] = None,
        dry_run: bool = False,
    ):
        """
        Initialize data retention service

        Args:
            config_path: Path to retention policies YAML file
            session_store: Session storage backend
            dry_run: If True, only simulate deletions without actually deleting
        """
        self.config_path = Path(config_path)
        self.session_store = session_store
        self.dry_run = dry_run
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load retention policies from YAML configuration"""
        try:
            if not self.config_path.exists():
                logger.warning(f"Retention config not found: {self.config_path}, using defaults")
                return self._default_config()

            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            logger.info(f"Loaded retention policies from {self.config_path}")
            return config

        except Exception as e:
            logger.error(f"Failed to load retention config: {e}", exc_info=True)
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default retention configuration"""
        return {
            "global": {"enabled": True, "dry_run": False},
            "retention_periods": {
                "user_sessions": {"inactive": 90},
                "conversations": {"archived": 90},
                "audit_logs": {"standard": 2555},
            },
        }

    async def cleanup_sessions(self) -> RetentionResult:
        """
        Clean up old sessions based on retention policy

        Returns:
            RetentionResult with deletion counts
        """
        with tracer.start_as_current_span("retention.cleanup_sessions") as span:
            policy_config = self.config.get("retention_periods", {}).get("user_sessions", {})
            retention_days = policy_config.get("inactive", 90)

            result = RetentionResult(
                policy_name="user_sessions",
                execution_timestamp=datetime.utcnow().isoformat() + "Z",
                dry_run=self.dry_run,
            )

            if not self.session_store:
                logger.warning("Session store not available for retention cleanup")
                result.errors.append("Session store not configured")
                return result

            try:
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                logger.info(
                    f"Cleaning up sessions inactive since {cutoff_date.isoformat()}",
                    extra={"retention_days": retention_days, "dry_run": self.dry_run},
                )

                # Get all sessions (implementation depends on SessionStore interface)
                # For now, this is a placeholder - actual implementation would query sessions
                deleted_count = await self._cleanup_inactive_sessions(cutoff_date)

                result.deleted_count = deleted_count
                span.set_attribute("deleted_count", deleted_count)

                # Track metrics
                if not self.dry_run:
                    metrics.successful_calls.add(1, {"operation": "session_cleanup"})

                logger.info(
                    f"Session cleanup completed",
                    extra={
                        "deleted_count": deleted_count,
                        "retention_days": retention_days,
                        "dry_run": self.dry_run,
                    },
                )

            except Exception as e:
                error_msg = f"Session cleanup failed: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                span.record_exception(e)

            return result

    async def cleanup_conversations(self) -> RetentionResult:
        """
        Clean up old conversations based on retention policy

        Returns:
            RetentionResult with deletion counts
        """
        with tracer.start_as_current_span("retention.cleanup_conversations"):
            policy_config = self.config.get("retention_periods", {}).get("conversations", {})
            archived_retention = policy_config.get("archived", 90)

            result = RetentionResult(
                policy_name="conversations",
                execution_timestamp=datetime.utcnow().isoformat() + "Z",
                dry_run=self.dry_run,
            )

            try:
                cutoff_date = datetime.utcnow() - timedelta(days=archived_retention)
                logger.info(
                    f"Cleaning up archived conversations older than {cutoff_date.isoformat()}",
                    extra={"retention_days": archived_retention, "dry_run": self.dry_run},
                )

                # Placeholder: Actual implementation would integrate with conversation store
                # deleted_count = await self._cleanup_archived_conversations(cutoff_date)
                deleted_count = 0

                result.deleted_count = deleted_count

                logger.info(
                    f"Conversation cleanup completed",
                    extra={"deleted_count": deleted_count, "dry_run": self.dry_run},
                )

            except Exception as e:
                error_msg = f"Conversation cleanup failed: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            return result

    async def cleanup_audit_logs(self) -> RetentionResult:
        """
        Clean up old audit logs based on retention policy

        Note: Most audit logs are retained for 7 years (2555 days) for compliance.

        Returns:
            RetentionResult with deletion/archive counts
        """
        with tracer.start_as_current_span("retention.cleanup_audit_logs"):
            policy_config = self.config.get("retention_periods", {}).get("audit_logs", {})
            retention_days = policy_config.get("standard", 2555)

            result = RetentionResult(
                policy_name="audit_logs",
                execution_timestamp=datetime.utcnow().isoformat() + "Z",
                dry_run=self.dry_run,
            )

            try:
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                logger.info(
                    f"Archiving audit logs older than {cutoff_date.isoformat()}",
                    extra={"retention_days": retention_days, "dry_run": self.dry_run},
                )

                # Placeholder: Actual implementation would archive to cold storage
                # archived_count = await self._archive_audit_logs(cutoff_date)
                archived_count = 0

                result.archived_count = archived_count

                logger.info(
                    f"Audit log cleanup completed",
                    extra={"archived_count": archived_count, "dry_run": self.dry_run},
                )

            except Exception as e:
                error_msg = f"Audit log cleanup failed: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            return result

    async def run_all_cleanups(self) -> List[RetentionResult]:
        """
        Run all configured retention policies

        Returns:
            List of RetentionResults for each policy
        """
        with tracer.start_as_current_span("retention.run_all_cleanups") as span:
            logger.info("Starting retention policy cleanup", extra={"dry_run": self.dry_run})

            results = []

            # Check if retention is globally enabled
            if not self.config.get("global", {}).get("enabled", True):
                logger.warning("Data retention globally disabled in configuration")
                return results

            # Run session cleanup
            if self.config.get("cleanup_actions", {}).get("sessions", {}).get("enabled", True):
                result = await self.cleanup_sessions()
                results.append(result)

            # Run conversation cleanup
            if self.config.get("cleanup_actions", {}).get("conversations", {}).get("enabled", True):
                result = await self.cleanup_conversations()
                results.append(result)

            # Run audit log cleanup
            if self.config.get("cleanup_actions", {}).get("audit_logs", {}).get("enabled", True):
                result = await self.cleanup_audit_logs()
                results.append(result)

            # Calculate totals
            total_deleted = sum(r.deleted_count for r in results)
            total_archived = sum(r.archived_count for r in results)
            total_errors = sum(len(r.errors) for r in results)

            span.set_attribute("total_deleted", total_deleted)
            span.set_attribute("total_archived", total_archived)
            span.set_attribute("total_errors", total_errors)

            logger.info(
                "Retention policy cleanup completed",
                extra={
                    "total_deleted": total_deleted,
                    "total_archived": total_archived,
                    "total_errors": total_errors,
                    "policies_run": len(results),
                    "dry_run": self.dry_run,
                },
            )

            return results

    async def _cleanup_inactive_sessions(self, cutoff_date: datetime) -> int:
        """
        Delete sessions not accessed since cutoff date

        Args:
            cutoff_date: Delete sessions last accessed before this date

        Returns:
            Number of sessions deleted
        """
        if not self.session_store:
            return 0

        if self.dry_run:
            # In dry-run mode, just count inactive sessions without deleting
            inactive_sessions = await self.session_store.get_inactive_sessions(cutoff_date)
            return len(inactive_sessions)
        else:
            # Actually delete inactive sessions
            return await self.session_store.delete_inactive_sessions(cutoff_date)

    def get_retention_summary(self) -> Dict[str, Any]:
        """
        Get summary of retention policies

        Returns:
            Dictionary with retention policy configuration
        """
        return {
            "enabled": self.config.get("global", {}).get("enabled", True),
            "dry_run": self.dry_run,
            "policies": {
                name: {
                    "retention_days": config.get("active", config.get("inactive", config.get("standard", 0))),
                    "description": config.get("description", ""),
                }
                for name, config in self.config.get("retention_periods", {}).items()
            },
            "next_cleanup": self._get_next_cleanup_time(),
        }

    def _get_next_cleanup_time(self) -> str:
        """Calculate next scheduled cleanup time"""
        # Parse cron schedule (0 3 * * * = daily at 3 AM)
        schedule = self.config.get("global", {}).get("cleanup_schedule", "0 3 * * *")
        # For now, just return tomorrow at 3 AM
        next_run = datetime.utcnow().replace(hour=3, minute=0, second=0, microsecond=0)
        if next_run < datetime.utcnow():
            next_run += timedelta(days=1)
        return next_run.isoformat() + "Z"
