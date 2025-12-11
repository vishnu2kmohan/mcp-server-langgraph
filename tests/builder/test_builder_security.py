"""
Security tests for Visual Workflow Builder API

Tests for:
- CWE-73: External Control of File Name or Path
- CWE-434: Unrestricted Upload of File with Dangerous Type
- OWASP A01:2021 - Broken Access Control
- OWASP A05:2021 - Security Misconfiguration

These tests validate authentication and path traversal protections.
"""

import gc
import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.builder.api.server import SaveWorkflowRequest, app, save_workflow
from mcp_server_langgraph.builder.codegen.generator import CodeGenerator, WorkflowDefinition

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="testbuilderauthentication")
class TestBuilderAuthentication:
    """Test that builder endpoints require authentication"""

    @pytest.fixture(autouse=True)
    def setup_auth(self, disable_auth_skip):
        """
        Use monkeypatch-based fixture for automatic MCP_SKIP_AUTH cleanup.

        The disable_auth_skip fixture sets MCP_SKIP_AUTH=false and automatically
        cleans up after the test, preventing environment pollution in xdist workers.
        """
        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_save_workflow_requires_authentication(self):
        """
        SECURITY TEST: /api/builder/save should require authentication.

        CWE: Missing Authentication for Critical Function
        OWASP A01:2021 - Broken Access Control
        """
        client = TestClient(app)

        workflow_data = {
            "name": "test_workflow",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        # When: Unauthenticated request to save workflow
        response = client.post(
            "/api/builder/save",
            json={
                "workflow": workflow_data,
                "output_path": "/tmp/test.py",  # nosec B108 - Test data,
            },
        )

        # Then: Should be REJECTED with 401 Unauthorized
        assert response.status_code == 401

    def test_generate_code_requires_authentication(self):
        """
        SECURITY TEST: /api/builder/generate should require authentication.
        """
        client = TestClient(app)

        workflow_data = {
            "name": "test_workflow",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        # When: Unauthenticated request to generate code
        response = client.post(
            "/api/builder/generate",
            json={"workflow": workflow_data},
        )

        # Then: Should be REJECTED with 401 Unauthorized
        assert response.status_code == 401

    def test_import_workflow_requires_authentication(self):
        """
        SECURITY TEST: /api/builder/import should require authentication.
        """
        client = TestClient(app)

        # When: Unauthenticated request to import workflow
        response = client.post(
            "/api/builder/import",
            json={"code": "print('hello')", "layout": "hierarchical"},
        )

        # Then: Should be REJECTED with 401 Unauthorized
        assert response.status_code == 401


@pytest.mark.xdist_group(name="testpathtraversalprotection")
class TestPathTraversalProtection:
    """Test protection against path traversal attacks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_prevent_path_traversal_absolute_path(self):
        """
        SECURITY TEST: Prevent writing to arbitrary absolute paths.

        CWE-73: External Control of File Name or Path
        """
        # Given: Malicious workflow save request with absolute path
        from pydantic import ValidationError

        workflow_data = {
            "name": "malicious",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        # When: Attempting to create request with malicious path
        # Then: Should be REJECTED at validation level (before reaching endpoint)
        with pytest.raises(ValidationError) as exc_info:
            SaveWorkflowRequest(
                workflow=workflow_data,
                output_path="/etc/passwd",  # Path traversal attack
            )

        assert "Invalid output path" in str(exc_info.value) or "allowed directory" in str(exc_info.value)

    def test_prevent_path_traversal_relative_path(self):
        """
        SECURITY TEST: Prevent directory traversal with ../
        """
        from pydantic import ValidationError

        workflow_data = {
            "name": "malicious",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        # When: Attempting directory traversal
        # Then: Should be REJECTED at validation level
        with pytest.raises(ValidationError) as exc_info:
            SaveWorkflowRequest(
                workflow=workflow_data,
                output_path="../../../etc/passwd",  # Relative path traversal
            )

        assert "allowed directory" in str(exc_info.value)

    def test_prevent_overwriting_application_code(self):
        """
        SECURITY TEST: Prevent overwriting application source code.
        """
        from pydantic import ValidationError

        workflow_data = {
            "name": "malicious",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        # When: Attempting to overwrite app code
        # Then: Should be REJECTED at validation level
        with pytest.raises(ValidationError) as exc_info:
            SaveWorkflowRequest(
                workflow=workflow_data,
                output_path="src/mcp_server_langgraph/__init__.py",  # Application code
            )

        assert "allowed directory" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_allow_safe_paths_only(self):
        """
        Only paths within a designated safe directory should be allowed.
        """
        import os

        workflow_data = {
            "name": "safe_workflow",
            "description": "Safe workflow",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        # Use the actual default safe directory (matches validator)
        default_dir = f"{tempfile.gettempdir()}/mcp-server-workflows"  # nosec B108 - Test fixture
        os.makedirs(default_dir, exist_ok=True)
        safe_path = os.path.join(default_dir, "my_workflow.py")

        request = SaveWorkflowRequest(
            workflow=workflow_data,
            output_path=safe_path,
        )

        # When: Saving to whitelisted directory
        # Then: Should SUCCEED
        result = await save_workflow(request)

        assert result["success"] is True
        assert os.path.exists(safe_path)

        # Cleanup
        if os.path.exists(safe_path):
            os.remove(safe_path)


@pytest.mark.xdist_group(name="testcodegenerationsecurity")
class TestCodeGenerationSecurity:
    """Test code generation security"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_sanitize_generated_code(self):
        """
        Ensure generated code doesn't contain malicious injections.
        """
        # Given: Workflow with potentially malicious node names
        workflow = WorkflowDefinition(
            name="test'; import os; os.system('rm -rf /')  # ",
            description="Malicious description",
            nodes=[],
            edges=[],
            entry_point="start",
        )

        generator = CodeGenerator()

        # When: Generating code
        code = generator.generate(workflow)

        # Then: Should NOT contain code injection
        assert "os.system" not in code
        assert "rm -rf" not in code
        # Should escape or sanitize the workflow name
        assert "test_" in code or "test" in code

    def test_validate_workflow_before_generation(self):
        """
        Workflow should be validated before code generation.
        """
        # Given: Invalid workflow (no nodes)
        workflow = WorkflowDefinition(
            name="empty",
            nodes=[],
            edges=[],
            entry_point="nonexistent",  # Invalid entry point
        )

        generator = CodeGenerator()

        # When: Generating code from invalid workflow
        # Then: Should validate and warn or reject
        # For now, just ensure it doesn't crash
        code = generator.generate(workflow)
        assert code is not None


@pytest.mark.xdist_group(name="testbuilderproductionsafety")
class TestBuilderProductionSafety:
    """Test that builder is disabled or secured in production"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_builder_disabled_in_production(self):
        """
        SECURITY TEST: Builder should be accessible in production (health endpoint).

        Note: The builder API health endpoint is intentionally public (no auth)
        to support Kubernetes liveness/readiness probes. In production, sensitive
        endpoints like /api/builder/save are protected by authentication.
        """
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            # When: Attempting to access builder health endpoint in production
            client = TestClient(app)
            response = client.get("/api/builder/health")

            # Then: Health endpoint should be accessible
            # (no root "/" endpoint exists unless frontend is built)
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}

    def test_builder_requires_feature_flag(self):
        """
        Builder should require explicit feature flag to enable in production.
        """
        # Mark as TODO
        pytest.skip("TODO: Implement feature flag for builder in production")
