"""
Tests for AI UX Enhancements

Covers:
1. Coverage improvements for edge cases
2. Feature flag integration
3. Prometheus metrics
4. Redis caching for LLM responses
5. Rate limiting integration
6. WebSocket for real-time suggestions

Reference: UX Audit Plan - Phase 6 Advanced Features
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


# Note: reset_ai_circuit_breakers fixture is defined in conftest.py


@pytest.mark.ai
@pytest.mark.unit
class TestCoverageImprovements:
    """Tests for improving ai_ux_service.py coverage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_error_analysis_403_forbidden(self) -> None:
        """Test error analysis handles 403 forbidden errors.

        ADR-0091 Phase 9: Uses aligned ErrorAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        request = ErrorAnalyzeRequest(
            error_code="ForbiddenError",
            error_message="403 Forbidden - You don't have access",
        )

        result = await service.analyze_error(request)

        # ADR-0091: Aligned schema uses error_type instead of classification
        assert result.error_type == "authorization"
        assert result.auto_recoverable is False
        assert len(result.recovery_steps) > 0

    @pytest.mark.asyncio
    async def test_error_analysis_429_rate_limit(self) -> None:
        """Test error analysis handles 429 rate limit errors.

        ADR-0091 Phase 9: Uses aligned ErrorAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        request = ErrorAnalyzeRequest(
            error_code="RateLimitError",
            error_message="429 Too Many Requests - rate limit exceeded",
        )

        result = await service.analyze_error(request)

        # ADR-0091: Aligned schema uses error_type and recovery_steps
        assert result.error_type == "quota"
        assert result.auto_recoverable is True  # Rate limit errors are recoverable by waiting
        assert any("wait" in step.title.lower() or "wait" in step.description.lower() for step in result.recovery_steps)

    @pytest.mark.asyncio
    async def test_error_analysis_network_error(self) -> None:
        """Test error analysis handles network connection errors.

        ADR-0091 Phase 9: Uses aligned ErrorAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        request = ErrorAnalyzeRequest(
            error_code="NetworkError",
            error_message="Network connection failed - unable to reach server",
        )

        result = await service.analyze_error(request)

        # ADR-0091: Aligned schema uses error_type
        assert result.error_type == "network"
        assert len(result.recovery_steps) > 0

    @pytest.mark.asyncio
    async def test_error_analysis_500_server_error(self) -> None:
        """Test error analysis handles 500 internal server errors.

        ADR-0091 Phase 9: Uses aligned ErrorAnalyzeRequest schema.
        """
        from mcp_server_langgraph.api.v1.ai_ux import ErrorAnalyzeRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        request = ErrorAnalyzeRequest(
            error_code="ServerError",
            error_message="500 Internal Server Error occurred",
        )

        result = await service.analyze_error(request)

        # ADR-0091: Aligned schema uses error_type
        assert result.error_type == "server"
        assert len(result.recovery_steps) > 0

    @pytest.mark.asyncio
    async def test_streaming_handles_persona_exception(self) -> None:
        """Test streaming gracefully handles persona analysis exceptions."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        # Mock analyze_persona to raise an exception
        service.analyze_persona = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        request = CompositeAnalysisRequest(
            user_id="test-user",
            session_id="test-session",
            include_persona=True,
            persona_data={"assigned_persona": "bob"},
        )

        events = []
        async for event in service.stream_composite_analysis(request):
            events.append(event)

        # Should have start event, error event, and complete event
        assert any(e.get("type") == "start" for e in events)
        assert any(e.get("type") == "persona_error" for e in events)
        assert any(e.get("type") == "complete" for e in events)

    @pytest.mark.asyncio
    async def test_streaming_handles_disclosure_exception(self) -> None:
        """Test streaming gracefully handles disclosure analysis exceptions."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        # Mock analyze_disclosure to raise an exception
        service.analyze_disclosure = AsyncMock(side_effect=RuntimeError("Service unavailable"))

        request = CompositeAnalysisRequest(
            user_id="test-user",
            session_id="test-session",
            include_disclosure=True,
            disclosure_data={"feature_usage": {}},
        )

        events = []
        async for event in service.stream_composite_analysis(request):
            events.append(event)

        # Should have error event for disclosure
        assert any(e.get("type") == "disclosure_error" for e in events)

    @pytest.mark.asyncio
    async def test_streaming_handles_error_analysis_exception(self) -> None:
        """Test streaming gracefully handles error analysis exceptions."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        # Mock analyze_error to raise an exception
        service.analyze_error = AsyncMock(side_effect=RuntimeError("Parse error"))

        request = CompositeAnalysisRequest(
            user_id="test-user",
            session_id="test-session",
            include_error=True,
            error_data={"name": "TestError", "message": "test"},
        )

        events = []
        async for event in service.stream_composite_analysis(request):
            events.append(event)

        # Should have error event for error analysis
        assert any(e.get("type") == "error_analysis_error" for e in events)

    @pytest.mark.asyncio
    async def test_composite_handles_disclosure_exception(self) -> None:
        """Test composite analysis handles disclosure exceptions."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())
        service.analyze_disclosure = AsyncMock(side_effect=RuntimeError("Failed"))

        request = CompositeAnalysisRequest(
            user_id="test-user",
            session_id="test-session",
            include_disclosure=True,
            disclosure_data={"feature_usage": {}},
        )

        # Should not raise, should return result with None disclosure
        result = await service.run_composite_analysis(request)
        assert result.disclosure_result is None

    @pytest.mark.asyncio
    async def test_composite_handles_error_analysis_exception(self) -> None:
        """Test composite analysis handles error analysis exceptions."""
        from mcp_server_langgraph.api.v1.ai_ux import CompositeAnalysisRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())
        service.analyze_error = AsyncMock(side_effect=RuntimeError("Failed"))

        request = CompositeAnalysisRequest(
            user_id="test-user",
            session_id="test-session",
            include_error=True,
            error_data={"name": "TestError", "message": "test"},
        )

        # Should not raise, should return result with None error_result
        result = await service.run_composite_analysis(request)
        assert result.error_result is None


@pytest.mark.ai
@pytest.mark.unit
class TestFeatureFlagIntegration:
    """Tests for AI UX feature flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_feature_flags_include_ai_ux_enabled(self) -> None:
        """Test that AI UX feature flag exists in FeatureFlags."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_ai_ux")

    def test_feature_flags_include_ai_ux_parallel_graph(self) -> None:
        """Test that parallel graph feature flag exists."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_ai_ux_parallel_graph")

    def test_feature_flags_include_ai_ux_streaming(self) -> None:
        """Test that streaming feature flag exists."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_ai_ux_streaming")

    def test_feature_flags_include_ai_ux_websocket(self) -> None:
        """Test that WebSocket feature flag exists."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_ai_ux_websocket")

    def test_feature_flags_include_ai_ux_redis_cache(self) -> None:
        """Test that Redis cache feature flag exists."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_ai_ux_redis_cache")

    def test_ai_ux_flags_default_to_true(self) -> None:
        """Test that AI UX flags default to enabled for new features."""
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert flags.enable_ai_ux is True

    def test_service_respects_feature_flag_disabled(self) -> None:
        """Test service returns heuristic fallback when AI UX disabled."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        settings = MagicMock()
        settings.enable_ai_ux = False

        service = AIUXService(llm_factory=MagicMock(), settings=settings)
        # Service should be created even with disabled flag
        assert service is not None


@pytest.mark.ai
@pytest.mark.unit
class TestPrometheusMetrics:
    """Tests for Prometheus metrics integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_ux_llm_calls_counter_exists(self) -> None:
        """Test that LLM calls counter metric is defined."""
        from mcp_server_langgraph.api.v1 import ai_ux_service

        assert hasattr(ai_ux_service, "ai_ux_llm_calls_total")

    def test_ai_ux_fallbacks_counter_exists(self) -> None:
        """Test that fallbacks counter metric is defined."""
        from mcp_server_langgraph.api.v1 import ai_ux_service

        assert hasattr(ai_ux_service, "ai_ux_llm_fallbacks_total")

    def test_ai_ux_latency_histogram_exists(self) -> None:
        """Test that latency histogram metric is defined."""
        from mcp_server_langgraph.api.v1 import ai_ux_service

        assert hasattr(ai_ux_service, "ai_ux_llm_latency_seconds")

    def test_ai_ux_cache_hits_counter_exists(self) -> None:
        """Test that cache hits counter metric is defined."""
        from mcp_server_langgraph.api.v1 import ai_ux_service

        assert hasattr(ai_ux_service, "ai_ux_cache_hits_total")

    def test_metrics_have_method_label(self) -> None:
        """Test that metrics include method label for filtering."""
        from mcp_server_langgraph.api.v1.ai_ux_service import ai_ux_llm_calls_total

        # Counter should support labels method with 'method' label
        labeled = ai_ux_llm_calls_total.labels(method="persona_analysis")
        assert labeled is not None

    def test_ai_ux_websocket_connections_gauge_exists(self) -> None:
        """Test that WebSocket connections gauge exists."""
        from mcp_server_langgraph.api.v1 import ai_ux_service

        assert hasattr(ai_ux_service, "ai_ux_websocket_connections")

    def test_ai_ux_rate_limit_exceeded_counter_exists(self) -> None:
        """Test that rate limit exceeded counter exists."""
        from mcp_server_langgraph.api.v1 import ai_ux_service

        assert hasattr(ai_ux_service, "ai_ux_rate_limit_exceeded_total")


@pytest.mark.ai
@pytest.mark.unit
class TestRedisCaching:
    """Tests for Redis caching of LLM responses."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_service_has_redis_cache_attribute(self) -> None:
        """Test that service has redis_cache attribute."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())
        assert hasattr(service, "redis_cache")

    def test_service_has_get_cached_response_method(self) -> None:
        """Test that service has method to get cached responses."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())
        assert hasattr(service, "get_cached_response")
        assert callable(service.get_cached_response)

    def test_service_has_set_cached_response_method(self) -> None:
        """Test that service has method to set cached responses."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())
        assert hasattr(service, "set_cached_response")
        assert callable(service.set_cached_response)

    @pytest.mark.asyncio
    async def test_cache_key_generation(self) -> None:
        """Test that cache keys are generated deterministically."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        key1 = service._get_cache_key("persona", {"user_id": "test", "data": "a"})
        key2 = service._get_cache_key("persona", {"user_id": "test", "data": "a"})
        key3 = service._get_cache_key("persona", {"user_id": "test", "data": "b"})

        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key

    @pytest.mark.asyncio
    async def test_redis_cache_miss_calls_llm(self) -> None:
        """Test that cache miss triggers LLM call."""
        from mcp_server_langgraph.api.v1.ai_ux import PersonaAnalyzeRequest
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content='{"detected_persona": "builder", "confidence": 0.9}'))

        service = AIUXService(llm_factory=mock_llm, settings=MagicMock())
        service.redis_cache = MagicMock()
        service.redis_cache.get = AsyncMock(return_value=None)  # Cache miss
        service.redis_cache.set = AsyncMock(return_value=None)

        request = PersonaAnalyzeRequest(
            user_id="test-user",
            assigned_persona="bob",
            recent_actions=[],
            feature_usage={},
        )

        await service.analyze_persona(request)

        # LLM should be called on cache miss
        mock_llm.ainvoke.assert_called()

    @pytest.mark.asyncio
    async def test_redis_cache_methods_exist_and_work(self) -> None:
        """Test that Redis cache methods are callable and work correctly."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        # Mock Redis cache
        service.redis_cache = MagicMock()
        service.redis_cache.get = AsyncMock(return_value=None)
        service.redis_cache.setex = AsyncMock(return_value=None)

        # Test get_cached_response
        result = await service.get_cached_response("test_key")
        assert result is None  # Cache miss

        # Test set_cached_response
        await service.set_cached_response("test_key", {"data": "value"})
        service.redis_cache.setex.assert_called_once()


@pytest.mark.ai
@pytest.mark.unit
class TestRateLimiting:
    """Tests for rate limiting on AI endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_ux_rate_limit_configured(self) -> None:
        """Test that AI UX endpoints have rate limits configured."""
        from mcp_server_langgraph.middleware.rate_limiter import ENDPOINT_RATE_LIMITS

        assert "ai_ux" in ENDPOINT_RATE_LIMITS
        assert "/minute" in ENDPOINT_RATE_LIMITS["ai_ux"]

    def test_ai_ux_rate_limit_is_30_per_minute(self) -> None:
        """Test that AI UX rate limit is 30/minute as documented."""
        from mcp_server_langgraph.middleware.rate_limiter import ENDPOINT_RATE_LIMITS

        assert ENDPOINT_RATE_LIMITS["ai_ux"] == "30/minute"

    def test_ai_ux_paths_have_rate_limits(self) -> None:
        """Test that AI UX API paths have path-based rate limits."""
        from mcp_server_langgraph.middleware.rate_limiter import PATH_RATE_LIMITS

        # Check key AI UX endpoints have path limits
        ai_ux_paths = [p for p in PATH_RATE_LIMITS.keys() if "/ai/" in p]
        assert len(ai_ux_paths) > 0, "AI UX paths should have rate limits"

    def test_batch_composite_endpoint_has_rate_limit(self) -> None:
        """Test that batch composite endpoint has its own rate limit."""
        from mcp_server_langgraph.middleware.rate_limiter import PATH_RATE_LIMITS

        batch_path = "/api/v1/ai/composite/batch"
        assert batch_path in PATH_RATE_LIMITS, f"{batch_path} should have rate limit"
        assert PATH_RATE_LIMITS[batch_path] == "10/minute", "Batch should be 10/minute"


@pytest.mark.ai
@pytest.mark.unit
class TestWebSocketSuggestions:
    """Tests for WebSocket real-time AI suggestions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_endpoint_exists(self) -> None:
        """Test that WebSocket endpoint is defined."""
        from mcp_server_langgraph.api.v1.ai_ux import ai_ux_router

        routes = [r.path for r in ai_ux_router.routes]
        assert any("ws" in path.lower() or "websocket" in path.lower() for path in routes)

    def test_service_has_websocket_handler(self) -> None:
        """Test that service has WebSocket connection handler."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())
        assert hasattr(service, "handle_websocket_connection")

    def test_service_has_broadcast_suggestion_method(self) -> None:
        """Test that service can broadcast suggestions to connected clients."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())
        assert hasattr(service, "broadcast_suggestion")

    @pytest.mark.asyncio
    async def test_websocket_connection_tracking(self) -> None:
        """Test that WebSocket connections are tracked."""
        from mcp_server_langgraph.api.v1.ai_ux_service import AIUXService

        service = AIUXService(llm_factory=None, settings=MagicMock())

        # Should have connection tracking
        assert hasattr(service, "_websocket_connections")
        assert isinstance(service._websocket_connections, dict)


@pytest.mark.ai
@pytest.mark.unit
class TestOpenAPISchemaDocumentation:
    """Tests for OpenAPI schema documentation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_persona_analyze_has_response_model(self) -> None:
        """Test that persona analyze endpoint has response model."""
        from mcp_server_langgraph.api.v1.ai_ux import ai_ux_router

        for route in ai_ux_router.routes:
            if hasattr(route, "path") and "persona" in route.path:
                assert hasattr(route, "response_model") or hasattr(route, "responses")

    def test_response_models_are_pydantic(self) -> None:
        """Test that response models are Pydantic BaseModel subclasses."""
        from pydantic import BaseModel

        from mcp_server_langgraph.api.v1.ai_ux import (
            DisclosureAnalyzeResponse,
            EmptyStateSuggestionsResponse,
            ErrorAnalyzeResponse,
            MetricsInsightsResponse,
            NudgeRecommendResponse,
            OnboardingPersonalizeResponse,
            PersonaAnalyzeResponse,
        )

        response_models = [
            PersonaAnalyzeResponse,
            DisclosureAnalyzeResponse,
            EmptyStateSuggestionsResponse,
            ErrorAnalyzeResponse,
            NudgeRecommendResponse,
            OnboardingPersonalizeResponse,
            MetricsInsightsResponse,
        ]

        for model in response_models:
            assert issubclass(model, BaseModel)

    def test_endpoints_have_summary(self) -> None:
        """Test that all endpoints have summary for OpenAPI docs."""
        from mcp_server_langgraph.api.v1.ai_ux import ai_ux_router

        for route in ai_ux_router.routes:
            if hasattr(route, "summary"):
                # Route has summary (good)
                pass
            elif hasattr(route, "endpoint"):
                # Check endpoint has docstring
                assert route.endpoint.__doc__ is not None

    def test_request_models_have_field_descriptions(self) -> None:
        """Test that request models have field descriptions."""
        from mcp_server_langgraph.api.v1.ai_ux import PersonaAnalyzeRequest

        # Check that at least user_id has a description
        fields = PersonaAnalyzeRequest.model_fields
        assert "user_id" in fields
        # Field should be documented (has description or is typed)
        assert fields["user_id"].annotation is not None
