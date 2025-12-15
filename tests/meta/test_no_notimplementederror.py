"""
Meta-test: Prevent NotImplementedError in API Service Implementations.

This test ensures that all service implementations in the api/v1 layer
have concrete implementations and do not raise NotImplementedError.

This prevents shipping stub services that break the frontend.

History:
- December 2024: Frontend was broken because CostService, ObservabilityService,
  and ChatService had stub implementations that raised NotImplementedError.
  This meta-test was added to prevent future regressions.
"""

from __future__ import annotations

import gc
import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.meta
@pytest.mark.xdist_group(name="no_notimplementederror")
class TestNoNotImplementedError:
    """Ensure API service implementations don't raise NotImplementedError."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # CostServiceImpl Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_cost_service_impl_get_summary_does_not_raise(self) -> None:
        """GIVEN CostServiceImpl with mocked storage
        WHEN get_summary() is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage = MagicMock()
        mock_storage.get_cost_summary = AsyncMock(
            return_value=MagicMock(
                total_cost=100.0,
                total_tokens=1000,
                request_count=10,
            )
        )

        service = CostServiceImpl(storage=mock_storage)

        # This should NOT raise NotImplementedError
        try:
            result = await service.get_summary()
            assert result is not None
        except NotImplementedError:
            pytest.fail("CostServiceImpl.get_summary() raised NotImplementedError!")

    @pytest.mark.asyncio
    async def test_cost_service_impl_get_by_model_does_not_raise(self) -> None:
        """GIVEN CostServiceImpl with mocked storage
        WHEN get_by_model() is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage = MagicMock()
        mock_storage.get_cost_by_model = AsyncMock(return_value=[])

        service = CostServiceImpl(storage=mock_storage)

        try:
            result = await service.get_by_model()
            assert result is not None
        except NotImplementedError:
            pytest.fail("CostServiceImpl.get_by_model() raised NotImplementedError!")

    @pytest.mark.asyncio
    async def test_cost_service_impl_get_history_does_not_raise(self) -> None:
        """GIVEN CostServiceImpl with mocked storage
        WHEN get_history() is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl

        mock_storage = MagicMock()
        mock_storage.get_cost_history = AsyncMock(return_value=[])

        service = CostServiceImpl(storage=mock_storage)

        try:
            result = await service.get_history()
            assert result is not None
        except NotImplementedError:
            pytest.fail("CostServiceImpl.get_history() raised NotImplementedError!")

    # =========================================================================
    # ObservabilityServiceImpl Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_observability_service_impl_list_traces_does_not_raise(self) -> None:
        """GIVEN ObservabilityServiceImpl with mocked tracing
        WHEN list_traces() is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing = MagicMock()
        mock_tracing.search_traces = AsyncMock(return_value=MagicMock(traces=[], next_cursor=None))

        service = ObservabilityServiceImpl(tracing=mock_tracing)

        try:
            result = await service.list_traces()
            assert result is not None
        except NotImplementedError:
            pytest.fail("ObservabilityServiceImpl.list_traces() raised NotImplementedError!")

    @pytest.mark.asyncio
    async def test_observability_service_impl_get_trace_does_not_raise(self) -> None:
        """GIVEN ObservabilityServiceImpl with mocked tracing
        WHEN get_trace() is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_tracing = MagicMock()
        mock_tracing.get_trace = AsyncMock(return_value=None)

        service = ObservabilityServiceImpl(tracing=mock_tracing)

        try:
            result = await service.get_trace("trace-123")
            # None is a valid result (trace not found)
            assert result is None
        except NotImplementedError:
            pytest.fail("ObservabilityServiceImpl.get_trace() raised NotImplementedError!")

    @pytest.mark.asyncio
    async def test_observability_service_impl_get_metrics_does_not_raise(self) -> None:
        """GIVEN ObservabilityServiceImpl with mocked metrics
        WHEN get_metrics() is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        mock_metrics = MagicMock()
        mock_metrics.query_instant = AsyncMock(return_value=MagicMock(series=[]))

        service = ObservabilityServiceImpl(metrics=mock_metrics)

        try:
            result = await service.get_metrics()
            assert result is not None
        except NotImplementedError:
            pytest.fail("ObservabilityServiceImpl.get_metrics() raised NotImplementedError!")

    # =========================================================================
    # ChatServiceImpl Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_chat_service_impl_create_completion_does_not_raise(self) -> None:
        """GIVEN ChatServiceImpl with mocked LLM
        WHEN create_completion() is called
        THEN it does NOT raise NotImplementedError
        """
        from unittest.mock import patch

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        mock_response = MagicMock()
        mock_response.id = "chatcmpl-123"
        mock_response.model = "gpt-4"
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = "Hello"
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_response

            service = ChatServiceImpl()

            try:
                result = await service.create_completion(
                    session_id="test-session",
                    messages=[{"role": "user", "content": "Hello"}],
                )
                assert result is not None
            except NotImplementedError:
                pytest.fail("ChatServiceImpl.create_completion() raised NotImplementedError!")

    @pytest.mark.asyncio
    async def test_chat_service_impl_create_stream_does_not_raise(self) -> None:
        """GIVEN ChatServiceImpl with mocked LLM
        WHEN create_stream() is called
        THEN it does NOT raise NotImplementedError
        """
        from unittest.mock import patch

        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        async def mock_stream():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hi"))])

        with patch("mcp_server_langgraph.api.v1.chat.acompletion") as mock_acompletion:
            mock_acompletion.return_value = mock_stream()

            service = ChatServiceImpl()

            try:
                chunks = []
                async for chunk in service.create_stream(
                    session_id="test-session",
                    messages=[{"role": "user", "content": "Hello"}],
                ):
                    chunks.append(chunk)
                assert len(chunks) >= 0  # May be empty, but should not raise
            except NotImplementedError:
                pytest.fail("ChatServiceImpl.create_stream() raised NotImplementedError!")

    @pytest.mark.asyncio
    async def test_chat_service_impl_get_history_does_not_raise(self) -> None:
        """GIVEN ChatServiceImpl
        WHEN get_history() is called
        THEN it does NOT raise NotImplementedError
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl

        service = ChatServiceImpl()

        try:
            result = await service.get_history("test-session")
            # Empty list is valid when no storage configured
            assert result is not None
        except NotImplementedError:
            pytest.fail("ChatServiceImpl.get_history() raised NotImplementedError!")

    # =========================================================================
    # Factory Function Tests
    # =========================================================================

    def test_get_cost_service_returns_impl(self) -> None:
        """GIVEN the cost service getter
        WHEN get_cost_service() is called
        THEN it returns CostServiceImpl (not the stub interface)
        """
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl, get_cost_service

        service = get_cost_service()

        # The factory should return a concrete implementation
        assert isinstance(service, CostServiceImpl)

    def test_get_observability_service_returns_impl(self) -> None:
        """GIVEN the observability service getter
        WHEN get_observability_service() is called
        THEN it returns ObservabilityServiceImpl (not the stub interface)
        """
        from mcp_server_langgraph.api.v1.observability import (
            ObservabilityServiceImpl,
            get_observability_service,
        )

        service = get_observability_service()

        assert isinstance(service, ObservabilityServiceImpl)

    def test_get_chat_service_returns_impl(self) -> None:
        """GIVEN the chat service getter
        WHEN get_chat_service() is called
        THEN it returns ChatServiceImpl (not the stub interface)
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl, get_chat_service

        service = get_chat_service()

        assert isinstance(service, ChatServiceImpl)

    # =========================================================================
    # Source Code Analysis Test
    # =========================================================================

    def test_service_impl_methods_do_not_contain_raise_notimplementederror(
        self,
    ) -> None:
        """GIVEN all service implementation classes
        WHEN inspecting their source code
        THEN no methods contain 'raise NotImplementedError'

        This is a static analysis check to catch stub implementations.
        """
        from mcp_server_langgraph.api.v1.chat import ChatServiceImpl
        from mcp_server_langgraph.api.v1.cost import CostServiceImpl
        from mcp_server_langgraph.api.v1.observability import ObservabilityServiceImpl

        impl_classes = [CostServiceImpl, ObservabilityServiceImpl, ChatServiceImpl]

        violations: list[str] = []

        for cls in impl_classes:
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                # Skip dunder methods and private methods
                if name.startswith("_") and not name.startswith("__"):
                    continue
                if name.startswith("__"):
                    continue

                try:
                    source = inspect.getsource(method)
                    if "raise NotImplementedError" in source:
                        violations.append(f"{cls.__name__}.{name}")
                except (OSError, TypeError):
                    # Can't get source for some methods (e.g., built-ins)
                    pass

        if violations:
            pytest.fail(f"The following methods contain 'raise NotImplementedError': {violations}")
