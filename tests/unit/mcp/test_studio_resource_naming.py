"""
Tests for Studio resource naming migration.

TDD Phase: RED - These tests define the expected behavior after migrating
from playground:// to studio:// URI scheme.

Migration: playground:// -> studio://
Related: ADR for unified Studio frontend consolidation
"""

import pytest

from mcp_server_langgraph.mcp.resources import (
    ResourceContent,
    ResourceHandler,
    alerts_provider,
    create_studio_resource_handler,
    logs_provider,
    metrics_provider,
    traces_provider,
)

pytestmark = pytest.mark.unit

class TestStudioResourceHandlerNaming:
    """Verify studio resource handler uses correct naming."""

    def test_studio_resource_handler_exists(self) -> None:
        """Handler should be named create_studio_resource_handler."""
        handler = create_studio_resource_handler()
        assert isinstance(handler, ResourceHandler)

    def test_handler_returns_resource_handler_instance(self) -> None:
        """Factory should return a properly configured ResourceHandler."""
        handler = create_studio_resource_handler()
        assert hasattr(handler, "list_templates")
        assert hasattr(handler, "register_template")
        assert hasattr(handler, "register_provider")


class TestStudioURIScheme:
    """Verify all templates use studio:// URI scheme."""

    def test_all_templates_use_studio_scheme(self) -> None:
        """All registered templates should use studio:// URI scheme."""
        handler = create_studio_resource_handler()
        templates = handler.list_templates()

        assert len(templates) > 0, "Expected at least one template to be registered"

        for template in templates:
            assert template.uriTemplate.startswith("studio://"), (
                f"Template '{template.name}' uses wrong scheme: {template.uriTemplate}. "
                "Expected studio:// scheme."
            )

    def test_session_traces_uses_studio_uri(self) -> None:
        """Traces template should use studio://session/{session_id}/traces."""
        handler = create_studio_resource_handler()
        templates = handler.list_templates()

        traces = next((t for t in templates if "traces" in t.uriTemplate.lower()), None)
        assert traces is not None, "Expected a traces template to be registered"
        assert traces.uriTemplate == "studio://session/{session_id}/traces"

    def test_session_logs_uses_studio_uri(self) -> None:
        """Logs template should use studio://session/{session_id}/logs."""
        handler = create_studio_resource_handler()
        templates = handler.list_templates()

        logs = next((t for t in templates if "logs" in t.uriTemplate.lower()), None)
        assert logs is not None, "Expected a logs template to be registered"
        assert logs.uriTemplate == "studio://session/{session_id}/logs"

    def test_session_metrics_uses_studio_uri(self) -> None:
        """Metrics template should use studio://session/{session_id}/metrics."""
        handler = create_studio_resource_handler()
        templates = handler.list_templates()

        metrics = next((t for t in templates if "metrics" in t.uriTemplate.lower()), None)
        assert metrics is not None, "Expected a metrics template to be registered"
        assert metrics.uriTemplate == "studio://session/{session_id}/metrics"

    def test_session_alerts_uses_studio_uri(self) -> None:
        """Alerts template should use studio://session/{session_id}/alerts."""
        handler = create_studio_resource_handler()
        templates = handler.list_templates()

        alerts = next((t for t in templates if "alerts" in t.uriTemplate.lower()), None)
        assert alerts is not None, "Expected an alerts template to be registered"
        assert alerts.uriTemplate == "studio://session/{session_id}/alerts"


class TestStudioResourceProviders:
    """Verify resource providers correctly parse studio:// URIs."""

    @pytest.mark.asyncio
    async def test_traces_provider_parses_studio_uri(self) -> None:
        """Traces provider should correctly parse studio:// URI."""
        uri = "studio://session/test-session-123/traces"
        result = await traces_provider(uri)

        assert isinstance(result, ResourceContent)
        assert result.uri == uri
        assert result.mimeType == "application/json"
        assert "test-session-123" in result.text

    @pytest.mark.asyncio
    async def test_logs_provider_parses_studio_uri(self) -> None:
        """Logs provider should correctly parse studio:// URI."""
        uri = "studio://session/test-session-456/logs"
        result = await logs_provider(uri)

        assert isinstance(result, ResourceContent)
        assert result.uri == uri
        assert result.mimeType == "application/json"
        assert "test-session-456" in result.text

    @pytest.mark.asyncio
    async def test_metrics_provider_parses_studio_uri(self) -> None:
        """Metrics provider should correctly parse studio:// URI."""
        uri = "studio://session/test-session-789/metrics"
        result = await metrics_provider(uri)

        assert isinstance(result, ResourceContent)
        assert result.uri == uri
        assert result.mimeType == "application/json"
        assert "test-session-789" in result.text

    @pytest.mark.asyncio
    async def test_alerts_provider_parses_studio_uri(self) -> None:
        """Alerts provider should correctly parse studio:// URI."""
        uri = "studio://session/test-session-abc/alerts"
        result = await alerts_provider(uri)

        assert isinstance(result, ResourceContent)
        assert result.uri == uri
        assert result.mimeType == "application/json"
        assert "test-session-abc" in result.text


class TestNoPlaygroundReferences:
    """Verify no playground:// references remain."""

    def test_no_playground_in_template_uris(self) -> None:
        """No templates should use deprecated playground:// scheme."""
        handler = create_studio_resource_handler()
        templates = handler.list_templates()

        for template in templates:
            assert "playground://" not in template.uriTemplate, (
                f"Template '{template.name}' still uses deprecated playground:// scheme"
            )

    @pytest.mark.asyncio
    async def test_providers_do_not_expect_playground_uri(self) -> None:
        """Providers should work with studio:// URIs, not playground://."""
        # If providers were still parsing playground://, these would fail
        # to extract the session_id correctly
        test_cases = [
            ("studio://session/my-session/traces", traces_provider),
            ("studio://session/my-session/logs", logs_provider),
            ("studio://session/my-session/metrics", metrics_provider),
            ("studio://session/my-session/alerts", alerts_provider),
        ]

        for uri, provider in test_cases:
            result = await provider(uri)
            # If parsing is correct, session_id should be "my-session"
            assert "my-session" in result.text, (
                f"Provider {provider.__name__} failed to parse session_id from {uri}"
            )
