"""
PostgreSQL Storage Implementation for GDPR/HIPAA/SOC2 Compliance

Implements persistent storage for:
- User profiles
- User preferences
- Consent records (7-year retention)
- Conversations (90-day retention)
- Audit logs (7-year retention)

Compliance Requirements:
- GDPR Articles 5, 15, 17 (retention, access, erasure)
- HIPAA §164.312(b), §164.316(b)(2)(i) (audit controls, 7-year retention)
- SOC2 CC6.6, PI1.4 (audit logs, data retention)

Design: Pure PostgreSQL (not hybrid) for:
- Simplicity (one source of truth)
- ACID guarantees (atomic GDPR operations)
- Cost efficiency (14x cheaper than Redis for 7-year data)
- Compliance auditing (single system to audit)
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import asyncpg

from mcp_server_langgraph.compliance.gdpr.storage import (
    AuditLogEntry,
    AuditLogStore,
    ConsentRecord,
    ConsentStore,
    Conversation,
    ConversationStore,
    PreferencesStore,
    UserPreferences,
    UserProfile,
    UserProfileStore,
)

# ============================================================================
# PostgreSQL User Profile Store
# ============================================================================


class PostgresUserProfileStore(UserProfileStore):
    """
    PostgreSQL implementation of user profile storage

    GDPR Compliance:
    - Article 15: Right to access (get method)
    - Article 17: Right to erasure (delete method)
    - Automatic last_updated timestamp via trigger
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize PostgreSQL user profile store

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def create(self, profile: UserProfile) -> bool:
        """
        Create a new user profile

        Args:
            profile: User profile to create

        Returns:
            True if created successfully, False if user already exists
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO user_profiles
                    (user_id, username, email, full_name, created_at, last_updated, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    profile.user_id,
                    profile.username,
                    profile.email,
                    profile.full_name,
                    profile.created_at,
                    profile.last_updated,
                    json.dumps(profile.metadata),
                )
                return True
        except asyncpg.UniqueViolationError:
            # User already exists
            return False

    async def get(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile by ID (GDPR Article 15 - Right to access)

        Args:
            user_id: User identifier

        Returns:
            User profile if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, username, email, full_name, created_at, last_updated, metadata
                FROM user_profiles
                WHERE user_id = $1
                """,
                user_id,
            )

            if row is None:
                return None

            return UserProfile(
                user_id=row["user_id"],
                username=row["username"],
                email=row["email"],
                full_name=row["full_name"],
                created_at=row["created_at"].isoformat().replace("+00:00", "Z"),
                last_updated=row["last_updated"].isoformat().replace("+00:00", "Z"),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

    async def update(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update user profile

        Args:
            user_id: User identifier
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully, False if user not found

        Note:
            last_updated is automatically updated by database trigger
        """
        # Build SET clause dynamically
        set_clauses = []
        values = []
        param_num = 1

        for key, value in updates.items():
            if key in ["email", "full_name", "username"]:
                set_clauses.append(f"{key} = ${param_num}")
                values.append(value)
                param_num += 1
            elif key == "metadata":
                set_clauses.append(f"metadata = ${param_num}")
                values.append(json.dumps(value))
                param_num += 1

        if not set_clauses:
            return False

        # Add user_id as final parameter
        values.append(user_id)

        # SECURITY: Safe from SQL injection because:
        # 1. Field names are validated against allowlist (lines 150-157)
        # 2. All values are passed as parameterized queries ($1, $2, etc.) via *values
        # 3. Only SQL structure (not data) is constructed via f-string
        # SET clause is built from validated field names, values are passed as parameters
        query = f"""
            UPDATE user_profiles
            SET {', '.join(set_clauses)}
            WHERE user_id = ${param_num}
        """  # nosec B608 - See security comment above

        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *values)
            # Check if any rows were updated (result is "UPDATE N")
            row_count: str = result.split()[-1]
            return row_count == "1"

    async def delete(self, user_id: str) -> bool:
        """
        Delete user profile (GDPR Article 17 - Right to erasure)

        Args:
            user_id: User identifier

        Returns:
            True if deleted successfully, False if user not found

        Note:
            Cascades to preferences, conversations, consents via foreign key
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_profiles WHERE user_id = $1",
                user_id,
            )
            # Check if any rows were deleted (result is "DELETE N")
            row_count: str = result.split()[-1]
            return row_count == "1"


# ============================================================================
# PostgreSQL Preferences Store
# ============================================================================


class PostgresPreferencesStore(PreferencesStore):
    """
    PostgreSQL implementation of user preferences storage

    Features:
    - UPSERT (INSERT ... ON CONFLICT UPDATE) for set operations
    - JSON merge for partial updates
    - Automatic updated_at timestamp via trigger
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize PostgreSQL preferences store

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def get(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, preferences, updated_at
                FROM user_preferences
                WHERE user_id = $1
                """,
                user_id,
            )

            if row is None:
                return None

            return UserPreferences(
                user_id=row["user_id"],
                preferences=json.loads(row["preferences"]) if row["preferences"] else {},
                updated_at=row["updated_at"].isoformat().replace("+00:00", "Z"),
            )

    async def set(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Set user preferences (UPSERT - insert or replace)

        Args:
            user_id: User identifier
            preferences: Preferences dictionary

        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_preferences (user_id, preferences, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    preferences = EXCLUDED.preferences,
                    updated_at = EXCLUDED.updated_at
                """,
                user_id,
                json.dumps(preferences),
                now,
            )
            return True

    async def update(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific preferences (merge with existing)

        Args:
            user_id: User identifier
            updates: Partial preferences to update

        Returns:
            True if successful, False if user has no preferences
        """
        # Get existing preferences
        existing = await self.get(user_id)
        if existing is None:
            return False

        # Merge updates
        merged = {**existing.preferences, **updates}

        # Set merged preferences
        return await self.set(user_id, merged)

    async def delete(self, user_id: str) -> bool:
        """Delete user preferences"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_preferences WHERE user_id = $1",
                user_id,
            )
            row_count: str = result.split()[-1]
            return row_count == "1"


# ============================================================================
# PostgreSQL Consent Store
# ============================================================================


class PostgresConsentStore(ConsentStore):
    """
    PostgreSQL implementation of consent record storage

    GDPR Article 7: Conditions for consent
    - Immutable consent records (append-only audit trail)
    - 7-year retention requirement
    - Latest consent determines current status
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize PostgreSQL consent store

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def create(self, record: ConsentRecord) -> str:
        """
        Create a consent record (append-only for audit trail)

        Args:
            record: Consent record to create

        Returns:
            consent_id of created record
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO consent_records
                (consent_id, user_id, consent_type, granted, timestamp, ip_address, user_agent, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                record.consent_id,
                record.user_id,
                record.consent_type,
                record.granted,
                record.timestamp,
                record.ip_address,
                record.user_agent,
                json.dumps(record.metadata),
            )
            return record.consent_id

    async def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """
        Get all consent records for a user (entire audit trail)

        Args:
            user_id: User identifier

        Returns:
            List of all consent records, ordered by timestamp descending
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT consent_id, user_id, consent_type, granted, timestamp, ip_address, user_agent, metadata
                FROM consent_records
                WHERE user_id = $1
                ORDER BY timestamp DESC
                """,
                user_id,
            )

            return [
                ConsentRecord(
                    consent_id=row["consent_id"],
                    user_id=row["user_id"],
                    consent_type=row["consent_type"],
                    granted=row["granted"],
                    timestamp=row["timestamp"].isoformat().replace("+00:00", "Z"),
                    ip_address=row["ip_address"],
                    user_agent=row["user_agent"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                for row in rows
            ]

    async def get_latest_consent(self, user_id: str, consent_type: str) -> Optional[ConsentRecord]:
        """
        Get the latest consent record for a specific type

        Args:
            user_id: User identifier
            consent_type: Type of consent (analytics, marketing, etc.)

        Returns:
            Latest consent record if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT consent_id, user_id, consent_type, granted, timestamp, ip_address, user_agent, metadata
                FROM consent_records
                WHERE user_id = $1 AND consent_type = $2
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                user_id,
                consent_type,
            )

            if row is None:
                return None

            return ConsentRecord(
                consent_id=row["consent_id"],
                user_id=row["user_id"],
                consent_type=row["consent_type"],
                granted=row["granted"],
                timestamp=row["timestamp"].isoformat().replace("+00:00", "Z"),
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

    async def delete_user_consents(self, user_id: str) -> int:
        """
        Delete all consent records for a user

        Note: Normally consents are kept for 7 years even after user deletion
        This is only for GDPR Right to Erasure in special cases

        Args:
            user_id: User identifier

        Returns:
            Number of consent records deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM consent_records WHERE user_id = $1",
                user_id,
            )
            return int(result.split()[-1])


# ============================================================================
# PostgreSQL Conversation Store
# ============================================================================


class PostgresConversationStore(ConversationStore):
    """
    PostgreSQL implementation of conversation storage

    GDPR Article 5(1)(e): Storage limitation (90-day retention)
    - Messages stored as JSONB array
    - Automatic cleanup view for retention enforcement
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize PostgreSQL conversation store

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def create(self, conversation: Conversation) -> str:
        """Create a new conversation"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations
                (conversation_id, user_id, title, messages, created_at, last_message_at, archived, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                conversation.conversation_id,
                conversation.user_id,
                conversation.title,
                json.dumps(conversation.messages),
                conversation.created_at,
                conversation.last_message_at,
                conversation.archived,
                json.dumps(conversation.metadata),
            )
            return conversation.conversation_id

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT conversation_id, user_id, title, messages, created_at, last_message_at, archived, metadata
                FROM conversations
                WHERE conversation_id = $1
                """,
                conversation_id,
            )

            if row is None:
                return None

            return Conversation(
                conversation_id=row["conversation_id"],
                user_id=row["user_id"],
                title=row["title"],
                messages=json.loads(row["messages"]) if row["messages"] else [],
                created_at=row["created_at"].isoformat().replace("+00:00", "Z"),
                last_message_at=row["last_message_at"].isoformat().replace("+00:00", "Z"),
                archived=row["archived"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

    async def list_user_conversations(self, user_id: str, archived: Optional[bool] = None) -> List[Conversation]:
        """
        List all conversations for a user

        Args:
            user_id: User identifier
            archived: Filter by archived status (None = all, True = archived only, False = active only)

        Returns:
            List of conversations ordered by last_message_at descending
        """
        if archived is None:
            query = """
                SELECT conversation_id, user_id, title, messages, created_at, last_message_at, archived, metadata
                FROM conversations
                WHERE user_id = $1
                ORDER BY last_message_at DESC NULLS LAST
            """
            params: List[Union[str, bool]] = [user_id]
        else:
            query = """
                SELECT conversation_id, user_id, title, messages, created_at, last_message_at, archived, metadata
                FROM conversations
                WHERE user_id = $1 AND archived = $2
                ORDER BY last_message_at DESC NULLS LAST
            """
            params = [user_id, archived]

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            return [
                Conversation(
                    conversation_id=row["conversation_id"],
                    user_id=row["user_id"],
                    title=row["title"],
                    messages=json.loads(row["messages"]) if row["messages"] else [],
                    created_at=row["created_at"].isoformat().replace("+00:00", "Z"),
                    last_message_at=row["last_message_at"].isoformat().replace("+00:00", "Z"),
                    archived=row["archived"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                for row in rows
            ]

    async def update(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update conversation

        Args:
            conversation_id: Conversation identifier
            updates: Dictionary of fields to update (title, messages, archived, last_message_at, metadata)

        Returns:
            True if updated, False if not found
        """
        set_clauses = []
        values = []
        param_num = 1

        for key, value in updates.items():
            if key in ["title", "last_message_at", "archived"]:
                set_clauses.append(f"{key} = ${param_num}")
                values.append(value)
                param_num += 1
            elif key in ["messages", "metadata"]:
                set_clauses.append(f"{key} = ${param_num}")
                values.append(json.dumps(value))
                param_num += 1

        if not set_clauses:
            return False

        values.append(conversation_id)
        # SECURITY: Safe from SQL injection because:
        # 1. Field names are validated against allowlist (lines 584-595)
        # 2. All values are passed as parameterized queries ($1, $2, etc.) via *values
        # 3. Only SQL structure (not data) is constructed via f-string
        # Parameterized query, field names validated, values as parameters
        query = f"""  # nosec B608 - See security comment above
            UPDATE conversations
            SET {', '.join(set_clauses)}
            WHERE conversation_id = ${param_num}
        """

        async with self.pool.acquire() as conn:
            result = await conn.execute(query, *values)
            row_count: str = result.split()[-1]
            return row_count == "1"

    async def delete(self, conversation_id: str) -> bool:
        """Delete conversation"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM conversations WHERE conversation_id = $1",
                conversation_id,
            )
            row_count: str = result.split()[-1]
            return row_count == "1"

    async def delete_user_conversations(self, user_id: str) -> int:
        """
        Delete all conversations for a user (GDPR Article 17)

        Args:
            user_id: User identifier

        Returns:
            Number of conversations deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM conversations WHERE user_id = $1",
                user_id,
            )
            return int(result.split()[-1])


# ============================================================================
# PostgreSQL Audit Log Store
# ============================================================================


class PostgresAuditLogStore(AuditLogStore):
    """
    PostgreSQL implementation of audit log storage

    HIPAA §164.312(b): Audit controls (7-year retention)
    SOC2 CC6.6: Audit logging and monitoring

    Features:
    - Immutable (append-only) audit trail
    - Anonymization support for GDPR Article 17
    - Time-series queries with optimized indexes
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize PostgreSQL audit log store

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def log(self, entry: AuditLogEntry) -> str:
        """
        Log an audit entry (append-only for compliance)

        Args:
            entry: Audit log entry to create

        Returns:
            log_id of created entry
        """
        # Handle empty user_id (system events)
        user_id = entry.user_id if entry.user_id else None

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_logs
                (log_id, user_id, action, resource_type, resource_id, timestamp, ip_address, user_agent, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                entry.log_id,
                user_id,
                entry.action,
                entry.resource_type,
                entry.resource_id,
                entry.timestamp,
                entry.ip_address,
                entry.user_agent,
                json.dumps(entry.metadata),
            )
            return entry.log_id

    async def get(self, log_id: str) -> Optional[AuditLogEntry]:
        """Get audit log entry by ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT log_id, user_id, action, resource_type, resource_id, timestamp, ip_address, user_agent, metadata
                FROM audit_logs
                WHERE log_id = $1
                """,
                log_id,
            )

            if row is None:
                return None

            return AuditLogEntry(
                log_id=row["log_id"],
                user_id=row["user_id"] or "",
                action=row["action"],
                resource_type=row["resource_type"] or "",
                resource_id=row["resource_id"],
                timestamp=row["timestamp"].isoformat().replace("+00:00", "Z"),
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )

    async def list_user_logs(
        self, user_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        List audit logs for a user (HIPAA/SOC2 compliance queries)

        Args:
            user_id: User identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries ordered by timestamp descending
        """
        # Build query dynamically based on filters
        conditions = ["user_id = $1"]
        params: List[Union[str, datetime, int]] = [user_id]
        param_num = 2

        if start_date is not None:
            conditions.append(f"timestamp >= ${param_num}")
            params.append(start_date)
            param_num += 1

        if end_date is not None:
            conditions.append(f"timestamp <= ${param_num}")
            params.append(end_date)
            param_num += 1

        # SECURITY: Safe from SQL injection because:
        # 1. WHERE conditions are built programmatically (not from user input) with fixed field names
        # 2. All values are passed as parameterized queries ($1, $2, etc.) via params list
        # 3. Only SQL structure (not data) is constructed via f-string
        # Parameterized query with validated conditions and parameter placeholders
        query = f"""  # nosec B608 - See security comment above
            SELECT log_id, user_id, action, resource_type, resource_id, timestamp, ip_address, user_agent, metadata
            FROM audit_logs
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
            LIMIT ${param_num}
        """
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            return [
                AuditLogEntry(
                    log_id=row["log_id"],
                    user_id=row["user_id"] or "",
                    action=row["action"],
                    resource_type=row["resource_type"] or "",
                    resource_id=row["resource_id"],
                    timestamp=row["timestamp"].isoformat().replace("+00:00", "Z"),
                    ip_address=row["ip_address"],
                    user_agent=row["user_agent"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                for row in rows
            ]

    async def anonymize_user_logs(self, user_id: str) -> int:
        """
        Anonymize audit logs for a user (GDPR Article 17 - Right to Erasure)

        Preserves audit trail for compliance while removing user identification.
        Logs are kept for 7 years (HIPAA/SOC2) but user_id is anonymized.

        Args:
            user_id: User identifier to anonymize

        Returns:
            Number of audit logs anonymized
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE audit_logs
                SET user_id = 'anonymized'
                WHERE user_id = $1
                """,
                user_id,
            )
            return int(result.split()[-1])
