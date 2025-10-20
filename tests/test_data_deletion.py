"""
Tests for GDPR Data Deletion Service (Article 17 - Right to Erasure)

Covers user data deletion and audit logging.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_langgraph.core.compliance.data_deletion import DataDeletionService, DeletionResult
from mcp_server_langgraph.core.compliance.storage import (
    InMemoryAuditLogStore,
    InMemoryConversationStore,
    InMemoryPreferencesStore,
    InMemoryUserProfileStore,
)


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


@pytest.mark.integration
class TestDataDeletionAuditLogging:
    """Test audit logging for data deletion operations"""

    @pytest.mark.asyncio
    async def test_deletion_creates_audit_record_with_store(
        self,
        mock_audit_log_store,
        mock_user_profile_store,
    ):
        """Test that deletion creates audit record when audit store is configured"""
        service = DataDeletionService(
            audit_log_store=mock_audit_log_store,
            user_profile_store=mock_user_profile_store,
        )

        # Create a user profile first
        from mcp_server_langgraph.core.compliance.storage import UserProfile

        user_id = "user:test123"
        username = "testuser"

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="test@example.com",
            created_at=datetime.utcnow().isoformat() + "Z",
            last_updated=datetime.utcnow().isoformat() + "Z",
        )
        await mock_user_profile_store.create(profile)

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
        audit_record = await mock_audit_log_store.get(result.audit_record_id)
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
    async def test_deletion_logs_without_store(self, mock_user_profile_store):
        """Test that deletion logs to application logs when audit store not configured"""
        service = DataDeletionService(
            audit_log_store=None,  # No audit store
            user_profile_store=mock_user_profile_store,
        )

        user_id = "user:test456"
        username = "testuser2"

        # Create a user profile first
        from mcp_server_langgraph.core.compliance.storage import UserProfile

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="test2@example.com",
            created_at=datetime.utcnow().isoformat() + "Z",
            last_updated=datetime.utcnow().isoformat() + "Z",
        )
        await mock_user_profile_store.create(profile)

        # Mock logger to verify logging
        with patch("mcp_server_langgraph.core.compliance.data_deletion.logger") as mock_logger:
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
        mock_audit_log_store,
        mock_user_profile_store,
        mock_conversation_store,
        mock_preferences_store,
    ):
        """Test that audit record includes comprehensive deletion details"""
        service = DataDeletionService(
            audit_log_store=mock_audit_log_store,
            user_profile_store=mock_user_profile_store,
            conversation_store=mock_conversation_store,
            preferences_store=mock_preferences_store,
        )

        user_id = "user:test789"
        username = "testuser3"

        # Create test data
        from mcp_server_langgraph.core.compliance.storage import (
            Conversation,
            UserPreferences,
            UserProfile,
        )

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="test3@example.com",
            created_at=datetime.utcnow().isoformat() + "Z",
            last_updated=datetime.utcnow().isoformat() + "Z",
        )
        await mock_user_profile_store.create(profile)

        # Add a conversation
        conversation = Conversation(
            conversation_id="conv_123",
            user_id=user_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            last_message_at=datetime.utcnow().isoformat() + "Z",
        )
        await mock_conversation_store.create(conversation)

        # Add preferences
        await mock_preferences_store.set(user_id, {"theme": "dark"})

        # Delete the user
        result = await service.delete_user_account(
            user_id=user_id,
            username=username,
            reason="gdpr_request",
        )

        # Verify deletion was successful
        assert result.success is True

        # Retrieve audit record
        audit_record = await mock_audit_log_store.get(result.audit_record_id)
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
    async def test_audit_record_anonymized(self, mock_audit_log_store, mock_user_profile_store):
        """Test that audit record properly anonymizes user data"""
        service = DataDeletionService(
            audit_log_store=mock_audit_log_store,
            user_profile_store=mock_user_profile_store,
        )

        user_id = "user:sensitive123"
        username = "sensitiveuser"

        # Create user
        from mcp_server_langgraph.core.compliance.storage import UserProfile

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="sensitive@example.com",
            created_at=datetime.utcnow().isoformat() + "Z",
            last_updated=datetime.utcnow().isoformat() + "Z",
        )
        await mock_user_profile_store.create(profile)

        # Delete user
        result = await service.delete_user_account(
            user_id=user_id,
            username=username,
            reason="user_request",
        )

        # Retrieve audit record
        audit_record = await mock_audit_log_store.get(result.audit_record_id)

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
    async def test_audit_record_on_partial_failure(self, mock_audit_log_store, mock_user_profile_store):
        """Test that audit record is created even when deletion partially fails"""
        service = DataDeletionService(
            audit_log_store=mock_audit_log_store,
            user_profile_store=mock_user_profile_store,
        )

        user_id = "user:partial123"
        username = "partialuser"

        # Create user
        from mcp_server_langgraph.core.compliance.storage import UserProfile

        profile = UserProfile(
            user_id=user_id,
            username=username,
            email="partial@example.com",
            created_at=datetime.utcnow().isoformat() + "Z",
            last_updated=datetime.utcnow().isoformat() + "Z",
        )
        await mock_user_profile_store.create(profile)

        # Mock a failure in conversation deletion
        mock_conversation_store = AsyncMock()
        mock_conversation_store.delete_user_conversations.side_effect = Exception("DB error")
        service.conversation_store = mock_conversation_store

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
        audit_record = await mock_audit_log_store.get(result.audit_record_id)
        assert audit_record is not None

        # Verify errors are included in metadata
        assert audit_record.metadata["errors_count"] > 0
        assert len(audit_record.metadata["errors"]) > 0
