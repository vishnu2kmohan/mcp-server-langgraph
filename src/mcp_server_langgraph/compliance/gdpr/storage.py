"""
Storage Backend Interfaces for Compliance Data

Provides abstract interfaces for storing compliance-related data:
- User profiles
- Conversations
- Preferences
- Audit logs
- Consent records

Implementations can be backed by:
- PostgreSQL
- MongoDB
- Redis
- File system
- In-memory (for testing)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Data Models
# ============================================================================


class UserProfile(BaseModel):
    """User profile data model"""

    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: str | None = Field(None, description="Full name")
    created_at: str = Field(..., description="Account creation timestamp (ISO format)")
    last_updated: str = Field(..., description="Last update timestamp (ISO format)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional profile data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user:alice",
                "username": "alice",
                "email": "alice@acme.com",
                "full_name": "Alice Smith",
                "created_at": "2025-01-01T00:00:00Z",
                "last_updated": "2025-01-01T00:00:00Z",
                "metadata": {"department": "Engineering"},
            }
        }
    )


class Conversation(BaseModel):
    """Conversation data model"""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    user_id: str = Field(..., description="User who owns this conversation")
    title: str | None = Field(None, description="Conversation title")
    messages: list[dict[str, Any]] = Field(default_factory=list, description="List of messages")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    last_message_at: str = Field(..., description="Last message timestamp (ISO format)")
    archived: bool = Field(default=False, description="Whether conversation is archived")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "conv_123",
                "user_id": "user:alice",
                "title": "Project Discussion",
                "messages": [{"role": "user", "content": "Hello"}],
                "created_at": "2025-01-01T00:00:00Z",
                "last_message_at": "2025-01-01T00:05:00Z",
                "archived": False,
                "metadata": {},
            }
        }
    )


class UserPreferences(BaseModel):
    """User preferences data model"""

    user_id: str = Field(..., description="User identifier")
    preferences: dict[str, Any] = Field(default_factory=dict, description="User preferences")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user:alice",
                "preferences": {"theme": "dark", "language": "en", "notifications": {"email": True, "sms": False}},
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }
    )


class AuditLogEntry(BaseModel):
    """Audit log entry data model"""

    log_id: str = Field(..., description="Unique log entry identifier")
    user_id: str = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: str | None = Field(None, description="Identifier of resource affected")
    timestamp: str = Field(..., description="Action timestamp (ISO format)")
    ip_address: str | None = Field(None, description="IP address of request")
    user_agent: str | None = Field(None, description="User agent string")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "log_id": "log_123",
                "user_id": "user:alice",
                "action": "profile.update",
                "resource_type": "user_profile",
                "resource_id": "user:alice",
                "timestamp": "2025-01-01T00:00:00Z",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "metadata": {"fields_updated": ["email"]},
            }
        }
    )


class ConsentRecord(BaseModel):
    """Consent record data model"""

    consent_id: str = Field(..., description="Unique consent record identifier")
    user_id: str = Field(..., description="User identifier")
    consent_type: str = Field(..., description="Type of consent (analytics, marketing, etc.)")
    granted: bool = Field(..., description="Whether consent is granted")
    timestamp: str = Field(..., description="Consent timestamp (ISO format)")
    ip_address: str | None = Field(None, description="IP address when consent was given")
    user_agent: str | None = Field(None, description="User agent when consent was given")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "consent_id": "consent_123",
                "user_id": "user:alice",
                "consent_type": "analytics",
                "granted": True,
                "timestamp": "2025-01-01T00:00:00Z",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "metadata": {},
            }
        }
    )


# ============================================================================
# Storage Interfaces
# ============================================================================


class UserProfileStore(ABC):
    """Abstract interface for user profile storage"""

    @abstractmethod
    async def create(self, profile: UserProfile) -> bool:
        """Create a new user profile"""

    @abstractmethod
    async def get(self, user_id: str) -> UserProfile | None:
        """Get user profile by ID"""

    @abstractmethod
    async def update(self, user_id: str, updates: dict[str, Any]) -> bool:
        """Update user profile"""

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete user profile"""


class ConversationStore(ABC):
    """Abstract interface for conversation storage"""

    @abstractmethod
    async def create(self, conversation: Conversation) -> str:
        """Create a new conversation and return its ID"""

    @abstractmethod
    async def get(self, conversation_id: str) -> Conversation | None:
        """Get conversation by ID"""

    @abstractmethod
    async def list_user_conversations(self, user_id: str, archived: bool | None = None) -> list[Conversation]:
        """List all conversations for a user"""

    @abstractmethod
    async def update(self, conversation_id: str, updates: dict[str, Any]) -> bool:
        """Update conversation"""

    @abstractmethod
    async def delete(self, conversation_id: str) -> bool:
        """Delete conversation"""

    @abstractmethod
    async def delete_user_conversations(self, user_id: str) -> int:
        """Delete all conversations for a user"""


class PreferencesStore(ABC):
    """Abstract interface for user preferences storage"""

    @abstractmethod
    async def get(self, user_id: str) -> UserPreferences | None:
        """Get user preferences"""

    @abstractmethod
    async def set(self, user_id: str, preferences: dict[str, Any]) -> bool:
        """Set user preferences"""

    @abstractmethod
    async def update(self, user_id: str, updates: dict[str, Any]) -> bool:
        """Update specific preferences"""

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        """Delete user preferences"""


class AuditLogStore(ABC):
    """Abstract interface for audit log storage"""

    @abstractmethod
    async def log(self, entry: AuditLogEntry) -> str:
        """Log an audit entry and return its ID"""

    @abstractmethod
    async def get(self, log_id: str) -> AuditLogEntry | None:
        """Get audit log entry by ID"""

    @abstractmethod
    async def list_user_logs(
        self, user_id: str, start_date: datetime | None = None, end_date: datetime | None = None, limit: int = 100
    ) -> list[AuditLogEntry]:
        """List audit logs for a user"""

    @abstractmethod
    async def anonymize_user_logs(self, user_id: str) -> int:
        """Anonymize audit logs for a user (GDPR compliance)"""


class ConsentStore(ABC):
    """Abstract interface for consent record storage"""

    @abstractmethod
    async def create(self, record: ConsentRecord) -> str:
        """Create a consent record and return its ID"""

    @abstractmethod
    async def get_user_consents(self, user_id: str) -> list[ConsentRecord]:
        """Get all consent records for a user"""

    @abstractmethod
    async def get_latest_consent(self, user_id: str, consent_type: str) -> ConsentRecord | None:
        """Get the latest consent record for a specific type"""

    @abstractmethod
    async def delete_user_consents(self, user_id: str) -> int:
        """Delete all consent records for a user"""


# ============================================================================
# In-Memory Implementations (for testing/development)
# ============================================================================


class InMemoryUserProfileStore(UserProfileStore):
    """In-memory implementation of user profile storage"""

    def __init__(self) -> None:
        self.profiles: dict[str, UserProfile] = {}

    async def create(self, profile: UserProfile) -> bool:
        if profile.user_id in self.profiles:
            return False
        self.profiles[profile.user_id] = profile
        return True

    async def get(self, user_id: str) -> UserProfile | None:
        return self.profiles.get(user_id)

    async def update(self, user_id: str, updates: dict[str, Any]) -> bool:
        if user_id not in self.profiles:
            return False

        profile = self.profiles[user_id]
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return True

    async def delete(self, user_id: str) -> bool:
        if user_id in self.profiles:
            del self.profiles[user_id]
            return True
        return False


class InMemoryConversationStore(ConversationStore):
    """In-memory implementation of conversation storage"""

    def __init__(self) -> None:
        self.conversations: dict[str, Conversation] = {}
        self.user_conversations: dict[str, list[str]] = {}

    async def create(self, conversation: Conversation) -> str:
        self.conversations[conversation.conversation_id] = conversation

        if conversation.user_id not in self.user_conversations:
            self.user_conversations[conversation.user_id] = []
        self.user_conversations[conversation.user_id].append(conversation.conversation_id)

        return conversation.conversation_id

    async def get(self, conversation_id: str) -> Conversation | None:
        return self.conversations.get(conversation_id)

    async def list_user_conversations(self, user_id: str, archived: bool | None = None) -> list[Conversation]:
        if user_id not in self.user_conversations:
            return []

        conversations = []
        for conv_id in self.user_conversations[user_id]:
            conv = self.conversations.get(conv_id)
            if conv:
                if archived is None or conv.archived == archived:
                    conversations.append(conv)

        return conversations

    async def update(self, conversation_id: str, updates: dict[str, Any]) -> bool:
        if conversation_id not in self.conversations:
            return False

        conversation = self.conversations[conversation_id]
        for key, value in updates.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)

        return True

    async def delete(self, conversation_id: str) -> bool:
        if conversation_id in self.conversations:
            conv = self.conversations.pop(conversation_id)
            if conv.user_id in self.user_conversations:
                try:
                    self.user_conversations[conv.user_id].remove(conversation_id)
                except ValueError:
                    pass
            return True
        return False

    async def delete_user_conversations(self, user_id: str) -> int:
        if user_id not in self.user_conversations:
            return 0

        conv_ids = self.user_conversations[user_id][:]
        count = 0

        for conv_id in conv_ids:
            if await self.delete(conv_id):
                count += 1

        return count


class InMemoryPreferencesStore(PreferencesStore):
    """In-memory implementation of preferences storage"""

    def __init__(self) -> None:
        self.preferences: dict[str, UserPreferences] = {}

    async def get(self, user_id: str) -> UserPreferences | None:
        return self.preferences.get(user_id)

    async def set(self, user_id: str, preferences: dict[str, Any]) -> bool:
        self.preferences[user_id] = UserPreferences(
            user_id=user_id, preferences=preferences, updated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        return True

    async def update(self, user_id: str, updates: dict[str, Any]) -> bool:
        if user_id not in self.preferences:
            # Create new preferences if they don't exist
            return await self.set(user_id, updates)

        prefs = self.preferences[user_id]
        prefs.preferences.update(updates)
        prefs.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return True

    async def delete(self, user_id: str) -> bool:
        if user_id in self.preferences:
            del self.preferences[user_id]
            return True
        return False


class InMemoryAuditLogStore(AuditLogStore):
    """In-memory implementation of audit log storage"""

    def __init__(self) -> None:
        self.logs: dict[str, AuditLogEntry] = {}
        self.user_logs: dict[str, list[str]] = {}

    async def log(self, entry: AuditLogEntry) -> str:
        self.logs[entry.log_id] = entry

        if entry.user_id not in self.user_logs:
            self.user_logs[entry.user_id] = []
        self.user_logs[entry.user_id].append(entry.log_id)

        return entry.log_id

    async def get(self, log_id: str) -> AuditLogEntry | None:
        return self.logs.get(log_id)

    async def list_user_logs(
        self, user_id: str, start_date: datetime | None = None, end_date: datetime | None = None, limit: int = 100
    ) -> list[AuditLogEntry]:
        if user_id not in self.user_logs:
            return []

        logs = []
        for log_id in self.user_logs[user_id]:
            log = self.logs.get(log_id)
            if log:
                # Filter by date if specified
                log_timestamp = datetime.fromisoformat(log.timestamp.replace("Z", ""))

                if start_date and log_timestamp < start_date:
                    continue
                if end_date and log_timestamp > end_date:
                    continue

                logs.append(log)

                if len(logs) >= limit:
                    break

        return logs

    async def anonymize_user_logs(self, user_id: str) -> int:
        """Replace user_id with hash in audit logs"""
        if user_id not in self.user_logs:
            return 0

        count = 0
        anonymized_id = f"anonymized_{hash(user_id)}"

        for log_id in self.user_logs[user_id]:
            if log_id in self.logs:
                self.logs[log_id].user_id = anonymized_id
                count += 1

        # Move to anonymized tracking
        self.user_logs[anonymized_id] = self.user_logs.pop(user_id)

        return count


class InMemoryConsentStore(ConsentStore):
    """In-memory implementation of consent storage"""

    def __init__(self) -> None:
        self.consents: dict[str, ConsentRecord] = {}
        self.user_consents: dict[str, list[str]] = {}

    async def create(self, record: ConsentRecord) -> str:
        self.consents[record.consent_id] = record

        if record.user_id not in self.user_consents:
            self.user_consents[record.user_id] = []
        self.user_consents[record.user_id].append(record.consent_id)

        return record.consent_id

    async def get_user_consents(self, user_id: str) -> list[ConsentRecord]:
        if user_id not in self.user_consents:
            return []

        consents = []
        for consent_id in self.user_consents[user_id]:
            consent = self.consents.get(consent_id)
            if consent:
                consents.append(consent)

        return consents

    async def get_latest_consent(self, user_id: str, consent_type: str) -> ConsentRecord | None:
        consents = await self.get_user_consents(user_id)

        # Filter by type
        type_consents = [c for c in consents if c.consent_type == consent_type]

        if not type_consents:
            return None

        # Sort by timestamp descending and return latest
        type_consents.sort(key=lambda c: c.timestamp, reverse=True)
        return type_consents[0]

    async def delete_user_consents(self, user_id: str) -> int:
        if user_id not in self.user_consents:
            return 0

        consent_ids = self.user_consents[user_id][:]
        count = 0

        for consent_id in consent_ids:
            if consent_id in self.consents:
                del self.consents[consent_id]
                count += 1

        del self.user_consents[user_id]
        return count
