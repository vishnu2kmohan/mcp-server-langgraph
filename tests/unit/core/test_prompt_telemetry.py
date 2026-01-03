"""
Tests for prompt telemetry functionality (Phase 7 - ADR-0089).

Validates:
- Prompt metadata retrieval
- Prometheus metrics recording
- Lightweight telemetry context
- Hash-based prompt version tracking
"""

from __future__ import annotations

import gc
from unittest.mock import MagicMock, patch

import pytest

# Module-level pytest marker
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptMetadata:
    """Tests for get_prompt_metadata function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_prompt_metadata_returns_dict(self) -> None:
        """Verify get_prompt_metadata returns a dictionary."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        metadata = get_prompt_metadata("router")
        assert isinstance(metadata, dict)

    def test_get_prompt_metadata_contains_name(self) -> None:
        """Verify metadata contains prompt_name."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        metadata = get_prompt_metadata("router")
        assert "prompt_name" in metadata
        assert metadata["prompt_name"] == "router"

    def test_get_prompt_metadata_contains_version(self) -> None:
        """Verify metadata contains prompt_version."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        metadata = get_prompt_metadata("router")
        assert "prompt_version" in metadata
        assert metadata["prompt_version"] == "v1"

    def test_get_prompt_metadata_contains_hash(self) -> None:
        """Verify metadata contains prompt_hash (8-char truncated MD5)."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        metadata = get_prompt_metadata("router")
        assert "prompt_hash" in metadata
        assert len(metadata["prompt_hash"]) == 8
        # Hash should be hexadecimal
        int(metadata["prompt_hash"], 16)  # Should not raise

    def test_get_prompt_metadata_hash_is_stable(self) -> None:
        """Verify prompt hash is stable across calls."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        hash1 = get_prompt_metadata("router")["prompt_hash"]
        hash2 = get_prompt_metadata("router")["prompt_hash"]
        assert hash1 == hash2

    def test_get_prompt_metadata_raises_for_unknown_prompt(self) -> None:
        """Verify get_prompt_metadata raises ValueError for unknown prompt."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        with pytest.raises(ValueError, match="Unknown prompt"):
            get_prompt_metadata("nonexistent_prompt")

    def test_get_prompt_metadata_works_for_all_prompts(self) -> None:
        """Verify get_prompt_metadata works for all registered prompts."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        known_prompts = [
            "router",
            "response",
            "verification",
            "orchestration_router",
            "error_analysis",
            "persona_analysis",
            "genui_widget",
            "workflow_generator",
            "plan_validation",
        ]

        for prompt_name in known_prompts:
            metadata = get_prompt_metadata(prompt_name)
            assert metadata["prompt_name"] == prompt_name
            assert "prompt_version" in metadata
            assert "prompt_hash" in metadata


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptUsageRecording:
    """Tests for record_prompt_usage function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_prompt_usage_does_not_raise(self) -> None:
        """Verify record_prompt_usage doesn't raise exceptions."""
        from mcp_server_langgraph.core.prompts import record_prompt_usage

        # Should not raise even if metrics unavailable
        record_prompt_usage("router", "v1")

    def test_record_prompt_usage_with_all_parameters(self) -> None:
        """Verify record_prompt_usage accepts all parameters."""
        from mcp_server_langgraph.core.prompts import record_prompt_usage

        # Should not raise
        record_prompt_usage(
            prompt_name="orchestration_router",
            prompt_version="v1",
            model="gpt-4",
            operation="chat",
        )

    @patch("mcp_server_langgraph.core.prompts.telemetry._prompt_usage_total")
    def test_record_prompt_usage_increments_counter(self, mock_counter: MagicMock) -> None:
        """Verify record_prompt_usage increments Prometheus counter."""
        from mcp_server_langgraph.core.prompts import record_prompt_usage

        # Configure mock to simulate available metrics
        mock_labels = MagicMock()
        mock_counter.labels.return_value = mock_labels

        with patch("mcp_server_langgraph.core.prompts.telemetry._metrics_available", True):
            record_prompt_usage("router", "v1")

        # Verify labels called with correct args
        mock_counter.labels.assert_called_once_with(prompt_name="router", prompt_version="v1")
        mock_labels.inc.assert_called_once()


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptTelemetryContext:
    """Tests for prompt_telemetry_context context manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompt_telemetry_context_exists(self) -> None:
        """Verify prompt_telemetry_context is importable."""
        from mcp_server_langgraph.core.prompts import prompt_telemetry_context

        assert callable(prompt_telemetry_context)

    def test_prompt_telemetry_context_returns_metadata(self) -> None:
        """Verify context manager returns metadata dict."""
        from mcp_server_langgraph.core.prompts import prompt_telemetry_context

        with prompt_telemetry_context("router") as ctx:
            assert isinstance(ctx, dict)
            assert "prompt_name" in ctx
            assert "prompt_version" in ctx

    def test_prompt_telemetry_context_records_on_exit(self) -> None:
        """Verify context manager records usage on exit."""
        from mcp_server_langgraph.core.prompts import prompt_telemetry_context

        with patch("mcp_server_langgraph.core.prompts.telemetry.record_prompt_usage") as mock_record:
            with prompt_telemetry_context("router"):
                pass  # Context body

            mock_record.assert_called_once()


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptMetricsIntegration:
    """Integration tests for prompt metrics with Prometheus."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompt_metrics_lazy_init(self) -> None:
        """Verify metrics are lazily initialized."""
        from mcp_server_langgraph.core.prompts import telemetry

        # Access should not raise
        assert hasattr(telemetry, "_init_prompt_metrics")

    def test_prompt_metrics_available_flag(self) -> None:
        """Verify _metrics_available flag is set after init."""
        from mcp_server_langgraph.core.prompts import telemetry

        # Should be boolean after module load
        assert telemetry._metrics_available in (True, False, None)

    def test_prompt_metrics_graceful_without_prometheus(self) -> None:
        """Verify metrics functions work without prometheus_client."""
        from mcp_server_langgraph.core.prompts import record_prompt_usage

        with patch(
            "mcp_server_langgraph.core.prompts.telemetry._metrics_available",
            False,
        ):
            # Should not raise
            record_prompt_usage("router", "v1")


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptSpanAttributes:
    """Tests for attach_prompt_to_span function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_attach_prompt_to_span_exists(self) -> None:
        """Verify attach_prompt_to_span is importable."""
        from mcp_server_langgraph.core.prompts import attach_prompt_to_span

        assert callable(attach_prompt_to_span)

    def test_attach_prompt_to_span_with_span(self) -> None:
        """Verify attach_prompt_to_span sets span attributes."""
        from mcp_server_langgraph.core.prompts import attach_prompt_to_span

        mock_span = MagicMock()
        attach_prompt_to_span(mock_span, "router")

        # Should have called set_attribute multiple times
        assert mock_span.set_attribute.call_count >= 3

    def test_attach_prompt_to_span_attributes(self) -> None:
        """Verify correct attributes are set on span."""
        from mcp_server_langgraph.core.prompts import attach_prompt_to_span

        mock_span = MagicMock()
        attach_prompt_to_span(mock_span, "router")

        # Extract all set_attribute calls
        calls = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}

        assert "prompt.name" in calls
        assert "prompt.version" in calls
        assert "prompt.hash" in calls
        assert calls["prompt.name"] == "router"

    def test_attach_prompt_to_span_with_none(self) -> None:
        """Verify attach_prompt_to_span handles None span gracefully."""
        from mcp_server_langgraph.core.prompts import attach_prompt_to_span

        # Should not raise
        attach_prompt_to_span(None, "router")


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptNormalization:
    """Tests for prompt and version normalization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_normalize_prompt_name_known(self) -> None:
        """Verify known prompt names pass through unchanged."""
        from mcp_server_langgraph.core.prompts.telemetry import _normalize_prompt_name

        assert _normalize_prompt_name("router") == "router"
        assert _normalize_prompt_name("orchestration_router") == "orchestration_router"

    def test_normalize_prompt_name_unknown(self) -> None:
        """Verify unknown prompt names normalize to 'other'."""
        from mcp_server_langgraph.core.prompts.telemetry import _normalize_prompt_name

        assert _normalize_prompt_name("unknown_prompt") == "other"
        assert _normalize_prompt_name("custom_prompt_v2") == "other"

    def test_normalize_version_known(self) -> None:
        """Verify known versions pass through unchanged."""
        from mcp_server_langgraph.core.prompts.telemetry import _normalize_version

        assert _normalize_version("v1") == "v1"
        assert _normalize_version("v2") == "v2"
        assert _normalize_version("latest") == "latest"

    def test_normalize_version_unknown(self) -> None:
        """Verify unknown versions normalize to 'other'."""
        from mcp_server_langgraph.core.prompts.telemetry import _normalize_version

        assert _normalize_version("v99") == "other"
        assert _normalize_version("custom") == "other"


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptTelemetryEdgeCases:
    """Tests for edge cases and error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prompt_telemetry_context_unknown_prompt(self) -> None:
        """Verify context manager handles unknown prompts gracefully."""
        from mcp_server_langgraph.core.prompts import prompt_telemetry_context

        # Should not raise, should return minimal metadata
        with prompt_telemetry_context("unknown_prompt_xyz") as ctx:
            assert ctx["prompt_name"] == "unknown_prompt_xyz"
            assert ctx["prompt_version"] == "unknown"

    def test_attach_prompt_to_span_unknown_prompt(self) -> None:
        """Verify attach_prompt_to_span handles unknown prompts."""
        from mcp_server_langgraph.core.prompts import attach_prompt_to_span

        mock_span = MagicMock()
        attach_prompt_to_span(mock_span, "totally_unknown_prompt")

        # Should still set attributes (with unknown values)
        calls = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
        assert calls["prompt.name"] == "totally_unknown_prompt"
        assert calls["prompt.version"] == "unknown"

    def test_record_prompt_usage_unknown_prompt(self) -> None:
        """Verify record_prompt_usage handles unknown prompts (normalizes to 'other')."""
        from mcp_server_langgraph.core.prompts import record_prompt_usage

        # Should not raise
        record_prompt_usage("totally_unknown_prompt", "v99")

    def test_attach_prompt_to_span_exception_handling(self) -> None:
        """Verify attach_prompt_to_span handles span exceptions gracefully."""
        from mcp_server_langgraph.core.prompts import attach_prompt_to_span

        # Create a span that raises on set_attribute
        mock_span = MagicMock()
        mock_span.set_attribute.side_effect = Exception("Span error")

        # Should not raise
        attach_prompt_to_span(mock_span, "router")


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestPromptHashStability:
    """Tests for prompt hash stability across versions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_different_prompts_have_different_hashes(self) -> None:
        """Verify different prompts produce different hashes."""
        from mcp_server_langgraph.core.prompts import get_prompt_metadata

        router_hash = get_prompt_metadata("router")["prompt_hash"]
        response_hash = get_prompt_metadata("response")["prompt_hash"]
        verification_hash = get_prompt_metadata("verification")["prompt_hash"]

        assert router_hash != response_hash
        assert router_hash != verification_hash
        assert response_hash != verification_hash

    def test_hash_changes_with_content(self) -> None:
        """Verify hash changes when prompt content changes."""

        from mcp_server_langgraph.core.prompts.telemetry import _compute_prompt_hash

        hash1 = _compute_prompt_hash("prompt content version 1")
        hash2 = _compute_prompt_hash("prompt content version 2")

        assert hash1 != hash2
        assert len(hash1) == 8
        assert len(hash2) == 8


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestAsyncPromptTelemetryContext:
    """Tests for async prompt telemetry context manager."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_async_prompt_telemetry_context_exists(self) -> None:
        """Verify async_prompt_telemetry_context is importable."""
        from mcp_server_langgraph.core.prompts import async_prompt_telemetry_context

        assert callable(async_prompt_telemetry_context)

    @pytest.mark.asyncio
    async def test_async_prompt_telemetry_context_returns_metadata(self) -> None:
        """Verify async context manager returns metadata dict."""
        from mcp_server_langgraph.core.prompts import async_prompt_telemetry_context

        async with async_prompt_telemetry_context("router") as ctx:
            assert isinstance(ctx, dict)
            assert "prompt_name" in ctx
            assert "prompt_version" in ctx
            assert ctx["prompt_name"] == "router"

    @pytest.mark.asyncio
    async def test_async_prompt_telemetry_context_records_on_exit(self) -> None:
        """Verify async context manager records usage on exit."""
        from mcp_server_langgraph.core.prompts import async_prompt_telemetry_context

        with patch("mcp_server_langgraph.core.prompts.telemetry.record_prompt_usage") as mock_record:
            async with async_prompt_telemetry_context("router"):
                pass  # Context body

            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_prompt_telemetry_context_unknown_prompt(self) -> None:
        """Verify async context handles unknown prompts gracefully."""
        from mcp_server_langgraph.core.prompts import async_prompt_telemetry_context

        # Should not raise
        async with async_prompt_telemetry_context("unknown_async_prompt") as ctx:
            assert ctx["prompt_name"] == "unknown_async_prompt"
            assert ctx["prompt_version"] == "unknown"

    @pytest.mark.asyncio
    async def test_async_prompt_telemetry_context_with_span(self) -> None:
        """Verify async context can attach to span."""
        from mcp_server_langgraph.core.prompts import async_prompt_telemetry_context

        mock_span = MagicMock()

        async with async_prompt_telemetry_context("router", span=mock_span) as ctx:
            assert ctx["prompt_name"] == "router"

        # Span should have attributes set
        assert mock_span.set_attribute.called


@pytest.mark.xdist_group(name="prompt_telemetry")
class TestStudioPrompt:
    """Tests for studio prompt coverage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_prompt_exists(self) -> None:
        """Verify STUDIO_SYSTEM_PROMPT exists and is non-empty."""
        from mcp_server_langgraph.core.prompts.studio_prompt import STUDIO_SYSTEM_PROMPT

        assert STUDIO_SYSTEM_PROMPT is not None
        assert len(STUDIO_SYSTEM_PROMPT) > 100

    def test_studio_prompt_has_artifact_instructions(self) -> None:
        """Verify studio prompt contains artifact guidance."""
        from mcp_server_langgraph.core.prompts.studio_prompt import STUDIO_SYSTEM_PROMPT

        assert "artifact" in STUDIO_SYSTEM_PROMPT.lower()

    def test_studio_prompt_has_code_block_guidance(self) -> None:
        """Verify studio prompt contains code block guidance."""
        from mcp_server_langgraph.core.prompts.studio_prompt import STUDIO_SYSTEM_PROMPT

        # Should mention code fences/markdown
        assert "mermaid" in STUDIO_SYSTEM_PROMPT or "tsx" in STUDIO_SYSTEM_PROMPT
