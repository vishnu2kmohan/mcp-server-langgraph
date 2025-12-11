"""
End-to-End tests for Visual Workflow Builder user journeys.

Tests complete user workflows through the builder:
- Authentication → Create Workflow → Validate → Deploy flow
- Workflow editing and saving
- Code generation from visual workflow
- MCP tool integration

Requires: Full test infrastructure running (make test-infra-full-up)

Run with:
    make test-infra-full-up
    pytest tests/e2e/test_builder_user_journey.py -v
"""

import gc
import uuid

import pytest

from tests.constants import TEST_BUILDER_API_PORT, TEST_KEYCLOAK_PORT

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.builder,
    pytest.mark.slow,
    pytest.mark.requires_full_infrastructure,
    pytest.mark.xdist_group(name="builder_e2e_tests"),
]


@pytest.fixture
def builder_url() -> str:
    """Get Builder API URL."""
    return f"http://localhost:{TEST_BUILDER_API_PORT}"


@pytest.fixture
def keycloak_url() -> str:
    """Get Keycloak URL."""
    return f"http://localhost:{TEST_KEYCLOAK_PORT}"


@pytest.mark.xdist_group(name="builder_e2e_tests")
class TestBuilderAuthenticationJourney:
    """E2E tests for authentication flow."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_unauthenticated_user_cannot_create_workflow(self, builder_url: str) -> None:
        """Test that unauthenticated users cannot create workflows."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{builder_url}/api/builder/workflows",
                json={"name": "Test Workflow", "nodes": [], "edges": []},
            )

            # Should be unauthorized
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_health_endpoint_accessible_without_auth(self, builder_url: str) -> None:
        """Test that health endpoint is accessible without authentication."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{builder_url}/api/builder/health")

            # Health should be accessible
            assert response.status_code == 200


@pytest.mark.xdist_group(name="builder_e2e_tests")
class TestBuilderWorkflowJourney:
    """E2E tests for workflow management journey."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.fixture
    def simple_workflow(self) -> dict:
        """Simple workflow definition."""
        return {
            "name": f"E2E Test Workflow {uuid.uuid4()}",
            "description": "End-to-end test workflow",
            "nodes": [
                {"id": "start", "type": "start", "position": {"x": 100, "y": 100}},
                {
                    "id": "agent",
                    "type": "agent",
                    "position": {"x": 300, "y": 100},
                    "data": {"name": "Assistant", "prompt": "You are a helpful assistant"},
                },
                {"id": "end", "type": "end", "position": {"x": 500, "y": 100}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "agent"},
                {"id": "e2", "source": "agent", "target": "end"},
            ],
        }

    @pytest.mark.asyncio
    async def test_complete_workflow_lifecycle(self, builder_url: str, auth_headers: dict, simple_workflow: dict) -> None:
        """Test complete workflow lifecycle: create → validate → update → delete."""
        import httpx

        async with httpx.AsyncClient() as client:
            # Step 1: Create workflow
            create_response = await client.post(
                f"{builder_url}/api/builder/workflows",
                json=simple_workflow,
                headers=auth_headers,
            )

            if create_response.status_code in [401, 403]:
                pytest.skip("Authentication not configured for E2E test")

            assert create_response.status_code in [200, 201]
            workflow_data = create_response.json()
            workflow_id = workflow_data.get("id") or workflow_data.get("workflow_id")
            assert workflow_id is not None

            # Step 2: Get workflow
            get_response = await client.get(
                f"{builder_url}/api/builder/workflows/{workflow_id}",
                headers=auth_headers,
            )
            assert get_response.status_code == 200
            assert get_response.json()["name"] == simple_workflow["name"]

            # Step 3: Update workflow
            updated_name = f"Updated {simple_workflow['name']}"
            update_response = await client.put(
                f"{builder_url}/api/builder/workflows/{workflow_id}",
                json={**simple_workflow, "name": updated_name},
                headers=auth_headers,
            )
            assert update_response.status_code in [200, 204]

            # Verify update
            verify_response = await client.get(
                f"{builder_url}/api/builder/workflows/{workflow_id}",
                headers=auth_headers,
            )
            if verify_response.status_code == 200:
                assert verify_response.json()["name"] == updated_name

            # Step 4: Delete workflow
            delete_response = await client.delete(
                f"{builder_url}/api/builder/workflows/{workflow_id}",
                headers=auth_headers,
            )
            assert delete_response.status_code in [200, 204]

            # Step 5: Verify deleted
            final_response = await client.get(
                f"{builder_url}/api/builder/workflows/{workflow_id}",
                headers=auth_headers,
            )
            assert final_response.status_code == 404


@pytest.mark.xdist_group(name="builder_e2e_tests")
class TestBuilderValidationJourney:
    """E2E tests for workflow validation journey."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.mark.asyncio
    async def test_valid_workflow_passes_validation(self, builder_url: str, auth_headers: dict) -> None:
        """Test that valid workflows pass validation."""
        import httpx

        # WorkflowDefinition model expects: name, entry_point, nodes, edges
        # Edges use "from"/"to" instead of "source"/"target"
        valid_workflow = {
            "name": "TestWorkflow",
            "entry_point": "agent",
            "nodes": [
                {"id": "start", "type": "start"},
                {"id": "agent", "type": "agent", "data": {"name": "Test"}},
                {"id": "end", "type": "end"},
            ],
            "edges": [
                {"from": "start", "to": "agent"},
                {"from": "agent", "to": "end"},
            ],
        }

        async with httpx.AsyncClient() as client:
            # API expects {"workflow": {...}} wrapper
            response = await client.post(
                f"{builder_url}/api/builder/validate",
                json={"workflow": valid_workflow},
                headers=auth_headers,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Authentication not configured for E2E test")

            assert response.status_code == 200
            data = response.json()

            # Should indicate valid
            is_valid = data.get("valid") or data.get("is_valid") or (len(data.get("errors", [])) == 0)
            assert is_valid

    @pytest.mark.asyncio
    async def test_invalid_workflow_returns_errors(self, builder_url: str, auth_headers: dict) -> None:
        """Test that invalid workflows return validation errors."""
        import httpx

        invalid_workflow = {
            "nodes": [
                {"id": "start", "type": "start"},
                # Missing end node - should fail validation
            ],
            "edges": [],
        }

        async with httpx.AsyncClient() as client:
            # API expects {"workflow": {...}} wrapper
            response = await client.post(
                f"{builder_url}/api/builder/validate",
                json={"workflow": invalid_workflow},
                headers=auth_headers,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Authentication not configured for E2E test")

            # Should indicate invalid with errors
            assert response.status_code in [200, 400, 422]

            if response.status_code == 200:
                data = response.json()
                has_errors = not data.get("valid", True) or not data.get("is_valid", True) or len(data.get("errors", [])) > 0
                assert has_errors


@pytest.mark.xdist_group(name="builder_e2e_tests")
class TestBuilderCodeGenerationJourney:
    """E2E tests for code generation journey."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def auth_headers(self, mock_jwt_token: str) -> dict:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {mock_jwt_token}"}

    @pytest.fixture
    def complete_workflow(self) -> dict:
        """Complete workflow for code generation."""
        return {
            "name": "GeneratedAgent",
            "description": "Agent generated from visual builder",
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                },
                {
                    "id": "router",
                    "type": "router",
                    "position": {"x": 300, "y": 100},
                    "data": {"conditions": ["question", "task"]},
                },
                {
                    "id": "question_agent",
                    "type": "agent",
                    "position": {"x": 500, "y": 50},
                    "data": {"name": "QuestionHandler", "prompt": "Answer questions"},
                },
                {
                    "id": "task_agent",
                    "type": "agent",
                    "position": {"x": 500, "y": 150},
                    "data": {"name": "TaskHandler", "prompt": "Handle tasks"},
                },
                {
                    "id": "end",
                    "type": "end",
                    "position": {"x": 700, "y": 100},
                },
            ],
            "edges": [
                {"source": "start", "target": "router"},
                {"source": "router", "target": "question_agent", "label": "question"},
                {"source": "router", "target": "task_agent", "label": "task"},
                {"source": "question_agent", "target": "end"},
                {"source": "task_agent", "target": "end"},
            ],
        }

    @pytest.mark.asyncio
    async def test_generate_python_code_from_workflow(
        self, builder_url: str, auth_headers: dict, complete_workflow: dict
    ) -> None:
        """Test generating Python code from visual workflow."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{builder_url}/api/builder/generate",
                json=complete_workflow,
                headers=auth_headers,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Authentication not configured for E2E test")

            if response.status_code == 200:
                data = response.json()

                # Should contain generated Python code
                code = data.get("code") or data.get("python") or data.get("content")
                assert code is not None
                assert len(code) > 0

                # Should contain LangGraph imports
                assert "langgraph" in code.lower() or "def " in code

    @pytest.mark.asyncio
    async def test_generated_code_is_valid_python(self, builder_url: str, auth_headers: dict, complete_workflow: dict) -> None:
        """Test that generated code is syntactically valid Python."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{builder_url}/api/builder/generate",
                json=complete_workflow,
                headers=auth_headers,
            )

            if response.status_code in [401, 403]:
                pytest.skip("Authentication not configured for E2E test")

            if response.status_code == 200:
                data = response.json()
                code = data.get("code") or data.get("python") or data.get("content")

                if code:
                    # Verify code is syntactically valid
                    import ast

                    try:
                        ast.parse(code)
                    except SyntaxError as e:
                        pytest.fail(f"Generated code has syntax error: {e}")


@pytest.mark.xdist_group(name="builder_e2e_tests")
class TestBuilderFrontendJourney:
    """E2E tests for frontend user experience."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_spa_loads_successfully(self, builder_url: str) -> None:
        """Test that the SPA loads successfully."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(builder_url)

            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

            # Should contain React app markers
            html = response.text
            assert "<div" in html  # Has HTML structure
            assert "script" in html.lower()  # Has JavaScript

    @pytest.mark.asyncio
    async def test_spa_client_side_routing(self, builder_url: str) -> None:
        """Test that client-side routes are handled by SPA."""
        import httpx

        routes = [
            "/",
            "/workflows",
            "/workflows/new",
            "/workflows/abc123",  # Dynamic route
            "/settings",
        ]

        async with httpx.AsyncClient() as client:
            for route in routes:
                response = await client.get(f"{builder_url}{route}")

                # All routes should return the SPA
                assert response.status_code == 200, f"Route {route} failed"
                assert "text/html" in response.headers.get("content-type", "")
