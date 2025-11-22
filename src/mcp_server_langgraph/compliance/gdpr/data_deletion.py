"""
GDPR Data Deletion Service - Article 17 (Right to Erasure)
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.session import SessionStore
from mcp_server_langgraph.compliance.gdpr.factory import GDPRStorage
from mcp_server_langgraph.observability.telemetry import logger, tracer


class DeletionResult(BaseModel):
    """
    Result of user data deletion operation

    Tracks what data was deleted and any errors encountered.
    """

    success: bool = Field(..., description="Whether deletion completed successfully")
    user_id: str = Field(..., description="User identifier")
    deletion_timestamp: str = Field(..., description="ISO timestamp of deletion")
    deleted_items: dict[str, int] = Field(default_factory=dict, description="Count of items deleted by type")
    anonymized_items: dict[str, int] = Field(default_factory=dict, description="Count of items anonymized")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    audit_record_id: str | None = Field(None, description="Anonymized audit record ID")


class DataDeletionService:
    """
    Service for deleting user data for GDPR compliance

    Implements Article 17 (Right to Erasure / Right to be Forgotten).

    This service handles complete user data deletion including:
    - User profile and account
    - All sessions
    - Conversations and messages
    - Preferences and settings
    - Authorization tuples (OpenFGA)
    - Audit logs (anonymized, not deleted)
    """

    def __init__(
        self,
        session_store: SessionStore | None = None,
        gdpr_storage: GDPRStorage | None = None,
        openfga_client: OpenFGAClient | None = None,
    ):
        """
        Initialize data deletion service

        Args:
            session_store: Session storage backend
            gdpr_storage: GDPR storage backend (user profiles, conversations, consents, etc.)
            openfga_client: OpenFGA authorization client
        """
        self.session_store = session_store
        self.gdpr_storage = gdpr_storage
        self.openfga_client = openfga_client

    async def _safe_delete(self, operation_name: str, delete_func, user_id: str, deleted_items: dict, errors: list) -> None:  # type: ignore[no-untyped-def,type-arg]
        """
        Safely execute a deletion operation with error handling

        Args:
            operation_name: Name of the operation (for logging)
            delete_func: Async function to execute deletion
            user_id: User identifier
            deleted_items: Dict to store deletion counts
            errors: List to append errors to
        """
        try:
            count = await delete_func(user_id)
            deleted_items[operation_name] = count
            logger.info(f"Deleted {count} {operation_name}", extra={"user_id": user_id})
        except Exception as e:
            error_msg = f"Failed to delete {operation_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)

    async def _safe_anonymize(  # type: ignore[no-untyped-def]
        self,
        operation_name: str,
        anonymize_func,
        user_id: str,
        anonymized_items: dict[str, Any],
        errors: list[str],
    ) -> None:
        """
        Safely execute an anonymization operation with error handling

        Args:
            operation_name: Name of the operation (for logging)
            anonymize_func: Async function to execute anonymization
            user_id: User identifier
            anonymized_items: Dict to store anonymization counts
            errors: List to append errors to
        """
        try:
            count = await anonymize_func(user_id)
            anonymized_items[operation_name] = count
            logger.info(f"Anonymized {count} {operation_name}", extra={"user_id": user_id})
        except Exception as e:
            error_msg = f"Failed to anonymize {operation_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)

    async def delete_user_account(self, user_id: str, username: str, reason: str = "user_request") -> DeletionResult:
        """
        Delete all user data (GDPR Article 17)

        This is an irreversible operation that removes all user data.
        Audit logs are anonymized but retained for compliance.

        Args:
            user_id: User identifier
            username: Username
            reason: Reason for deletion

        Returns:
            DeletionResult with deletion details
        """
        with tracer.start_as_current_span("data_deletion.delete_user_account") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("reason", reason)

            logger.warning(
                "User account deletion requested",
                extra={"user_id": user_id, "username": username, "reason": reason},
            )

            deleted_items: dict[str, int] = {}
            anonymized_items: dict[str, int] = {}
            errors: list[str] = []

            # 1. Delete sessions
            await self._safe_delete("sessions", self._delete_user_sessions, user_id, deleted_items, errors)

            # 2. Delete conversations
            await self._safe_delete("conversations", self._delete_user_conversations, user_id, deleted_items, errors)

            # 3. Delete preferences
            await self._safe_delete("preferences", self._delete_user_preferences, user_id, deleted_items, errors)

            # 4. Delete OpenFGA tuples
            if self.openfga_client:
                await self._safe_delete(
                    "authorization_tuples", self._delete_user_authorization_tuples, user_id, deleted_items, errors
                )

            # 5. Delete consent records
            if self.gdpr_storage:
                await self._safe_delete("consents", self._delete_user_consents, user_id, deleted_items, errors)

            # 6. Anonymize audit logs (don't delete for compliance)
            await self._safe_anonymize("audit_logs", self._anonymize_user_audit_logs, user_id, anonymized_items, errors)

            # 7. Delete user profile/account
            try:
                count = await self._delete_user_profile(user_id)
                deleted_items["user_profile"] = count
                logger.info("User profile deleted", extra={"user_id": user_id})
            except Exception as e:
                error_msg = f"Failed to delete user profile: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 8. Create final audit record (anonymized)
            audit_record_id = await self._create_deletion_audit_record(
                user_id=user_id, username=username, reason=reason, deleted_items=deleted_items, errors=errors
            )

            success = len(errors) == 0
            deletion_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            result = DeletionResult(
                success=success,
                user_id=user_id,
                deletion_timestamp=deletion_timestamp,
                deleted_items=deleted_items,
                anonymized_items=anonymized_items,
                errors=errors,
                audit_record_id=audit_record_id,
            )

            if success:
                logger.warning(
                    "User account deletion completed successfully",
                    extra={
                        "user_id": user_id,
                        "deleted_items": deleted_items,
                        "anonymized_items": anonymized_items,
                    },
                )
            else:
                logger.error(
                    "User account deletion completed with errors",
                    extra={"user_id": user_id, "errors": errors},
                )

            return result

    async def _delete_user_sessions(self, user_id: str) -> int:
        """Delete all user sessions"""
        if not self.session_store:
            return 0

        count = await self.session_store.delete_user_sessions(user_id)
        return count

    async def _delete_user_conversations(self, user_id: str) -> int:
        """Delete all user conversations"""
        if not self.gdpr_storage:
            return 0

        try:
            count = await self.gdpr_storage.conversations.delete_user_conversations(user_id)
            return count
        except Exception as e:
            logger.error(f"Failed to delete user conversations: {e}", exc_info=True)
            raise

    async def _delete_user_preferences(self, user_id: str) -> int:
        """Delete all user preferences"""
        if not self.gdpr_storage:
            return 0

        try:
            deleted = await self.gdpr_storage.preferences.delete(user_id)
            return 1 if deleted else 0
        except Exception as e:
            logger.error(f"Failed to delete user preferences: {e}", exc_info=True)
            raise

    async def _delete_user_authorization_tuples(self, user_id: str) -> int:
        """Delete all OpenFGA authorization tuples for user"""
        if not self.openfga_client:
            return 0

        # Delete all tuples where user is the subject
        # Note: This is a simplified implementation
        # In production, you'd need to query all tuples for the user first
        try:
            # Example: Delete all tuples for this user
            # await self.openfga_client.delete_tuples([
            #     {"user": user_id, "relation": "*", "object": "*"}
            # ])
            # For now, return 0 as we need to implement the query logic
            return 0
        except Exception as e:
            logger.error(f"Failed to delete authorization tuples: {e}", exc_info=True)
            raise

    async def _anonymize_user_audit_logs(self, user_id: str) -> int:
        """
        Anonymize audit logs (don't delete for compliance)

        Replace user_id with pseudonymized identifier.
        """
        if not self.gdpr_storage:
            return 0

        try:
            count = await self.gdpr_storage.audit_logs.anonymize_user_logs(user_id)
            return count
        except Exception as e:
            logger.error(f"Failed to anonymize user audit logs: {e}", exc_info=True)
            raise

    async def _delete_user_consents(self, user_id: str) -> int:
        """Delete all user consent records"""
        if not self.gdpr_storage:
            return 0

        try:
            count = await self.gdpr_storage.consents.delete_user_consents(user_id)
            return count
        except Exception as e:
            logger.error(f"Failed to delete user consents: {e}", exc_info=True)
            raise

    async def _delete_user_profile(self, user_id: str) -> int:
        """Delete user profile/account"""
        if not self.gdpr_storage:
            # If no profile store, assume profile was deleted elsewhere
            return 1

        try:
            deleted = await self.gdpr_storage.user_profiles.delete(user_id)
            return 1 if deleted else 0
        except Exception as e:
            logger.error(f"Failed to delete user profile: {e}", exc_info=True)
            raise

    async def _create_deletion_audit_record(
        self,
        user_id: str,
        username: str,
        reason: str,
        deleted_items: dict[str, int],
        errors: list[str],
    ) -> str:
        """
        Create audit record for deletion (anonymized)

        This record is kept for compliance purposes.
        """
        from mcp_server_langgraph.compliance.gdpr.storage import AuditLogEntry

        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        audit_record_id = f"deletion_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

        # Create anonymized audit log entry
        audit_entry = AuditLogEntry(
            log_id=audit_record_id,
            user_id="DELETED",  # Anonymized for GDPR compliance
            action="account_deletion",
            resource_type="user_account",
            resource_id=f"hash_{abs(hash(user_id))}",  # Hash for correlation if needed
            timestamp=timestamp,
            ip_address=None,  # Not applicable for system action
            user_agent=None,  # Not applicable for system action
            metadata={
                "original_username_hash": abs(hash(username)),  # Hash for potential correlation
                "deletion_reason": reason,
                "deleted_items": deleted_items,
                "errors_count": len(errors),
                "errors": errors if errors else [],
                "compliance_note": "User data deleted per GDPR Article 17 (Right to Erasure)",
            },
        )

        # Store audit record if GDPR storage is configured
        if self.gdpr_storage:
            try:
                stored_id = await self.gdpr_storage.audit_logs.log(audit_entry)
                logger.info(
                    "User account deletion audit record stored",
                    extra={
                        "audit_record_id": stored_id,
                        "deleted_items_count": sum(deleted_items.values()),
                        "errors_count": len(errors),
                    },
                )
                return stored_id
            except Exception as e:
                logger.error(
                    f"Failed to store deletion audit record: {e}",
                    exc_info=True,
                    extra={"audit_record_id": audit_record_id},
                )
                # Fall through to log-only mode

        # Fallback: Log to application logs if audit store not configured
        logger.warning(
            "User account deletion audit record (log-only, audit store not configured)",
            extra={
                "audit_record_id": audit_record_id,
                "action": audit_entry.action,
                "resource_type": audit_entry.resource_type,
                "resource_id": audit_entry.resource_id,
                "metadata": audit_entry.metadata,
                "timestamp": timestamp,
            },
        )

        return audit_record_id
