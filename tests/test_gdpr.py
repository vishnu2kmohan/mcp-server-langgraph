"""
Comprehensive tests for GDPR compliance endpoints and services
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from mcp_server_langgraph.api.gdpr import ConsentRecord, ConsentType, UserProfileUpdate, router
from mcp_server_langgraph.auth.session import InMemorySessionStore, SessionData
from mcp_server_langgraph.compliance.gdpr.data_deletion import DataDeletionService, DeletionResult
from mcp_server_langgraph.compliance.gdpr.data_export import DataExportService, UserDataExport

# ==================== Test Fixtures ====================


@pytest.fixture
def app():
    """Create FastAPI test app"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_session_store():
    """Mock session store"""
    store = AsyncMock(spec=InMemorySessionStore)
    return store


@pytest.fixture
def mock_user_request():
    """Mock authenticated request"""
    request = MagicMock(spec=Request)
    request.state.user = {
        "user_id": "user:alice",
        "username": "alice",
        "email": "alice@acme.com",
        "roles": ["user"],
    }
    request.client.host = "192.168.1.1"
    request.headers = {"user-agent": "test-client/1.0"}
    return request


# ==================== DataExportService Tests ====================


@pytest.mark.unit
@pytest.mark.gdpr
class TestDataExportService:
    """Test GDPR data export service"""

    @pytest.mark.asyncio
    async def test_export_user_data_basic(self, mock_session_store):
        """Test basic user data export"""
        # Setup
        service = DataExportService(session_store=mock_session_store)

        # Mock session data
        mock_session_store.list_user_sessions.return_value = [
            SessionData(
                session_id="sess_123456789012345678901234567890ab",
                user_id="user:alice",
                username="alice",
                roles=["user"],
                created_at="2025-01-01T10:00:00Z",
                last_accessed="2025-01-01T12:00:00Z",
                expires_at="2025-01-02T10:00:00Z",
            )
        ]

        # Execute
        export = await service.export_user_data(
            user_id="user:alice",
            username="alice",
            email="alice@acme.com",
        )

        # Assert
        assert isinstance(export, UserDataExport)
        assert export.user_id == "user:alice"
        assert export.username == "alice"
        assert export.email == "alice@acme.com"
        assert len(export.sessions) == 1
        assert export.sessions[0]["session_id"] == "sess_123456789012345678901234567890ab"
        assert export.export_id.startswith("exp_")
        assert export.metadata["gdpr_article"] == "15"

    @pytest.mark.asyncio
    async def test_export_user_data_no_sessions(self, mock_session_store):
        """Test export when user has no sessions"""
        service = DataExportService(session_store=mock_session_store)
        mock_session_store.list_user_sessions.return_value = []

        export = await service.export_user_data(
            user_id="user:bob",
            username="bob",
            email="bob@acme.com",
        )

        assert len(export.sessions) == 0
        assert export.user_id == "user:bob"

    @pytest.mark.asyncio
    async def test_export_portable_json_format(self, mock_session_store):
        """Test portable export in JSON format"""
        service = DataExportService(session_store=mock_session_store)
        mock_session_store.list_user_sessions.return_value = []

        data_bytes, content_type = await service.export_user_data_portable(
            user_id="user:alice",
            username="alice",
            email="alice@acme.com",
            format="json",
        )

        assert content_type == "application/json"
        assert isinstance(data_bytes, bytes)

        # Verify JSON is valid
        data = json.loads(data_bytes.decode("utf-8"))
        assert data["user_id"] == "user:alice"
        assert data["username"] == "alice"

    @pytest.mark.asyncio
    async def test_export_portable_csv_format(self, mock_session_store):
        """Test portable export in CSV format"""
        service = DataExportService(session_store=mock_session_store)
        mock_session_store.list_user_sessions.return_value = []

        data_bytes, content_type = await service.export_user_data_portable(
            user_id="user:alice",
            username="alice",
            email="alice@acme.com",
            format="csv",
        )

        assert content_type == "text/csv"
        assert isinstance(data_bytes, bytes)

        # Verify CSV contains expected headers
        csv_content = data_bytes.decode("utf-8")
        assert "Export Metadata" in csv_content
        assert "User ID" in csv_content
        assert "user:alice" in csv_content

    @pytest.mark.asyncio
    async def test_export_portable_invalid_format(self, mock_session_store):
        """Test export with invalid format raises error"""
        service = DataExportService(session_store=mock_session_store)

        with pytest.raises(ValueError, match="Unsupported export format"):
            await service.export_user_data_portable(
                user_id="user:alice",
                username="alice",
                email="alice@acme.com",
                format="xml",  # Invalid format
            )

    @pytest.mark.asyncio
    async def test_export_handles_session_store_error(self, mock_session_store):
        """Test export gracefully handles session store errors"""
        service = DataExportService(session_store=mock_session_store)
        mock_session_store.list_user_sessions.side_effect = Exception("Database connection error")

        # Should not raise, but return empty sessions
        export = await service.export_user_data(
            user_id="user:alice",
            username="alice",
            email="alice@acme.com",
        )

        assert len(export.sessions) == 0  # Empty due to error


# ==================== DataDeletionService Tests ====================


@pytest.mark.unit
@pytest.mark.gdpr
class TestDataDeletionService:
    """Test GDPR data deletion service"""

    @pytest.mark.asyncio
    async def test_delete_user_account_success(self, mock_session_store):
        """Test successful user account deletion"""
        service = DataDeletionService(session_store=mock_session_store)
        mock_session_store.delete_user_sessions.return_value = 3  # Deleted 3 sessions

        result = await service.delete_user_account(
            user_id="user:alice",
            username="alice",
            reason="user_request",
        )

        assert isinstance(result, DeletionResult)
        assert result.success is True
        assert result.user_id == "user:alice"
        assert result.deleted_items["sessions"] == 3
        assert result.deleted_items["user_profile"] == 1
        assert len(result.errors) == 0
        assert result.audit_record_id is not None
        mock_session_store.delete_user_sessions.assert_called_once_with("user:alice")

    @pytest.mark.asyncio
    async def test_delete_user_account_no_sessions(self, mock_session_store):
        """Test deletion when user has no sessions"""
        service = DataDeletionService(session_store=mock_session_store)
        mock_session_store.delete_user_sessions.return_value = 0

        result = await service.delete_user_account(
            user_id="user:bob",
            username="bob",
            reason="account_inactive",
        )

        assert result.success is True
        assert result.deleted_items["sessions"] == 0

    @pytest.mark.asyncio
    async def test_delete_user_account_partial_failure(self, mock_session_store):
        """Test deletion with partial failures"""
        service = DataDeletionService(session_store=mock_session_store)
        mock_session_store.delete_user_sessions.side_effect = Exception("Database error")

        result = await service.delete_user_account(
            user_id="user:alice",
            username="alice",
            reason="user_request",
        )

        assert result.success is False
        assert len(result.errors) > 0
        assert any("Failed to delete sessions" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_delete_user_account_no_session_store(self):
        """Test deletion without session store"""
        service = DataDeletionService(session_store=None)

        result = await service.delete_user_account(
            user_id="user:alice",
            username="alice",
            reason="user_request",
        )

        assert result.success is True
        assert "sessions" in result.deleted_items
        assert result.deleted_items["sessions"] == 0

    @pytest.mark.asyncio
    async def test_delete_creates_audit_record(self, mock_session_store):
        """Test that deletion creates anonymized audit record"""
        service = DataDeletionService(session_store=mock_session_store)
        mock_session_store.delete_user_sessions.return_value = 1

        result = await service.delete_user_account(
            user_id="user:alice",
            username="alice",
            reason="gdpr_request",
        )

        assert result.audit_record_id is not None
        assert result.audit_record_id.startswith("deletion_")


# ==================== GDPR API Endpoint Tests ====================


@pytest.mark.unit
@pytest.mark.gdpr
@pytest.mark.skip(reason="Requires auth mocking infrastructure - tracked in TODO_TRACKING_ISSUES.md #7")
class TestGDPREndpoints:
    """Test GDPR API endpoints

    NOTE: These tests are currently skipped pending implementation of proper
    authentication mocking infrastructure. See reports/TODO_TRACKING_ISSUES.md
    for the implementation plan.

    Prerequisites for implementation:
    1. Auth mocking helper that works with FastAPI dependency injection
    2. Test user fixtures with various permission levels
    3. Expected API response schemas

    Issue: Implement GDPR API endpoint tests with auth mocking
    """

    def test_get_user_data_endpoint(self, client):
        """Test GET /api/v1/users/me/data endpoint"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: authenticated user can retrieve their own data
        pass

    def test_export_user_data_json(self, client):
        """Test GET /api/v1/users/me/export?format=json"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: JSON export format with complete user data
        pass

    def test_export_user_data_csv(self, client):
        """Test GET /api/v1/users/me/export?format=csv"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: CSV export format with flattened user data
        pass

    def test_update_user_profile(self, client):
        """Test PATCH /api/v1/users/me"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: user can update their own profile fields
        pass

    def test_delete_user_account(self, client):
        """Test DELETE /api/v1/users/me?confirm=true"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: user can delete their account with confirmation
        pass

    def test_delete_user_account_without_confirmation(self, client):
        """Test DELETE /api/v1/users/me without confirmation"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: deletion fails without confirmation parameter
        pass

    def test_update_consent(self, client):
        """Test POST /api/v1/users/me/consent"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: user can update consent preferences
        pass

    def test_get_consent_status(self, client):
        """Test GET /api/v1/users/me/consent"""
        # TODO(issue-7): Implement with auth mocking
        # Should test: user can retrieve current consent status
        pass


# ==================== Model Tests ====================


@pytest.mark.unit
@pytest.mark.gdpr
class TestGDPRModels:
    """Test GDPR Pydantic models"""

    def test_user_profile_update_model(self):
        """Test UserProfileUpdate model validation"""
        update = UserProfileUpdate(name="Alice Smith", email="alice@acme.com")

        assert update.name == "Alice Smith"
        assert update.email == "alice@acme.com"
        assert update.preferences is None

    def test_user_profile_update_partial(self):
        """Test partial profile update"""
        update = UserProfileUpdate(name="Alice")

        data = update.model_dump(exclude_unset=True)
        assert "name" in data
        assert "email" not in data
        assert "preferences" not in data

    def test_consent_record_model(self):
        """Test ConsentRecord model"""
        consent = ConsentRecord(consent_type=ConsentType.ANALYTICS, granted=True)

        assert consent.consent_type == ConsentType.ANALYTICS
        assert consent.granted is True
        assert consent.timestamp is None  # Set by endpoint

    def test_consent_record_all_types(self):
        """Test all consent types are valid"""
        for consent_type in ConsentType:
            consent = ConsentRecord(consent_type=consent_type, granted=True)
            assert consent.consent_type == consent_type

    def test_user_data_export_model(self):
        """Test UserDataExport model"""
        export = UserDataExport(
            export_id="exp_123",
            export_timestamp="2025-01-01T12:00:00Z",
            user_id="user:alice",
            username="alice",
            email="alice@acme.com",
        )

        assert export.export_id == "exp_123"
        assert export.user_id == "user:alice"
        assert len(export.sessions) == 0  # Default empty
        assert len(export.conversations) == 0  # Default empty

    def test_deletion_result_model(self):
        """Test DeletionResult model"""
        result = DeletionResult(
            success=True,
            user_id="user:alice",
            deletion_timestamp="2025-01-01T12:00:00Z",
            deleted_items={"sessions": 3, "conversations": 5},
            anonymized_items={"audit_logs": 10},
        )

        assert result.success is True
        assert result.deleted_items["sessions"] == 3
        assert result.anonymized_items["audit_logs"] == 10
        assert len(result.errors) == 0


# ==================== Integration Tests ====================


@pytest.mark.integration
@pytest.mark.gdpr
class TestGDPRIntegration:
    """Integration tests for GDPR compliance"""

    @pytest.mark.asyncio
    async def test_full_data_lifecycle(self):
        """Test complete data lifecycle: create, export, delete"""
        # Setup
        session_store = InMemorySessionStore()
        export_service = DataExportService(session_store=session_store)
        deletion_service = DataDeletionService(session_store=session_store)

        user_id = "user:testuser"
        username = "testuser"
        email = "testuser@acme.com"

        # 1. Create session
        session_id = await session_store.create(
            user_id=user_id,
            username=username,
            roles=["user"],
        )

        # 2. Export data
        export = await export_service.export_user_data(user_id, username, email)
        assert len(export.sessions) == 1
        assert export.sessions[0]["session_id"] == session_id

        # 3. Delete account
        result = await deletion_service.delete_user_account(user_id, username)
        assert result.success is True
        assert result.deleted_items["sessions"] >= 1

        # 4. Verify deletion
        sessions = await session_store.list_user_sessions(user_id)
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_data_portability_formats(self):
        """Test data can be exported in multiple formats"""
        session_store = InMemorySessionStore()
        service = DataExportService(session_store=session_store)

        user_id = "user:testuser"

        # Export in JSON
        json_data, json_type = await service.export_user_data_portable(user_id, "testuser", "test@acme.com", "json")
        assert json_type == "application/json"
        json_obj = json.loads(json_data.decode())
        assert json_obj["user_id"] == user_id

        # Export in CSV
        csv_data, csv_type = await service.export_user_data_portable(user_id, "testuser", "test@acme.com", "csv")
        assert csv_type == "text/csv"
        assert user_id in csv_data.decode()


# ==================== Edge Cases ====================


@pytest.mark.unit
@pytest.mark.gdpr
class TestGDPREdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_export_very_large_user_data(self, mock_session_store):
        """Test export with large amount of user data"""
        service = DataExportService(session_store=mock_session_store)

        # Mock many sessions
        many_sessions = [
            SessionData(
                session_id=f"sess_{i:032d}",  # Pad to 32 chars minimum
                user_id="user:alice",
                username="alice",
                roles=["user"],
                created_at="2025-01-01T10:00:00Z",
                last_accessed="2025-01-01T12:00:00Z",
                expires_at="2025-01-02T10:00:00Z",
            )
            for i in range(100)
        ]
        mock_session_store.list_user_sessions.return_value = many_sessions

        export = await service.export_user_data("user:alice", "alice", "alice@acme.com")
        assert len(export.sessions) == 100

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, mock_session_store):
        """Test deleting user that doesn't exist"""
        service = DataDeletionService(session_store=mock_session_store)
        mock_session_store.delete_user_sessions.return_value = 0

        result = await service.delete_user_account(
            user_id="user:nonexistent",
            username="nonexistent",
        )

        # Should succeed but delete 0 items
        assert result.success is True
        assert result.deleted_items["sessions"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_deletion_attempts(self, mock_session_store):
        """Test handling of concurrent deletion attempts"""
        # TODO: Implement test for concurrent deletion
        pass
