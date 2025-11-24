"""
GDPR Data Export Service - Article 15 (Right to Access) & Article 20 (Data Portability)
"""

import csv
import io
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.auth.session import SessionStore
from mcp_server_langgraph.compliance.gdpr.factory import GDPRStorage
from mcp_server_langgraph.observability.telemetry import logger, tracer


class UserDataExport(BaseModel):
    """
    Complete user data export for GDPR compliance

    Includes all personal data associated with a user.
    """

    export_id: str = Field(..., description="Unique export identifier")
    export_timestamp: str = Field(..., description="ISO timestamp of export")
    user_id: str = Field(..., description="User identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email address")
    profile: dict[str, Any] = Field(default_factory=dict, description="User profile data")
    sessions: list[dict[str, Any]] = Field(default_factory=list, description="Active and recent sessions")
    conversations: list[dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    preferences: dict[str, Any] = Field(default_factory=dict, description="User preferences and settings")
    audit_log: list[dict[str, Any]] = Field(default_factory=list, description="User activity audit log")
    consents: list[dict[str, Any]] = Field(default_factory=list, description="Consent records")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "export_id": "exp_20250101120000_user123",
                "export_timestamp": "2025-01-01T12:00:00Z",
                "user_id": "user:alice",
                "username": "alice",
                "email": "alice@acme.com",
                "profile": {"name": "Alice", "created_at": "2024-01-01"},
                "sessions": [{"session_id": "sess_123", "created_at": "2025-01-01T10:00:00Z"}],
                "conversations": [],
                "preferences": {"theme": "dark"},
                "audit_log": [],
                "consents": [],
            }
        }
    )


class DataExportService:
    """
    Service for exporting user data for GDPR compliance

    Implements Article 15 (Right to Access) and Article 20 (Data Portability).
    """

    def __init__(
        self,
        session_store: SessionStore | None = None,
        gdpr_storage: GDPRStorage | None = None,
    ):
        """
        Initialize data export service

        Args:
            session_store: Session storage backend
            gdpr_storage: GDPR storage backend (user profiles, conversations, consents, etc.)
        """
        self.session_store = session_store
        self.gdpr_storage = gdpr_storage

    async def export_user_data(self, user_id: str, username: str, email: str) -> UserDataExport:
        """
        Export all data for a user (GDPR Article 15)

        Args:
            user_id: User identifier
            username: Username
            email: User email

        Returns:
            Complete user data export
        """
        with tracer.start_as_current_span("data_export.export_user_data") as span:
            span.set_attribute("user_id", user_id)

            export_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{user_id.replace(':', '_')}"

            logger.info("Starting user data export", extra={"user_id": user_id, "export_id": export_id})

            # Gather all user data
            profile = await self._get_user_profile(user_id)
            sessions = await self._get_user_sessions(user_id)
            conversations = await self._get_user_conversations(user_id)
            preferences = await self._get_user_preferences(user_id)
            audit_log = await self._get_user_audit_log(user_id)
            consents = await self._get_user_consents(user_id)

            export = UserDataExport(
                export_id=export_id,
                export_timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                user_id=user_id,
                username=username,
                email=email,
                profile=profile,
                sessions=sessions,
                conversations=conversations,
                preferences=preferences,
                audit_log=audit_log,
                consents=consents,
                metadata={"export_reason": "user_request", "gdpr_article": "15"},
            )

            logger.info(
                "User data export completed",
                extra={
                    "user_id": user_id,
                    "export_id": export_id,
                    "sessions_count": len(sessions),
                    "conversations_count": len(conversations),
                },
            )

            return export

    async def export_user_data_portable(
        self, user_id: str, username: str, email: str, format: str = "json"
    ) -> tuple[bytes, str]:
        """
        Export user data in portable format (GDPR Article 20)

        Args:
            user_id: User identifier
            username: Username
            email: User email
            format: Export format ('json' or 'csv')

        Returns:
            Tuple of (data_bytes, content_type)
        """
        with tracer.start_as_current_span("data_export.export_portable") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("format", format)

            export = await self.export_user_data(user_id, username, email)

            if format == "json":
                # JSON export (machine-readable)
                data = export.model_dump_json(indent=2).encode("utf-8")
                content_type = "application/json"

            elif format == "csv":
                # CSV export (human-readable)
                data = self._convert_to_csv(export)
                content_type = "text/csv"

            else:
                raise ValueError(f"Unsupported export format: {format}")

            logger.info(
                "Portable data export completed",
                extra={"user_id": user_id, "format": format, "size_bytes": len(data)},
            )

            return data, content_type

    def _convert_to_csv(self, export: UserDataExport) -> bytes:
        """Convert export data to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["Export Metadata"])
        writer.writerow(["Export ID", export.export_id])
        writer.writerow(["Export Timestamp", export.export_timestamp])
        writer.writerow(["User ID", export.user_id])
        writer.writerow(["Username", export.username])
        writer.writerow(["Email", export.email])
        writer.writerow([])

        # Write profile
        writer.writerow(["Profile"])
        writer.writerow(["Key", "Value"])
        for key, value in export.profile.items():
            writer.writerow([key, str(value)])
        writer.writerow([])

        # Write sessions
        writer.writerow(["Sessions"])
        if export.sessions:
            # Get all unique keys from sessions
            keys = set()  # type: ignore
            for session in export.sessions:
                keys.update(session.keys())
            writer.writerow(list(keys))
            for session in export.sessions:
                writer.writerow([session.get(key, "") for key in keys])
        else:
            writer.writerow(["No sessions found"])
        writer.writerow([])

        # Write conversations
        writer.writerow(["Conversations"])
        if export.conversations:
            keys = set()
            for conv in export.conversations:
                keys.update(conv.keys())
            writer.writerow(list(keys))
            for conv in export.conversations:
                writer.writerow([conv.get(key, "") for key in keys])
        else:
            writer.writerow(["No conversations found"])
        writer.writerow([])

        # Write preferences
        writer.writerow(["Preferences"])
        writer.writerow(["Key", "Value"])
        for key, value in export.preferences.items():
            writer.writerow([key, str(value)])
        writer.writerow([])

        # Write consents
        writer.writerow(["Consents"])
        if export.consents:
            keys = set()
            for consent in export.consents:
                keys.update(consent.keys())
            writer.writerow(list(keys))
            for consent in export.consents:
                writer.writerow([consent.get(key, "") for key in keys])
        else:
            writer.writerow(["No consent records found"])

        return output.getvalue().encode("utf-8")

    async def _get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Get user profile data"""
        if not self.gdpr_storage:
            # Return minimal data if no storage configured
            return {
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

        try:
            profile = await self.gdpr_storage.user_profiles.get(user_id)
            if profile:
                return profile.model_dump()
            else:
                # User exists but no profile data
                return {
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }
        except Exception as e:
            logger.error(f"Failed to retrieve user profile: {e}", exc_info=True)
            return {"user_id": user_id, "error": "Failed to retrieve profile"}

    async def _get_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """Get all user sessions"""
        if not self.session_store:
            return []

        try:
            sessions = await self.session_store.list_user_sessions(user_id)
            return [
                {
                    "session_id": s.session_id,
                    "username": s.username,
                    "roles": s.roles,
                    "created_at": s.created_at,
                    "last_accessed": s.last_accessed,
                    "expires_at": s.expires_at,
                    "metadata": s.metadata,
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve user sessions: {e}", exc_info=True)
            return []

    async def _get_user_conversations(self, user_id: str) -> list[dict[str, Any]]:
        """Get user conversation history"""
        if not self.gdpr_storage:
            return []

        try:
            conversations = await self.gdpr_storage.conversations.list_user_conversations(user_id)
            return [conv.model_dump() for conv in conversations]
        except Exception as e:
            logger.error(f"Failed to retrieve user conversations: {e}", exc_info=True)
            return []

    async def _get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user preferences"""
        if not self.gdpr_storage:
            return {}

        try:
            preferences = await self.gdpr_storage.preferences.get(user_id)
            if preferences:
                return preferences.preferences
            return {}
        except Exception as e:
            logger.error(f"Failed to retrieve user preferences: {e}", exc_info=True)
            return {}

    async def _get_user_audit_log(self, user_id: str) -> list[dict[str, Any]]:
        """Get user audit log entries"""
        if not self.gdpr_storage:
            return []

        try:
            logs = await self.gdpr_storage.audit_logs.list_user_logs(user_id, limit=1000)
            return [log.model_dump() for log in logs]
        except Exception as e:
            logger.error(f"Failed to retrieve user audit logs: {e}", exc_info=True)
            return []

    async def _get_user_consents(self, user_id: str) -> list[dict[str, Any]]:
        """Get user consent records"""
        if not self.gdpr_storage:
            return []

        try:
            consents = await self.gdpr_storage.consents.get_user_consents(user_id)
            return [consent.model_dump() for consent in consents]
        except Exception as e:
            logger.error(f"Failed to retrieve user consents: {e}", exc_info=True)
            return []
