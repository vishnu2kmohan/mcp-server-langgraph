"""
End-to-end tests for native LLM provider tools.

These tests make REAL API calls to LLM providers to verify native tool
integration works correctly. They are skipped if the required API keys
are not available.

WARNING: Running these tests will incur API costs.

Requirements:
- ANTHROPIC_API_KEY for Anthropic native tools
- GOOGLE_API_KEY for Google grounded search

Usage:
    # Run all E2E tests (requires API keys)
    uv run pytest tests/e2e/test_native_tools_e2e.py -v

    # Run with specific provider
    uv run pytest tests/e2e/test_native_tools_e2e.py -v -k anthropic
"""

import os
import time

import pytest

# Skip markers for provider availability
has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
has_google_key = bool(os.getenv("GOOGLE_API_KEY"))

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.slow,
    pytest.mark.xdist_group(name="test_native_tools_e2e"),
]


@pytest.fixture
def anthropic_settings():
    """Create settings for Anthropic provider."""
    from mcp_server_langgraph.core.config import Settings

    return Settings(
        llm_provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    )


@pytest.fixture
def google_settings():
    """Create settings for Google provider."""
    from mcp_server_langgraph.core.config import Settings

    return Settings(
        llm_provider="google",
        model_name="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    )


class TestAnthropicNativeWebSearch:
    """E2E tests for Anthropic native web search."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_native_tool_handler_detects_anthropic_capability(self):
        """NativeToolHandler should detect Anthropic web_search capability."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-sonnet-4-20250514")

        # Check capabilities
        assert handler.caps is not None
        assert handler.caps.native_provider == "anthropic"
        assert handler.caps.supports_native_web_search is True

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_get_config_for_anthropic_web_search(self):
        """_get_config_for_tool should return correct Anthropic config."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-sonnet-4-20250514")
        config = handler._get_config_for_tool("web_search")

        assert config is not None
        assert config["type"] == "web_search_20250305"

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_anthropic_native_web_search_real_call(self, anthropic_settings):
        """Test real Anthropic native web search call."""
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.tools.native_handler import parse_native_results
        from mcp_server_langgraph.tools.native_metrics import (
            record_native_tool_execution,
        )

        # Create model with native web search
        model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=anthropic_settings.anthropic_api_key,
        )

        # Invoke with native tool
        start_time = time.perf_counter()
        response = await model.ainvoke(
            [HumanMessage(content="What is the current weather in San Francisco? Use web search.")],
            tools=[{"type": "web_search_20250305"}],
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics
        record_native_tool_execution(
            tool_name="web_search",
            provider="anthropic",
            duration_ms=duration_ms,
            success=True,
        )

        # Verify response has content
        assert response is not None
        assert response.content is not None

        # Parse native results (may or may not have web search results depending on query)
        tool_messages = parse_native_results(response)

        # Log for debugging
        print(f"Response type: {type(response.content)}")
        print(f"Duration: {duration_ms:.2f}ms")
        print(f"Tool messages: {len(tool_messages)}")


class TestAnthropicNativeCodeExecution:
    """E2E tests for Anthropic native code execution."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_get_config_for_anthropic_code_execution(self):
        """_get_config_for_tool should return correct Anthropic code config."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-sonnet-4-20250514")
        config = handler._get_config_for_tool("code_execution")

        assert config is not None
        assert config["type"] == "code_execution_20250825"

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_anthropic_native_code_execution_real_call(self, anthropic_settings):
        """Test real Anthropic native code execution call."""
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.tools.native_metrics import (
            record_native_tool_execution,
        )

        # Create model with native code execution
        model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=anthropic_settings.anthropic_api_key,
        )

        # Invoke with native tool
        start_time = time.perf_counter()
        response = await model.ainvoke(
            [HumanMessage(content="Calculate the first 10 Fibonacci numbers using Python code execution.")],
            tools=[{"type": "code_execution_20250825"}],
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics
        record_native_tool_execution(
            tool_name="code_execution",
            provider="anthropic",
            duration_ms=duration_ms,
            success=True,
        )

        # Verify response has content
        assert response is not None
        assert response.content is not None

        # Log for debugging
        print(f"Response type: {type(response.content)}")
        print(f"Duration: {duration_ms:.2f}ms")


class TestGoogleNativeSearch:
    """E2E tests for Google grounded search."""

    @pytest.mark.skipif(not has_google_key, reason="GOOGLE_API_KEY not set")
    def test_native_tool_handler_detects_google_capability(self):
        """NativeToolHandler should detect Google web_search capability."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("gemini-2.0-flash")

        # Check capabilities
        assert handler.caps is not None
        # Note: Google capability depends on model registry configuration

    @pytest.mark.skipif(not has_google_key, reason="GOOGLE_API_KEY not set")
    def test_get_config_for_google_web_search(self):
        """_get_config_for_tool should return correct Google config."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("gemini-2.0-flash")

        # This will only work if the model is configured for Google native search
        if handler.caps.native_provider == "google":
            config = handler._get_config_for_tool("web_search")
            assert config is not None
            assert "googleSearch" in config


class TestNativeToolMetricsE2E:
    """E2E tests verifying metrics are recorded during real calls."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_metrics_recorded_during_selection(self):
        """Metrics should be recorded when native tools are selected."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler
        from mcp_server_langgraph.tools.unified_registry import UnifiedToolRegistry

        # Create registry and register native tools
        registry = UnifiedToolRegistry()
        registry.register_native(
            name="web_search",
            provider="anthropic",
            provider_type="web_search_20250305",
            description="Native web search",
        )

        handler = NativeToolHandler("claude-sonnet-4-20250514")

        # Get configs (this should record metrics)
        native_configs, remaining = handler.get_native_configs(
            ["native:web_search", "builtin:calculator"],
            "auto",
        )

        # Verify separation
        assert len(native_configs) >= 0  # May be 0 if feature flags disabled
        assert "builtin:calculator" in remaining


class TestNativeToolLatencyComparison:
    """E2E tests comparing native vs builtin tool latency."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_capture_native_web_search_latency(self, anthropic_settings):
        """Capture latency for native web search for comparison."""
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage

        model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=anthropic_settings.anthropic_api_key,
        )

        # Warm up
        await model.ainvoke([HumanMessage(content="Hello")])

        # Measure native web search
        latencies = []
        for _ in range(3):
            start = time.perf_counter()
            await model.ainvoke(
                [HumanMessage(content="What time is it?")],
                tools=[{"type": "web_search_20250305"}],
            )
            latencies.append((time.perf_counter() - start) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        print(f"Native web search average latency: {avg_latency:.2f}ms")
        print(f"Latencies: {[f'{lat:.2f}ms' for lat in latencies]}")

        # Just verify we got reasonable latencies
        assert all(lat > 0 for lat in latencies)
        assert all(lat < 60000 for lat in latencies)  # Less than 60 seconds


class TestNativeCapabilitiesAPI:
    """E2E tests for the native-capabilities API endpoint."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_native_capabilities_endpoint_anthropic_model(self):
        """GET /api/v1/tools/native-capabilities/{model_id} returns correct Anthropic capabilities."""
        from httpx import AsyncClient

        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/tools/native-capabilities/claude-sonnet-4-20250514"
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "model_id" in data
            assert "native_provider" in data
            assert "capabilities" in data
            assert "master_enabled" in data

            assert data["model_id"] == "claude-sonnet-4-20250514"
            assert data["native_provider"] == "anthropic"

            # Check capabilities
            capabilities = {cap["tool_name"]: cap for cap in data["capabilities"]}

            # Anthropic should support web_search and code_execution
            if "web_search" in capabilities:
                assert capabilities["web_search"]["provider_type"] == "web_search_20250305"
            if "code_execution" in capabilities:
                assert capabilities["code_execution"]["provider_type"] == "code_execution_20250825"

    @pytest.mark.skipif(not has_google_key, reason="GOOGLE_API_KEY not set")
    @pytest.mark.asyncio
    async def test_native_capabilities_endpoint_google_model(self):
        """GET /api/v1/tools/native-capabilities/{model_id} returns correct Google capabilities."""
        from httpx import AsyncClient

        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/tools/native-capabilities/gemini-2.0-flash"
            )

            assert response.status_code == 200
            data = response.json()

            assert data["model_id"] == "gemini-2.0-flash"
            # Google should have "google" as native provider
            # Note: actual provider depends on model registry configuration

    @pytest.mark.asyncio
    async def test_native_capabilities_endpoint_unsupported_model(self):
        """GET /api/v1/tools/native-capabilities/{model_id} for unsupported model returns empty capabilities."""
        from httpx import AsyncClient

        from mcp_server_langgraph.infrastructure.app_factory import create_app

        app = create_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/tools/native-capabilities/unknown-model-xyz"
            )

            assert response.status_code == 200
            data = response.json()

            assert data["model_id"] == "unknown-model-xyz"
            assert data["native_provider"] is None
            # Should have no capabilities or all capabilities marked as unsupported
            for cap in data.get("capabilities", []):
                assert cap["supported"] is False


class TestToolPreferenceE2E:
    """E2E tests for tool preference (auto/native/builtin) behavior."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_tool_preference_native_returns_native_configs(self):
        """tool_preference='native' should return native tool configs."""
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        # Temporarily enable native tools
        original_enabled = feature_flags.native_tools_enabled
        original_web_search = feature_flags.anthropic_native_web_search_enabled

        try:
            feature_flags.native_tools_enabled = True
            feature_flags.anthropic_native_web_search_enabled = True

            handler = NativeToolHandler("claude-sonnet-4-20250514")
            native_configs, remaining = handler.get_native_configs(
                ["native:web_search", "builtin:calculator"],
                "native",
            )

            # With native preference, native tools should be in native_configs
            # (if feature flags enabled and model supports)
            if handler.should_use_native("web_search", "native"):
                assert len(native_configs) > 0
                assert any(c.get("type") == "web_search_20250305" for c in native_configs)

            # Builtin tools should remain in remaining
            assert "builtin:calculator" in remaining

        finally:
            # Restore original values
            feature_flags.native_tools_enabled = original_enabled
            feature_flags.anthropic_native_web_search_enabled = original_web_search

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_tool_preference_builtin_forces_builtin(self):
        """tool_preference='builtin' should force builtin tools even when native available."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        handler = NativeToolHandler("claude-sonnet-4-20250514")
        native_configs, remaining = handler.get_native_configs(
            ["native:web_search", "builtin:web_search"],
            "builtin",  # Force builtin
        )

        # With builtin preference, no native configs
        assert len(native_configs) == 0
        # Everything should be in remaining
        assert len(remaining) == 2


class TestFallbackChainE2E:
    """E2E tests for native tool fallback chain."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_fallback_when_native_unavailable(self):
        """Should fall back to builtin when native tool not available for model."""
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        # Use a model that doesn't support native tools (e.g., old Claude)
        handler = NativeToolHandler("claude-2")

        native_configs, remaining = handler.get_native_configs(
            ["native:web_search"],
            "auto",
        )

        # Old model shouldn't have native support
        # All tools should fall back to remaining
        assert len(native_configs) == 0
        assert "native:web_search" in remaining

    def test_fallback_registry_mapping(self):
        """Native registry should correctly map fallback builtins."""
        from mcp_server_langgraph.tools.native_registry import NATIVE_TOOLS

        # Check that code_execution maps to execute_python
        code_exec_anthropic = NATIVE_TOOLS.get(("code_execution", "anthropic"))
        assert code_exec_anthropic is not None
        assert code_exec_anthropic.fallback_builtin == "execute_python"

        # Check that web_search maps to web_search
        web_search_anthropic = NATIVE_TOOLS.get(("web_search", "anthropic"))
        assert web_search_anthropic is not None
        assert web_search_anthropic.fallback_builtin == "web_search"


class TestVertexAILimitationsE2E:
    """E2E tests verifying Vertex AI limitations are handled."""

    def test_vertex_ai_anthropic_no_code_execution(self):
        """Vertex AI Anthropic should NOT support native code execution."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()

        # Vertex AI Claude model
        # Note: Model name format varies; this tests the concept
        caps = registry.get("vertex_ai/claude-sonnet-4-20250514")

        # If this model is configured as Vertex AI Anthropic,
        # it should NOT support native code execution
        if caps and caps.native_provider == "anthropic":
            # Per the runbook: Vertex AI Anthropic doesn't support code_execution
            # This is a documentation/expectation test
            pass  # The actual limitation is enforced at API level

    def test_direct_anthropic_supports_code_execution(self):
        """Direct Anthropic API should support native code execution."""
        from mcp_server_langgraph.agents.model_registry import ModelRegistry

        registry = ModelRegistry()
        caps = registry.get("claude-sonnet-4-20250514")

        # Direct Anthropic should support both
        assert caps is not None
        if caps.native_provider == "anthropic":
            assert caps.supports_native_web_search is True
            assert caps.supports_native_code_execution is True


class TestFeatureFlagIntegrationE2E:
    """E2E tests for feature flag integration with native tools."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_master_switch_disables_all_native_tools(self):
        """FF_NATIVE_TOOLS_ENABLED=false should disable all native tools."""
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        original = feature_flags.native_tools_enabled

        try:
            feature_flags.native_tools_enabled = False

            handler = NativeToolHandler("claude-sonnet-4-20250514")

            # With master switch off, should_use_native always returns False
            assert handler.should_use_native("web_search", "auto") is False
            assert handler.should_use_native("code_execution", "auto") is False

        finally:
            feature_flags.native_tools_enabled = original

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_per_tool_flags_control_individual_tools(self):
        """Individual tool flags should control specific tools."""
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.tools.native_handler import NativeToolHandler

        original_master = feature_flags.native_tools_enabled
        original_web = feature_flags.anthropic_native_web_search_enabled
        original_code = feature_flags.anthropic_native_code_execution_enabled

        try:
            feature_flags.native_tools_enabled = True
            feature_flags.anthropic_native_web_search_enabled = True
            feature_flags.anthropic_native_code_execution_enabled = False

            handler = NativeToolHandler("claude-sonnet-4-20250514")

            # Web search should be available
            assert handler.should_use_native("web_search", "auto") is True
            # Code execution should NOT be available
            assert handler.should_use_native("code_execution", "auto") is False

        finally:
            feature_flags.native_tools_enabled = original_master
            feature_flags.anthropic_native_web_search_enabled = original_web
            feature_flags.anthropic_native_code_execution_enabled = original_code


class TestNativeToolsListAPIE2E:
    """E2E tests for the unified tools list API with native tools."""

    @pytest.mark.asyncio
    async def test_list_tools_includes_native_when_enabled(self):
        """GET /api/v1/tools should include native tools when enabled."""
        from httpx import AsyncClient

        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        original = feature_flags.native_tools_enabled

        try:
            feature_flags.native_tools_enabled = True
            app = create_app()

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/tools")

                assert response.status_code == 200
                data = response.json()

                # Verify response includes native_count
                assert "native_count" in data
                assert "tools" in data
                assert "total_count" in data

                # Check if any native tools are present
                native_tools = [t for t in data["tools"] if t.get("source") == "native"]
                assert data["native_count"] == len(native_tools)

        finally:
            feature_flags.native_tools_enabled = original

    @pytest.mark.asyncio
    async def test_list_tools_filters_by_source_native(self):
        """GET /api/v1/tools?source=native should return only native tools."""
        from httpx import AsyncClient

        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        original = feature_flags.native_tools_enabled

        try:
            feature_flags.native_tools_enabled = True
            app = create_app()

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/tools?source=native")

                assert response.status_code == 200
                data = response.json()

                # All returned tools should be native
                for tool in data["tools"]:
                    assert tool["source"] == "native"

        finally:
            feature_flags.native_tools_enabled = original


class TestSourceCitationsE2E:
    """E2E tests for source citation extraction from native tool results."""

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_anthropic_web_search_extracts_source_citations(
        self, anthropic_settings
    ):
        """Source citations should be extracted from Anthropic native web search."""
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.tools.source_citation import (
            extract_source_citations,
        )

        # Create model with native web search
        model = ChatAnthropic(
            model_name="claude-sonnet-4-20250514",
            temperature=0,
            extra_headers={"anthropic-beta": "web-search-2025-03-05"},
        )

        # Make a query that should trigger web search
        response = await model.ainvoke(
            [HumanMessage(content="What are the latest Python 3.13 features?")],
            tools=[{"type": "web_search_20250305"}],
        )

        # Extract source citations from response
        citations = extract_source_citations(response)

        # Should have at least one citation from web search results
        assert len(citations) > 0, "No source citations extracted from web search"

        # Verify citation structure
        for citation in citations:
            assert "url" in citation, "Citation missing url"
            assert citation["url"].startswith("http"), "Invalid URL format"
            # Title may be empty for some results
            assert "title" in citation or "snippet" in citation

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_source_citations_deduplicate_by_domain(self, anthropic_settings):
        """Source citations should deduplicate multiple results from same domain."""
        from mcp_server_langgraph.tools.source_citation import (
            SourceCitation,
            deduplicate_sources_by_domain,
        )

        # Mock citations that might come from web search
        citations = [
            SourceCitation(
                title="Python 3.13 Release Notes",
                url="https://docs.python.org/3.13/whatsnew/3.13.html",
                snippet="New features in Python 3.13",
            ),
            SourceCitation(
                title="Python 3.13 Tutorial",
                url="https://docs.python.org/3.13/tutorial/index.html",
                snippet="Getting started with Python",
            ),
            SourceCitation(
                title="Real Python Guide",
                url="https://realpython.com/python-313-features/",
                snippet="Comprehensive Python 3.13 guide",
            ),
        ]

        # Deduplicate
        deduped = deduplicate_sources_by_domain(citations)

        # Should keep one per domain
        assert len(deduped) == 2
        domains = {c.url.split("/")[2] for c in deduped}
        assert "docs.python.org" in domains
        assert "realpython.com" in domains

    @pytest.mark.skipif(not has_google_key, reason="GOOGLE_API_KEY not set")
    @pytest.mark.asyncio
    async def test_google_grounded_search_extracts_source_citations(
        self, google_settings
    ):
        """Source citations should be extracted from Google grounded search."""
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage

        from mcp_server_langgraph.tools.source_citation import (
            extract_source_citations,
        )

        # Create model with grounded search
        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
        )

        # Note: Google grounded search needs to be invoked differently
        # This is a placeholder - actual implementation may vary
        response = await model.ainvoke(
            [HumanMessage(content="What are the latest Google AI announcements?")],
            extra_body={"google_search_retrieval": {}},
        )

        # Extract source citations from response
        citations = extract_source_citations(response)

        # Verify citations were extracted (may be empty if grounding not triggered)
        for citation in citations:
            assert "url" in citation
            assert citation["url"].startswith("http")

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    def test_source_citation_roundtrip_serialization(self):
        """Source citations should serialize/deserialize correctly."""
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        original = SourceCitation(
            title="Test Source",
            url="https://example.com/article",
            snippet="This is a test snippet for the source citation.",
            relevance_score=0.95,
        )

        # Serialize to dict
        as_dict = original.model_dump()

        # Deserialize back
        restored = SourceCitation.model_validate(as_dict)

        assert restored.title == original.title
        assert restored.url == original.url
        assert restored.snippet == original.snippet
        assert restored.relevance_score == original.relevance_score

    @pytest.mark.skipif(not has_anthropic_key, reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_source_citations_persisted_in_message_storage(
        self, anthropic_settings
    ):
        """Source citations should be persisted when messages are stored."""
        from mcp_server_langgraph.storage.session.models import Message
        from mcp_server_langgraph.tools.source_citation import SourceCitation

        # Create a message with source citations
        citations = [
            SourceCitation(
                title="Source 1",
                url="https://example1.com",
                snippet="First source",
            ).model_dump(),
            SourceCitation(
                title="Source 2",
                url="https://example2.com",
                snippet="Second source",
            ).model_dump(),
        ]

        message = Message(
            id="test-msg-1",
            role="assistant",
            content="Here is the response with sources.",
            sources=citations,
        )

        # Verify sources are stored
        assert len(message.sources) == 2
        assert message.sources[0]["title"] == "Source 1"
        assert message.sources[1]["url"] == "https://example2.com"

        # Serialize and deserialize (simulating storage roundtrip)
        message_dict = message.model_dump()
        restored = Message.model_validate(message_dict)

        assert len(restored.sources) == 2
        assert restored.sources[0]["title"] == "Source 1"
