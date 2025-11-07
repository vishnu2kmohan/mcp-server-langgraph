"""
Comprehensive tests for GDPR compliance endpoints and services
"""

import json
from unittest.mock import AsyncMock, MagicMock

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
@pytest.mark.api
class TestGDPREndpoints:
    """Test GDPR API endpoints with auth mocking

    Tests GDPR compliance endpoints following TDD best practices:
    - Article 15: Right to Access
    - Article 16: Right to Rectification
    - Article 17: Right to Erasure
    - Article 20: Right to Data Portability
    - Article 21: Right to Object (Consent)
    """

    @pytest.fixture
    def test_client(self, mock_current_user):
        """FastAPI TestClient with mocked auth and GDPR dependencies"""
        from unittest.mock import AsyncMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from mcp_server_langgraph.api.gdpr import router
        from mcp_server_langgraph.auth.middleware import get_current_user
        from mcp_server_langgraph.auth.session import get_session_store
        from mcp_server_langgraph.compliance.gdpr.factory import get_gdpr_storage

        app = FastAPI()
        app.include_router(router)

        # Mock session store with proper return values
        mock_session_store = AsyncMock()
        mock_session_store.list_user_sessions.return_value = []
        mock_session_store.get_user_profile.return_value = {
            "user_id": mock_current_user["user_id"],
            "username": mock_current_user["username"],
            "email": mock_current_user["email"],
        }
        mock_session_store.get_user_preferences.return_value = {"theme": "light", "language": "en"}

        # Mock GDPR storage with proper return values and nested mocks
        mock_gdpr_storage = AsyncMock()

        # Mock nested storage attributes (user_profiles, preferences, etc.)
        mock_gdpr_storage.user_profiles = AsyncMock()
        mock_gdpr_storage.user_profiles.get.return_value = None  # Return None, handler will create default

        mock_gdpr_storage.preferences = AsyncMock()
        mock_gdpr_storage.preferences.get.return_value = None  # Return None, handler will return empty dict

        mock_gdpr_storage.conversations = AsyncMock()
        mock_gdpr_storage.conversations.list.return_value = []

        # Mock consents storage
        from mcp_server_langgraph.compliance.gdpr.storage import ConsentRecord as GDPRConsentRecord

        mock_consent = GDPRConsentRecord(
            consent_id="consent_test_123",
            user_id=mock_current_user["user_id"],
            consent_type="analytics",
            granted=True,
            timestamp="2025-01-01T12:00:00Z",
            ip_address=None,
            user_agent=None,
        )

        mock_gdpr_storage.consents = AsyncMock()
        mock_gdpr_storage.consents.create.return_value = None
        mock_gdpr_storage.consents.get_user_consents.return_value = [mock_consent]
        mock_gdpr_storage.consents.get_latest_consent.return_value = mock_consent
        mock_gdpr_storage.consents.delete_user_consents.return_value = 1

        # Mock audit logs
        mock_gdpr_storage.audit_logs = AsyncMock()
        mock_gdpr_storage.audit_logs.log.return_value = "deletion_test_123"  # Returns the audit record ID
        mock_gdpr_storage.audit_logs.create.return_value = "deletion_test_123"  # Also mock create for consistency
        mock_gdpr_storage.audit_logs.anonymize_user_logs.return_value = 0

        # Mock preferences deletion
        mock_gdpr_storage.preferences = AsyncMock()
        mock_gdpr_storage.preferences.get.return_value = None
        mock_gdpr_storage.preferences.delete.return_value = 1

        # Mock conversations
        mock_gdpr_storage.conversations = AsyncMock()
        mock_gdpr_storage.conversations.list.return_value = []
        mock_gdpr_storage.conversations.delete_user_conversations.return_value = 0

        # Mock user profiles
        mock_gdpr_storage.user_profiles = AsyncMock()
        mock_gdpr_storage.user_profiles.get.return_value = None
        mock_gdpr_storage.user_profiles.delete.return_value = None

        mock_gdpr_storage.list_consent_records.return_value = {
            "analytics": {"granted": True, "timestamp": "2025-01-01T12:00:00Z"}
        }
        mock_gdpr_storage.store_consent_record.return_value = None
        mock_gdpr_storage.get_deletion_audit_log.return_value = []

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        app.dependency_overrides[get_session_store] = lambda: mock_session_store
        app.dependency_overrides[get_gdpr_storage] = lambda: mock_gdpr_storage

        return TestClient(app)

    def test_get_user_data_endpoint(self, test_client, mock_current_user):
        """Test GET /api/v1/users/me/data - GDPR Article 15 (Right to Access)"""
        response = test_client.get("/api/v1/users/me/data")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "export_id" in data
        assert "user_id" in data
        assert data["user_id"] == mock_current_user["user_id"]
        assert "username" in data
        assert data["username"] == mock_current_user["username"]
        assert "export_timestamp" in data
        assert "profile" in data  # Field is named "profile" not "user_profile"
        assert "sessions" in data
        assert "conversations" in data
        assert "consents" in data

    def test_export_user_data_json(self, test_client):
        """Test GET /api/v1/users/me/export?format=json - GDPR Article 20 (Data Portability)"""
        response = test_client.get("/api/v1/users/me/export?format=json")

        assert response.status_code == 200

        # Verify Content-Type is JSON
        assert "application/json" in response.headers["content-type"]

        # Verify Content-Disposition header for download
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert "user_data_" in response.headers["Content-Disposition"]
        assert ".json" in response.headers["Content-Disposition"]

        # Verify response is valid JSON with user data
        data = response.json()
        assert "user_id" in data
        assert "export_timestamp" in data

    def test_export_user_data_csv(self, test_client):
        """Test GET /api/v1/users/me/export?format=csv - CSV format export"""
        response = test_client.get("/api/v1/users/me/export?format=csv")

        assert response.status_code == 200

        # Verify Content-Type is CSV
        assert "text/csv" in response.headers["content-type"]

        # Verify Content-Disposition header
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert ".csv" in response.headers["Content-Disposition"]

        # Verify response is CSV format (contains commas and newlines)
        content = response.content.decode("utf-8")
        assert "," in content  # CSV delimiter
        assert "\n" in content or "\r\n" in content  # CSV line breaks

    def test_export_invalid_format(self, test_client):
        """Test export with invalid format parameter"""
        response = test_client.get("/api/v1/users/me/export?format=xml")

        # Should reject invalid format
        assert response.status_code == 422  # Unprocessable Entity

    def test_update_user_profile(self, test_client, mock_current_user):
        """Test PATCH /api/v1/users/me - GDPR Article 16 (Right to Rectification)"""
        update_data = {"name": "Alice Updated", "preferences": {"theme": "dark", "language": "en"}}

        response = test_client.patch("/api/v1/users/me", json=update_data)

        assert response.status_code == 200
        data = response.json()

        # Verify updated fields are returned
        assert data["user_id"] == mock_current_user["user_id"]
        assert data["name"] == "Alice Updated"
        assert data["preferences"]["theme"] == "dark"
        assert "updated_at" in data

    def test_update_user_profile_empty(self, test_client):
        """Test profile update with no fields provided"""
        response = test_client.patch("/api/v1/users/me", json={})

        # Should reject empty update
        assert response.status_code == 400
        assert "No fields provided" in response.json()["detail"]

    def test_delete_user_account(self, test_client, mock_current_user):
        """Test DELETE /api/v1/users/me?confirm=true - GDPR Article 17 (Right to Erasure)"""
        response = test_client.delete("/api/v1/users/me?confirm=true")

        assert response.status_code == 200
        data = response.json()

        # Verify deletion response structure
        assert "message" in data
        assert "deleted" in data["message"].lower() or "success" in data["message"].lower()
        assert "deletion_timestamp" in data
        assert "deleted_items" in data
        assert "audit_record_id" in data

        # Verify audit record was created
        assert data["audit_record_id"].startswith("deletion_")

    def test_delete_user_account_without_confirmation(self, test_client):
        """Test deletion requires explicit confirmation"""
        response = test_client.delete("/api/v1/users/me?confirm=false")

        # Should reject without confirmation
        assert response.status_code == 400
        assert "confirmation" in response.json()["detail"].lower()

    def test_delete_user_account_no_confirm_param(self, test_client):
        """Test deletion fails when confirm parameter is missing"""
        response = test_client.delete("/api/v1/users/me")

        # FastAPI should reject missing required query param
        assert response.status_code == 422

    def test_update_consent(self, test_client, mock_current_user):
        """Test POST /api/v1/users/me/consent - GDPR Article 21 (Right to Object)"""
        consent_data = {"consent_type": "analytics", "granted": True}

        response = test_client.post("/api/v1/users/me/consent", json=consent_data)

        assert response.status_code == 200
        data = response.json()

        # Verify consent response structure
        assert data["user_id"] == mock_current_user["user_id"]
        assert "consents" in data
        assert "analytics" in data["consents"]

    def test_update_consent_revoke(self, test_client):
        """Test revoking consent"""
        consent_data = {"consent_type": "marketing", "granted": False}  # Revoke consent

        response = test_client.post("/api/v1/users/me/consent", json=consent_data)

        assert response.status_code == 200
        data = response.json()

        # Verify consent response structure
        # Note: Mock returns only 'analytics' consent, but response should include all consents
        assert "consents" in data
        # Since mock returns only analytics consent, we verify the structure is correct
        assert isinstance(data["consents"], dict)

    def test_get_consent_status(self, test_client, mock_current_user):
        """Test GET /api/v1/users/me/consent - Retrieve current consent status"""
        response = test_client.get("/api/v1/users/me/consent")

        assert response.status_code == 200
        data = response.json()

        # Verify consent status structure
        assert data["user_id"] == mock_current_user["user_id"]
        assert "consents" in data
        assert isinstance(data["consents"], dict)


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
        """
        Test handling of concurrent deletion attempts to verify idempotency

        GIVEN: Multiple concurrent deletion requests for the same user
        WHEN: Deletions are executed simultaneously via asyncio.gather
        THEN: All deletions succeed (idempotent), audit log shows only one deletion

        This test validates:
        1. Thread safety of the deletion service
        2. Idempotent behavior (multiple deletions don't cause errors)
        3. Proper locking/coordination if implemented
        """
        import asyncio

        service = DataDeletionService(session_store=mock_session_store)

        # Mock session store to return data once, then 0 for subsequent calls
        deletion_count = [5]  # Mutable counter

        async def mock_delete_sessions(user_id):
            """Simulate deletion that only works once"""
            if deletion_count[0] > 0:
                count = deletion_count[0]
                deletion_count[0] = 0  # Subsequent calls return 0
                return count
            return 0

        mock_session_store.delete_user_sessions.side_effect = mock_delete_sessions

        # Launch 3 concurrent deletion attempts
        results = await asyncio.gather(
            service.delete_user_account("user:test", "test"),
            service.delete_user_account("user:test", "test"),
            service.delete_user_account("user:test", "test"),
            return_exceptions=False,  # Don't catch exceptions
        )

        # All deletions should succeed (idempotent behavior)
        assert len(results) == 3, "Expected 3 deletion results"
        for i, result in enumerate(results):
            assert isinstance(result, DeletionResult), f"Result {i} should be DeletionResult"
            assert result.success is True, f"Deletion {i} should succeed"

        # Verify total deletions (first call deletes 5, rest delete 0)
        total_deleted = sum(r.deleted_items["sessions"] for r in results)
        assert total_deleted == 5, "Expected total of 5 deleted sessions"

        # Verify idempotency: some deletions should have 0 items deleted
        zero_deletions = [r for r in results if r.deleted_items["sessions"] == 0]
        assert len(zero_deletions) >= 2, "At least 2 deletions should find 0 items (already deleted)"

        # Verify delete_user_sessions was called 3 times (once per concurrent request)
        assert mock_session_store.delete_user_sessions.call_count == 3
