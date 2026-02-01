"""ChatModel wrapper preserving ADR-0080 hooks (v7).

EXACTLY mirrors LLMFactory.ainvoke() behavior:
- Message formatting before BEFORE_MODEL dispatch
- All behaviors: deny (error), skip (early_return), allow (continue)
- updated_input APPLIED TO ACTUAL INNER CALL (not just tracing)
- Rate limiting + adaptive bulkhead with record_error() on failures
- AFTER_MODEL with modified_output support
- Native configs passed via invocation kwargs (not bind_tools)
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict

from mcp_server_langgraph.core.exceptions import LLMProviderError
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.core.hooks import HookContext, TokenUsage as HookTokenUsage
from mcp_server_langgraph.observability.telemetry import get_tracer
from mcp_server_langgraph.resilience.adaptive import get_provider_adaptive_bulkhead
from mcp_server_langgraph.resilience.rate_limit import get_provider_token_bucket


class HookedChatModel(BaseChatModel):
    """Wraps LangChain ChatModel with ADR-0080 hooks and resilience.

    This wrapper provides:
    - BEFORE_MODEL hook dispatch (can modify, skip, or deny requests)
    - AFTER_MODEL hook dispatch (can modify output)
    - Rate limiting via provider-specific token buckets
    - Adaptive bulkhead for concurrency control
    - Native tool config passing via invocation kwargs

    Note: Resilience decorators (circuit_breaker, retry_with_backoff, etc.)
    are intentionally NOT applied here since the inner model may already
    have its own resilience handling. The wrapper focuses on hooks only.
    """

    inner: Any  # BaseChatModel - using Any to support testing with mocks
    hook_dispatcher: Any = None  # HookDispatcher | None - using Any to avoid Pydantic forward ref issues
    model_name: str = ""
    provider: str = "unknown"
    temperature: float = 1.0
    max_tokens: int = 8192

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        inner: BaseChatModel,
        hook_dispatcher: Any = None,  # HookDispatcher | None
        model_name: str = "",
        provider: str = "unknown",
        temperature: float = 1.0,
        max_tokens: int = 8192,
        **kwargs: Any,
    ) -> None:
        """Initialize the hooked chat model.

        Args:
            inner: The underlying LangChain ChatModel to wrap
            hook_dispatcher: Optional hook dispatcher for BEFORE_MODEL/AFTER_MODEL hooks
            model_name: Model identifier for telemetry and hooks
            provider: Provider name (anthropic, openai, google, etc.)
            temperature: Default temperature for generation
            max_tokens: Default max tokens for generation
            **kwargs: Additional kwargs passed to parent
        """
        super().__init__(
            inner=inner,
            hook_dispatcher=hook_dispatcher,
            model_name=model_name,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM type."""
        return f"hooked_{self.inner._llm_type}"

    def _format_messages(self, messages: list[BaseMessage]) -> list[dict[str, str]]:
        """Format LangChain messages for hook dispatch.

        Converts LangChain message types to role/content dicts
        for hook consumption.

        Args:
            messages: List of LangChain BaseMessage objects

        Returns:
            List of dicts with role and content keys
        """
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

    def _rebuild_messages(self, formatted: list[dict[str, str]]) -> list[BaseMessage]:
        """Rebuild LangChain messages from formatted dicts.

        Used to apply updated_input from hooks to the actual LLM call.

        Args:
            formatted: List of dicts with role and content keys

        Returns:
            List of LangChain BaseMessage objects
        """
        messages: list[BaseMessage] = []
        for msg in formatted:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous generation (blocking).

        Delegates to async implementation via event loop.
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self._agenerate(messages, stop, **kwargs))

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        *,
        hook_context: HookContext | None = None,
        native_tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate with full ADR-0080 hook support and resilience.

        This method mirrors LLMFactory.ainvoke() behavior:
        1. Format messages for hooks
        2. Dispatch BEFORE_MODEL hook (may deny, skip, or modify)
        3. Acquire rate limit token
        4. Execute under adaptive bulkhead
        5. Dispatch AFTER_MODEL hook (may modify output)

        Args:
            messages: List of LangChain messages
            stop: Optional stop sequences
            hook_context: Context for hook dispatch
            native_tools: Native tool configs to pass via kwargs
            **kwargs: Additional generation parameters

        Returns:
            ChatResult with generation output

        Raises:
            LLMProviderError: If hook denies the request
        """
        start_time = time.perf_counter()
        tracer = get_tracer()

        with tracer.start_as_current_span("llm.hooked_ainvoke") as span:
            span.set_attribute("gen_ai.system", self.provider)
            span.set_attribute("gen_ai.request.model", self.model_name)

            formatted_messages = self._format_messages(messages)
            ctx = hook_context or HookContext(session_id="default")
            messages_to_use = messages  # May be replaced by updated_input

            # Extract temperature and max_tokens from kwargs or use defaults
            effective_temperature = kwargs.pop("temperature", self.temperature)
            effective_max_tokens = kwargs.pop("max_tokens", self.max_tokens)

            # ===== BEFORE_MODEL HOOK =====
            if self.hook_dispatcher and feature_flags.enable_llm_hooks:
                before_result = await self.hook_dispatcher.dispatch_before_model(
                    messages=formatted_messages,
                    model=self.model_name,
                    context=ctx,
                    temperature=effective_temperature,
                    max_tokens=effective_max_tokens,
                )

                if before_result.behavior == "deny":
                    msg = before_result.message or "LLM request denied by hook"
                    span.set_attribute("hook.before_model.denied", True)
                    raise LLMProviderError(
                        message=msg,
                        metadata={
                            "model": self.model_name,
                            "provider": self.provider,
                            "hook_denied": True,
                        },
                    )

                if before_result.behavior == "skip" and before_result.early_return is not None:
                    span.set_attribute("hook.before_model.skipped", True)
                    return ChatResult(
                        generations=[
                            ChatGeneration(
                                text=str(before_result.early_return),
                                message=AIMessage(content=str(before_result.early_return)),
                            )
                        ]
                    )

                # CRITICAL (v7): Apply updated_input to ACTUAL inner call
                if before_result.updated_input is not None and isinstance(before_result.updated_input, list):
                    span.set_attribute("hook.before_model.updated_input", True)
                    messages_to_use = self._rebuild_messages(before_result.updated_input)

            # ===== RATE LIMITING =====
            rate_limit_bucket = get_provider_token_bucket(self.provider)
            await rate_limit_bucket.acquire(timeout=30.0)

            # ===== ADAPTIVE BULKHEAD =====
            adaptive_bulkhead = get_provider_adaptive_bulkhead(self.provider)
            semaphore = adaptive_bulkhead.get_semaphore()

            async with semaphore:
                try:
                    # v7: Pass native_tools via provider-specific kwargs
                    invoke_kwargs = {**kwargs}
                    if native_tools:
                        # Anthropic: tools=[{"type": "web_search_20250305"}]
                        invoke_kwargs["tools"] = native_tools

                    result = await self.inner._agenerate(
                        messages_to_use,  # Use potentially modified messages
                        stop=stop,
                        **invoke_kwargs,
                    )
                    adaptive_bulkhead.record_success()
                except Exception:
                    # CRITICAL (v7): Use record_error() not record_failure()
                    adaptive_bulkhead.record_error()
                    raise

            duration_ms = (time.perf_counter() - start_time) * 1000
            content = result.generations[0].text if result.generations else ""

            # ===== AFTER_MODEL HOOK =====
            if self.hook_dispatcher and feature_flags.enable_llm_hooks:
                hook_usage = None
                if hasattr(result, "llm_output") and result.llm_output:
                    usage = result.llm_output.get("token_usage", {})
                    if usage:
                        hook_usage = HookTokenUsage(
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            total_tokens=usage.get("total_tokens", 0),
                        )

                after_result = await self.hook_dispatcher.dispatch_after_model(
                    content=content,
                    model=self.model_name,
                    context=ctx,
                    usage=hook_usage,
                    latency_ms=duration_ms,
                    finish_reason="stop",
                )

                if after_result.modified_output is not None:
                    content = after_result.modified_output
                    span.set_attribute("hook.after_model.modified", True)
                    return ChatResult(
                        generations=[ChatGeneration(text=content, message=AIMessage(content=content))],
                        llm_output=result.llm_output,
                    )

            return result

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> HookedChatModel:
        """Delegate bind_tools to inner model, preserve wrapper.

        NOTE: Native tool configs are NOT passed here. Use invocation kwargs.

        Args:
            tools: List of tools to bind
            **kwargs: Additional kwargs for bind_tools

        Returns:
            New HookedChatModel wrapping the bound inner model
        """
        bound_inner = self.inner.bind_tools(tools, **kwargs)
        return HookedChatModel(
            inner=bound_inner,
            hook_dispatcher=self.hook_dispatcher,
            model_name=self.model_name,
            provider=self.provider,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def _astream(self, *args: Any, **kwargs: Any) -> Any:
        """Stream without hooks (matches LLMFactory behavior).

        Streaming bypasses hooks for simplicity - hook support for
        streaming would require chunk aggregation which is complex.
        """
        async for chunk in self.inner._astream(*args, **kwargs):
            yield chunk
