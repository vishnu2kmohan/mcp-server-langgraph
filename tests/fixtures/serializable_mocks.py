"""
Serializable Mock Objects for LangGraph Testing

Problem: MagicMock objects cannot be serialized by msgpack, which LangGraph uses
for checkpoint serialization. This breaks performance regression tests.

Solution: Create lightweight, serializable mock classes that can pass through
LangGraph's checkpoint system while still providing test functionality.

Usage:
    from tests.fixtures.serializable_mocks import SerializableLLMMock

    mock_llm = SerializableLLMMock(
        responses=["Response 1", "Response 2"],
        delay_seconds=0.1
    )

    # Use in tests - can be serialized by msgpack
    result = await mock_llm.ainvoke("test input")
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field, PrivateAttr


class SerializableLLMMock(BaseChatModel):
    """
    Serializable LLM mock for LangGraph testing.

    This class is msgpack-serializable (uses Pydantic for compatibility with BaseChatModel)
    and can pass through LangGraph's checkpoint system.

    Attributes:
        responses: List of responses to return (cycles if exhausted)
        delay_seconds: Simulated response delay for performance testing
        call_count: Number of times the mock has been invoked
        _current_index: Internal index for cycling through responses
    """

    responses: list[str] = Field(default_factory=lambda: ["Mock LLM response"])
    delay_seconds: float = Field(default=0.0)

    # Private attributes (not part of model schema, excluded from serialization)
    _call_count: int = PrivateAttr(default=0)
    _current_index: int = PrivateAttr(default=0)

    # LangChain required properties
    model_name: str = Field(default="mock-llm")

    @property
    def call_count(self) -> int:
        """Get the current call count."""
        return self._call_count

    @call_count.setter
    def call_count(self, value: int) -> None:
        """Set the call count."""
        self._call_count = value

    @property
    def _llm_type(self) -> str:
        """Return identifier of llm type."""
        return "serializable_mock"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Synchronous generation method.

        Args:
            messages: List of messages (only last message is considered)
            stop: Stop sequences (ignored in mock)
            run_manager: Run manager (ignored in mock)
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            ChatResult with mock AI message
        """
        # Simulate delay for performance testing
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        # Get response
        response = self._get_next_response()

        # Track call
        self._call_count += 1

        # Create AI message
        message = AIMessage(content=response)

        # Return result
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Asynchronous generation method.

        Args:
            messages: List of messages (only last message is considered)
            stop: Stop sequences (ignored in mock)
            run_manager: Run manager (ignored in mock)
            **kwargs: Additional arguments (ignored in mock)

        Returns:
            ChatResult with mock AI message
        """
        # Simulate delay for performance testing
        if self.delay_seconds > 0:
            import asyncio

            await asyncio.sleep(self.delay_seconds)

        # Get response
        response = self._get_next_response()

        # Track call
        self._call_count += 1

        # Create AI message
        message = AIMessage(content=response)

        # Return result
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _get_next_response(self) -> str:
        """
        Get next response from the response list.

        Cycles through responses if list is exhausted.
        """
        if not self.responses:
            return "Default mock response"

        response = self.responses[self._current_index % len(self.responses)]
        self._current_index += 1
        return response

    def reset(self) -> None:
        """Reset mock state (call count and response index)."""
        self._call_count = 0
        self._current_index = 0

    def __reduce__(self):
        """
        Custom pickle support for msgpack serialization.

        Returns tuple for object reconstruction during deserialization.
        """
        return (
            self.__class__,
            (),
            {
                "responses": self.responses,
                "delay_seconds": self.delay_seconds,
                "model_name": self.model_name,
                "_call_count": self._call_count,
                "_current_index": self._current_index,
            },
        )

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore object state during deserialization."""
        # Restore public fields
        self.responses = state.get("responses", ["Mock LLM response"])
        self.delay_seconds = state.get("delay_seconds", 0.0)
        self.model_name = state.get("model_name", "mock-llm")

        # Restore private attributes
        self._call_count = state.get("_call_count", 0)
        self._current_index = state.get("_current_index", 0)


@dataclass
class SerializableToolMock:
    """
    Serializable tool mock for testing tool execution.

    Unlike MagicMock, this can be serialized by msgpack and used
    in LangGraph checkpoints.

    Attributes:
        name: Tool name
        return_value: Value to return when invoked
        execution_time: Simulated execution time
        call_count: Number of invocations
        call_args: List of arguments from each call
    """

    name: str = "mock_tool"
    return_value: Any = "Mock tool result"
    execution_time: float = 0.0
    call_count: int = field(default=0, init=False)
    call_args: list[dict[str, Any]] = field(default_factory=list, init=False)

    def __call__(self, **kwargs: Any) -> Any:
        """
        Invoke the mock tool.

        Args:
            **kwargs: Tool arguments (recorded for inspection)

        Returns:
            Configured return_value
        """
        # Record call
        self.call_count += 1
        self.call_args.append(kwargs)

        # Simulate execution time
        if self.execution_time > 0:
            time.sleep(self.execution_time)

        return self.return_value

    async def ainvoke(self, **kwargs: Any) -> Any:
        """
        Async invoke the mock tool.

        Args:
            **kwargs: Tool arguments (recorded for inspection)

        Returns:
            Configured return_value
        """
        # Record call
        self.call_count += 1
        self.call_args.append(kwargs)

        # Simulate execution time
        if self.execution_time > 0:
            import asyncio

            await asyncio.sleep(self.execution_time)

        return self.return_value

    def reset(self) -> None:
        """Reset mock state."""
        self.call_count = 0
        self.call_args.clear()


# Pytest fixtures


def pytest_serializable_llm_mock():
    """
    Pytest fixture for SerializableLLMMock.

    Usage:
        def test_with_mock_llm(serializable_llm_mock):
            result = serializable_llm_mock._generate([HumanMessage(content="test")])
            assert result.generations[0].message.content
    """
    return SerializableLLMMock(
        responses=[
            "I am a mock AI assistant. This is response 1.",
            "This is mock response 2 with different content.",
            "Mock response 3 for testing variety.",
        ],
        delay_seconds=0.1,  # 100ms delay for performance testing
    )
