"""
Tests for Storage Backend Interfaces for Compliance Data

Covers abstract interfaces and data models for compliance data storage.
"""

import gc
from datetime import datetime

import pytest

from mcp_server_langgraph.compliance.gdpr.storage import (
    AuditLogEntry,
    ConsentRecord,
    Conversation,
    InMemoryAuditLogStore,
    InMemoryConsentStore,
    InMemoryConversationStore,
    InMemoryPreferencesStore,
    InMemoryUserProfileStore,
    UserPreferences,
    UserProfile,
)

pytestmark = [pytest.mark.unit]


@pytest.mark.unit
@pytest.mark.xdist_group(name="testuserprofile")
class TestUserProfile:
    """Test UserProfile data model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
        # Test that profile can be created with empty string
        # (Pydantic doesn't validate empty strings by default)
        profile = UserProfile(
            user_id="",  # Empty string is allowed
            username="test",
            email="test@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )
        assert profile.user_id == ""


@pytest.mark.unit
@pytest.mark.xdist_group(name="testconversation")
class TestConversation:
    """Test Conversation data model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
@pytest.mark.xdist_group(name="testuserpreferences")
class TestUserPreferences:
    """Test UserPreferences data model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
        prefs = UserPreferences(user_id="user:bob", updated_at="2025-01-01T00:00:00Z")

        assert prefs.preferences == {}


@pytest.mark.unit
@pytest.mark.xdist_group(name="testauditlogentry")
class TestAuditLogEntry:
    """Test AuditLogEntry data model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_audit_log_creation(self):
        """Test creating audit log"""
        log = AuditLogEntry(
            log_id="log_123",
            user_id="user:alice",
            action="data_export",
            resource_type="export",
            timestamp="2025-01-01T00:00:00Z",
            metadata={"export_format": "json", "data_types": ["profile", "conversations"]},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert log.log_id == "log_123"
        assert log.action == "data_export"
        assert log.ip_address == "192.168.1.1"

    def test_audit_log_minimal(self):
        """Test audit log with minimal fields"""
        log = AuditLogEntry(
            log_id="log_456",
            user_id="user:bob",
            action="login",
            resource_type="auth",
            timestamp="2025-01-01T00:00:00Z",
        )

        assert log.metadata == {}
        assert log.ip_address is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="testconsentrecord")
class TestConsentRecord:
    """Test ConsentRecord data model"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_consent_record_creation(self):
        """Test creating consent record"""
        consent = ConsentRecord(
            consent_id="consent_123",
            user_id="user:alice",
            consent_type="data_processing",
            granted=True,
            timestamp="2025-01-01T00:00:00Z",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert consent.consent_id == "consent_123"
        assert consent.consent_type == "data_processing"
        assert consent.granted is True

    def test_consent_record_revoked(self):
        """Test revoked consent"""
        consent = ConsentRecord(
            consent_id="consent_456",
            user_id="user:bob",
            consent_type="marketing",
            granted=False,
            timestamp="2025-01-01T00:00:00Z",
        )

        assert consent.granted is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinmemoryuserprofilestore")
class TestInMemoryUserProfileStore:
    """Test in-memory user profile storage"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_and_retrieve_user_profile(self):
        """Test creating and retrieving user profile"""
        storage = InMemoryUserProfileStore()

        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )

        # Create profile
        created = await storage.create(profile)
        assert created is True

        # Retrieve profile
        retrieved = await storage.get("user:alice")

        assert retrieved is not None
        assert retrieved.user_id == "user:alice"
        assert retrieved.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_profile(self):
        """Test retrieving non-existent user profile"""
        storage = InMemoryUserProfileStore()

        profile = await storage.get("user:nonexistent")

        assert profile is None

    @pytest.mark.asyncio
    async def test_update_user_profile(self):
        """Test updating user profile"""
        storage = InMemoryUserProfileStore()

        # Create initial profile
        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            full_name="Alice",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )
        await storage.create(profile)

        # Update profile
        updated = await storage.update("user:alice", {"email": "alice@newdomain.com", "full_name": "Alice Smith"})
        assert updated is True

        # Retrieve and verify
        retrieved = await storage.get("user:alice")
        assert retrieved.email == "alice@newdomain.com"
        assert retrieved.full_name == "Alice Smith"

    @pytest.mark.asyncio
    async def test_delete_user_profile(self):
        """Test deleting user profile"""
        storage = InMemoryUserProfileStore()

        # Create profile
        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )
        await storage.create(profile)

        # Delete profile
        deleted = await storage.delete("user:alice")
        assert deleted is True

        # Verify deletion
        retrieved = await storage.get("user:alice")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_profile(self):
        """Test deleting non-existent user profile"""
        storage = InMemoryUserProfileStore()

        deleted = await storage.delete("user:nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_create_duplicate_profile(self):
        """Test that creating duplicate profile fails"""
        storage = InMemoryUserProfileStore()

        profile = UserProfile(
            user_id="user:alice",
            username="alice",
            email="alice@example.com",
            created_at="2025-01-01T00:00:00Z",
            last_updated="2025-01-01T00:00:00Z",
        )

        # First create should succeed
        created = await storage.create(profile)
        assert created is True

        # Second create should fail
        created_again = await storage.create(profile)
        assert created_again is False


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinmemoryconversationstore")
class TestInMemoryConversationStore:
    """Test in-memory conversation storage"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_and_retrieve_conversation(self):
        """Test creating and retrieving conversation"""
        storage = InMemoryConversationStore()

        conversation = Conversation(
            conversation_id="conv_123",
            user_id="user:alice",
            title="Test Chat",
            messages=[{"role": "user", "content": "Hello"}],
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:05:00Z",
        )

        # Create conversation
        conv_id = await storage.create(conversation)
        assert conv_id == "conv_123"

        # Retrieve conversation
        retrieved = await storage.get("conv_123")

        assert retrieved is not None
        assert retrieved.conversation_id == "conv_123"
        assert retrieved.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_list_user_conversations(self):
        """Test listing all conversations for a user"""
        storage = InMemoryConversationStore()

        # Create multiple conversations
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

        await storage.create(conv1)
        await storage.create(conv2)
        await storage.create(conv3)

        # Get conversations for alice
        alice_convs = await storage.list_user_conversations("user:alice")

        assert len(alice_convs) == 2
        assert all(c.user_id == "user:alice" for c in alice_convs)

    @pytest.mark.asyncio
    async def test_list_archived_conversations(self):
        """Test listing archived conversations"""
        storage = InMemoryConversationStore()

        conv1 = Conversation(
            conversation_id="conv_1",
            user_id="user:alice",
            archived=False,
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:00:00Z",
        )
        conv2 = Conversation(
            conversation_id="conv_2",
            user_id="user:alice",
            archived=True,
            created_at="2025-01-02T00:00:00Z",
            last_message_at="2025-01-02T00:00:00Z",
        )

        await storage.create(conv1)
        await storage.create(conv2)

        # Get only archived conversations
        archived = await storage.list_user_conversations("user:alice", archived=True)
        assert len(archived) == 1
        assert archived[0].archived is True

    @pytest.mark.asyncio
    async def test_delete_conversation(self):
        """Test deleting conversation"""
        storage = InMemoryConversationStore()

        conversation = Conversation(
            conversation_id="conv_123",
            user_id="user:alice",
            created_at="2025-01-01T00:00:00Z",
            last_message_at="2025-01-01T00:00:00Z",
        )
        await storage.create(conversation)

        # Delete conversation
        deleted = await storage.delete("conv_123")
        assert deleted is True

        # Verify deletion
        retrieved = await storage.get("conv_123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_user_conversations(self):
        """Test deleting all conversations for a user"""
        storage = InMemoryConversationStore()

        # Create conversations
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

        await storage.create(conv1)
        await storage.create(conv2)

        # Delete all user conversations
        count = await storage.delete_user_conversations("user:alice")
        assert count == 2

        # Verify deletion
        alice_convs = await storage.list_user_conversations("user:alice")
        assert len(alice_convs) == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinmemorypreferencesstore")
class TestInMemoryPreferencesStore:
    """Test in-memory preferences storage"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_set_and_retrieve_preferences(self):
        """Test setting and retrieving user preferences"""
        storage = InMemoryPreferencesStore()

        preferences = {"theme": "dark", "language": "en"}

        # Set preferences
        success = await storage.set("user:alice", preferences)
        assert success is True

        # Retrieve preferences
        retrieved = await storage.get("user:alice")

        assert retrieved is not None
        assert retrieved.preferences["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_update_preferences(self):
        """Test updating existing preferences"""
        storage = InMemoryPreferencesStore()

        # Set initial preferences
        await storage.set("user:alice", {"theme": "dark"})

        # Update preferences
        success = await storage.update("user:alice", {"language": "fr"})
        assert success is True

        # Verify both settings exist
        prefs = await storage.get("user:alice")
        assert prefs.preferences["theme"] == "dark"
        assert prefs.preferences["language"] == "fr"

    @pytest.mark.asyncio
    async def test_update_nonexistent_preferences(self):
        """Test updating preferences for user without existing preferences"""
        storage = InMemoryPreferencesStore()

        # Update should create new preferences
        success = await storage.update("user:new", {"theme": "light"})
        assert success is True

        prefs = await storage.get("user:new")
        assert prefs.preferences["theme"] == "light"

    @pytest.mark.asyncio
    async def test_delete_preferences(self):
        """Test deleting user preferences"""
        storage = InMemoryPreferencesStore()

        # Set preferences
        await storage.set("user:alice", {"theme": "dark"})

        # Delete preferences
        deleted = await storage.delete("user:alice")
        assert deleted is True

        # Verify deletion
        prefs = await storage.get("user:alice")
        assert prefs is None


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinmemoryauditlogstore")
class TestInMemoryAuditLogStore:
    """Test in-memory audit log storage"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_log_and_retrieve_audit_entry(self):
        """Test logging and retrieving audit entry"""
        storage = InMemoryAuditLogStore()

        log_entry = AuditLogEntry(
            log_id="log_123",
            user_id="user:alice",
            action="data_export",
            resource_type="export",
            timestamp="2025-01-01T00:00:00Z",
            metadata={"format": "json"},
        )

        # Log entry
        log_id = await storage.log(log_entry)
        assert log_id == "log_123"

        # Retrieve entry
        retrieved = await storage.get("log_123")
        assert retrieved is not None
        assert retrieved.action == "data_export"

    @pytest.mark.asyncio
    async def test_list_user_logs(self):
        """Test listing audit logs for a user"""
        storage = InMemoryAuditLogStore()

        # Log multiple entries
        log1 = AuditLogEntry(
            log_id="log_1",
            user_id="user:alice",
            action="login",
            resource_type="auth",
            timestamp="2025-01-01T00:00:00Z",
        )
        log2 = AuditLogEntry(
            log_id="log_2",
            user_id="user:alice",
            action="logout",
            resource_type="auth",
            timestamp="2025-01-02T00:00:00Z",
        )

        await storage.log(log1)
        await storage.log(log2)

        # Get user logs
        logs = await storage.list_user_logs("user:alice")

        assert len(logs) == 2
        assert all(log.user_id == "user:alice" for log in logs)

    @pytest.mark.asyncio
    async def test_list_user_logs_with_date_filter(self):
        """Test filtering logs by date range"""
        storage = InMemoryAuditLogStore()

        log1 = AuditLogEntry(
            log_id="log_1",
            user_id="user:alice",
            action="action1",
            resource_type="test",
            timestamp="2025-01-01T00:00:00Z",
        )
        log2 = AuditLogEntry(
            log_id="log_2",
            user_id="user:alice",
            action="action2",
            resource_type="test",
            timestamp="2025-01-15T00:00:00Z",
        )

        await storage.log(log1)
        await storage.log(log2)

        # Filter to logs after Jan 10
        start_date = datetime(2025, 1, 10)
        logs = await storage.list_user_logs("user:alice", start_date=start_date)

        assert len(logs) == 1
        assert logs[0].log_id == "log_2"

    @pytest.mark.asyncio
    async def test_anonymize_user_logs(self):
        """Test anonymizing user logs (GDPR compliance)"""
        storage = InMemoryAuditLogStore()

        log1 = AuditLogEntry(
            log_id="log_1",
            user_id="user:alice",
            action="action1",
            resource_type="test",
            timestamp="2025-01-01T00:00:00Z",
        )

        await storage.log(log1)

        # Anonymize logs
        count = await storage.anonymize_user_logs("user:alice")
        assert count == 1

        # Verify logs are anonymized
        retrieved = await storage.get("log_1")
        assert retrieved.user_id.startswith("anonymized_")


@pytest.mark.unit
@pytest.mark.xdist_group(name="testinmemoryconsentstore")
class TestInMemoryConsentStore:
    """Test in-memory consent storage"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_create_and_retrieve_consent(self):
        """Test creating and retrieving consent record"""
        storage = InMemoryConsentStore()

        consent = ConsentRecord(
            consent_id="consent_123",
            user_id="user:alice",
            consent_type="data_processing",
            granted=True,
            timestamp="2025-01-01T00:00:00Z",
        )

        # Create consent
        consent_id = await storage.create(consent)
        assert consent_id == "consent_123"

        # Get user consents
        consents = await storage.get_user_consents("user:alice")

        assert len(consents) == 1
        assert consents[0].consent_type == "data_processing"
        assert consents[0].granted is True

    @pytest.mark.asyncio
    async def test_get_latest_consent(self):
        """Test getting latest consent for a type"""
        storage = InMemoryConsentStore()

        # Create multiple consents of same type
        consent1 = ConsentRecord(
            consent_id="consent_1",
            user_id="user:alice",
            consent_type="marketing",
            granted=True,
            timestamp="2025-01-01T00:00:00Z",
        )
        consent2 = ConsentRecord(
            consent_id="consent_2",
            user_id="user:alice",
            consent_type="marketing",
            granted=False,
            timestamp="2025-01-02T00:00:00Z",
        )

        await storage.create(consent1)
        await storage.create(consent2)

        # Get latest marketing consent
        latest = await storage.get_latest_consent("user:alice", "marketing")

        assert latest is not None
        assert latest.consent_id == "consent_2"
        assert latest.granted is False

    @pytest.mark.asyncio
    async def test_delete_user_consents(self):
        """Test deleting all consents for a user"""
        storage = InMemoryConsentStore()

        # Create consents
        consent1 = ConsentRecord(
            consent_id="consent_1",
            user_id="user:alice",
            consent_type="analytics",
            granted=True,
            timestamp="2025-01-01T00:00:00Z",
        )
        consent2 = ConsentRecord(
            consent_id="consent_2",
            user_id="user:alice",
            consent_type="marketing",
            granted=True,
            timestamp="2025-01-01T00:00:00Z",
        )

        await storage.create(consent1)
        await storage.create(consent2)

        # Delete all consents
        count = await storage.delete_user_consents("user:alice")
        assert count == 2

        # Verify deletion
        consents = await storage.get_user_consents("user:alice")
        assert len(consents) == 0
