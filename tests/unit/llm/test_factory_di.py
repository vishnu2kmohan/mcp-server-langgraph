"""
Unit tests for LLMFactory dependency injection.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 2.4 DIP - Testing telemetry injection in LLMFactory.

Reference: Plan - Phase 2.4 DIP: Inject Dependencies into LLMFactory
"""

import gc
from unittest.mock import MagicMock

import pytest


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.llm,
]


@pytest.mark.xdist_group(name="test_factory_di")
class TestLLMFactoryTelemetryInjection:
    """Test LLMFactory telemetry dependency injection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_factory_accepts_telemetry_parameter(self):
        """
        GIVEN: LLMFactory class
        WHEN: Creating instance with telemetry parameter
        THEN: Should accept and store telemetry provider
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Arrange
        mock_telemetry = MagicMock()
        mock_telemetry.logger = MagicMock()
        mock_telemetry.metrics = MagicMock()
        mock_telemetry.tracer = MagicMock()

        # Act
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
            telemetry=mock_telemetry,
        )

        # Assert
        assert factory.telemetry is mock_telemetry

    def test_factory_uses_default_telemetry_when_none_provided(self):
        """
        GIVEN: LLMFactory class
        WHEN: Creating instance without telemetry parameter
        THEN: Should use default telemetry (backward compatible)
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Act
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
        )

        # Assert - should have telemetry set (either default or from module)
        assert factory.telemetry is not None

    def test_factory_telemetry_has_logger(self):
        """
        GIVEN: LLMFactory with injected telemetry
        WHEN: Accessing telemetry.logger
        THEN: Should have logger available
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Arrange
        mock_telemetry = MagicMock()
        mock_telemetry.logger = MagicMock()

        # Act
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
            telemetry=mock_telemetry,
        )

        # Assert
        assert factory.telemetry.logger is mock_telemetry.logger

    def test_factory_telemetry_has_tracer(self):
        """
        GIVEN: LLMFactory with injected telemetry
        WHEN: Accessing telemetry.tracer
        THEN: Should have tracer available
        """
        from mcp_server_langgraph.llm.factory import LLMFactory

        # Arrange
        mock_telemetry = MagicMock()
        mock_telemetry.tracer = MagicMock()

        # Act
        factory = LLMFactory(
            provider="openai",
            model_name="gpt-4",
            telemetry=mock_telemetry,
        )

        # Assert
        assert factory.telemetry.tracer is mock_telemetry.tracer


@pytest.mark.xdist_group(name="test_factory_di")
class TestLLMFactoryTelemetryProtocol:
    """Test LLMFactory telemetry protocol compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_telemetry_implements_protocol(self):
        """
        GIVEN: Default telemetry provider
        WHEN: Checking protocol compliance
        THEN: Should have logger, metrics, and tracer
        """
        from mcp_server_langgraph.llm.factory import get_default_telemetry

        # Act
        telemetry = get_default_telemetry()

        # Assert
        assert hasattr(telemetry, "logger")
        assert hasattr(telemetry, "metrics")
        assert hasattr(telemetry, "tracer")
