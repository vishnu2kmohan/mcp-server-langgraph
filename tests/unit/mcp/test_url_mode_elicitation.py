"""
Tests for MCP URL Mode Elicitation (SEP-1036).

MCP 2025-11-25 adds URL mode elicitation for secure OAuth credential
collection. When mode="url", clients open the URL in a browser for
authentication instead of inline form rendering.

TDD: RED phase - Define expected behavior for SEP-1036 implementation.
"""

import pytest

pytestmark = pytest.mark.unit


class TestElicitationMode:
    """Test elicitation mode types."""

    def test_elicitation_request_default_mode_is_inline(self) -> None:
        """ElicitationRequest should default to inline mode."""
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationRequest,
            ElicitationSchema,
        )

        schema = ElicitationSchema(
            type="object",
            properties={"name": {"type": "string"}},
        )

        request = ElicitationRequest(
            message="Enter your name",
            requestedSchema=schema,
        )

        # Default mode should be "inline"
        assert request.mode == "inline"
        assert request.url is None

    def test_elicitation_request_inline_mode(self) -> None:
        """ElicitationRequest with explicit inline mode."""
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationRequest,
            ElicitationSchema,
        )

        schema = ElicitationSchema(
            type="object",
            properties={"value": {"type": "string"}},
        )

        request = ElicitationRequest(
            message="Enter value",
            requestedSchema=schema,
            mode="inline",
        )

        assert request.mode == "inline"
        assert request.url is None

    def test_elicitation_request_url_mode_with_url(self) -> None:
        """ElicitationRequest with URL mode should include URL."""
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationRequest,
            ElicitationSchema,
        )

        schema = ElicitationSchema(type="object")

        request = ElicitationRequest(
            message="Authenticate with OAuth",
            requestedSchema=schema,
            mode="url",
            url="https://auth.example.com/oauth/authorize",
        )

        assert request.mode == "url"
        assert request.url == "https://auth.example.com/oauth/authorize"


class TestElicitationUrlModeJsonRpc:
    """Test URL mode in JSON-RPC serialization."""

    def test_url_mode_elicitation_to_jsonrpc(self) -> None:
        """URL mode elicitation should include mode and url in JSON-RPC."""
        from mcp_server_langgraph.mcp.elicitation import (
            Elicitation,
            ElicitationSchema,
        )

        schema = ElicitationSchema(type="object")

        elicitation = Elicitation(
            id="test-123",
            request_id=1,
            message="OAuth authentication required",
            requestedSchema=schema,
            mode="url",
            url="https://keycloak.example.com/auth?redirect_uri=...",
        )

        jsonrpc = elicitation.to_jsonrpc()

        assert jsonrpc["method"] == "elicitation/create"
        params = jsonrpc["params"]
        assert params["mode"] == "url"
        assert params["url"] == "https://keycloak.example.com/auth?redirect_uri=..."

    def test_inline_mode_elicitation_to_jsonrpc(self) -> None:
        """Inline mode elicitation should include mode in JSON-RPC."""
        from mcp_server_langgraph.mcp.elicitation import (
            Elicitation,
            ElicitationSchema,
        )

        schema = ElicitationSchema(
            type="object",
            properties={"confirm": {"type": "boolean"}},
        )

        elicitation = Elicitation(
            id="test-456",
            request_id=2,
            message="Confirm action?",
            requestedSchema=schema,
            mode="inline",
        )

        jsonrpc = elicitation.to_jsonrpc()

        params = jsonrpc["params"]
        assert params["mode"] == "inline"
        assert "url" not in params or params.get("url") is None


class TestElicitationHandlerUrlMode:
    """Test ElicitationHandler with URL mode support."""

    def test_create_url_mode_elicitation(self) -> None:
        """ElicitationHandler should create URL mode elicitations."""
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationHandler,
            ElicitationSchema,
        )

        handler = ElicitationHandler()
        schema = ElicitationSchema(type="object")

        elicitation = handler.create_elicitation(
            message="OAuth login required",
            schema=schema,
            mode="url",
            url="https://oauth.example.com/authorize",
        )

        assert elicitation.mode == "url"
        assert elicitation.url == "https://oauth.example.com/authorize"

    def test_create_inline_mode_elicitation(self) -> None:
        """ElicitationHandler should create inline mode elicitations."""
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationHandler,
            ElicitationSchema,
        )

        handler = ElicitationHandler()
        schema = ElicitationSchema(
            type="object",
            properties={"name": {"type": "string"}},
        )

        elicitation = handler.create_elicitation(
            message="Enter your name",
            schema=schema,
        )

        assert elicitation.mode == "inline"
        assert elicitation.url is None


class TestTypescriptTypes:
    """Test that TypeScript types are aligned with Python models."""

    def test_elicitation_mode_types_defined(self) -> None:
        """Verify the expected modes are supported."""
        from mcp_server_langgraph.mcp.elicitation import (
            ElicitationRequest,
            ElicitationSchema,
        )

        schema = ElicitationSchema(type="object")

        # Both modes should be valid
        inline_req = ElicitationRequest(
            message="Inline test",
            requestedSchema=schema,
            mode="inline",
        )
        assert inline_req.mode == "inline"

        url_req = ElicitationRequest(
            message="URL test",
            requestedSchema=schema,
            mode="url",
            url="https://example.com",
        )
        assert url_req.mode == "url"
