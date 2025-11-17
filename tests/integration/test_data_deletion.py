"""
Tests for GDPR Data Deletion Service (Article 17 - Right to Erasure)

Covers user data deletion and audit logging.
"""

import gc
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService
from mcp_server_langgraph.compliance.gdpr.factory import GDPRStorage
from mcp_server_langgraph.compliance.gdpr.storage import (
    InMemoryAuditLogStore,
    InMemoryConsentStore,
    InMemoryConversationStore,
    InMemoryPreferencesStore,
    InMemoryUserProfileStore,
)
from tests.conftest import get_user_id


@pytest.fixture
def mock_audit_log_store():
    """Create mock audit log store"""
    return InMemoryAuditLogStore()


@pytest.fixture
def mock_user_profile_store():
    """Create mock user profile store"""
    return InMemoryUserProfileStore()


@pytest.fixture
def mock_conversation_store():
    """Create mock conversation store"""
    return InMemoryConversationStore()


@pytest.fixture
def mock_preferences_store():
    """Create mock preferences store"""
    return InMemoryPreferencesStore()


@pytest.fixture
def mock_consent_store():
    """Create mock consent store"""
    return InMemoryConsentStore()


@pytest.fixture
def gdpr_storage(
    mock_user_profile_store,
    mock_preferences_store,
    mock_consent_store,
    mock_conversation_store,
    mock_audit_log_store,
):
    """Create GDPRStorage with all mock stores"""
    return GDPRStorage(
        user_profiles=mock_user_profile_store,
        preferences=mock_preferences_store,
        consents=mock_consent_store,
        conversations=mock_conversation_store,
        audit_logs=mock_audit_log_store,
    )


@pytest.mark.integration
@pytest.mark.xdist_group(name="data_deletion_tests")
class TestDataDeletionAuditLogging:
    """Test audit logging for data deletion operations"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_deletion_creates_audit_record_with_store(
        self,
        gdpr_storage,
    ):
        """Test that deletion creates audit record when audit store is configured"""
        service = DataDeletionService(
            gdpr_storage=gdpr_storage,
        )

        # Create a user profile first
        from mcp_server_langgraph.compliance.gdpr.storage import UserProfile

        user_id = get_user_id("test123")
        username = "testuser"

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="test@example.com",
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            last_updated=datetime.now(timezone.utc).isoformat() + "Z",
        )
        await gdpr_storage.user_profiles.create(profile)

        # Delete the user
        result = await service.delete_user_account(
            user_id=user_id,
            username=username,
            reason="user_request",
        )

        # Verify deletion was successful
        assert result.success is True
        assert result.user_id == user_id

        # Verify audit record was created
        assert result.audit_record_id is not None
        assert result.audit_record_id.startswith("deletion_")

        # Verify audit record was stored
        audit_record = await gdpr_storage.audit_logs.get(result.audit_record_id)
        assert audit_record is not None
        assert audit_record.action == "account_deletion"
        assert audit_record.user_id == "DELETED"  # Anonymized
        assert audit_record.resource_type == "user_account"

        # Verify metadata contains deletion details
        assert "deletion_reason" in audit_record.metadata
        assert audit_record.metadata["deletion_reason"] == "user_request"
        assert "deleted_items" in audit_record.metadata
        assert "compliance_note" in audit_record.metadata

    @pytest.mark.asyncio
    async def test_deletion_logs_without_store(
        self,
        mock_user_profile_store,
        mock_preferences_store,
        mock_consent_store,
        mock_conversation_store,
    ):
        """Test that deletion logs to application logs when audit store not configured"""
        # Create GDPRStorage without audit log store
        gdpr_storage_no_audit = GDPRStorage(
            user_profiles=mock_user_profile_store,
            preferences=mock_preferences_store,
            consents=mock_consent_store,
            conversations=mock_conversation_store,
            audit_logs=None,  # No audit store
        )

        service = DataDeletionService(
            gdpr_storage=gdpr_storage_no_audit,
        )

        user_id = get_user_id("test456")
        username = "testuser2"

        # Create a user profile first
        from mcp_server_langgraph.compliance.gdpr.storage import UserProfile

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="test2@example.com",
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            last_updated=datetime.now(timezone.utc).isoformat() + "Z",
        )
        await gdpr_storage_no_audit.user_profiles.create(profile)

        # Mock logger to verify logging
        with patch("mcp_server_langgraph.compliance.gdpr.data_deletion.logger") as mock_logger:
            result = await service.delete_user_account(
                user_id=user_id,
                username=username,
                reason="user_request",
            )

            # Verify deletion completed
            assert result.audit_record_id is not None

            # Verify warning was logged about no audit store
            assert mock_logger.warning.called
            # Check that at least one warning call mentions audit record
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("audit" in str(call).lower() for call in warning_calls)

    @pytest.mark.asyncio
    async def test_audit_record_includes_deletion_details(
        self,
        gdpr_storage,
    ):
        """Test that audit record includes comprehensive deletion details"""
        service = DataDeletionService(
            gdpr_storage=gdpr_storage,
        )

        user_id = get_user_id("test789")
        username = "testuser3"

        # Create test data
        from mcp_server_langgraph.compliance.gdpr.storage import Conversation, UserProfile

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="test3@example.com",
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            last_updated=datetime.now(timezone.utc).isoformat() + "Z",
        )
        await gdpr_storage.user_profiles.create(profile)

        # Add a conversation
        conversation = Conversation(
            conversation_id="conv_123",
            user_id=user_id,
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            last_message_at=datetime.now(timezone.utc).isoformat() + "Z",
        )
        await gdpr_storage.conversations.create(conversation)

        # Add preferences
        await gdpr_storage.preferences.set(user_id, {"theme": "dark"})

        # Delete the user
        result = await service.delete_user_account(
            user_id=user_id,
            username=username,
            reason="gdpr_request",
        )

        # Verify deletion was successful
        assert result.success is True

        # Retrieve audit record
        audit_record = await gdpr_storage.audit_logs.get(result.audit_record_id)
        assert audit_record is not None

        # Verify audit record includes all deletion details
        metadata = audit_record.metadata
        assert metadata["deletion_reason"] == "gdpr_request"
        assert "deleted_items" in metadata
        assert metadata["deleted_items"]["user_profile"] == 1
        assert metadata["deleted_items"]["conversations"] == 1
        assert metadata["deleted_items"]["preferences"] == 1

        # Verify GDPR compliance note is included
        assert "GDPR Article 17" in metadata["compliance_note"]

    @pytest.mark.asyncio
    async def test_audit_record_anonymized(self, gdpr_storage):
        """Test that audit record properly anonymizes user data"""
        service = DataDeletionService(
            gdpr_storage=gdpr_storage,
        )

        user_id = get_user_id("sensitive123")
        username = "sensitiveuser"

        # Create user
        from mcp_server_langgraph.compliance.gdpr.storage import UserProfile

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="sensitive@example.com",
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            last_updated=datetime.now(timezone.utc).isoformat() + "Z",
        )
        await gdpr_storage.user_profiles.create(profile)

        # Delete user
        result = await service.delete_user_account(
            user_id=user_id,
            username=username,
            reason="user_request",
        )

        # Retrieve audit record
        audit_record = await gdpr_storage.audit_logs.get(result.audit_record_id)

        # Verify user ID is anonymized
        assert audit_record.user_id == "DELETED"
        assert user_id not in str(audit_record.model_dump())  # Original ID should not appear

        # Verify resource ID uses hash
        assert audit_record.resource_id.startswith("hash_")
        assert username not in str(audit_record.model_dump())  # Original username should not appear

        # Verify metadata uses hashes for correlation
        assert "original_username_hash" in audit_record.metadata
        assert isinstance(audit_record.metadata["original_username_hash"], int)

    @pytest.mark.asyncio
    async def test_audit_record_on_partial_failure(self, gdpr_storage):
        """Test that audit record is created even when deletion partially fails"""
        service = DataDeletionService(
            gdpr_storage=gdpr_storage,
        )

        user_id = get_user_id("partial123")
        username = "partialuser"

        # Create user
        from mcp_server_langgraph.compliance.gdpr.storage import UserProfile

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="partial@example.com",
            created_at=datetime.now(timezone.utc).isoformat() + "Z",
            last_updated=datetime.now(timezone.utc).isoformat() + "Z",
        )
        await gdpr_storage.user_profiles.create(profile)

        # Mock a failure in conversation deletion
        mock_conversation_store = AsyncMock()
        mock_conversation_store.delete_user_conversations.side_effect = Exception("DB error")
        gdpr_storage.conversations = mock_conversation_store

        # Delete user (should partially fail)
        result = await service.delete_user_account(
            user_id=user_id,
            username=username,
            reason="user_request",
        )

        # Deletion should be marked as failed
        assert result.success is False
        assert len(result.errors) > 0

        # But audit record should still be created
        assert result.audit_record_id is not None

        # Retrieve audit record
        audit_record = await gdpr_storage.audit_logs.get(result.audit_record_id)
        assert audit_record is not None

        # Verify errors are included in metadata
        assert audit_record.metadata["errors_count"] > 0
        assert len(audit_record.metadata["errors"]) > 0
