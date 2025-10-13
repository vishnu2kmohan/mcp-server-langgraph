"""
Tests for Storage Backend Interfaces for Compliance Data

Covers abstract interfaces and data models for compliance data storage.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from mcp_server_langgraph.core.compliance.storage import (
    UserProfile,
    Conversation,
    UserPreferences,
    AuditLog,
    ConsentRecord,
    ComplianceStorageBackend,
    InMemoryComplianceStorage,
)


@pytest.mark.unit
class TestUserProfile:
    """Test UserProfile data model"""

    def test_user_profile_creation(self):
        """Test creating user profile"""
        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            full_name="Alice Smith",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
            metadata={"department": "Engineering"},
        )

        assert profile.user_id == "user:alice"
        assert profile.username == "alice"
        assert profile.email == "alice@example.com"
        assert profile.full_name == "Alice Smith"
        assert profile.metadata["department"] == "Engineering"

    def test_user_profile_minimal(self):
        """Test user profile with minimal required fields"""
        profile = UserProfile(
            user_id="user:bob",
            username="bob",
            email="bob@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )

        assert profile.full_name is None
        assert profile.metadata == {}

    def test_user_profile_validation(self):
        """Test user profile validation"""
        with pytest.raises(Exception):  # Pydantic validation error
            UserProfile(
                user_id="",  # Empty user_id should fail
                username="test",
                email="test@example.com",
                created_at="2025-01-01T00:00:00Z",
                last_updated="2025-01-01T00:00:00Z",
            )


@pytest.mark.unit
class TestConversation:
    """Test Conversation data model"""

    def test_conversation_creation(self):
        """Test creating conversation"""
        conversation = Conversation(
            conversation_id="conv_123",
            user_id="user:alice",
            title="Test Conversation",
            messages=[{"role": "user", "content": "Hello"}],
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:05:00Z",
            archived=False,
            metadata={"category": "support"},
        )

        assert conversation.conversation_id == "conv_123"
        assert conversation.user_id == "user:alice"
        assert conversation.title == "Test Conversation"
        assert len(conversation.messages) == 1
        assert conversation.archived is False

    def test_conversation_defaults(self):
        """Test conversation default values"""
        conversation = Conversation(
            conversation_id="conv_456",
            user_id="user:bob",
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:00:00Z",
        )

        assert conversation.title is None
        assert conversation.messages == []
        assert conversation.archived is False
        assert conversation.metadata == {}

    def test_conversation_archived(self):
        """Test archived conversation"""
        conversation = Conversation(
            conversation_id="conv_789",
            user_id="user:charlie",
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:00:00Z",
            archived=True,
        )

        assert conversation.archived is True


@pytest.mark.unit
class TestUserPreferences:
    """Test UserPreferences data model"""

    def test_user_preferences_creation(self):
        """Test creating user preferences"""
        prefs = UserPreferences(
            user_id="user:alice",
            preferences={
                "theme": "dark",
                "language": "en",
                "notifications": {"email": True, "sms": False},
            },
            updated_at="2025-01-01T00:00:00Z",
        )

        assert prefs.user_id == "user:alice"
        assert prefs.preferences["theme"] == "dark"
        assert prefs.preferences["notifications"]["email"] is True

    def test_user_preferences_defaults(self):
        """Test user preferences with defaults"""
        prefs = UserPreferences(
            user_id="user:bob", updated_at="2025-01-01T00:00:00Z"
        )

        assert prefs.preferences == {}


@pytest.mark.unit
class TestAuditLog:
    """Test AuditLog data model"""

    def test_audit_log_creation(self):
        """Test creating audit log"""
        log = AuditLog(
            log_id="log_123",
            user_id="user:alice",
            action="data_export",
            timestamp="2025-01-01T00:00:00Z",
            details={"export_format": "json", "data_types": ["profile", "conversations"]},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert log.log_id == "log_123"
        assert log.action == "data_export"
        assert log.ip_address == "192.168.1.1"

    def test_audit_log_minimal(self):
        """Test audit log with minimal fields"""
        log = AuditLog(
            log_id="log_456",
            user_id="user:bob",
            action="login",
            timestamp="2025-01-01T00:00:00Z",
        )

        assert log.details == {}
        assert log.ip_address is None


@pytest.mark.unit
class TestConsentRecord:
    """Test ConsentRecord data model"""

    def test_consent_record_creation(self):
        """Test creating consent record"""
        consent = ConsentRecord(
            consent_id="consent_123",
            user_id="user:alice",
            purpose="data_processing",
            granted=True,
            granted_at="2025-01-01T00:00:00Z",
            expires_at="2026-01-01T00:00:00Z",
            version="1.0",
        )

        assert consent.consent_id == "consent_123"
        assert consent.purpose == "data_processing"
        assert consent.granted is True

    def test_consent_record_revoked(self):
        """Test revoked consent"""
        consent = ConsentRecord(
            consent_id="consent_456",
            user_id="user:bob",
            purpose="marketing",
            granted=False,
            granted_at="2025-01-01T00:00:00Z",
            revoked_at="2025-02-01T00:00:00Z",
            version="1.0",
        )

        assert consent.granted is False
        assert consent.revoked_at is not None


@pytest.mark.unit
class TestInMemoryComplianceStorage:
    """Test in-memory compliance storage backend"""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_user_profile(self):
        """Test storing and retrieving user profile"""
        storage = InMemoryComplianceStorage()

        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )

        # Store profile
        await storage.store_user_profile(profile)

        # Retrieve profile
        retrieved = await storage.get_user_profile("user:alice")

        assert retrieved is not None
        assert retrieved.user_id == "user:alice"
        assert retrieved.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_profile(self):
        """Test retrieving non-existent user profile"""
        storage = InMemoryComplianceStorage()

        profile = await storage.get_user_profile("user:nonexistent")

        assert profile is None

    @pytest.mark.asyncio
    async def test_update_user_profile(self):
        """Test updating user profile"""
        storage = InMemoryComplianceStorage()

        # Store initial profile
        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            full_name="Alice",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )
        await storage.store_user_profile(profile)

        # Update profile
        updated_profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@newdomain.com",
            full_name="Alice Smith",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-02-01T00:00:00Z",
        )
        await storage.store_user_profile(updated_profile)

        # Retrieve and verify
        retrieved = await storage.get_user_profile("user:alice")
        assert retrieved.email == "alice@newdomain.com"
        assert retrieved.full_name == "Alice Smith"

    @pytest.mark.asyncio
    async def test_delete_user_profile(self):
        """Test deleting user profile"""
        storage = InMemoryComplianceStorage()

        # Store profile
        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )
        await storage.store_user_profile(profile)

        # Delete profile
        deleted = await storage.delete_user_profile("user:alice")
        assert deleted is True

        # Verify deletion
        retrieved = await storage.get_user_profile("user:alice")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_profile(self):
        """Test deleting non-existent user profile"""
        storage = InMemoryComplianceStorage()

        deleted = await storage.delete_user_profile("user:nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_store_and_retrieve_conversation(self):
        """Test storing and retrieving conversation"""
        storage = InMemoryComplianceStorage()

        conversation = Conversation(
            conversation_id="conv_123",
            user_id="user:alice",
            title="Test Chat",
            messages=[{"role": "user", "content": "Hello"}],
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:05:00Z",
        )

        # Store conversation
        await storage.store_conversation(conversation)

        # Retrieve conversation
        retrieved = await storage.get_conversation("conv_123")

        assert retrieved is not None
        assert retrieved.conversation_id == "conv_123"
        assert retrieved.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_get_user_conversations(self):
        """Test retrieving all conversations for a user"""
        storage = InMemoryComplianceStorage()

        # Store multiple conversations
        conv1 = Conversation(
            conversation_id="conv_1",
            user_id="user:alice",
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:00:00Z",
        )
        conv2 = Conversation(
            conversation_id="conv_2",
            user_id="user:alice",
            created_at="2025-01-02T00:00:00Z",
            last_message_at="2025-01-02T00:00:00Z",
        )
        conv3 = Conversation(
            conversation_id="conv_3",
            user_id="user:bob",
            created_at="2025-01-03T00:00:00Z",
            last_message_at="2025-01-03T00:00:00Z",
        )

        await storage.store_conversation(conv1)
        await storage.store_conversation(conv2)
        await storage.store_conversation(conv3)

        # Get conversations for alice
        alice_convs = await storage.get_user_conversations("user:alice")

        assert len(alice_convs) == 2
        assert all(c.user_id == "user:alice" for c in alice_convs)

    @pytest.mark.asyncio
    async def test_delete_conversation(self):
        """Test deleting conversation"""
        storage = InMemoryComplianceStorage()

        conversation = Conversation(
            conversation_id="conv_123",
            user_id="user:alice",
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:00:00Z",
        )
        await storage.store_conversation(conversation)

        # Delete conversation
        deleted = await storage.delete_conversation("conv_123")
        assert deleted is True

        # Verify deletion
        retrieved = await storage.get_conversation("conv_123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_store_and_retrieve_preferences(self):
        """Test storing and retrieving user preferences"""
        storage = InMemoryComplianceStorage()

        prefs = UserPreferences(
            user_id="user:alice",
            preferences={"theme": "dark", "language": "en"},
            updated_at="2025-01-01T00:00:00Z",
        )

        # Store preferences
        await storage.store_user_preferences(prefs)

        # Retrieve preferences
        retrieved = await storage.get_user_preferences("user:alice")

        assert retrieved is not None
        assert retrieved.preferences["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_store_and_retrieve_audit_log(self):
        """Test storing and retrieving audit log"""
        storage = InMemoryComplianceStorage()

        log = AuditLog(
            log_id="log_123",
            user_id="user:alice",
            action="data_export",
            timestamp="2025-01-01T00:00:00Z",
            details={"format": "json"},
        )

        # Store log
        await storage.store_audit_log(log)

        # Get user audit logs
        logs = await storage.get_user_audit_logs("user:alice")

        assert len(logs) == 1
        assert logs[0].log_id == "log_123"
        assert logs[0].action == "data_export"

    @pytest.mark.asyncio
    async def test_store_and_retrieve_consent_record(self):
        """Test storing and retrieving consent record"""
        storage = InMemoryComplianceStorage()

        consent = ConsentRecord(
            consent_id="consent_123",
            user_id="user:alice",
            purpose="data_processing",
            granted=True,
            granted_at="2025-01-01T00:00:00Z",
            version="1.0",
        )

        # Store consent
        await storage.store_consent_record(consent)

        # Get user consents
        consents = await storage.get_user_consents("user:alice")

        assert len(consents) == 1
        assert consents[0].purpose == "data_processing"
        assert consents[0].granted is True

    @pytest.mark.asyncio
    async def test_delete_all_user_data(self):
        """Test deleting all data for a user (GDPR right to erasure)"""
        storage = InMemoryComplianceStorage()

        # Store various data for user
        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )
        conversation = Conversation(
            conversation_id="conv_123",
            user_id="user:alice",
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:00:00Z",
        )
        prefs = UserPreferences(
            user_id="user:alice",
            preferences={"theme": "dark"},
            updated_at="2025-01-01T00:00:00Z",
        )

        await storage.store_user_profile(profile)
        await storage.store_conversation(conversation)
        await storage.store_user_preferences(prefs)

        # Delete all user data
        deleted_count = await storage.delete_all_user_data("user:alice")

        # Verify all data deleted
        assert await storage.get_user_profile("user:alice") is None
        assert await storage.get_user_preferences("user:alice") is None
        assert len(await storage.get_user_conversations("user:alice")) == 0

    @pytest.mark.asyncio
    async def test_export_all_user_data(self):
        """Test exporting all user data (GDPR data portability)"""
        storage = InMemoryComplianceStorage()

        # Store data
        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )
        await storage.store_user_profile(profile)

        # Export data
        exported_data = await storage.export_all_user_data("user:alice")

        assert "profile" in exported_data
        assert exported_data["profile"]["email"] == "alice@example.com"
