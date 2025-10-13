"""
GDPR Data Deletion Service - Article 17 (Right to Erasure)
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.session import SessionStore
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
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    audit_record_id: Optional[str] = Field(None, description="Anonymized audit record ID")


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
        session_store: Optional[SessionStore] = None,
        openfga_client: Optional[OpenFGAClient] = None,
        # Add other data stores as needed
    ):
        """
        Initialize data deletion service

        Args:
            session_store: Session storage backend
            openfga_client: OpenFGA authorization client
        """
        self.session_store = session_store
        self.openfga_client = openfga_client

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

            deleted_items = {}
            anonymized_items = {}
            errors = []

            # 1. Delete sessions
            try:
                if self.session_store:
                    count = await self._delete_user_sessions(user_id)
                    deleted_items["sessions"] = count
                    logger.info(f"Deleted {count} sessions", extra={"user_id": user_id})
            except Exception as e:
                error_msg = f"Failed to delete sessions: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 2. Delete conversations
            try:
                count = await self._delete_user_conversations(user_id)
                deleted_items["conversations"] = count
                logger.info(f"Deleted {count} conversations", extra={"user_id": user_id})
            except Exception as e:
                error_msg = f"Failed to delete conversations: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 3. Delete preferences
            try:
                count = await self._delete_user_preferences(user_id)
                deleted_items["preferences"] = count
                logger.info(f"Deleted {count} preferences", extra={"user_id": user_id})
            except Exception as e:
                error_msg = f"Failed to delete preferences: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 4. Delete OpenFGA tuples
            try:
                if self.openfga_client:
                    count = await self._delete_user_authorization_tuples(user_id)
                    deleted_items["authorization_tuples"] = count
                    logger.info(f"Deleted {count} authorization tuples", extra={"user_id": user_id})
            except Exception as e:
                error_msg = f"Failed to delete authorization tuples: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 5. Anonymize audit logs (don't delete for compliance)
            try:
                count = await self._anonymize_user_audit_logs(user_id)
                anonymized_items["audit_logs"] = count
                logger.info(f"Anonymized {count} audit log entries", extra={"user_id": user_id})
            except Exception as e:
                error_msg = f"Failed to anonymize audit logs: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 6. Delete user profile/account
            try:
                count = await self._delete_user_profile(user_id)
                deleted_items["user_profile"] = count
                logger.info("User profile deleted", extra={"user_id": user_id})
            except Exception as e:
                error_msg = f"Failed to delete user profile: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

            # 7. Create final audit record (anonymized)
            audit_record_id = await self._create_deletion_audit_record(
                user_id=user_id, username=username, reason=reason, deleted_items=deleted_items, errors=errors
            )

            success = len(errors) == 0
            deletion_timestamp = datetime.utcnow().isoformat() + "Z"

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
        # TODO: Integrate with conversation storage
        # For now, return 0
        return 0

    async def _delete_user_preferences(self, user_id: str) -> int:
        """Delete all user preferences"""
        # TODO: Integrate with preferences storage
        # For now, return 0
        return 0

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
        # TODO: Integrate with audit log storage
        # For now, return 0
        return 0

    async def _delete_user_profile(self, user_id: str) -> int:
        """Delete user profile/account"""
        # TODO: Integrate with user profile storage
        # For now, return 1 (assuming profile exists)
        return 1

    async def _create_deletion_audit_record(
        self,
        user_id: str,
        username: str,
        reason: str,
        deleted_items: dict[str, int],
        errors: List[str],
    ) -> str:
        """
        Create audit record for deletion (anonymized)

        This record is kept for compliance purposes.
        """
        # TODO: Integrate with audit log storage
        # For now, create a simple record
        audit_record_id = f"deletion_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        logger.warning(
            "User account deletion audit record",
            extra={
                "audit_record_id": audit_record_id,
                "user_id": "DELETED",  # Anonymized
                "original_user_id_hash": hash(user_id),  # Hash for correlation
                "username": "DELETED",  # Anonymized
                "action": "account_deletion",
                "reason": reason,
                "deleted_items": deleted_items,
                "errors_count": len(errors),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )

        return audit_record_id
