"""
Tests for LLM Factory Output Validation (TDD - RED Phase)

Tests the integration of runtime validation with the LLM factory.
This enables automatic validation of LLM outputs against Pydantic schemas.

Following TDD pattern:
1. Write these tests first (RED)
2. Implement validation wrapper (GREEN)
3. Refactor as needed

Memory Safety:
- Uses @pytest.mark.xdist_group for parallel test safety
- Includes teardown_method with gc.collect()

References:
- ADR-0089: Prompt Architecture Centralization
- Phase 7: Telemetry & Metadata
"""

from __future__ import annotations

import gc
import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

if TYPE_CHECKING:
    pass

# Module-level pytest marker
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="llm_factory_validation")
class TestLLMFactoryValidatedInvokeExists:
    """Tests that ainvoke_validated method exists and is callable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ainvoke_validated_method_exists(self) -> None:
        """Verify LLMFactory has ainvoke_validated method."""
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Create factory instance
        factory = LLMFactory(model_name="gpt-4", provider="openai")
        assert hasattr(factory, "ainvoke_validated")
        assert callable(factory.ainvoke_validated)


@pytest.mark.xdist_group(name="llm_factory_validation")
class TestLLMFactoryValidatedInvokeSuccess:
    """Tests for successful validation scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_returns_validation_result(self) -> None:
        """Verify ainvoke_validated returns ValidationResult."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.core.prompts.validation import ValidationResult
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        # Mock the underlying ainvoke to return valid JSON
        valid_response = json.dumps({
            "content": "Hello, world!",
            "confidence": 0.95,
        })

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert isinstance(result, ValidationResult)
            assert result.success is True
            assert result.parsed_output is not None
            assert isinstance(result.parsed_output, ResponseOutput)

    @pytest.mark.asyncio
    async def test_ainvoke_validated_parses_valid_json(self) -> None:
        """Verify ainvoke_validated correctly parses valid JSON response."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        valid_response = json.dumps({
            "content": "Test response content",
            "confidence": 0.85,
            "requires_clarification": False,
            "sources": ["source1", "source2"],
        })

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is True
            assert result.parsed_output.content == "Test response content"
            assert result.parsed_output.confidence == 0.85
            assert result.parsed_output.sources == ["source1", "source2"]

    @pytest.mark.asyncio
    async def test_ainvoke_validated_strips_markdown_code_blocks(self) -> None:
        """Verify ainvoke_validated strips markdown code blocks from response."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        # Response wrapped in markdown code block
        markdown_response = '''```json
{"content": "Test", "confidence": 0.9}
```'''

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=markdown_response)

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is True
            assert result.parsed_output.content == "Test"


@pytest.mark.xdist_group(name="llm_factory_validation")
class TestLLMFactoryValidatedInvokeFailure:
    """Tests for validation failure scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_handles_invalid_json(self) -> None:
        """Verify ainvoke_validated handles invalid JSON gracefully."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content="not valid json {{{")

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is False
            assert result.error is not None
            assert "json" in result.error.lower() or "parse" in result.error.lower()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_handles_schema_mismatch(self) -> None:
        """Verify ainvoke_validated handles schema mismatch gracefully."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        # Missing required 'content' field
        invalid_schema_response = json.dumps({
            "confidence": 0.5,
        })

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=invalid_schema_response)

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_ainvoke_validated_handles_constraint_violation(self) -> None:
        """Verify ainvoke_validated handles constraint violations gracefully."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        # Confidence > 1.0 violates constraint
        constraint_violation_response = json.dumps({
            "content": "Test",
            "confidence": 1.5,  # Invalid: > 1.0
        })

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=constraint_violation_response)

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is False
            assert result.error is not None


@pytest.mark.xdist_group(name="llm_factory_validation")
class TestLLMFactoryValidatedInvokeFallback:
    """Tests for fallback behavior on validation failure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_uses_fallback_on_failure(self) -> None:
        """Verify ainvoke_validated uses fallback value on validation failure."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        fallback = ResponseOutput(
            content="Fallback response",
            confidence=0.0,
        )

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content="invalid json")

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
                fallback=fallback,
            )

            assert result.success is False
            assert result.parsed_output is not None
            assert result.parsed_output.content == "Fallback response"
            assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_ainvoke_validated_no_fallback_returns_none(self) -> None:
        """Verify ainvoke_validated returns None parsed_output when no fallback."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content="invalid json")

            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is False
            assert result.parsed_output is None
            assert result.used_fallback is False


@pytest.mark.xdist_group(name="llm_factory_validation")
class TestLLMFactoryValidatedInvokeMetrics:
    """Tests for validation metrics recording."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_records_success_metric(self) -> None:
        """Verify successful validation increments success counter."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        valid_response = json.dumps({
            "content": "Test",
            "confidence": 0.9,
        })

        with (
            patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke,
            patch(
                "mcp_server_langgraph.core.prompts.validation._record_validation_metric"
            ) as mock_metric,
        ):
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            # Metric should be recorded
            mock_metric.assert_called()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_records_prompt_telemetry(self) -> None:
        """Verify validation records prompt usage telemetry."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        valid_response = json.dumps({
            "content": "Test",
            "confidence": 0.9,
        })

        with (
            patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke,
            patch(
                "mcp_server_langgraph.core.prompts.telemetry.record_prompt_usage"
            ) as mock_telemetry,
        ):
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            # Telemetry should be recorded
            mock_telemetry.assert_called_once_with(prompt_name="response", prompt_version="latest")


@pytest.mark.xdist_group(name="llm_factory_validation")
class TestLLMFactoryValidatedInvokePassthrough:
    """Tests that ainvoke_validated passes through all kwargs to ainvoke."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_passes_temperature(self) -> None:
        """Verify temperature is passed through to ainvoke."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        valid_response = json.dumps({"content": "Test", "confidence": 0.9})

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
                temperature=0.5,
            )

            # Check temperature was passed
            mock_ainvoke.assert_called_once()
            call_kwargs = mock_ainvoke.call_args[1]
            assert call_kwargs.get("temperature") == 0.5

    @pytest.mark.asyncio
    async def test_ainvoke_validated_passes_max_tokens(self) -> None:
        """Verify max_tokens is passed through to ainvoke."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        valid_response = json.dumps({"content": "Test", "confidence": 0.9})

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=valid_response)

            await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
                max_tokens=1000,
            )

            # Check max_tokens was passed
            mock_ainvoke.assert_called_once()
            call_kwargs = mock_ainvoke.call_args[1]
            assert call_kwargs.get("max_tokens") == 1000


@pytest.mark.xdist_group(name="llm_factory_validation")
class TestLLMFactoryValidatedInvokeNonBlocking:
    """Tests that validation is non-blocking and doesn't raise exceptions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ainvoke_validated_never_raises_on_validation_error(self) -> None:
        """Verify ainvoke_validated doesn't raise on validation errors."""
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content="{{{{completely invalid")

            # Should not raise
            result = await factory.ainvoke_validated(
                messages=[HumanMessage(content="Test")],
                schema=ResponseOutput,
                prompt_name="response",
            )

            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_ainvoke_validated_propagates_llm_errors(self) -> None:
        """Verify LLM provider errors are still raised (validation doesn't swallow them)."""
        from mcp_server_langgraph.core.exceptions import LLMProviderError
        from mcp_server_langgraph.core.prompts.schemas import ResponseOutput
        from mcp_server_langgraph.llm.factory import LLMFactory

        factory = LLMFactory(model_name="gpt-4", provider="openai")

        with patch.object(factory, "ainvoke", new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.side_effect = LLMProviderError(
                message="Provider unavailable",
                metadata={"model": "gpt-4"},
            )

            # LLM errors should still raise
            with pytest.raises(LLMProviderError):
                await factory.ainvoke_validated(
                    messages=[HumanMessage(content="Test")],
                    schema=ResponseOutput,
                    prompt_name="response",
                )
