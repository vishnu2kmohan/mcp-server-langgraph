"""
Tests for MCP Resources Protocol (2025-06-18 Spec).

Tests the resources/list and resources/read endpoints that allow servers
to expose data and context to clients. Resources are like REST GET endpoints.
"""

import gc
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.mcp.resources import (
    Resource,
    ResourceContent,
    ResourceHandler,
    ResourcesListResponse,
    ResourceReadResponse,
    ResourceTemplate,
)

# Module-level marker for test categorization
pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="mcp_resources")
@pytest.mark.unit
class TestResourceModels:
    """Test resource data models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_resource_creation_with_uri_and_name_succeeds(self) -> None:
        """Test basic resource creation."""
        resource = Resource(
            uri="playground://session/abc123/traces",
            name="Session Traces",
            description="OpenTelemetry traces for this session",
            mimeType="application/json",
        )
        assert resource.uri == "playground://session/abc123/traces"
        assert resource.name == "Session Traces"
        assert resource.mimeType == "application/json"

    def test_resource_without_mime_type(self) -> None:
        """Test resource without explicit MIME type."""
        resource = Resource(
            uri="playground://session/abc123/logs",
            name="Session Logs",
        )
        assert resource.uri == "playground://session/abc123/logs"
        assert resource.mimeType is None

    def test_resource_content_text(self) -> None:
        """Test text resource content."""
        content = ResourceContent(
            uri="playground://session/abc123/summary",
            mimeType="text/plain",
            text="Session summary: 5 messages, 3 tool calls",
        )
        assert content.text is not None
        assert content.blob is None

    def test_resource_content_json(self) -> None:
        """Test JSON resource content."""
        data = {"traces": [{"id": "trace-1", "name": "chat"}]}
        content = ResourceContent(
            uri="playground://session/abc123/traces",
            mimeType="application/json",
            text=json.dumps(data),
        )
        parsed = json.loads(content.text)
        assert parsed["traces"][0]["id"] == "trace-1"

    def test_resource_content_blob(self) -> None:
        """Test binary resource content (base64)."""
        content = ResourceContent(
            uri="playground://session/abc123/screenshot",
            mimeType="image/png",
            blob="iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB",  # Base64
        )
        assert content.blob is not None
        assert content.text is None

    def test_resource_template_with_uri_pattern_succeeds(self) -> None:
        """Test resource template with URI pattern."""
        template = ResourceTemplate(
            uriTemplate="playground://session/{session_id}/traces",
            name="Session Traces",
            description="Traces for a specific session",
            mimeType="application/json",
        )
        assert "{session_id}" in template.uriTemplate

    def test_resources_list_response(self) -> None:
        """Test resources/list response structure."""
        response = ResourcesListResponse(
            resources=[
                Resource(
                    uri="playground://session/abc/traces",
                    name="Traces",
                ),
                Resource(
                    uri="playground://session/abc/logs",
                    name="Logs",
                ),
            ]
        )
        assert len(response.resources) == 2

    def test_resource_read_response(self) -> None:
        """Test resources/read response structure."""
        response = ResourceReadResponse(
            contents=[
                ResourceContent(
                    uri="playground://session/abc/metrics",
                    mimeType="application/json",
                    text='{"latency_p50_ms": 150}',
                )
            ]
        )
        assert len(response.contents) == 1


@pytest.mark.xdist_group(name="mcp_resources")
@pytest.mark.unit
class TestResourceHandler:
    """Test ResourceHandler for managing resources."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def handler(self) -> ResourceHandler:
        """Create a fresh resource handler."""
        return ResourceHandler()

    def test_register_resource_adds_to_resource_list(self, handler: ResourceHandler) -> None:
        """Test registering a new resource."""
        handler.register_resource(
            uri="playground://session/abc/traces",
            name="Session Traces",
            description="Traces for session abc",
            mime_type="application/json",
        )
        resources = handler.list_resources()
        assert len(resources) == 1
        assert resources[0].uri == "playground://session/abc/traces"

    def test_register_template_adds_to_template_list(self, handler: ResourceHandler) -> None:
        """Test registering a resource template."""
        handler.register_template(
            uri_template="playground://session/{session_id}/traces",
            name="Session Traces",
            description="Traces for any session",
            mime_type="application/json",
        )
        templates = handler.list_templates()
        assert len(templates) == 1
        assert "{session_id}" in templates[0].uriTemplate

    def test_register_resource_provider(self, handler: ResourceHandler) -> None:
        """Test registering a resource provider function."""

        async def traces_provider(uri: str) -> ResourceContent:
            return ResourceContent(
                uri=uri,
                mimeType="application/json",
                text='[{"trace_id": "123"}]',
            )

        handler.register_provider(
            uri_pattern="playground://session/*/traces",
            provider=traces_provider,
        )

        assert handler.has_provider("playground://session/abc/traces")

    @pytest.mark.asyncio
    async def test_read_resource(self, handler: ResourceHandler) -> None:
        """Test reading a resource."""

        async def logs_provider(uri: str) -> ResourceContent:
            return ResourceContent(
                uri=uri,
                mimeType="application/json",
                text='[{"level": "info", "message": "test"}]',
            )

        handler.register_resource(
            uri="playground://session/abc/logs",
            name="Logs",
            mime_type="application/json",
        )
        handler.register_provider(
            uri_pattern="playground://session/*/logs",
            provider=logs_provider,
        )

        content = await handler.read_resource("playground://session/abc/logs")
        assert content.mimeType == "application/json"
        assert "info" in content.text

    @pytest.mark.asyncio
    async def test_read_nonexistent_resource(self, handler: ResourceHandler) -> None:
        """Test error when reading nonexistent resource."""
        with pytest.raises(ValueError, match="not found"):
            await handler.read_resource("playground://nonexistent")

    def test_expand_template_with_args_produces_full_uri(self, handler: ResourceHandler) -> None:
        """Test expanding a URI template."""
        handler.register_template(
            uri_template="playground://session/{session_id}/{resource_type}",
            name="Session Resource",
        )

        expanded = handler.expand_template(
            "playground://session/{session_id}/{resource_type}",
            {"session_id": "abc123", "resource_type": "traces"},
        )

        assert expanded == "playground://session/abc123/traces"

    def test_list_resources_for_session(self, handler: ResourceHandler) -> None:
        """Test listing resources filtered by session."""
        handler.register_resource(
            uri="playground://session/session1/traces",
            name="Session 1 Traces",
        )
        handler.register_resource(
            uri="playground://session/session1/logs",
            name="Session 1 Logs",
        )
        handler.register_resource(
            uri="playground://session/session2/traces",
            name="Session 2 Traces",
        )

        session1_resources = handler.list_resources(filter_pattern="playground://session/session1/*")
        assert len(session1_resources) == 2


@pytest.mark.xdist_group(name="mcp_resources")
@pytest.mark.integration
class TestResourceJSONRPC:
    """Test resources via JSON-RPC 2.0 protocol."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def handler(self) -> ResourceHandler:
        """Create handler for JSON-RPC tests."""
        return ResourceHandler()

    def test_resources_list_jsonrpc_format(self, handler: ResourceHandler) -> None:
        """Test resources/list response in JSON-RPC format."""
        handler.register_resource(
            uri="playground://session/abc/traces",
            name="Traces",
            description="Session traces",
            mime_type="application/json",
        )

        resources = handler.list_resources()
        jsonrpc_response = ResourcesListResponse(resources=resources).to_jsonrpc(request_id=1)

        assert jsonrpc_response["jsonrpc"] == "2.0"
        assert jsonrpc_response["id"] == 1
        assert len(jsonrpc_response["result"]["resources"]) == 1

    @pytest.mark.asyncio
    async def test_resources_read_jsonrpc_format(self, handler: ResourceHandler) -> None:
        """Test resources/read response in JSON-RPC format."""

        async def provider(uri: str) -> ResourceContent:
            return ResourceContent(
                uri=uri,
                mimeType="application/json",
                text='{"data": "test"}',
            )

        handler.register_resource(
            uri="playground://test/resource",
            name="Test",
        )
        handler.register_provider(
            uri_pattern="playground://test/*",
            provider=provider,
        )

        content = await handler.read_resource("playground://test/resource")
        jsonrpc_response = ResourceReadResponse(contents=[content]).to_jsonrpc(request_id=2)

        assert jsonrpc_response["jsonrpc"] == "2.0"
        assert jsonrpc_response["id"] == 2
        assert len(jsonrpc_response["result"]["contents"]) == 1


@pytest.mark.xdist_group(name="mcp_resources")
@pytest.mark.integration
class TestResourceSubscriptions:
    """Test resource subscription functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def handler(self) -> ResourceHandler:
        """Create handler for subscription tests."""
        return ResourceHandler()

    def test_subscribe_to_resource(self, handler: ResourceHandler) -> None:
        """Test subscribing to resource changes."""
        handler.register_resource(
            uri="playground://session/abc/logs",
            name="Logs",
        )

        callback = MagicMock()
        subscription_id = handler.subscribe(
            uri="playground://session/abc/logs",
            callback=callback,
        )

        assert subscription_id is not None
        assert handler.has_subscription(subscription_id)

    def test_unsubscribe_from_resource(self, handler: ResourceHandler) -> None:
        """Test unsubscribing from resource changes."""
        handler.register_resource(
            uri="playground://session/abc/logs",
            name="Logs",
        )

        callback = MagicMock()
        subscription_id = handler.subscribe(
            uri="playground://session/abc/logs",
            callback=callback,
        )

        handler.unsubscribe(subscription_id)
        assert not handler.has_subscription(subscription_id)

    @pytest.mark.asyncio
    async def test_notify_subscribers(self, handler: ResourceHandler) -> None:
        """Test notifying subscribers of resource changes."""

        async def provider(uri: str) -> ResourceContent:
            return ResourceContent(
                uri=uri,
                mimeType="application/json",
                text='{"updated": true}',
            )

        handler.register_resource(
            uri="playground://session/abc/logs",
            name="Logs",
        )
        handler.register_provider(
            uri_pattern="playground://session/*/logs",
            provider=provider,
        )

        callback = AsyncMock()
        handler.subscribe(
            uri="playground://session/abc/logs",
            callback=callback,
        )

        await handler.notify_change("playground://session/abc/logs")

        callback.assert_called_once()


@pytest.mark.xdist_group(name="mcp_resources")
@pytest.mark.integration
class TestPlaygroundResources:
    """Test Playground-specific resources."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_traces_resource(self) -> None:
        """Test session traces resource structure."""
        from mcp_server_langgraph.mcp.resources import (
            create_playground_resource_handler,
        )

        handler = create_playground_resource_handler()
        templates = handler.list_templates()

        # Should have traces template
        traces_template = next(
            (t for t in templates if "traces" in t.uriTemplate),
            None,
        )
        assert traces_template is not None
        assert "{session_id}" in traces_template.uriTemplate

    def test_session_logs_resource(self) -> None:
        """Test session logs resource structure."""
        from mcp_server_langgraph.mcp.resources import (
            create_playground_resource_handler,
        )

        handler = create_playground_resource_handler()
        templates = handler.list_templates()

        logs_template = next(
            (t for t in templates if "logs" in t.uriTemplate),
            None,
        )
        assert logs_template is not None

    def test_session_metrics_resource(self) -> None:
        """Test session metrics resource structure."""
        from mcp_server_langgraph.mcp.resources import (
            create_playground_resource_handler,
        )

        handler = create_playground_resource_handler()
        templates = handler.list_templates()

        metrics_template = next(
            (t for t in templates if "metrics" in t.uriTemplate),
            None,
        )
        assert metrics_template is not None

    def test_session_alerts_resource(self) -> None:
        """Test session alerts resource structure."""
        from mcp_server_langgraph.mcp.resources import (
            create_playground_resource_handler,
        )

        handler = create_playground_resource_handler()
        templates = handler.list_templates()

        alerts_template = next(
            (t for t in templates if "alerts" in t.uriTemplate),
            None,
        )
        assert alerts_template is not None
