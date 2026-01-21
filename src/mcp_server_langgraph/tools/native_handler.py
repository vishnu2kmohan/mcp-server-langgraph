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

        Args:
            tool_name: Tool name (e.g., "web_search", "code_execution")
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

        # Check model capability and specific feature flags
        if tool_name == "web_search":
            if not self.caps.supports_native_web_search:
                return False
            if self.caps.native_provider == "anthropic":
                return feature_flags.anthropic_native_web_search_enabled
            if self.caps.native_provider == "google":
                return feature_flags.google_native_search_enabled
        elif tool_name in ("code_execution", "execute_python"):
            if not self.caps.supports_native_code_execution:
                return False
            return feature_flags.anthropic_native_code_execution_enabled

        return False

    def get_native_configs(
        self,
        tool_ids: list[str],
        preference: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Get native configs and remaining tool_ids for builtins.

        Separates tool_ids into native configs (for provider) and
        remaining tool_ids (for builtin/MCP execution).

        Args:
            tool_ids: List of tool_id strings (e.g., "native:web_search")
            preference: User preference for tool type

        Returns:
            Tuple of (native_configs, remaining_tool_ids)
        """
        native_configs: list[dict[str, Any]] = []
        remaining: list[str] = []

        for tool_id in tool_ids:
            parts = tool_id.split(":", 1)
            source = parts[0] if len(parts) > 1 else "builtin"
            name = parts[1] if len(parts) > 1 else tool_id

            if source == "native" and self.should_use_native(name, preference):
                # Get provider-specific config
                config = self._get_config_for_tool(name)
                if config:
                    native_configs.append(config)
                    continue

            remaining.append(tool_id)

        return native_configs, remaining

    def _get_config_for_tool(self, name: str) -> dict[str, Any] | None:
        """Get provider-specific native tool config.

        Args:
            name: Tool name (e.g., "web_search", "code_execution")

        Returns:
            Provider-specific config dict, or None if unsupported
        """
        provider = self.caps.native_provider
        if not provider:
            return None

        if provider == "anthropic":
            if name == "web_search":
                return {"type": "web_search_20250305"}
            if name in ("code_execution", "execute_python"):
                return {"type": "code_execution_20250825"}
        elif provider == "google":
            if name == "web_search":
                return {"googleSearch": {}}

        return None


def parse_native_results(response: AIMessage) -> list[ToolMessage]:
    """Parse native tool results from AIMessage content blocks.

    Native tools (Anthropic web_search, code_execution) return results
    as content blocks embedded in the response. This function extracts
    them and converts to ToolMessage format for consistency.

    Content block types handled:
    - tool_result: Direct tool result with tool_use_id
    - web_search_results: Search results with title/url/snippet

    Args:
        response: AIMessage from model with potential native results

    Returns:
        List of ToolMessage objects extracted from native results
    """
    tool_messages: list[ToolMessage] = []

    # Only process list content (native results are blocks)
    if not isinstance(response.content, list):
        return tool_messages

    for block in response.content:
        if not isinstance(block, dict):
            continue

        # Handle tool_result blocks (Anthropic pattern)
        if block.get("type") == "tool_result":
            tool_messages.append(
                ToolMessage(
                    content=str(block.get("content", "")),
                    tool_call_id=block.get("tool_use_id", "native"),
                    name=block.get("name", "native_tool"),
                )
            )

        # Handle web_search_results blocks (Anthropic web search)
        elif block.get("type") == "web_search_results":
            results = block.get("results", [])
            content = "\n".join(
                f"[{r.get('title', '')}]({r.get('url', '')}): {r.get('snippet', '')}"
                for r in results
            )
            tool_messages.append(
                ToolMessage(
                    content=content,
                    tool_call_id="web_search",
                    name="web_search",
                )
            )

    return tool_messages
