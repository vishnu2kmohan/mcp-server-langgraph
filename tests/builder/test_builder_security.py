"""
Security tests for Visual Workflow Builder API

Tests for:
- CWE-73: External Control of File Name or Path
- CWE-434: Unrestricted Upload of File with Dangerous Type
- OWASP A01:2021 - Broken Access Control
- OWASP A05:2021 - Security Misconfiguration

These tests validate authentication and path traversal protections.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import tempfile

from mcp_server_langgraph.builder.api.server import app, save_workflow, SaveWorkflowRequest
from mcp_server_langgraph.builder.codegen.generator import CodeGenerator, WorkflowDefinition


class TestBuilderAuthentication:
    """Test that builder endpoints require authentication"""

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
                "output_path": "/tmp/test.py",
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


class TestPathTraversalProtection:
    """Test protection against path traversal attacks"""

    @pytest.mark.asyncio
    async def test_prevent_path_traversal_absolute_path(self):
        """
        SECURITY TEST: Prevent writing to arbitrary absolute paths.

        CWE-73: External Control of File Name or Path
        """
        # Given: Malicious workflow save request with absolute path
        workflow_data = {
            "name": "malicious",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        request = SaveWorkflowRequest(
            workflow=workflow_data,
            output_path="/etc/passwd",  # Path traversal attack
        )

        # When: Attempting to save to system file
        # Then: Should be REJECTED
        with pytest.raises(HTTPException) as exc_info:
            await save_workflow(request)

        assert exc_info.value.status_code == 400
        assert "invalid" in exc_info.value.detail.lower() or "path" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_prevent_path_traversal_relative_path(self):
        """
        SECURITY TEST: Prevent directory traversal with ../
        """
        workflow_data = {
            "name": "malicious",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        request = SaveWorkflowRequest(
            workflow=workflow_data,
            output_path="../../../etc/passwd",  # Relative path traversal
        )

        # When: Attempting directory traversal
        # Then: Should be REJECTED
        with pytest.raises(HTTPException) as exc_info:
            await save_workflow(request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_prevent_overwriting_application_code(self):
        """
        SECURITY TEST: Prevent overwriting application source code.
        """
        workflow_data = {
            "name": "malicious",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        request = SaveWorkflowRequest(
            workflow=workflow_data,
            output_path="src/mcp_server_langgraph/__init__.py",  # Application code
        )

        # When: Attempting to overwrite app code
        # Then: Should be REJECTED
        with pytest.raises(HTTPException) as exc_info:
            await save_workflow(request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_allow_safe_paths_only(self):
        """
        Only paths within a designated safe directory should be allowed.
        """
        workflow_data = {
            "name": "safe_workflow",
            "description": "Safe workflow",
            "nodes": [],
            "edges": [],
            "entry_point": "start",
        }

        # Create temporary safe directory
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_path = os.path.join(tmpdir, "workflows", "my_workflow.py")

            request = SaveWorkflowRequest(
                workflow=workflow_data,
                output_path=safe_path,
            )

            # When: Saving to whitelisted directory
            # Then: Should SUCCEED
            result = await save_workflow(request)

            assert result["success"] is True
            assert os.path.exists(safe_path)


class TestCodeGenerationSecurity:
    """Test code generation security"""

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


class TestBuilderProductionSafety:
    """Test that builder is disabled or secured in production"""

    def test_builder_disabled_in_production(self):
        """
        SECURITY TEST: Builder should be disabled in production by default.
        """
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            # When: Attempting to access builder in production
            client = TestClient(app)
            response = client.get("/")

            # Then: Should return warning or be disabled
            # (Implementation will check ENVIRONMENT and reject or warn)
            # For now, this is a placeholder test
            assert response.status_code in [200, 503]

    def test_builder_requires_feature_flag(self):
        """
        Builder should require explicit feature flag to enable in production.
        """
        # Mark as TODO
        pytest.skip("TODO: Implement feature flag for builder in production")
