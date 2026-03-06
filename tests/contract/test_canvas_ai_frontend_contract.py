"""
Contract Tests: Canvas AI Frontend ↔ Backend Parity.

Ensures the frontend CanvasShortcutAction types are supported by the backend
/api/v1/ai/canvas/{action} endpoint.

This test prevents the scenario where:
1. Frontend adds new canvas actions (e.g., "explain", "fix")
2. Backend valid_actions set is not updated
3. Users get 400 Bad Request errors at runtime

Sprint: Post-audit fix for canvas/explain and canvas/fix 400 errors.
Root cause: Frontend had 7 actions, backend only had 5 (with 0 overlap for AI actions).

Run: uv run pytest tests/contract/test_canvas_ai_frontend_contract.py -v
"""

from __future__ import annotations

import gc
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract, pytest.mark.xdist_group(name="canvas_contract")]


def get_frontend_canvas_actions() -> set[str]:
    """
    Extract CanvasShortcutAction types from frontend TypeScript.

    Parses the type definition from CanvasShortcutsMenu.tsx.
    """
    frontend_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "mcp_server_langgraph"
        / "studio"
        / "frontend"
        / "src"
        / "canvas"
        / "CanvasShortcutsMenu.tsx"
    )

    if not frontend_path.exists():
        pytest.skip(f"Frontend canvas file not found at {frontend_path}")

    content = frontend_path.read_text()

    # Parse: export type CanvasShortcutAction = "review" | "comments" | ...
    pattern = r"export type CanvasShortcutAction\s*=\s*([^;]+);"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        pytest.skip("Could not parse CanvasShortcutAction type from frontend")

    type_def = match.group(1)

    # Extract individual action strings
    actions = set(re.findall(r'"(\w+)"', type_def))

    return actions


def get_backend_canvas_actions() -> set[str]:
    """
    Extract valid_actions from backend ai.py endpoint.

    Parses the valid_actions set from execute_canvas_action().
    """
    backend_path = Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1" / "ai.py"

    if not backend_path.exists():
        pytest.skip(f"Backend AI router not found at {backend_path}")

    content = backend_path.read_text()

    # Parse: valid_actions = {"save", "export", ...}
    pattern = r"valid_actions\s*=\s*\{([^}]+)\}"
    match = re.search(pattern, content)

    if not match:
        pytest.skip("Could not parse valid_actions from backend")

    actions_def = match.group(1)

    # Extract individual action strings
    actions = set(re.findall(r'"(\w+)"', actions_def))

    return actions


def get_canvas_request_model_fields() -> set[str]:
    """
    Extract CanvasActionRequest fields from backend.

    Ensures the Pydantic model accepts all fields sent by frontend.
    """
    backend_path = Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1" / "ai.py"

    if not backend_path.exists():
        pytest.skip(f"Backend AI router not found at {backend_path}")

    content = backend_path.read_text()

    # Find CanvasActionRequest class and extract fields
    pattern = r"class CanvasActionRequest\(BaseModel\):(.*?)(?=\nclass|\n@|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        pytest.skip("Could not parse CanvasActionRequest from backend")

    class_body = match.group(1)

    # Extract field names (pattern: field_name: type = Field(...))
    fields = set(re.findall(r"^\s+(\w+):\s*\w+", class_body, re.MULTILINE))

    return fields


@pytest.mark.contract
class TestCanvasAIFrontendBackendContract:
    """
    Contract tests for Canvas AI action parity.

    These tests ensure frontend canvas actions are supported by the backend.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_frontend_canvas_actions_exist(self) -> None:
        """Frontend should define CanvasShortcutAction types."""
        actions = get_frontend_canvas_actions()
        assert len(actions) >= 5, f"Expected at least 5 frontend canvas actions, found {len(actions)}: {actions}"

    def test_backend_canvas_actions_exist(self) -> None:
        """Backend should define valid_actions for canvas endpoint."""
        actions = get_backend_canvas_actions()
        assert len(actions) >= 5, f"Expected at least 5 backend canvas actions, found {len(actions)}: {actions}"

    def test_frontend_ai_actions_supported_by_backend(self) -> None:
        """
        All frontend AI canvas actions must be in backend valid_actions.

        This is the critical test that would have caught the canvas/explain
        and canvas/fix 400 errors.
        """
        frontend_actions = get_frontend_canvas_actions()
        backend_actions = get_backend_canvas_actions()

        # Frontend AI actions that require backend support
        # (These are the actions that call /api/v1/ai/canvas/{action})
        ai_actions = {"explain", "fix", "review", "comments", "logging", "port", "tests"}
        frontend_ai_actions = frontend_actions & ai_actions

        missing = frontend_ai_actions - backend_actions

        if missing:
            pytest.fail(
                f"Frontend canvas AI actions not supported by backend:\n"
                f"  Missing: {sorted(missing)}\n"
                f"  Frontend actions: {sorted(frontend_actions)}\n"
                f"  Backend actions: {sorted(backend_actions)}\n\n"
                f"To fix: Add the missing actions to valid_actions in "
                f"src/mcp_server_langgraph/api/v1/ai.py execute_canvas_action()"
            )

    def test_backend_has_handlers_for_actions(self) -> None:
        """
        Backend should have handler code for each valid_action.

        Ensures that valid_actions aren't just declared but actually implemented.
        """
        backend_path = Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1" / "ai.py"

        if not backend_path.exists():
            pytest.skip(f"Backend AI router not found at {backend_path}")

        content = backend_path.read_text()
        backend_actions = get_backend_canvas_actions()

        # Check that each action has a handler (elif action == "xxx":)
        unhandled = []
        for action in backend_actions:
            # Look for handler pattern
            handler_patterns = [
                f'action == "{action}"',
                f"action == '{action}'",
            ]
            has_handler = any(p in content for p in handler_patterns)
            if not has_handler:
                unhandled.append(action)

        if unhandled:
            pytest.fail(
                f"Backend valid_actions without handlers:\n"
                f"  {sorted(unhandled)}\n\n"
                f"Each action in valid_actions must have a corresponding "
                f"'if/elif action == \"xxx\":' handler."
            )

    def test_canvas_request_model_has_frontend_fields(self) -> None:
        """
        CanvasActionRequest should accept all fields sent by frontend.

        Frontend sends: artifact_id, content, content_type, language, session_id
        Backend model must accept these fields.
        """
        model_fields = get_canvas_request_model_fields()

        # Fields the frontend sends for AI actions
        required_frontend_fields = {
            "artifact_id",
            "content",
            "content_type",
            "language",
            "session_id",
        }

        missing = required_frontend_fields - model_fields

        if missing:
            pytest.fail(
                f"CanvasActionRequest missing fields sent by frontend:\n"
                f"  Missing: {sorted(missing)}\n"
                f"  Model has: {sorted(model_fields)}\n\n"
                f"To fix: Add the missing fields to CanvasActionRequest in "
                f"src/mcp_server_langgraph/api/v1/ai.py"
            )

    def test_canvas_telemetry_actions_match(self) -> None:
        """
        Canvas telemetry action types should match frontend actions.

        Ensures sessionTelemetry.ts CanvasActionEvent includes frontend actions.

        Note: Telemetry types often include `| string` for extensibility,
        so we check that known actions are documented, not exact match.
        """
        frontend_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mcp_server_langgraph"
            / "studio"
            / "frontend"
            / "src"
            / "utils"
            / "sessionTelemetry.ts"
        )

        if not frontend_path.exists():
            pytest.skip(f"Telemetry file not found at {frontend_path}")

        content = frontend_path.read_text()

        # Find CanvasActionEvent interface/type and extract action field
        # Pattern: action: "review" | "comment" | "fix" | ... | string;
        pattern = r"export interface CanvasActionEvent[^}]+action:\s*([^;]+);"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            # Telemetry may use `| string` which accepts any action
            # Check if the type allows arbitrary strings
            if "| string" in content and "CanvasActionEvent" in content:
                # Type is extensible, test passes
                return
            pytest.skip("Could not parse CanvasActionEvent from telemetry")

        action_type_def = match.group(1)

        # Extract quoted action names
        telemetry_actions = set(re.findall(r'"(\w+)"', action_type_def))

        # Check if type includes `| string` for extensibility
        allows_any_string = "string" in action_type_def.replace('"', "")

        frontend_actions = get_frontend_canvas_actions()

        # If telemetry allows any string, all frontend actions are valid
        if allows_any_string:
            return  # Test passes - type is extensible

        # Otherwise, check that telemetry includes frontend actions
        missing = frontend_actions - telemetry_actions

        if missing:
            pytest.fail(
                f"Telemetry CanvasActionEvent missing frontend actions:\n"
                f"  Missing: {sorted(missing)}\n"
                f"  Telemetry has: {sorted(telemetry_actions)}\n"
                f"  Frontend has: {sorted(frontend_actions)}\n\n"
                f"Add missing actions to CanvasActionEvent in sessionTelemetry.ts"
            )


@pytest.mark.contract
class TestCanvasAPIEndpointContract:
    """
    Contract tests for the canvas API endpoint structure.

    Ensures the endpoint path and HTTP methods are correctly defined.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_canvas_endpoint_in_openapi(self) -> None:
        """Canvas action endpoint should be documented in OpenAPI schema."""
        import json

        openapi_path = Path(__file__).parent.parent.parent / "api" / "openapi.json"

        if not openapi_path.exists():
            pytest.skip("OpenAPI schema not found")

        with open(openapi_path) as f:
            schema = json.load(f)

        paths = schema.get("paths", {})

        # Canvas endpoint should exist
        canvas_path = "/api/v1/ai/canvas/{action}"
        assert canvas_path in paths, (
            f"Canvas endpoint {canvas_path} not found in OpenAPI schema.\n"
            f"Run 'uv run python scripts/export_openapi.py' to regenerate."
        )

        # Should support POST method
        assert "post" in paths[canvas_path], f"Canvas endpoint {canvas_path} should support POST method"

    def test_canvas_endpoint_schema_has_action_param(self) -> None:
        """Canvas endpoint should have {action} path parameter."""
        import json

        openapi_path = Path(__file__).parent.parent.parent / "api" / "openapi.json"

        if not openapi_path.exists():
            pytest.skip("OpenAPI schema not found")

        with open(openapi_path) as f:
            schema = json.load(f)

        canvas_path = "/api/v1/ai/canvas/{action}"
        endpoint = schema.get("paths", {}).get(canvas_path, {}).get("post", {})

        parameters = endpoint.get("parameters", [])

        # Should have action path parameter
        action_param = next(
            (p for p in parameters if p.get("name") == "action" and p.get("in") == "path"),
            None,
        )

        assert action_param is not None, "Canvas endpoint missing 'action' path parameter in OpenAPI schema"


def get_canvas_response_model_fields() -> set[str]:
    """
    Extract CanvasActionResponse fields from backend.

    Ensures the response model matches frontend expectations.
    """
    backend_path = Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1" / "ai.py"

    if not backend_path.exists():
        pytest.skip(f"Backend AI router not found at {backend_path}")

    content = backend_path.read_text()

    # Find CanvasActionResponse class and extract fields
    pattern = r"class CanvasActionResponse\(BaseModel\):(.*?)(?=\nclass|\n@|\ndef |\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        pytest.skip("Could not parse CanvasActionResponse from backend")

    class_body = match.group(1)

    # Extract field names (pattern: field_name: type = Field(...))
    fields = set(re.findall(r"^\s+(\w+):\s*\w+", class_body, re.MULTILINE))

    return fields


@pytest.mark.contract
class TestCanvasResponseSchemaContract:
    """
    Contract tests for Canvas action response schema.

    Ensures the backend response matches what the frontend expects.

    This test class would have caught the schema mismatch where frontend
    expected `result.content` but backend returned `result.data.content`.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_canvas_response_has_top_level_content_field(self) -> None:
        """
        CanvasActionResponse should have 'content' at top level.

        Frontend expects: result.content (for AI actions)
        NOT: result.data.content

        This is the critical test that would have caught the schema mismatch.
        """
        response_fields = get_canvas_response_model_fields()

        assert "content" in response_fields, (
            f"CanvasActionResponse missing top-level 'content' field!\n"
            f"  Current fields: {sorted(response_fields)}\n\n"
            f"Frontend expects 'result.content' for AI canvas actions.\n"
            f"To fix: Add 'content: str | None = Field(...)' to CanvasActionResponse in "
            f"src/mcp_server_langgraph/api/v1/ai.py"
        )

    def test_canvas_response_has_expected_fields(self) -> None:
        """
        CanvasActionResponse should have all expected fields.

        Frontend expects:
        - success: boolean
        - message: optional string
        - content: optional string (for AI-generated content)
        - data: optional dict (for additional metadata)
        """
        response_fields = get_canvas_response_model_fields()

        expected_fields = {"success", "message", "content", "data"}
        missing = expected_fields - response_fields

        if missing:
            pytest.fail(
                f"CanvasActionResponse missing expected fields:\n"
                f"  Missing: {sorted(missing)}\n"
                f"  Current fields: {sorted(response_fields)}\n\n"
                f"To fix: Add the missing fields to CanvasActionResponse in "
                f"src/mcp_server_langgraph/api/v1/ai.py"
            )

    def test_ai_handlers_return_content_at_top_level(self) -> None:
        """
        All AI action handlers should return 'content' at top level.

        Verifies that handlers use 'content=...' not 'data={"content": ...}'
        for the AI-generated content.
        """
        backend_path = Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "api" / "v1" / "ai.py"

        if not backend_path.exists():
            pytest.skip(f"Backend AI router not found at {backend_path}")

        content = backend_path.read_text()

        # AI actions that should return content at top level
        ai_actions = {"explain", "fix", "review", "comments", "logging", "port", "tests"}

        # Find handlers with data={"content": ...} pattern (the OLD pattern)
        # This pattern indicates content is nested in data instead of top-level
        old_pattern_matches = []

        for action in ai_actions:
            # Look for handler returning data with nested content
            # Pattern: action == "explain" ... data={ "content": ...
            action_pattern = rf'action == "{action}".*?return CanvasActionResponse\([^)]*data=\{{\s*[^}}]*"content":'
            if re.search(action_pattern, content, re.DOTALL):
                old_pattern_matches.append(action)

        if old_pattern_matches:
            pytest.fail(
                f"AI action handlers using old nested content pattern:\n"
                f"  Handlers with 'data={{\"content\": ...}}': {sorted(old_pattern_matches)}\n\n"
                f"Frontend expects 'result.content', not 'result.data.content'.\n"
                f"To fix: Change these handlers to use 'content=...' at top level:\n"
                f"  CanvasActionResponse(success=True, content=generated_content, data={{...}})"
            )
