"""
LiteLLM ChatModel Adapter.

Provides a minimal LangChain-compatible ChatModel wrapper around LiteLLM
for providers that don't have native LangChain integrations.

This adapter is used as a fallback when:
- The provider doesn't have a native LangChain integration
- langchain-community is not installed
- Anthropic-on-Vertex AI is used (ChatVertexAI doesn't support Claude)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings


class LiteLLMChatModel(BaseChatModel):
    """Minimal LangChain ChatModel wrapper around LiteLLM.

    This adapter provides LangChain compatibility for LiteLLM-supported
    providers that don't have native LangChain integrations.
    """

    model_name: str
    temperature: float
    max_tokens: int
    provider: str

    def __init__(self, settings: "Settings") -> None:
        """Initialize with settings.

        Args:
            settings: Application settings containing LLM configuration
        """
        super().__init__(
            model_name=settings.model_name,
            temperature=settings.model_temperature,
            max_tokens=settings.model_max_tokens,
            provider=settings.llm_provider,
        )

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM type."""
        return f"litellm_{self.provider}"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous generation (blocking)."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self._agenerate(messages, stop, **kwargs)
        )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Asynchronous generation via LiteLLM."""
        from litellm import acompletion

        # Convert LangChain messages to LiteLLM format
        formatted_messages = self._format_messages(messages)

        response = await acompletion(
            model=self.model_name,
            messages=formatted_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stop=stop,
            **kwargs,
        )

        # Extract content from response
        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""

        return ChatResult(
            generations=[ChatGeneration(text=content, message=AIMessage(content=content))],
            llm_output={
                "token_usage": {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                }
            },
        )

    def _format_messages(self, messages: list[BaseMessage]) -> list[dict[str, str]]:
        """Convert LangChain messages to LiteLLM format."""
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                formatted.append({"role": "user", "content": content})
            elif isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                formatted.append({"role": "assistant", "content": content})
            elif isinstance(msg, SystemMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                formatted.append({"role": "system", "content": content})
            else:
                formatted.append({"role": "user", "content": str(getattr(msg, "content", msg))})
        return formatted
