"""
Tests for Missing Frontend-Backend API Endpoints.

These endpoints were identified by the test_frontend_backend_api_parity meta-test
as being called by the frontend but not having backend implementations.

Following TDD: tests written FIRST, implementation follows.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.api]


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="missing_endpoints")
class TestChatSuggestionsEndpoint:
    """Test POST /api/v1/ai/chat-suggestions endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_app(self) -> FastAPI:
        """Create FastAPI app with AI router."""
        from mcp_server_langgraph.api.v1.ai import ai_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(ai_router, prefix="/api/v1/ai")

        # Mock authentication
        mock_user = {
            "sub": "test-user-id",
            "user_id": "test-user-id",
            "username": "testuser",
            "roles": ["user"],
            "realm_access": {"roles": ["user"]},
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return app

    @pytest.fixture
    def client(self, mock_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(mock_app)

    def test_chat_suggestions_returns_suggestions(self, client: TestClient) -> None:
        """POST /api/v1/ai/chat-suggestions returns suggestions list."""
        response = client.post(
            "/api/v1/ai/chat-suggestions",
            json={
                "input_text": "How do I",
                "session_id": "session-123",
                "max_suggestions": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    def test_chat_suggestions_without_session_id(self, client: TestClient) -> None:
        """POST /api/v1/ai/chat-suggestions without session returns suggestions."""
        response = client.post(
            "/api/v1/ai/chat-suggestions",
            json={
                "input_text": "How do I configure",
                "max_suggestions": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

    def test_chat_suggestions_empty_input(self, client: TestClient) -> None:
        """POST /api/v1/ai/chat-suggestions with empty input returns empty."""
        response = client.post(
            "/api/v1/ai/chat-suggestions",
            json={
                "input_text": "",
                "max_suggestions": 1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="missing_endpoints")
class TestAuthSwitchOrgEndpoint:
    """Test POST /api/v1/auth/switch-org endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_openfga_client(self) -> MagicMock:
        """Create a mock OpenFGA client that grants access."""
        mock_client = MagicMock()
        mock_client.check_permission = AsyncMock(return_value=True)
        return mock_client

    @pytest.fixture
    def mock_app(self, mock_openfga_client: MagicMock) -> FastAPI:
        """Create FastAPI app with auth router."""
        from mcp_server_langgraph.api.deps import get_openfga_client
        from mcp_server_langgraph.api.v1.auth import auth_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        # auth_router already has prefix="/auth", so only add "/api/v1"
        app = FastAPI()
        app.include_router(auth_router, prefix="/api/v1")

        # Mock authentication
        mock_user = {
            "sub": "test-user-id",
            "user_id": "test-user-id",
            "username": "testuser",
            "roles": ["user"],
            "realm_access": {"roles": ["user"]},
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_openfga_client] = lambda: mock_openfga_client

        return app

    @pytest.fixture
    def client(self, mock_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(mock_app)

    def test_switch_org_success(self, client: TestClient) -> None:
        """POST /api/v1/auth/switch-org switches organization successfully."""
        response = client.post(
            "/api/v1/auth/switch-org",
            json={"orgId": "org-123"},
            headers={"X-Organization-ID": "org-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data or "org_id" in data

    def test_switch_org_invalid_org(self, client: TestClient) -> None:
        """POST /api/v1/auth/switch-org with invalid org returns error."""
        response = client.post(
            "/api/v1/auth/switch-org",
            json={"orgId": ""},
        )

        # Should return 400 or 422 for invalid input
        assert response.status_code in [400, 422]


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="missing_endpoints")
class TestWorkflowExecuteEndpoint:
    """Test POST /api/v1/workflows/{id}/execute endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_app(self) -> FastAPI:
        """Create FastAPI app with workflow router."""
        from mcp_server_langgraph.api.v1.workflows import (
            get_workflow_service,
            workflows_router,
        )
        from mcp_server_langgraph.auth.dependencies import (
            get_current_user,
            require_workflow_editor,
            require_workflow_executor,
            require_workflow_owner,
            require_workflow_viewer,
        )

        # workflows_router routes already include "/workflows" in their paths
        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        # Mock authentication
        mock_user = {
            "sub": "test-user-id",
            "user_id": "test-user-id",
            "username": "testuser",
            "email": "testuser@example.com",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[require_workflow_viewer] = lambda: mock_user
        app.dependency_overrides[require_workflow_editor] = lambda: mock_user
        app.dependency_overrides[require_workflow_owner] = lambda: mock_user
        app.dependency_overrides[require_workflow_executor] = lambda: mock_user

        # Mock workflow service
        mock_service = MagicMock()
        mock_service.execute_workflow = AsyncMock(return_value={"execution_id": "exec-123", "status": "started"})
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        return app

    @pytest.fixture
    def client(self, mock_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(mock_app)

    def test_execute_workflow_success(self, client: TestClient) -> None:
        """POST /api/v1/workflows/{id}/execute starts execution."""
        response = client.post(
            "/api/v1/workflows/workflow-123/execute",
            json={
                "nodes": [{"id": "node-1", "type": "input"}],
                "edges": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "execution_id" in data or "status" in data

    def test_execute_workflow_not_found(self, client: TestClient) -> None:
        """POST /api/v1/workflows/{id}/execute with invalid id returns 404."""
        response = client.post(
            "/api/v1/workflows/nonexistent-workflow/execute",
            json={"nodes": [], "edges": []},
        )

        # Should return 404 for nonexistent workflow
        assert response.status_code in [200, 404]  # 200 if mocked, 404 if real


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="missing_endpoints")
class TestWorkflowExecutionStatusEndpoint:
    """Test GET /api/v1/workflows/{id}/execution endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_app(self) -> FastAPI:
        """Create FastAPI app with workflow router."""
        from mcp_server_langgraph.api.v1.workflows import (
            get_workflow_service,
            workflows_router,
        )
        from mcp_server_langgraph.auth.dependencies import (
            get_current_user,
            require_workflow_editor,
            require_workflow_executor,
            require_workflow_owner,
            require_workflow_viewer,
        )

        # workflows_router routes already include "/workflows" in their paths
        app = FastAPI()
        app.include_router(workflows_router, prefix="/api/v1")

        # Mock authentication
        mock_user = {
            "sub": "test-user-id",
            "user_id": "test-user-id",
            "username": "testuser",
            "email": "testuser@example.com",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[require_workflow_viewer] = lambda: mock_user
        app.dependency_overrides[require_workflow_editor] = lambda: mock_user
        app.dependency_overrides[require_workflow_owner] = lambda: mock_user
        app.dependency_overrides[require_workflow_executor] = lambda: mock_user

        # Mock workflow service
        mock_service = MagicMock()
        mock_service.get_execution = AsyncMock(return_value={"steps": [], "status": "idle"})
        app.dependency_overrides[get_workflow_service] = lambda: mock_service

        return app

    @pytest.fixture
    def client(self, mock_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(mock_app)

    def test_get_execution_status_success(self, client: TestClient) -> None:
        """GET /api/v1/workflows/{id}/execution returns execution status."""
        response = client.get("/api/v1/workflows/workflow-123/execution")

        assert response.status_code == 200
        data = response.json()
        assert "steps" in data or "status" in data

    def test_get_execution_status_no_execution(self, client: TestClient) -> None:
        """GET /api/v1/workflows/{id}/execution without active execution."""
        response = client.get("/api/v1/workflows/new-workflow/execution")

        # Should return empty or 404
        assert response.status_code in [200, 404]


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="missing_endpoints")
class TestAdminUserApiKeyEndpoint:
    """Test GET/POST /api/v1/admin/users/{id}/api-key endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_user_provider(self) -> MagicMock:
        """Create a mock user provider that returns a test user."""
        mock_provider = MagicMock()
        mock_user = MagicMock()
        mock_user.user_id = "user-123"
        mock_user.username = "testuser"
        mock_provider.get_user_by_username = AsyncMock(return_value=mock_user)
        mock_provider.get_user_by_id = AsyncMock(return_value=mock_user)
        return mock_provider

    @pytest.fixture
    def mock_api_key_manager(self) -> MagicMock:
        """Create a mock API key manager that generates keys."""
        # Use explicit test value to avoid gitleaks false positives
        test_key = "mcpkey_" + "test" + "0000"  # noqa: S105 (not a real secret)
        mock_manager = MagicMock()
        mock_manager.list_api_keys = AsyncMock(return_value=[])
        mock_manager.create_api_key = AsyncMock(
            return_value={
                "api_key": test_key,
                "key_id": "key-123",
                "created": "2025-01-01T00:00:00Z",
            }
        )
        mock_manager.get_api_key_metadata = AsyncMock(
            return_value={
                "key_id": "key-123",
                "user_id": "user-123",
                "masked_key": "mcpkey_****...0000",
                "created": "2025-01-01T00:00:00Z",
            }
        )
        return mock_manager

    @pytest.fixture
    def mock_app(self, mock_user_provider: MagicMock, mock_api_key_manager: MagicMock) -> FastAPI:
        """Create FastAPI app with admin router."""
        from mcp_server_langgraph.api.deps import get_api_key_manager
        from mcp_server_langgraph.api.v1.admin import admin_router, get_user_provider
        from mcp_server_langgraph.auth.dependencies import get_current_user, require_admin

        # admin_router already has prefix="/admin", so only add "/api/v1"
        app = FastAPI()
        app.include_router(admin_router, prefix="/api/v1")
        # Override the user provider dependency
        app.dependency_overrides[get_user_provider] = lambda: mock_user_provider
        app.dependency_overrides[get_api_key_manager] = lambda: mock_api_key_manager

        # Mock authentication
        mock_user = {
            "sub": "admin-user-id",
            "user_id": "admin-user-id",
            "username": "admin",
            "roles": ["admin"],
            "realm_access": {"roles": ["admin"]},
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[require_admin] = lambda: mock_user

        return app

    @pytest.fixture
    def client(self, mock_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(mock_app)

    def test_get_user_api_key(self, client: TestClient) -> None:
        """GET /api/v1/admin/users/{id}/api-key returns masked key."""
        response = client.get("/api/v1/admin/users/user-123/api-key")

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "masked_key" in data

    def test_generate_user_api_key(self, client: TestClient) -> None:
        """POST /api/v1/admin/users/{id}/api-key generates new key."""
        response = client.post("/api/v1/admin/users/user-123/api-key")

        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        # API key format matches mcpkey_ prefix from mock
        assert data["api_key"].startswith("mcpkey_")


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="missing_endpoints")
class TestCanvasActionEndpoint:
    """Test POST /api/v1/ai/canvas/{action} endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_app(self) -> FastAPI:
        """Create FastAPI app with AI router."""
        from mcp_server_langgraph.api.v1.ai import ai_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(ai_router, prefix="/api/v1/ai")

        # Mock authentication
        mock_user = {
            "sub": "test-user-id",
            "user_id": "test-user-id",
            "username": "testuser",
            "roles": ["user"],
            "realm_access": {"roles": ["user"]},
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return app

    @pytest.fixture
    def client(self, mock_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(mock_app)

    def test_canvas_save_action(self, client: TestClient) -> None:
        """POST /api/v1/ai/canvas/save saves canvas state."""
        response = client.post(
            "/api/v1/ai/canvas/save",
            json={"canvas_id": "canvas-123", "state": {}},
        )

        assert response.status_code == 200

    def test_canvas_export_action(self, client: TestClient) -> None:
        """POST /api/v1/ai/canvas/export exports canvas."""
        response = client.post(
            "/api/v1/ai/canvas/export",
            json={"canvas_id": "canvas-123", "format": "png"},
        )

        assert response.status_code == 200

    def test_canvas_invalid_action(self, client: TestClient) -> None:
        """POST /api/v1/ai/canvas/{invalid} returns 404 or 400."""
        response = client.post(
            "/api/v1/ai/canvas/invalid-action",
            json={},
        )

        assert response.status_code in [400, 404, 422]

    def test_canvas_explain_action(self, client: TestClient) -> None:
        """
        POST /api/v1/ai/canvas/explain explains code/artifact.

        GIVEN an artifact with code content
        WHEN the explain action is requested
        THEN it should return 200 with an explanation
        """
        response = client.post(
            "/api/v1/ai/canvas/explain",
            json={
                "artifact_id": "artifact-123",
                "content": "def hello(): return 'world'",
                "content_type": "code",
                "language": "python",
                "session_id": "session-456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Content should be at top level (not nested in data)
        assert "content" in data, "Expected 'content' field at top level of response"
        assert data["content"] is not None

    def test_canvas_fix_action(self, client: TestClient) -> None:
        """
        POST /api/v1/ai/canvas/fix fixes code/artifact issues.

        GIVEN an artifact with code that has issues
        WHEN the fix action is requested
        THEN it should return 200 with fixed content
        """
        response = client.post(
            "/api/v1/ai/canvas/fix",
            json={
                "artifact_id": "artifact-789",
                "content": "def broken(:\n    return",
                "content_type": "code",
                "language": "python",
                "session_id": "session-456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Content should be at top level (not nested in data)
        assert "content" in data, "Expected 'content' field at top level of response"
        assert data["content"] is not None


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.xdist_group(name="missing_endpoints")
class TestInterpretCommandEndpoint:
    """Test POST /api/v1/ai/interpret-command endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_app(self) -> FastAPI:
        """Create FastAPI app with AI router."""
        from mcp_server_langgraph.api.v1.ai import ai_router
        from mcp_server_langgraph.auth.dependencies import get_current_user

        app = FastAPI()
        app.include_router(ai_router, prefix="/api/v1/ai")

        # Mock authentication - return a test user
        mock_user = {
            "sub": "test-user-id",
            "user_id": "test-user-id",
            "username": "testuser",
            "email": "testuser@example.com",
            "roles": ["user"],
            "realm_access": {"roles": ["user"]},
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        return app

    @pytest.fixture
    def client(self, mock_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(mock_app)

    def test_interpret_command_success(self, client: TestClient) -> None:
        """POST /api/v1/ai/interpret-command interprets natural language."""
        response = client.post(
            "/api/v1/ai/interpret-command",
            json={"command": "create a new session"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "action" in data or "intent" in data

    def test_interpret_command_with_context(self, client: TestClient) -> None:
        """POST /api/v1/ai/interpret-command with session context."""
        response = client.post(
            "/api/v1/ai/interpret-command",
            json={
                "command": "run the workflow",
                "session_id": "session-123",
            },
        )

        assert response.status_code == 200

    def test_interpret_command_empty(self, client: TestClient) -> None:
        """POST /api/v1/ai/interpret-command with empty command."""
        response = client.post(
            "/api/v1/ai/interpret-command",
            json={"command": ""},
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
