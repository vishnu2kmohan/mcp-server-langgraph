"""Native tool configuration and result parsing.

Handles native LLM provider tools (Anthropic web_search, code_execution,
Google grounded search) - configuration generation and result parsing.

Native Tool Types by Provider:
- Anthropic: web_search_20250305, code_execution_20250825
- Google: googleSearch (grounded search)

Usage:
    from mcp_server_langgraph.tools.native_handler import (
        NativeToolHandler,
        parse_native_results,
    )

    handler = NativeToolHandler(model_name="claude-sonnet-4-20250514")
    if handler.should_use_native("web_search", "auto"):
        config = handler._get_config_for_tool("web_search")
        # Pass config to model invocation

    # After model response, parse native results
    tool_messages = parse_native_results(response)
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from mcp_server_langgraph.agents.model_registry import ModelRegistry
from mcp_server_langgraph.core.feature_flags import feature_flags
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.tools.native_metrics import (
    record_builtin_tool_execution,
    record_native_fallback,
    record_native_tool_error,
    record_native_tool_execution,
    record_native_tool_selection,
    record_tool_source_selection,
)

# Known source prefixes - only these are parsed as source:name
# Unknown prefixes (e.g., "github:") are MCP qualified names and preserved intact
KNOWN_SOURCES = {"native", "builtin", "mcp"}


class NativeToolHandler:
    """Handles native tool configuration and results.

    Determines when to use native provider tools vs builtin tools,
    generates provider-specific configurations, and parses results.

    Attributes:
        model_name: The model identifier
        caps: Model capabilities from ModelRegistry
    """

    def __init__(self, model_name: str) -> None:
        """Initialize with model name.

        Args:
            model_name: Model identifier for capability lookup
        """
        self.model_name = model_name
        self.caps = ModelRegistry().get(model_name)

    def should_use_native(self, tool_name: str, preference: str) -> bool:
        """Check if native tool should be used.

        Evaluates feature flags, model capabilities, and user preference
        to determine if a native tool should be used.

        Uses get_native_for_builtin() to map builtin names to native equivalents.
        CRITICAL: For OpenAI, also requires use_responses_api_for_openai flag.

        Args:
            tool_name: Tool name (e.g., "web_search", "code_execution", "execute_python")
            preference: User preference ("auto", "native", "builtin", "mcp")

        Returns:
            True if native tool should be used, False otherwise
        """
        # Check master feature flag
        if not feature_flags.native_tools_enabled:
            return False

        # "builtin" or "mcp" preference forces non-native
        if preference in ("builtin", "mcp"):
            return False

        # Map builtin name to native name if needed (e.g., execute_python → code_execution)
        from mcp_server_langgraph.tools.native_registry import get_native_for_builtin

        native_def = get_native_for_builtin(tool_name, self.caps.native_provider or "")
        effective_name = native_def.name if native_def else tool_name

        # Check model capability and specific feature flags
        if effective_name == "web_search":
            if not self.caps.supports_native_web_search:
                return False
            if self.caps.native_provider == "anthropic":
                return feature_flags.anthropic_native_web_search_enabled
            if self.caps.native_provider == "google":
                return feature_flags.google_native_search_enabled
            if self.caps.native_provider == "openai":
                # CRITICAL: OpenAI native tools require Responses API
                return feature_flags.openai_native_web_search_enabled and feature_flags.use_responses_api_for_openai
        elif effective_name == "code_execution":
            if not self.caps.supports_native_code_execution:
                return False
            if self.caps.native_provider == "anthropic":
                return feature_flags.anthropic_native_code_execution_enabled
            if self.caps.native_provider == "openai":
                # CRITICAL: OpenAI native tools require Responses API
                return feature_flags.openai_native_code_interpreter_enabled and feature_flags.use_responses_api_for_openai

        return False

    def get_native_configs(
        self,
        tool_names_or_ids: list[str],
        preference: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Get native configs and remaining tool names/IDs for builtins.

        Accepts:
        - Known qualified IDs: "native:web_search", "builtin:calculator", "mcp:server/tool"
        - MCP qualified names: "github:create_issue" (preserved intact!)
        - Plain tool names: "web_search", "execute_python"

        CRITICAL: MCP qualified names (e.g., "github:create_issue") must be preserved
        intact in remaining - they are NOT source:name prefixes.

        Args:
            tool_names_or_ids: List of tool name or tool_id strings
            preference: User preference for tool type

        Returns:
            Tuple of (native_configs, remaining_tool_ids)
        """
        native_configs: list[dict[str, Any]] = []
        remaining: list[str] = []

        for tool_id in tool_names_or_ids:
            source: str | None = None
            name: str = tool_id
            prefix: str | None = None

            # Only parse as source:name if prefix is a known source
            if ":" in tool_id:
                parts = tool_id.split(":", 1)
                prefix = parts[0]
                if prefix in KNOWN_SOURCES:
                    source = prefix
                    name = parts[1]
                # else: MCP qualified name like "github:create_issue" - keep as-is

            # Check if this tool should use native execution
            should_native = False
            if source == "native":
                should_native = self.should_use_native(name, preference)
            elif source is None and preference in ("auto", "native"):
                # Plain name with auto/native preference - check if native available
                should_native = self.should_use_native(name, preference)
            # Note: source == "mcp" or MCP qualified names skip native check

            if should_native:
                config = self._get_config_for_tool(name)
                if config:
                    native_configs.append(config)
                    provider = self.caps.native_provider or "unknown"
                    record_native_tool_selection(
                        tool_name=name,
                        provider=provider,
                        preference=preference,
                    )
                    record_tool_source_selection(
                        tool_name=name,
                        source="native",
                        model=self.model_name,
                    )
                    continue
                else:
                    logger.warning(f"Native tool '{name}' config unavailable, falling back to builtin")

            # Add to remaining - preserve original tool_id (important for MCP!)
            # Determine correct source for metrics
            if source:
                metric_source = source  # Known source (native, builtin, mcp)
            elif prefix is not None and prefix not in KNOWN_SOURCES:
                metric_source = "mcp"  # Unknown prefix = MCP qualified name
            else:
                metric_source = "builtin"  # Plain name = builtin

            record_tool_source_selection(
                tool_name=name,
                source=metric_source,
                model=self.model_name,
            )
            remaining.append(tool_id)  # Preserve original ID for MCP matching

        return native_configs, remaining

    def _get_config_for_tool(self, name: str) -> dict[str, Any] | None:
        """Get provider-specific native tool config.

        Handles name mapping (execute_python → code_execution).
        CRITICAL: Checks model capabilities before returning config.

        Args:
            name: Tool name (e.g., "web_search", "code_execution", "execute_python")

        Returns:
            Provider-specific config dict, or None if unsupported
        """
        provider = self.caps.native_provider
        if not provider:
            return None

        # Map builtin name to native name
        from mcp_server_langgraph.tools.native_registry import get_native_for_builtin

        native_def = get_native_for_builtin(name, provider)
        effective_name = native_def.name if native_def else name

        # CRITICAL: Check model capability before returning config
        # This prevents returning configs for unsupported tools
        # (e.g., code_execution on Vertex AI Anthropic)
        if effective_name == "web_search" and not self.caps.supports_native_web_search:
            return None
        if effective_name == "code_execution" and not self.caps.supports_native_code_execution:
            return None

        if provider == "anthropic":
            if effective_name == "web_search":
                return {"type": "web_search_20250305"}
            if effective_name == "code_execution":
                return {"type": "code_execution_20250825"}
        elif provider == "google":
            if effective_name == "web_search":
                return {"googleSearch": {}}
        elif provider == "openai":
            if effective_name == "web_search":
                return {
                    "type": "web_search_preview",
                    "search_context_size": "medium",
                }
            if effective_name == "code_execution":
                return {
                    "type": "code_interpreter",
                    "container": {"type": "auto"},
                }

        return None


def parse_native_results(response: AIMessage) -> list[ToolMessage]:
    """Parse native tool results from AIMessage.

    Checks both:
    - response.content (list of blocks) for Anthropic/Google
    - response.additional_kwargs["native_output"] for OpenAI Responses API

    Content block types handled:
    - tool_result: Direct tool result with tool_use_id
    - web_search_results: Search results with title/url/snippet (Anthropic)
    - web_search_call: OpenAI web search results (Responses API)
    - code_interpreter_call: OpenAI code interpreter results (Responses API)

    Args:
        response: AIMessage from model with potential native results

    Returns:
        List of ToolMessage objects extracted from native results
    """
    tool_messages: list[ToolMessage] = []

    # Check additional_kwargs for OpenAI Responses API output
    native_output = response.additional_kwargs.get("native_output")
    if native_output:
        for item in native_output:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type")

            # OpenAI message with content blocks
            if item_type == "message":
                for block in item.get("content", []):
                    block_type = block.get("type")
                    if block_type == "web_search_call":
                        results = block.get("results", [])
                        content = "\n".join(
                            f"[{r.get('title', '')}]({r.get('url', '')}): {r.get('snippet', '')}" for r in results
                        )
                        tool_messages.append(
                            ToolMessage(
                                content=content,
                                tool_call_id=block.get("id", "web_search"),
                                name="web_search",
                            )
                        )
                    elif block_type == "code_interpreter_call":
                        output = block.get("output", block.get("result", ""))
                        tool_messages.append(
                            ToolMessage(
                                content=str(output),
                                tool_call_id=block.get("id", "code_interpreter"),
                                name="code_execution",
                            )
                        )

            # Direct tool call items (top-level)
            elif item_type == "web_search_call":
                results = item.get("results", [])
                content = "\n".join(f"[{r.get('title', '')}]({r.get('url', '')}): {r.get('snippet', '')}" for r in results)
                tool_messages.append(
                    ToolMessage(
                        content=content,
                        tool_call_id=item.get("id", "web_search"),
                        name="web_search",
                    )
                )
            elif item_type == "code_interpreter_call":
                output = item.get("output", item.get("result", ""))
                tool_messages.append(
                    ToolMessage(
                        content=str(output),
                        tool_call_id=item.get("id", "code_interpreter"),
                        name="code_execution",
                    )
                )

    # Check content blocks for Anthropic/Google (existing logic)
    if isinstance(response.content, list):
        for block in response.content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")

            # Handle tool_result blocks (Anthropic pattern)
            if block_type == "tool_result":
                tool_messages.append(
                    ToolMessage(
                        content=str(block.get("content", "")),
                        tool_call_id=block.get("tool_use_id", "native"),
                        name=block.get("name", "native_tool"),
                    )
                )

            # Handle web_search_results blocks (Anthropic web search)
            elif block_type == "web_search_results":
                results = block.get("results", [])
                content = "\n".join(f"[{r.get('title', '')}]({r.get('url', '')}): {r.get('snippet', '')}" for r in results)
                tool_messages.append(
                    ToolMessage(
                        content=content,
                        tool_call_id="web_search",
                        name="web_search",
                    )
                )

    return tool_messages


# =============================================================================
# Fallback Chain (v7)
# =============================================================================

# Mapping of native tool names to their builtin equivalents
NATIVE_TO_BUILTIN_MAP: dict[str, str] = {
    "web_search": "web_search",  # Same name, different implementation
    "code_execution": "execute_python",  # Anthropic code_execution → builtin execute_python
    "execute_python": "execute_python",  # Direct mapping
}


class NativeToolFallbackChain:
    """Fallback chain for native tool execution.

    When native tools fail (timeout, rate limit, error), this handler
    automatically falls back to builtin equivalents if available.

    Features:
    - Automatic fallback on native tool errors
    - Metrics recording for failures and fallbacks
    - Configurable retry behavior
    - Seamless integration with tool execution layer

    Usage:
        from mcp_server_langgraph.tools.native_handler import (
            NativeToolFallbackChain,
        )

        chain = NativeToolFallbackChain()

        # Execute with automatic fallback
        result = await chain.execute_with_fallback(
            tool_name="web_search",
            args={"query": "AI news"},
            native_executor=native_tool_fn,
            builtin_executor=builtin_tool_fn,
            provider="anthropic",
        )
    """

    def __init__(
        self,
        max_native_retries: int = 1,
        enable_fallback: bool = True,
    ) -> None:
        """Initialize fallback chain.

        Args:
            max_native_retries: Max retries before falling back (default: 1)
            enable_fallback: Whether to fall back to builtins (default: True)
        """
        self.max_native_retries = max_native_retries
        self.enable_fallback = enable_fallback

    async def execute_with_fallback(
        self,
        tool_name: str,
        args: dict[str, Any],
        native_executor: Any,
        builtin_executor: Any | None,
        provider: str,
    ) -> tuple[str, str]:
        """Execute native tool with fallback to builtin on failure.

        Attempts to execute the native tool first. If it fails, falls back
        to the builtin equivalent if available and fallback is enabled.

        Args:
            tool_name: Name of the tool (e.g., "web_search")
            args: Arguments to pass to the tool
            native_executor: Async callable for native tool execution
            builtin_executor: Async callable for builtin tool (or None)
            provider: Native provider name (e.g., "anthropic")

        Returns:
            Tuple of (result_content, execution_source)
            execution_source is "native" or "builtin"

        Raises:
            Exception: If both native and builtin fail
        """
        import time

        # Try native execution first
        for attempt in range(self.max_native_retries + 1):
            try:
                start_time = time.perf_counter()
                result = await native_executor(args)
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record successful native execution
                record_native_tool_execution(
                    tool_name=tool_name,
                    provider=provider,
                    duration_ms=duration_ms,
                    success=True,
                )

                logger.info(
                    f"Native tool '{tool_name}' executed successfully",
                    extra={
                        "tool_name": tool_name,
                        "provider": provider,
                        "duration_ms": round(duration_ms, 2),
                    },
                )

                return str(result), "native"

            except Exception as e:
                error_type = self._classify_error(e)

                # Record native tool error
                record_native_tool_error(
                    tool_name=tool_name,
                    provider=provider,
                    error_type=error_type,
                )

                logger.warning(
                    f"Native tool '{tool_name}' failed (attempt {attempt + 1}/{self.max_native_retries + 1}): {e}",
                    extra={
                        "tool_name": tool_name,
                        "provider": provider,
                        "error_type": error_type,
                        "attempt": attempt + 1,
                    },
                )

                # If not last attempt, retry
                if attempt < self.max_native_retries:
                    continue

                # Last attempt failed - try fallback
                if self.enable_fallback and builtin_executor is not None:
                    return await self._execute_builtin_fallback(
                        tool_name=tool_name,
                        args=args,
                        builtin_executor=builtin_executor,
                        provider=provider,
                        reason=error_type,
                    )

                # No fallback - re-raise
                raise

        # Should never reach here, but satisfy type checker
        msg = f"Native tool '{tool_name}' failed after all retries"
        raise RuntimeError(msg)

    async def _execute_builtin_fallback(
        self,
        tool_name: str,
        args: dict[str, Any],
        builtin_executor: Any,
        provider: str,
        reason: str,
    ) -> tuple[str, str]:
        """Execute builtin tool as fallback.

        Args:
            tool_name: Original tool name
            args: Arguments to pass
            builtin_executor: Callable for builtin execution
            provider: Native provider that failed
            reason: Reason for fallback

        Returns:
            Tuple of (result_content, "builtin")
        """
        import time

        builtin_name = NATIVE_TO_BUILTIN_MAP.get(tool_name, tool_name)

        # Record fallback event
        record_native_fallback(
            tool_name=tool_name,
            from_provider=provider,
            to_source="builtin",
            reason=reason,
        )

        logger.info(
            f"Falling back from native '{tool_name}' to builtin '{builtin_name}'",
            extra={
                "tool_name": tool_name,
                "builtin_name": builtin_name,
                "provider": provider,
                "reason": reason,
            },
        )

        try:
            start_time = time.perf_counter()
            result = await builtin_executor(args)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record successful builtin execution
            record_builtin_tool_execution(
                tool_name=builtin_name,
                duration_ms=duration_ms,
                success=True,
            )

            logger.info(
                f"Builtin fallback '{builtin_name}' executed successfully",
                extra={
                    "tool_name": builtin_name,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            return str(result), "builtin"

        except Exception as e:
            # Record builtin failure
            record_builtin_tool_execution(
                tool_name=builtin_name,
                duration_ms=0.0,
                success=False,
            )

            logger.error(
                f"Builtin fallback '{builtin_name}' also failed: {e}",
                extra={
                    "tool_name": builtin_name,
                    "error": str(e),
                },
            )
            raise

    def _classify_error(self, error: Exception) -> str:
        """Classify error type for metrics.

        Args:
            error: The exception that occurred

        Returns:
            Error type string for metrics labeling
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        if "timeout" in error_str or "timeout" in error_type:
            return "timeout"
        if "rate" in error_str and "limit" in error_str:
            return "rate_limit"
        if "quota" in error_str:
            return "quota_exceeded"
        if "auth" in error_str or "unauthorized" in error_str:
            return "auth_error"
        if "connection" in error_str or "network" in error_str:
            return "network_error"
        if "api" in error_type:
            return "api_error"

        return "unknown"

    def get_builtin_equivalent(self, tool_name: str) -> str | None:
        """Get the builtin equivalent for a native tool.

        Args:
            tool_name: Native tool name

        Returns:
            Builtin tool name or None if no equivalent
        """
        return NATIVE_TO_BUILTIN_MAP.get(tool_name)


# Global fallback chain instance
_fallback_chain: NativeToolFallbackChain | None = None


def get_fallback_chain() -> NativeToolFallbackChain:
    """Get the global fallback chain instance."""
    global _fallback_chain
    if _fallback_chain is None:
        _fallback_chain = NativeToolFallbackChain()
    return _fallback_chain


def reset_fallback_chain() -> None:
    """Reset the global fallback chain (for testing)."""
    global _fallback_chain
    _fallback_chain = None
