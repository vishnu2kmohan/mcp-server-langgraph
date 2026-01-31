"""
Chat Router

Provides real-time chat interactions under /api/v1/chat/*.

This consolidates chat functionality from playground into a unified API.

Usage:
    POST /api/v1/chat/completions - Create a chat completion
    POST /api/v1/chat/completions/stream - Create a streaming chat completion
    GET /api/v1/chat/{session_id}/history - Get chat history for a session

LLM Integration:
    All streaming uses LLMFactory.astream() which provides:
    - Circuit breaker resilience
    - Retry with exponential backoff
    - OTEL tracing integration
    - Cost tracking via LiteLLM's CostTrackingCallback

    Note: The legacy _stream_via_litellm() method has been removed.
    LLMFactory is now the only streaming path, providing unified resilience patterns.

Authorization:
    All endpoints require authentication. Chat sessions are user-owned resources.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any, Callable, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from litellm import acompletion
from opentelemetry import trace
from pydantic import BaseModel, Field

from mcp_server_langgraph.api.deps import get_audit_service, get_openfga_client
from mcp_server_langgraph.api.v1.serializers import plan_to_dict
from mcp_server_langgraph.auth.dependencies import get_current_user
from mcp_server_langgraph.core.agent import create_agent_graph
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.tools.source_citation import SourceCitation

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Note: Cost tracking is now handled automatically by CostTrackingCallback
# registered in llm/factory.py. No manual record_usage() calls needed here.
# The callback uses LiteLLM's response_cost as the authoritative source.


chat_router = APIRouter(tags=["chat"])


# ============================================================================
# Authorization Type Aliases
# ============================================================================

# Type alias for authenticated user dependency
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


def _get_user_id(user: dict[str, Any]) -> str:
    """Extract user ID from authenticated user dict."""
    return user.get("sub") or user.get("user_id") or user.get("preferred_username") or "anonymous"


async def _summarize_conversation(messages: list[dict[str, Any]]) -> str:
    """Summarize conversation history for swarm context (Phase 2).

    Creates a concise summary of the conversation for use when
    context_strategy="summarized" is selected. This provides workers
    with relevant context without overwhelming them with full history.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        Summarized conversation string. Empty string if no messages.
    """
    if not messages:
        return ""

    # For single message, just return its content
    if len(messages) == 1:
        return messages[0].get("content", "")

    # For multiple messages, create a structured summary
    # Format: condensed view of conversation turns
    summary_parts = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Truncate long messages for summary
        if len(content) > 200:
            content = content[:200] + "..."

        if role == "user":
            summary_parts.append(f"User: {content}")
        elif role == "assistant":
            summary_parts.append(f"Assistant: {content}")
        elif role == "system":
            summary_parts.append(f"System: {content}")

    return "\n".join(summary_parts)


# Request/Response Models


class ChatMessage(BaseModel):
    """A message in the chat conversation."""

    role: Literal["user", "assistant", "system"] = Field(description="Message role")
    content: str = Field(description="Message content")


class ChatCompletionRequest(BaseModel):
    """Request body for chat completion."""

    session_id: str = Field(description="Session ID for the conversation")
    messages: list[ChatMessage] = Field(description="List of messages in the conversation", min_length=1)
    model: str | None = Field(default=None, description="Model to use for completion")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(default=None, ge=1, le=4096, description="Maximum tokens to generate")
    resource_uris: list[str] | None = Field(
        default=None,
        description="Optional list of MCP resource URIs to inject as context (MCP 2025-11-25)",
    )
    # Extended thinking / reasoning effort parameters
    reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Reasoning effort level for models supporting extended thinking (Claude Opus 4.5, Sonnet 4, Gemini 2.5). "
        "Maps to LiteLLM's reasoning_effort parameter which translates to Anthropic's thinking budget.",
    )
    enable_thinking: bool = Field(
        default=True,
        description="Whether to enable extended thinking for supported models. Set to False to disable thinking even on models that support it.",
    )
    # Knowledge Base focus mode (Perplexity-style context retrieval control)
    kb_focus: Literal["all", "kb_only", "web_only", "none"] = Field(
        default="all",
        description="Knowledge Base focus mode controlling context retrieval strategy. "
        "'all' = use both KB and web search (default), "
        "'kb_only' = only use KB/vector store for context, "
        "'web_only' = only use web search for context, "
        "'none' = disable context augmentation.",
    )
    # Manual tool selection parameters
    selected_tools: list[str] | None = Field(
        default=None,
        description="Optional list of tool names to use. When provided with tool_selection_mode='manual', "
        "bypasses semantic search and uses only these tools. Tool names must match exactly "
        "(use qualified names for MCP tools, e.g., 'github:create_issue').",
    )
    tool_selection_mode: Literal["auto", "manual", "none"] = Field(
        default="auto",
        description="Tool selection mode: 'auto' = semantic search (default), "
        "'manual' = use selected_tools only, 'none' = disable all tools.",
    )
    tool_preference: Literal["auto", "native", "builtin", "mcp"] = Field(
        default="auto",
        description="Tool preference for this request: 'auto' = prefer native tools when available, "
        "'native' = only use native LLM provider tools (fallback to builtin if unavailable), "
        "'builtin' = only use built-in tools, 'mcp' = only use MCP server tools.",
    )
    # Execution mode for plan-and-execute workflow (Shift+Tab toggle in UI)
    execution_mode: Literal["default", "plan", "auto_accept", "bypass"] = Field(
        default="default",
        description="Execution mode controlling plan approval workflow. "
        "'default' = approval required for medium/high-risk plans, "
        "'plan' = all plans require approval, "
        "'auto_accept' = auto-approve all plans (no modal), "
        "'bypass' = skip all approvals (admin only, audited).",
    )


class ChatUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(description="Tokens in the prompt")
    completion_tokens: int = Field(description="Tokens in the completion")
    total_tokens: int | None = Field(default=None, description="Total tokens used")


class ThinkingContent(BaseModel):
    """Thinking/reasoning content from extended thinking models."""

    content: str = Field(description="The model's internal reasoning/thinking content")
    tokens: int | None = Field(default=None, description="Number of tokens used for thinking")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completion."""

    id: str = Field(description="Completion ID")
    message: ChatMessage = Field(description="Assistant's response message")
    usage: ChatUsage | None = Field(default=None, description="Token usage")
    model: str | None = Field(default=None, description="Model used")
    trace_id: str | None = Field(default=None, description="OpenTelemetry trace ID for observability correlation")
    thinking: ThinkingContent | None = Field(
        default=None,
        description="Thinking/reasoning content from extended thinking models (Claude Opus 4.5, Sonnet 4, Gemini 2.5)",
    )
    sources: list[SourceCitation] | None = Field(
        default=None,
        description="Source citations from web search results (native or builtin tools)",
    )


# ==============================================================================
# Extended Thinking Support
# ==============================================================================

# Models that support extended thinking / reasoning effort
# Based on LiteLLM docs: https://docs.litellm.ai/docs/reasoning_content
THINKING_MODELS = frozenset(
    {
        # Anthropic models with extended thinking
        "claude-opus-4-5",
        "claude-opus-4-5-20250514",
        "claude-sonnet-4-5",
        "claude-sonnet-4-5-20250514",
        "claude-sonnet-4",
        "claude-3-7-sonnet",
        "claude-3-7-sonnet-20250219",
        "claude-3.7-sonnet",
        "claude-3.5-sonnet",  # May support thinking in newer versions
        # Anthropic prefixed models
        "anthropic/claude-opus-4-5",
        "anthropic/claude-opus-4-5-20250514",
        "anthropic/claude-sonnet-4-5",
        "anthropic/claude-sonnet-4-5-20250514",
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3-7-sonnet",
        "anthropic/claude-3-7-sonnet-20250219",
        "anthropic/claude-3.7-sonnet",
        # Google Gemini models with thinking
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-thinking",
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-flash-thinking",
        # OpenAI o-series reasoning models
        "o1",
        "o1-preview",
        "o1-mini",
        "o3",
        "o3-mini",
        "openai/o1",
        "openai/o1-preview",
        "openai/o1-mini",
        "openai/o3",
        "openai/o3-mini",
        # DeepSeek reasoning models
        "deepseek-reasoner",
        "deepseek/deepseek-reasoner",
    }
)


def model_supports_thinking(model_name: str) -> bool:
    """
    Check if a model supports extended thinking / reasoning effort.

    Args:
        model_name: The model name to check (e.g., "claude-opus-4-5", "gemini-2.5-flash")

    Returns:
        True if the model supports extended thinking, False otherwise.
    """
    if not model_name:
        return False

    model_lower = model_name.lower()

    # Check exact match first
    if model_lower in THINKING_MODELS:
        return True

    # Check pattern-based matching for common naming variants
    thinking_patterns = [
        "claude-opus-4",
        "claude-sonnet-4",
        "claude-3.7",
        "claude-3-7",
        "gemini-2.5",
        "o1-",
        "o3-",
        "deepseek-reasoner",
    ]

    return any(pattern in model_lower for pattern in thinking_patterns)


# ==============================================================================
# Dynamic Context Configuration
# ==============================================================================

# Supported embedding providers for DynamicContextLoader
# Reference: src/mcp_server_langgraph/core/dynamic_context_loader.py
SUPPORTED_EMBEDDING_PROVIDERS = frozenset(
    {
        "google_vertex",  # VertexAIEmbeddings (GCP WIF auth)
        "google",  # GoogleGenerativeAIEmbeddings (API key auth)
        "openai",  # OpenAIEmbeddings
        "local",  # SentenceTransformer (no auth needed)
        "huggingface",  # HuggingFaceEmbeddings
    }
)


@dataclass
class DynamicContextConfigResult:
    """Result of dynamic context configuration validation.

    Used by validate_dynamic_context_config() to report configuration status
    before attempting to initialize DynamicContextLoader.
    """

    is_valid: bool = False
    missing_config: list[str] = field(default_factory=list)
    guidance: str | None = None


# Service Interface


class ChatService:
    """Interface for chat operations. Implemented by LLM layer."""

    async def create_completion(self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Create a chat completion. Returns the response."""
        raise NotImplementedError

    async def create_stream(
        self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Create a streaming chat completion. Yields chunks."""
        raise NotImplementedError
        yield  # type: ignore[unreachable]  # Makes mypy recognize this as an async generator

    async def get_history(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get chat history for a session. Returns None if not found."""
        raise NotImplementedError


def _build_langgraph_messages(
    messages: list[dict[str, Any]],
    record_metrics: bool = True,
) -> list[HumanMessage | AIMessage | SystemMessage]:
    """Build properly role-mapped LangChain messages for LangGraph.

    Converts a list of chat message dicts to LangChain message objects.
    This is used by both _stream_via_langgraph and _stream_via_llm_factory
    to ensure consistent role mapping.

    Also records token usage metrics for monitoring (Phase 4.1).

    Args:
        messages: List of chat messages with 'role' and 'content' keys
        record_metrics: Whether to record token usage metrics (default: True)

    Returns:
        List of LangChain message objects (HumanMessage, AIMessage, SystemMessage)
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    from mcp_server_langgraph.observability.telemetry import metrics

    langchain_messages: list[HumanMessage | AIMessage | SystemMessage] = []
    role_counts = {"system": 0, "user": 0, "assistant": 0}
    total_chars = 0

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        total_chars += len(content)

        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
            role_counts["system"] += 1
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
            role_counts["assistant"] += 1
        else:
            langchain_messages.append(HumanMessage(content=content))
            role_counts["user"] += 1

    # Record metrics for monitoring token usage (Phase 4.1)
    if record_metrics and langchain_messages:
        # Record message count histogram
        metrics.conversation_message_count.record(len(langchain_messages))

        # Estimate tokens (rough: ~4 chars per token)
        estimated_tokens = total_chars // 4
        metrics.conversation_token_estimate.record(estimated_tokens)

        # Record by role
        for role, count in role_counts.items():
            if count > 0:
                metrics.conversation_by_role.add(count, {"role": role})

    return langchain_messages


class ChatServiceImpl(ChatService):
    """
    Implementation of ChatService that integrates with MCP agent and LiteLLM.

    Provides:
    - Non-streaming chat completions via create_completion()
    - Streaming chat completions via create_stream()
    - Session history retrieval via get_history()

    Uses MCPBridge for full agent execution with MCP tools when available,
    falls back to LiteLLM for direct LLM calls when MCP is not configured.
    """

    def __init__(
        self,
        session_storage: Any | None = None,
        mcp_bridge: Any | None = None,
        langgraph_agent: Any | None = None,
        llm_factory: Any | None = None,
        router_agent: Any | None = None,
        capability_provider: Any | None = None,
        thinking_budget_manager: Any | None = None,
    ) -> None:
        """
        Initialize with optional dependencies.

        Args:
            session_storage: Optional storage backend for session history.
                             If None, history will return empty list.
            mcp_bridge: Optional MCPBridge instance for agent communication.
                        If None, uses LiteLLM as fallback.
            langgraph_agent: Optional compiled LangGraph agent for astream_events.
                             If provided, enables real-time node/edge streaming.
            llm_factory: Optional LLMFactory instance for streaming via astream().
                         If None, falls back to direct litellm.acompletion.
            router_agent: Optional RouterAgent for orchestration routing.
                         If provided, enables dynamic routing based on request classification.
            capability_provider: Optional CapabilityProvider for hierarchical tool/skill
                         resolution (ADR-0105 Phase 2). Used by swarm workers.
            thinking_budget_manager: Optional ThinkingBudgetManager for extended thinking
                         support (ADR-0105 Phase 2). Used by swarm workers.
        """
        self._session_storage = session_storage
        self._mcp_bridge = mcp_bridge
        self._langgraph_agent = langgraph_agent
        self._llm_factory = llm_factory
        self._router_agent = router_agent
        self._capability_provider = capability_provider
        self._thinking_budget_manager = thinking_budget_manager

    @property
    def mcp_bridge(self) -> Any | None:
        """Get the MCP bridge, lazily initializing from environment if available."""
        if self._mcp_bridge is None:
            from mcp_server_langgraph.api.v1.mcp_bridge import get_mcp_bridge

            self._mcp_bridge = get_mcp_bridge()
        return self._mcp_bridge

    @property
    def llm_factory(self) -> Any | None:
        """Get the LLM factory, lazily initializing if needed."""
        if self._llm_factory is None:
            from mcp_server_langgraph.llm.factory import create_llm_from_config

            self._llm_factory = create_llm_from_config(settings)
        return self._llm_factory

    @property
    def langgraph_agent(self) -> Any | None:
        """Get the LangGraph agent, lazily initializing if needed.

        This enables DynamicContextLoader integration with Connected Chat.
        The agent graph is built with settings from core.config which respects
        the enable_dynamic_context_loading feature flag.

        Returns:
            Compiled LangGraph agent with DynamicContextLoader if enabled,
            or None if initialization fails.
        """
        if self._langgraph_agent is None:
            try:
                from mcp_server_langgraph.observability.telemetry import logger

                self._langgraph_agent = create_agent_graph()
                logger.info("LangGraph agent lazily initialized for ChatServiceImpl")
            except Exception as e:
                from mcp_server_langgraph.observability.telemetry import logger

                logger.warning(f"Failed to initialize LangGraph agent: {e}")
                # Return None - caller should fallback to LLM factory
        return self._langgraph_agent

    @property
    def router_agent(self) -> Any | None:
        """Get the router agent, lazily initializing if needed."""
        if self._router_agent is None:
            # Only initialize if LLM factory is available
            if self.llm_factory is not None:
                from mcp_server_langgraph.agents.router_agent import RouterAgent

                self._router_agent = RouterAgent(llm_factory=self.llm_factory)
        return self._router_agent

    def validate_dynamic_context_config(self) -> DynamicContextConfigResult:
        """Validate configuration required for dynamic context loading.

        Performs preflight checks before attempting to initialize DynamicContextLoader.
        Checks Qdrant URL, embedding provider, and required credentials.

        Returns:
            DynamicContextConfigResult with validation status and guidance.
        """
        # If dynamic context loading is disabled, return valid (no validation needed)
        if not settings.enable_dynamic_context_loading:
            return DynamicContextConfigResult(is_valid=True)

        missing: list[str] = []
        guidance_parts: list[str] = []

        # Check Qdrant configuration
        if not settings.qdrant_url:
            missing.append("qdrant_url")
            guidance_parts.append(
                "Qdrant URL is required for dynamic context loading. "
                "Set QDRANT_URL environment variable or qdrant_url in settings."
            )

        # Check embedding provider is supported
        provider = settings.embedding_provider
        if provider not in SUPPORTED_EMBEDDING_PROVIDERS:
            missing.append("embedding_provider")
            supported_list = ", ".join(sorted(SUPPORTED_EMBEDDING_PROVIDERS))
            guidance_parts.append(
                f"Unsupported embedding provider '{provider}'. "
                f"Supported providers: {supported_list}. "
                "google_vertex (recommended for GCP) uses Workload Identity Federation."
            )

        # Check provider-specific credentials
        if provider == "google":
            # GoogleGenerativeAIEmbeddings requires API key
            if not getattr(settings, "google_api_key", None):
                missing.append("google_api_key")
                guidance_parts.append(
                    "Google embedding provider requires GOOGLE_API_KEY. "
                    "Set GOOGLE_API_KEY environment variable or use google_vertex "
                    "provider with GCP Workload Identity Federation (no API key needed)."
                )
        elif provider == "openai":
            # OpenAI embeddings require API key
            if not getattr(settings, "openai_api_key", None):
                missing.append("openai_api_key")
                guidance_parts.append(
                    "OpenAI embedding provider requires OPENAI_API_KEY. Set OPENAI_API_KEY environment variable."
                )

        # Build result
        if missing:
            return DynamicContextConfigResult(
                is_valid=False,
                missing_config=missing,
                guidance=" ".join(guidance_parts),
            )

        return DynamicContextConfigResult(is_valid=True, guidance="")

    def _get_current_trace_id(self) -> str | None:
        """Get the current OpenTelemetry trace ID for observability correlation.

        Returns:
            32-character hex string trace ID, or None if no active trace.
        """
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if not span_context.is_valid or not span_context.trace_id:
            return None
        # Format as 32-character hex string (padded with zeros)
        return format(span_context.trace_id, "032x")

    async def _create_completion_via_mcp(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create completion using MCP agent."""
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError

        bridge = self.mcp_bridge
        if not bridge or not bridge.is_configured:
            raise ChatError("MCP bridge not configured")

        # Extract the last user message
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        user_id = kwargs.get("user_id", "anonymous")

        response = await bridge.send_chat_message(
            session_id=session_id,
            message=last_user_message,
            user_id=user_id,
        )

        # Prefer trace_id from MCP response, fallback to current span
        trace_id = response.trace_id or self._get_current_trace_id()

        return {
            "id": f"chatcmpl-{uuid4().hex[:8]}",
            "message": {
                "role": "assistant",
                "content": response.content,
            },
            "usage": response.usage,
            "model": "mcp-agent",
            "trace_id": trace_id,
        }

    async def _read_resources_for_context(
        self,
        resource_uris: list[str],
    ) -> str:
        """
        Read resources and build context string for injection.

        Args:
            resource_uris: List of resource URIs to read

        Returns:
            Formatted context string with all resource contents
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import MCPResourceNotFoundError
        from mcp_server_langgraph.observability.telemetry import logger

        bridge = self.mcp_bridge
        if bridge is None:
            logger.warning("Cannot inject resources: MCP bridge not configured")
            return ""

        context_parts: list[str] = []

        for uri in resource_uris:
            try:
                contents = await bridge.read_resource(uri)
                for content in contents:
                    if content.text:
                        context_parts.append(f"[Resource: {uri}]\n{content.text}\n")
                    elif content.blob:
                        # For binary content, just note it's available
                        context_parts.append(f"[Resource: {uri}] (binary content, {len(content.blob)} bytes)\n")
            except MCPResourceNotFoundError as e:
                logger.warning(f"Resource not found, skipping: {e}")
            except Exception as e:
                logger.warning(f"Failed to read resource {uri}: {e}")

        return "\n".join(context_parts)

    async def _inject_resource_context(
        self,
        messages: list[dict[str, Any]],
        resource_uris: list[str] | None,
    ) -> list[dict[str, Any]]:
        """
        Inject resource context into messages.

        If resource_uris are provided, reads the resources and prepends
        a system message with their contents.

        Args:
            messages: Original message list
            resource_uris: Optional list of resource URIs to inject

        Returns:
            Message list with optional resource context prepended
        """
        if not resource_uris:
            return messages

        context = await self._read_resources_for_context(resource_uris)
        if not context:
            return messages

        # Create a system message with resource context
        context_message = {
            "role": "system",
            "content": f"The following resources are available as context:\n\n{context}",
        }

        # Prepend context to messages
        return [context_message] + list(messages)

    def _get_model_aware_history_limit(self) -> int:
        """
        Get model-aware token limit for conversation history loading.

        Uses the same model-aware approach as ContextManager when
        enable_model_aware_compaction is enabled. This ensures history
        loading respects the model's context window size.

        The limit is calculated as a percentage of the model's effective
        context limit, leaving headroom for system prompts, tools, and response.

        Returns:
            Token limit for history loading (default: 8000 if not model-aware)
        """
        from mcp_server_langgraph.core.feature_flags import feature_flags

        # Default limit when not model-aware
        DEFAULT_HISTORY_LIMIT = 8000

        if not feature_flags.enable_model_aware_compaction:
            return DEFAULT_HISTORY_LIMIT

        try:
            from mcp_server_langgraph.agents.model_registry import get_default_registry

            model_name = settings.model_name
            registry = get_default_registry()
            caps = registry.get(model_name)

            # Use effective limit (accounts for reserved tokens) or context limit
            effective_limit = caps.effective_limit if caps.effective_limit else caps.context_limit

            # Use same threshold percentage as ContextManager (default 0.5)
            # This leaves 50% for system prompts, dynamic context, tools, and response
            threshold_percentage = feature_flags.context_compaction_threshold_percentage
            history_limit = int(effective_limit * threshold_percentage)

            # Ensure we have a reasonable minimum
            return max(history_limit, 2000)

        except Exception:
            # Graceful fallback to default
            return DEFAULT_HISTORY_LIMIT

    async def _load_and_merge_history(
        self,
        session_id: str,
        new_messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Load session history from storage and merge with new messages.

        This ensures the LLM receives full conversation context, not just
        the current message. History is deduplicated and progressively loaded
        to fit within token limits (prioritizing recent messages).

        Args:
            session_id: Session ID to load history for
            new_messages: New message(s) from the current request

        Returns:
            Merged message list: history + new messages (token-aware, deduplicated)
        """
        from mcp_server_langgraph.context.conversation_loader import (
            ConversationMessage,
            ConversationProgressiveLoader,
        )
        from mcp_server_langgraph.observability.telemetry import logger

        # If no storage configured, just return new messages
        if self._session_storage is None:
            return new_messages

        try:
            # Load stored history
            stored_messages = await self._session_storage.get_messages(session_id)
            if not stored_messages:
                return new_messages

            # Convert to list if needed
            history = list(stored_messages)

            # Deduplicate: don't add new messages that already exist in history
            # Compare by role + content to identify duplicates
            history_set = {(msg.get("role"), msg.get("content")) for msg in history}

            unique_new = [msg for msg in new_messages if (msg.get("role"), msg.get("content")) not in history_set]

            # Merge: history first, then unique new messages
            merged = history + unique_new

            # Apply progressive loading to fit within token limits
            # This prioritizes recent messages and truncates oldest when over limit
            # Uses model-aware token limits when enable_model_aware_compaction is enabled
            max_tokens = self._get_model_aware_history_limit()
            loader = ConversationProgressiveLoader(max_tokens=max_tokens)

            # Convert to ConversationMessage format
            conversation_messages = [
                ConversationMessage(role=msg.get("role", "user"), content=msg.get("content", "")) for msg in merged
            ]

            loaded_context = await loader.load(conversation_messages)

            # Convert back to dict format
            result = [{"role": msg.role, "content": msg.content} for msg in loaded_context.messages]

            if loaded_context.was_truncated:
                logger.info(
                    f"Conversation history truncated for session {session_id}: "
                    f"{len(merged)} -> {len(result)} messages, {loaded_context.total_tokens} tokens"
                )
            else:
                logger.debug(
                    f"Loaded {len(history)} messages from history, "
                    f"adding {len(unique_new)} new messages for session {session_id}"
                )

            return result

        except Exception as e:
            # Graceful fallback: log and continue with just new messages
            logger.warning(f"Failed to load session history for {session_id}: {e}")
            return new_messages

    async def _create_completion_via_litellm(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create completion using LiteLLM directly."""
        model = kwargs.get("model") or settings.model_name
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens")
        reasoning_effort = kwargs.get("reasoning_effort")
        enable_thinking = kwargs.get("enable_thinking", True)

        # Inject resource context if provided
        resource_uris = kwargs.get("resource_uris")
        messages = await self._inject_resource_context(messages, resource_uris)

        # Build completion parameters
        completion_params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        # Add reasoning_effort for models that support extended thinking
        # Only add if thinking is enabled and the model supports it
        supports_thinking = model_supports_thinking(model)
        if supports_thinking and enable_thinking and reasoning_effort:
            completion_params["reasoning_effort"] = reasoning_effort

        # Add OTEL metadata for distributed tracing
        # LiteLLM propagates metadata.* attributes to OTEL spans
        from mcp_server_langgraph.llm.otel_integration import build_otel_metadata

        completion_params["metadata"] = build_otel_metadata(
            session_id=session_id,
            workflow_id=kwargs.get("workflow_id"),
            orchestrator_id=kwargs.get("orchestrator_id"),
            user_id=kwargs.get("user_id"),
            request_id=kwargs.get("request_id"),
            feature="chat",
            # Organizational hierarchy for cost attribution
            organization_id=kwargs.get("organization_id"),
            project_id=kwargs.get("project_id"),
            team_id=kwargs.get("team_id"),
        )

        response = await acompletion(**completion_params)

        choice = response.choices[0]
        message_data = {
            "role": choice.message.role,
            "content": choice.message.content,
        }

        usage_data = None
        if response.usage:
            usage_data = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": getattr(response.usage, "total_tokens", None),
            }

            # Cost tracking is now handled automatically by CostTrackingCallback
            # registered in llm/factory.py. The callback uses LiteLLM's response_cost
            # as the authoritative source and extracts organizational context from
            # completion_params["metadata"] (built by build_otel_metadata above).
            # Reference: Plan Phase 1 - LiteLLM Cost Integration via Custom Callback

        # Extract thinking content from response if available
        # LiteLLM returns thinking content in different ways:
        # 1. response.reasoning_content (unified field)
        # 2. response.thinking_blocks (Anthropic-specific)
        thinking_data = None
        reasoning_content = getattr(response, "reasoning_content", None)
        if reasoning_content:
            thinking_data = {
                "content": reasoning_content,
                "tokens": getattr(response.usage, "reasoning_tokens", None) if response.usage else None,
            }
        elif hasattr(choice.message, "thinking_blocks") and choice.message.thinking_blocks:
            # Anthropic-specific thinking blocks
            thinking_blocks = choice.message.thinking_blocks
            combined_thinking = "\n\n".join(block.get("text", "") for block in thinking_blocks if block.get("text"))
            if combined_thinking:
                thinking_data = {
                    "content": combined_thinking,
                    "tokens": None,  # Anthropic doesn't provide separate token count for thinking
                }

        # Get current trace_id for observability correlation
        trace_id = self._get_current_trace_id()

        return {
            "id": response.id or f"chatcmpl-{uuid4().hex[:8]}",
            "message": message_data,
            "usage": usage_data,
            "model": response.model or model,
            "trace_id": trace_id,
            "thinking": thinking_data,
        }

    async def create_completion(self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """
        Create a chat completion.

        Tries MCP agent first (for full tool support), falls back to LiteLLM.

        Args:
            session_id: Session ID for tracking
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (model, temperature, max_tokens, user_id)

        Returns:
            Dict matching ChatCompletionResponse format
        """
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError
        from mcp_server_langgraph.observability.telemetry import logger

        # Load session history from storage and merge with new messages
        # Ensures non-streaming calls receive full conversation context
        messages = await self._load_and_merge_history(session_id, messages)

        # Try MCP agent first if configured
        if self.mcp_bridge and self.mcp_bridge.is_configured:
            try:
                return await self._create_completion_via_mcp(session_id, messages, **kwargs)
            except ChatError as e:
                logger.warning(f"MCP agent failed, falling back to LiteLLM: {e}")

        # Fallback to LiteLLM
        return await self._create_completion_via_litellm(session_id, messages, **kwargs)

    async def _stream_via_mcp(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream completion using MCP agent."""
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError

        bridge = self.mcp_bridge
        if not bridge or not bridge.is_configured:
            raise ChatError("MCP bridge not configured")

        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break

        user_id = kwargs.get("user_id", "anonymous")

        async for chunk in bridge.stream_chat_message(
            session_id=session_id,
            message=last_user_message,
            user_id=user_id,
        ):
            if not chunk.is_final:
                yield {
                    "delta": {
                        "content": chunk.content,
                    },
                }

    async def _stream_via_llm_factory(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream completion using LLMFactory.astream().

        This uses the resilience-enhanced LLMFactory for streaming,
        providing bulkhead isolation and structured error handling.

        Args:
            session_id: Session identifier for tracing
            messages: List of chat messages
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Yields:
            dict: Delta content dictionaries with optional thinking
        """
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError

        # Convert dict messages to LangChain messages
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))

        factory = self.llm_factory
        if not factory:
            # LLMFactory is required for streaming - legacy litellm path removed
            raise ChatError("LLMFactory is required for streaming. Please configure LLM settings.")

        async for chunk in factory.astream(langchain_messages, **kwargs):
            # Only yield non-final chunks (final chunk typically has empty content)
            chunk_data: dict[str, Any] = {
                "delta": {
                    "content": chunk.content,
                },
            }

            # Include thinking content if present
            if chunk.thinking:
                chunk_data["delta"]["thinking"] = chunk.thinking

            yield chunk_data

    # NOTE: _stream_via_litellm has been removed.
    # All streaming now goes through LLMFactory.astream() which provides:
    # - Circuit breaker resilience
    # - Retry with backoff
    # - OTEL tracing integration
    # - Cost tracking via callbacks

    def _create_llm_worker(self, name: str, system_prompt: str) -> Callable[[str], str]:
        """Create a LangGraph-compatible worker that uses LLMFactory for LLM calls.

        Creates a sync function suitable for use with LangGraph patterns (Supervisor,
        Hierarchical). Uses async→sync bridging via asyncio for LLMFactory.ainvoke().

        Based on research:
        - RunnableLambda accepts sync functions and handles async internally
        - LiteLLMChatModel uses asyncio.get_event_loop().run_until_complete() pattern
        - Workers should have graceful error handling with fallback responses

        Args:
            name: Worker name for identification and logging
            system_prompt: System prompt defining the worker's role and capabilities

        Returns:
            Callable that takes task input (str) and returns LLM response (str)

        Example:
            worker = self._create_llm_worker("research", "You are a research analyst.")
            result = worker("Analyze market trends")  # Returns LLM response
        """
        import asyncio

        from langchain_core.messages import HumanMessage, SystemMessage

        from mcp_server_langgraph.observability.telemetry import logger

        llm_factory = self.llm_factory

        def worker(task_input: str) -> str:
            """Sync worker function for LangGraph compatibility."""
            if not llm_factory:
                logger.warning(f"[{name}] LLMFactory not available, using fallback")
                return f"[{name}] Unable to process: LLM not configured"

            # Build messages with system prompt and task
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task_input),
            ]

            async def _invoke_async() -> str:
                """Async wrapper for LLMFactory.ainvoke()."""
                try:
                    response = await llm_factory.ainvoke(messages)
                    return response.content if hasattr(response, "content") else str(response)
                except Exception as e:
                    logger.error(f"[{name}] LLM invocation failed: {e}")
                    return f"[{name}] Error processing request: {e!s}"

            # Async→sync bridging for LangGraph compatibility
            try:
                # Check if we're already in an async context
                try:
                    asyncio.get_running_loop()
                    # We're in async context - use run_coroutine_threadsafe or nest
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, _invoke_async())
                        return future.result(timeout=60.0)
                except RuntimeError:
                    # No running loop - safe to use asyncio.run()
                    return asyncio.run(_invoke_async())
            except Exception as e:
                logger.error(f"[{name}] Worker execution failed: {e}")
                return f"[{name}] Fallback response for: {task_input[:50]}..."

        return worker

    async def _stream_via_langgraph(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Stream completion using LangGraph agent with astream_events.

        Emits:
        - langgraph_node: Node execution updates (name, type, status)
        - langgraph_edge: Edge traversals (from, to, condition)
        - current_node: Currently executing node ID
        - delta.content: Streaming content from LLM
        """

        from mcp_server_langgraph.observability.telemetry import logger

        agent = self.langgraph_agent  # Uses lazy initialization property
        if not agent or not hasattr(agent, "astream_events"):
            raise ValueError("LangGraph agent not configured or doesn't support astream_events")

        otel_tracer = trace.get_tracer(__name__)
        broadcaster = None
        try:
            from mcp_server_langgraph.websocket.registry import get_devtools_broadcaster

            broadcaster = get_devtools_broadcaster()
            logger.debug(
                "DevTools broadcaster initialized for LangGraph trace streaming",
                extra={"session_id": session_id, "has_broadcaster": broadcaster is not None},
            )
        except Exception as e:
            # DevTools broadcaster is optional; continue without it if unavailable.
            logger.warning(
                "Failed to initialize DevTools broadcaster for trace streaming: %s",
                str(e),
                extra={"session_id": session_id, "error": str(e)},
            )
            broadcaster = None

        node_start_times: dict[str, int] = {}
        node_ids: dict[str, str] = {}

        def _schedule_trace_step(
            node_name: str,
            status: str,
            attributes: dict[str, Any] | None = None,
        ) -> None:
            if broadcaster is None:
                return

            start_time_ms = node_start_times.get(node_name, int(time.time() * 1000))
            if status == "running":
                node_start_times[node_name] = start_time_ms

            end_time_ms = int(time.time() * 1000)
            safe_attrs: dict[str, Any] | None = None
            if attributes:
                safe_attrs = {}
                for key, value in attributes.items():
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        safe_attrs[key] = value
                    else:
                        safe_attrs[key] = str(value)

            payload = {
                "id": node_ids.get(node_name) or f"{node_name}-{start_time_ms}",
                "session_id": session_id,
                "node_id": node_name,
                "name": node_name,
                "status": status,
                "start_time": start_time_ms,
            }

            if status != "running":
                payload["end_time"] = end_time_ms
                payload["duration_ms"] = max(end_time_ms - start_time_ms, 0)

            if safe_attrs:
                payload["attributes"] = safe_attrs

            if node_name not in node_ids:
                node_ids[node_name] = str(payload["id"])

            try:
                loop = asyncio.get_running_loop()
                _task = loop.create_task(
                    broadcaster.broadcast_trace_step(payload, context_entity_id=session_id),
                )
                del _task  # Fire-and-forget; suppress RUF006
                logger.debug(
                    "Scheduled trace step broadcast",
                    extra={
                        "session_id": session_id,
                        "node_name": node_name,
                        "status": status,
                    },
                )
            except RuntimeError:
                # No running loop; skip best-effort devtools broadcast
                logger.debug(
                    "No running loop for trace step broadcast",
                    extra={"session_id": session_id, "node_name": node_name},
                )
            except Exception as exc:  # pragma: no cover - defensive logging only
                logger.debug("Failed to broadcast trace step: %s", exc)

        # Build initial state from messages - use full conversation history
        # with proper role mapping (Phase 4.1 fix)
        langgraph_messages = _build_langgraph_messages(messages)

        # Extract kb_focus from kwargs (default: "all" per ADR-0094)
        kb_focus = kwargs.pop("kb_focus", "all")

        # v7: Extract tool parameters for native tools integration
        tool_preference = kwargs.pop("tool_preference", "auto")
        tool_selection_mode = kwargs.pop("tool_selection_mode", "auto")
        selected_tools = kwargs.pop("selected_tools", None)

        initial_state = {
            "messages": langgraph_messages,
            "next_action": "",
            "user_id": kwargs.get("user_id"),
            "request_id": session_id,
            "kb_focus": kb_focus,
            # v7: Tool controls for native tools integration
            "tool_preference": tool_preference,
            "tool_selection_mode": tool_selection_mode,
            "selected_tools": selected_tools,
        }

        config = {"configurable": {"thread_id": session_id}}
        node_statuses: dict[str, str] = {}  # Track node statuses
        last_node: str | None = None
        with otel_tracer.start_as_current_span("langgraph.execution") as exec_span:
            exec_span.set_attribute("session.id", session_id)
            exec_span.set_attribute("session_id", session_id)
            exec_span.set_attribute("sessionId", session_id)

            try:
                async for event in agent.astream_events(initial_state, config=config, version="v2"):
                    event_type = event.get("event", "")
                    metadata = event.get("metadata", {})
                    langgraph_node = metadata.get("langgraph_node")

                    # Handle node start events
                    if event_type == "on_chain_start" and langgraph_node:
                        node_name = langgraph_node
                        node_statuses[node_name] = "running"
                        _schedule_trace_step(node_name, "running", metadata)

                        # Emit current_node update
                        yield {"current_node": node_name}

                        # Emit langgraph_node event
                        yield {
                            "langgraph_node": {
                                "id": node_name,
                                "name": node_name,
                                "type": self._infer_node_type(node_name),
                                "status": "running",
                            }
                        }

                        # Emit edge from previous node if exists
                        if last_node and last_node != node_name:
                            yield {
                                "langgraph_edge": {
                                    "from": last_node,
                                    "to": node_name,
                                }
                            }

                        last_node = node_name

                    # Handle node end events
                    elif event_type == "on_chain_end" and langgraph_node:
                        node_name = langgraph_node
                        node_statuses[node_name] = "completed"
                        _schedule_trace_step(node_name, "completed", metadata)

                        # Emit langgraph_node event with completed status
                        yield {
                            "langgraph_node": {
                                "id": node_name,
                                "name": node_name,
                                "type": self._infer_node_type(node_name),
                                "status": "completed",
                            }
                        }

                        # Check for triggered edges in metadata
                        triggers = metadata.get("langgraph_triggers", [])
                        for trigger in triggers:
                            yield {
                                "langgraph_edge": {
                                    "from": node_name,
                                    "to": trigger,
                                }
                            }

                    # Handle custom events (e.g., dynamic context loaded, selected tools)
                    elif event_type == "on_custom":
                        event_name = event.get("name", "")
                        if event_name == "dynamic_context_loaded":
                            data = event.get("data", {})
                            yield {
                                "context_loaded": {
                                    "refs_count": data.get("refs_count", 0),
                                    "tokens_loaded": data.get("tokens_loaded", 0),
                                }
                            }
                        elif event_name == "selected_tools":
                            # Phase 5: Emit selected_tools SSE event for frontend visibility
                            # Shows which tools were semantically selected for this request
                            data = event.get("data", {})
                            selected_tools_event: dict[str, Any] = {
                                "selected_tools": data.get("selected_tools", []),
                            }
                            # Include optional selection scores if available
                            if "selection_scores" in data:
                                selected_tools_event["selection_scores"] = data["selection_scores"]
                            # Include total available tools count if provided
                            if "total_available" in data:
                                selected_tools_event["total_available"] = data["total_available"]
                            yield selected_tools_event
                        elif event_name == "auth_required":
                            # Emit auth_required event when tool call fails due to auth
                            # This allows frontend to prompt user for connection setup
                            data = event.get("data", {})
                            yield {
                                "type": "auth_required",
                                "connection_id": data.get("connection_id"),
                                "template_id": data.get("template_id"),
                                "tool_name": data.get("tool_name", ""),
                                "message": data.get("message", "Authentication required"),
                                "retry_message_id": data.get("retry_message_id"),
                            }
                        elif event_name == "sources_collected":
                            # Emit sources SSE event for web search citations
                            # Frontend displays these as source links in the chat message
                            data = event.get("data", {})
                            sources = data.get("sources", [])
                            if sources:
                                yield {"sources": sources}

                    # Handle streaming content from chat model
                    elif event_type == "on_chat_model_stream":
                        data = event.get("data", {})
                        chunk = data.get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            yield {
                                "delta": {
                                    "content": chunk.content,
                                }
                            }

            except Exception as e:
                exec_span.record_exception(e)
                logger.error(f"LangGraph streaming error: {e}", exc_info=True)
                raise

    def _infer_node_type(self, node_name: str) -> str:
        """Infer node type from name for visualization."""
        name_lower = node_name.lower()
        if name_lower in ("__start__", "start"):
            return "start"
        elif name_lower in ("__end__", "end"):
            return "end"
        elif "tool" in name_lower:
            return "tool"
        elif "router" in name_lower or "route" in name_lower:
            return "conditional"
        elif "agent" in name_lower:
            return "agent"
        return "default"

    async def _stream_via_swarm(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        selection: Any,  # OrchestratorSelection
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute via SwarmOrchestrator and stream results.

        Implements ADR-0105: AsyncIO swarm orchestration for parallel multi-agent
        execution. Bypasses plan/critique loop for speed.

        Args:
            session_id: Session identifier for tracing
            messages: List of chat messages
            selection: OrchestratorSelection with swarm config
            max_tokens: Optional max tokens limit
            temperature: Optional temperature for sampling
            **kwargs: Additional parameters

        Yields:
            dict: swarm_result metadata and delta content for SSE persistence
        """
        from mcp_server_langgraph.agents.base_agent import AgentRequest
        from mcp_server_langgraph.agents.swarm_orchestrator import (
            SwarmConfig,
            SwarmOrchestrator,
            SwarmStrategy,
        )
        from mcp_server_langgraph.agents.worker_agent import WorkerAgent
        from mcp_server_langgraph.observability.telemetry import logger

        # Build WorkerAgents with correct constructor signature
        # Phase 2: Support optional CapabilityProvider and ThinkingBudgetManager
        workers = [
            WorkerAgent(
                llm_factory=self.llm_factory,
                model_id=selection.worker_model,
                thinking_budget_manager=self._thinking_budget_manager,
                capability_provider=self._capability_provider,
            )
            for _ in range(selection.worker_count)
        ]

        # Map strategy string to enum
        strategy_map = {
            "race": SwarmStrategy.RACE,
            "cascade": SwarmStrategy.CASCADE,
            "consensus": SwarmStrategy.CONSENSUS,
        }
        strategy = strategy_map.get(selection.swarm_strategy or "race", SwarmStrategy.RACE)

        # Create swarm config
        config = SwarmConfig(
            strategy=strategy,
            max_agents=selection.worker_count,
            timeout_seconds=60.0,
        )

        # Create orchestrator
        swarm = SwarmOrchestrator(agents=workers, config=config)

        # Phase 2: Build task based on context_strategy
        context_strategy = getattr(selection, "context_strategy", "scoped")

        if context_strategy == "summarized" and len(messages) > 1:
            # Summarize conversation history for consensus-style agreement
            conversation_summary = await _summarize_conversation(messages[:-1])
            last_message = messages[-1].get("content", "") if messages else ""
            task = f"<conversation_summary>\n{conversation_summary}\n</conversation_summary>\n\n<current_request>\n{last_message}\n</current_request>"
        elif context_strategy == "full":
            # Include full conversation history
            full_context = "\n".join(f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in messages)
            task = full_context
        else:
            # "scoped" - default: just last message for speed
            task = messages[-1].get("content", "") if messages else ""

        # Phase 2: Inject resource content if provided
        resource_content = kwargs.get("resource_content")
        if resource_content:
            # Prepend resource content as context for the task
            task = f"<context>\n{resource_content}\n</context>\n\n{task}"

        # Build AgentRequest with essential params
        request = AgentRequest(
            message=task,
            session_id=session_id,
            max_tokens=max_tokens,
        )

        logger.info(
            "Swarm orchestration started",
            extra={
                "session_id": session_id,
                "strategy": selection.swarm_strategy,
                "worker_count": selection.worker_count,
            },
        )

        # Run swarm - returns AgentResult
        result = await swarm.run(request=request)

        # Emit swarm metadata as SSE event
        yield {
            "swarm_result": {
                "strategy": selection.swarm_strategy,
                "worker_count": len(workers),
                "success": result.success,
                "model_used": result.model_used,
                "error": result.error,
            }
        }

        # Emit content as delta for SSE persistence
        if result.success and result.content:
            yield {"delta": {"content": result.content}}
        elif result.error:
            yield {"delta": {"content": f"Swarm execution failed: {result.error}"}}

        logger.info(
            "Swarm orchestration completed",
            extra={
                "session_id": session_id,
                "success": result.success,
            },
        )

    async def _stream_via_task_orchestrator(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        selection: Any,  # OrchestratorSelection
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute via task decomposition Orchestrator and stream results.

        Implements ADR-0105: AsyncIO task orchestration with subtask decomposition.
        Feature-gated via enable_multi_agent_orchestration.

        Args:
            session_id: Session identifier for tracing
            messages: List of chat messages
            selection: OrchestratorSelection with task config
            max_tokens: Optional max tokens limit
            **kwargs: Additional parameters

        Yields:
            dict: task_decomposition, subtask_completed, and delta content
        """
        from mcp_server_langgraph.agents.orchestrator import Orchestrator
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.observability.telemetry import logger

        # Extract last user message as task
        task = messages[-1].get("content", "") if messages else ""

        # Create orchestrator for task decomposition
        orchestrator = Orchestrator(session_id=session_id)

        try:
            # Step 1: Decompose task into subtasks (feature-gated)
            num_subtasks = orchestrator.scale_effort(task)
            decomposition = orchestrator.decompose_task(task, num_subtasks=num_subtasks)

            logger.info(
                "Task decomposition completed",
                extra={
                    "session_id": session_id,
                    "subtask_count": len(decomposition.subtasks),
                },
            )

            # Emit decomposition event
            yield {
                "task_decomposition": {
                    "original_task": decomposition.original_task,
                    "subtask_count": len(decomposition.subtasks),
                    "subtasks": [{"id": s.task_id, "title": s.title} for s in decomposition.subtasks],
                }
            }

            # Step 2: Execute via Orchestrator.execute() (feature-gated, async)
            subagent_results = await orchestrator.execute(decomposition)

            # Emit progress for each completed subtask
            for result in subagent_results:
                yield {
                    "subtask_completed": {
                        "task_id": result.task_id,
                        "success": result.success,
                        "confidence": result.confidence,
                    }
                }

            # Step 3: Synthesize results
            successful_results = [r for r in subagent_results if r.success and r.output]
            if successful_results:
                synthesized = "\n\n".join(str(r.output) for r in successful_results)
                yield {"delta": {"content": synthesized}}
            else:
                yield {"delta": {"content": "Task orchestration failed: all subtasks failed"}}

            # Emit completion metadata
            yield {
                "task_orchestrator_result": {
                    "success": len(successful_results) > 0,
                    "subtasks_completed": len(successful_results),
                    "subtasks_total": len(decomposition.subtasks),
                }
            }

            logger.info(
                "Task orchestration completed",
                extra={
                    "session_id": session_id,
                    "success": len(successful_results) > 0,
                    "subtasks_completed": len(successful_results),
                },
            )

        except FeatureDisabledError as e:
            # Feature gate not enabled
            logger.warning(f"Task orchestration disabled: {e}")
            yield {"delta": {"content": f"Task orchestration disabled: {e}"}}
            yield {
                "task_orchestrator_result": {
                    "success": False,
                    "error": "enable_multi_agent_orchestration feature flag is disabled",
                }
            }

    async def _stream_via_langgraph_hierarchical(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        selection: Any,  # OrchestratorSelection
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute via LangGraph Hierarchical pattern with astream_events streaming.

        Phase 3: Direct LangGraph pattern integration without LangGraph Server.
        Uses astream_events() for real-time event streaming.

        The hierarchical pattern organizes agents in a tree structure:
        CEO → Managers → Workers

        Args:
            session_id: Session ID for tracking
            messages: Conversation messages
            selection: OrchestratorSelection with langgraph_pattern="hierarchical"
            max_tokens: Optional max tokens limit

        Yields:
            SSE events:
            - langgraph_node: Node execution events (ceo, manager_*, worker_*, consolidate)
            - delta: Content chunks for SSE persistence
            - langgraph_hierarchical_result: Execution metadata
        """
        from mcp_server_langgraph.observability.telemetry import logger
        from mcp_server_langgraph.patterns.hierarchical import HierarchicalCoordinator

        logger.info(
            "Starting LangGraph Hierarchical streaming",
            extra={
                "session_id": session_id,
                "pattern": selection.langgraph_pattern,
                "worker_count": getattr(selection, "worker_count", 3),
            },
        )

        # Extract task from last user message
        task = messages[-1].get("content", "") if messages else ""

        # Create hierarchical agent structure using LLMFactory-powered workers
        # CEO → Managers → Workers pattern with specialized prompts
        worker_count = getattr(selection, "worker_count", 3)

        # Role definitions with specialized prompts for each level
        ceo_prompt = (
            "You are the CEO overseeing a complex project. Make strategic decisions, "
            "delegate to department managers, and ensure alignment with project goals. "
            "Provide clear direction and synthesize team outputs into coherent plans."
        )

        manager_prompts = {
            "research_manager": (
                "You are the Research Manager. Coordinate research activities, "
                "assign tasks to researchers, and synthesize their findings into actionable insights."
            ),
            "dev_manager": (
                "You are the Development Manager. Coordinate development tasks, "
                "assign work to developers, and ensure quality and timely delivery."
            ),
        }

        worker_prompts = {
            "Researcher": (
                "You are a research analyst. Investigate topics thoroughly, "
                "find relevant information, and provide well-sourced findings."
            ),
            "Developer": ("You are a software developer. Implement solutions, write clean code, and follow best practices."),
        }

        # Build hierarchical structure with LLMFactory-powered agents
        ceo_agent = self._create_llm_worker("CEO", ceo_prompt)
        managers = {name: self._create_llm_worker(name, prompt) for name, prompt in manager_prompts.items()}
        workers = {
            "research_manager": [
                self._create_llm_worker(f"Researcher_{i}", worker_prompts["Researcher"])
                for i in range(1, worker_count // 2 + 2)
            ],
            "dev_manager": [
                self._create_llm_worker(f"Developer_{i}", worker_prompts["Developer"]) for i in range(1, worker_count // 2 + 2)
            ],
        }

        # Create and compile hierarchical coordinator
        coordinator = HierarchicalCoordinator(
            ceo_agent=ceo_agent,
            managers=managers,
            workers=workers,
            delegation_strategy="balanced",
        )
        compiled_graph = coordinator.compile()

        # Use astream_events for real-time streaming
        config = {"configurable": {"thread_id": session_id}}

        try:
            async for event in compiled_graph.astream_events(
                {"project": task},
                config=config,
                version="v2",
            ):
                event_type = event.get("event", "")
                metadata = event.get("metadata", {})
                langgraph_node = metadata.get("langgraph_node")
                data = event.get("data", {})

                # Emit node start/end events
                if event_type == "on_chain_start" and langgraph_node:
                    yield {
                        "langgraph_node": {
                            "name": langgraph_node,
                            "type": "chain_start",
                            "status": "started",
                        }
                    }

                elif event_type == "on_chain_end" and langgraph_node:
                    output = data.get("output", {})
                    yield {
                        "langgraph_node": {
                            "name": langgraph_node,
                            "type": "chain_end",
                            "status": "completed",
                            "has_result": bool(output),
                        }
                    }

                    # If this is the consolidate node, extract final report
                    if langgraph_node == "consolidate" and isinstance(output, dict):
                        final_report = output.get("final_report", "")
                        if final_report:
                            yield {"delta": {"content": final_report}}

                # Handle streaming content from LLM
                elif event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {"delta": {"content": chunk.content}}

            # Emit completion metadata
            yield {
                "langgraph_hierarchical_result": {
                    "success": True,
                    "pattern": "hierarchical",
                    "worker_count": worker_count,
                }
            }

            logger.info(
                "LangGraph Hierarchical streaming completed",
                extra={"session_id": session_id, "success": True},
            )

        except Exception as e:
            logger.exception(f"LangGraph Hierarchical error: {e}")
            yield {"delta": {"content": f"LangGraph Hierarchical error: {e}"}}
            yield {
                "langgraph_hierarchical_result": {
                    "success": False,
                    "error": str(e),
                }
            }

    async def _stream_via_langgraph_supervisor(
        self,
        session_id: str,
        messages: list[dict[str, Any]],
        selection: Any,  # OrchestratorSelection
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute via LangGraph Supervisor pattern with astream_events streaming.

        Phase 3: Direct LangGraph pattern integration without LangGraph Server.
        Uses astream_events() for real-time event streaming.

        Args:
            session_id: Session ID for tracking
            messages: Conversation messages
            selection: OrchestratorSelection with langgraph_pattern="supervisor"
            max_tokens: Optional max tokens limit

        Yields:
            SSE events:
            - langgraph_node: Node execution events (supervisor, worker, aggregate)
            - delta: Content chunks for SSE persistence
            - langgraph_supervisor_result: Execution metadata
        """
        from mcp_server_langgraph.observability.telemetry import logger
        from mcp_server_langgraph.patterns.supervisor import Supervisor

        logger.info(
            "Starting LangGraph Supervisor streaming",
            extra={
                "session_id": session_id,
                "pattern": selection.langgraph_pattern,
                "worker_count": selection.worker_count,
            },
        )

        # Extract task from last user message
        task = messages[-1].get("content", "") if messages else ""

        # Create worker agents for the supervisor pattern using LLMFactory
        # Each worker has a specialized system prompt for its role
        worker_count = getattr(selection, "worker_count", 3)

        # Worker role definitions with specialized prompts
        worker_roles = {
            "research": "You are a research analyst. Analyze information, find key insights, and provide well-sourced findings.",
            "writer": "You are a technical writer. Create clear, concise content based on the research and requirements provided.",
            "reviewer": "You are a quality reviewer. Check for accuracy, completeness, and clarity. Provide constructive feedback.",
        }

        # Build agent dictionary for supervisor using LLMFactory-powered workers
        agents = {}
        worker_names = list(worker_roles.keys())[:worker_count]
        for name in worker_names:
            agents[name] = self._create_llm_worker(name, worker_roles[name])

        # Create and compile supervisor
        supervisor = Supervisor(
            agents=agents,
            routing_strategy="conditional",
        )
        compiled_graph = supervisor.compile()

        # Use astream_events for real-time streaming (no LangGraph Server needed)
        config = {"configurable": {"thread_id": session_id}}

        try:
            async for event in compiled_graph.astream_events(
                {"task": task},
                config=config,
                version="v2",
            ):
                event_type = event.get("event", "")
                metadata = event.get("metadata", {})
                langgraph_node = metadata.get("langgraph_node")
                data = event.get("data", {})

                # Emit node start/end events
                if event_type == "on_chain_start" and langgraph_node:
                    yield {
                        "langgraph_node": {
                            "name": langgraph_node,
                            "type": "chain_start",
                            "status": "started",
                        }
                    }

                elif event_type == "on_chain_end" and langgraph_node:
                    output = data.get("output", {})
                    yield {
                        "langgraph_node": {
                            "name": langgraph_node,
                            "type": "chain_end",
                            "status": "completed",
                            "has_result": bool(output),
                        }
                    }

                    # If this is the aggregate node, extract final result
                    if langgraph_node == "aggregate" and isinstance(output, dict):
                        final_result = output.get("final_result", "")
                        if final_result:
                            yield {"delta": {"content": final_result}}

                # Handle streaming content from LLM
                elif event_type == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {"delta": {"content": chunk.content}}

            # Emit completion metadata
            yield {
                "langgraph_supervisor_result": {
                    "success": True,
                    "pattern": "supervisor",
                    "worker_count": worker_count,
                }
            }

            logger.info(
                "LangGraph Supervisor streaming completed",
                extra={"session_id": session_id, "success": True},
            )

        except Exception as e:
            logger.exception(f"LangGraph Supervisor error: {e}")
            yield {"delta": {"content": f"LangGraph Supervisor error: {e}"}}
            yield {
                "langgraph_supervisor_result": {
                    "success": False,
                    "error": str(e),
                }
            }

    async def create_stream(
        self, session_id: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Create a streaming chat completion.

        When routing is enabled, classifies the request first and emits a routing_decision event.
        Then selects streaming strategy based on routing (LangGraph, MCP, or LLMFactory).

        Args:
            session_id: Session ID for tracking
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters:
                - enable_routing: Enable router agent classification (default: False)
                - use_langgraph: Force LangGraph agent (overridden by routing)
                - model, temperature, max_tokens, user_id: Standard LLM parameters

        Yields:
            Streaming chunks with:
            - routing_decision: First event when routing enabled (classification result)
            - delta: Content chunks with text/thinking
            - langgraph_node/langgraph_edge: Graph execution events (if using LangGraph)
        """
        from mcp_server_langgraph.agents.router_agent import DEFAULT_ROUTER_OUTPUT, RouterOutput
        from mcp_server_langgraph.api.v1.mcp_bridge import ChatError
        from mcp_server_langgraph.observability.telemetry import logger

        # Load session history from storage and merge with new messages
        # This ensures the LLM has full conversation context
        messages = await self._load_and_merge_history(session_id, messages)

        # Check enable_routing: explicit param > feature flag > default False
        enable_routing = kwargs.pop("enable_routing", None)
        if enable_routing is None:
            # Fall back to feature flag if not explicitly set
            enable_routing = getattr(settings, "enable_chat_routing", False)
        use_langgraph = kwargs.pop("use_langgraph", False)

        # Inject resource context if provided
        resource_uris = kwargs.pop("resource_uris", None)
        messages = await self._inject_resource_context(messages, resource_uris)

        # Extract last user message for classification/plan generation
        last_user_message = next(
            (msg.get("content", "") for msg in reversed(messages) if msg.get("role") == "user"),
            "",
        )

        # Get execution mode from kwargs (defaults to "default")
        execution_mode = kwargs.get("execution_mode", "default")

        # Router agent classification when enabled
        routing_decision: RouterOutput | None = None

        # =======================================================================
        # ROUTER CLASSIFICATION (Independent of Plan Mode)
        # =======================================================================
        # The router agent classifies the task to determine:
        # - execution_mode: How to execute (pure_llm, tool_calling, react, etc.)
        # - complexity: Model tier selection (simple, complicated, complex)
        # - risk: Risk assessment (low, medium, high)
        # - critique_rounds: Refinement passes needed
        # - thinking_budget: Extended reasoning level
        #
        # Plan mode is a WORKFLOW overlay that adds approval requirements.
        # It does NOT override the router's intelligent classification.
        # =======================================================================

        if enable_routing and self.router_agent is not None:
            try:
                routing_decision = await self.router_agent.route(message=last_user_message)
                logger.info(
                    f"Router decision: orchestrator={routing_decision.suggested_orchestrator}, "
                    f"complexity={routing_decision.complexity}, confidence={routing_decision.confidence}"
                )

                # Emit routing decision as first SSE event
                yield {
                    "routing_decision": {
                        "complexity": routing_decision.complexity,
                        "risk": routing_decision.risk,
                        "task_type": routing_decision.task_type,
                        "tools_needed": routing_decision.tools_needed,
                        "suggested_orchestrator": routing_decision.suggested_orchestrator,
                        "critique_rounds": routing_decision.critique_rounds,
                        "thinking_budget": routing_decision.thinking_budget,
                        "confidence": routing_decision.confidence,
                        "skills_needed": routing_decision.skills_needed,
                        "execution_mode": routing_decision.execution_mode,
                        "routing_rationale": routing_decision.routing_rationale,
                    }
                }

                # ADR-0105: Select orchestrator implementation based on routing decision
                from mcp_server_langgraph.core.feature_flags import feature_flags as ff

                orchestrator_selection = await self.router_agent.select_orchestrator(
                    routing_decision=routing_decision,
                    feature_flags=ff,
                )

                # CRITICAL: Dispatch AsyncIO orchestrators BEFORE plan/critique (bypass behavior)
                if orchestrator_selection.orchestrator_type == "asyncio_swarm":
                    async for chunk in self._stream_via_swarm(
                        session_id=session_id,
                        messages=messages,
                        selection=orchestrator_selection,
                        max_tokens=kwargs.get("max_tokens"),
                        temperature=kwargs.get("temperature"),
                    ):
                        yield chunk
                    return  # Exit - swarm bypasses plan/critique

                elif orchestrator_selection.orchestrator_type == "asyncio_task":
                    async for chunk in self._stream_via_task_orchestrator(
                        session_id=session_id,
                        messages=messages,
                        selection=orchestrator_selection,
                        max_tokens=kwargs.get("max_tokens"),
                    ):
                        yield chunk
                    return  # Exit - task orchestrator bypasses plan/critique

                # ADR-0105 Phase 3: LangGraph pattern dispatching
                elif orchestrator_selection.orchestrator_type == "langgraph_supervisor":
                    async for chunk in self._stream_via_langgraph_supervisor(
                        session_id=session_id,
                        messages=messages,
                        selection=orchestrator_selection,
                        max_tokens=kwargs.get("max_tokens"),
                    ):
                        yield chunk
                    return  # Exit - LangGraph supervisor bypasses plan/critique

                elif orchestrator_selection.orchestrator_type == "langgraph_hierarchical":
                    async for chunk in self._stream_via_langgraph_hierarchical(
                        session_id=session_id,
                        messages=messages,
                        selection=orchestrator_selection,
                        max_tokens=kwargs.get("max_tokens"),
                    ):
                        yield chunk
                    return  # Exit - LangGraph hierarchical bypasses plan/critique

                # For "standard" type: Continue to plan/critique and standard LangGraph/LiteLLM path

            except Exception as e:
                logger.warning(f"Router classification failed, using defaults: {e}")
                routing_decision = DEFAULT_ROUTER_OUTPUT

                # Emit default routing decision
                yield {
                    "routing_decision": {
                        "complexity": routing_decision.complexity,
                        "risk": routing_decision.risk,
                        "task_type": routing_decision.task_type,
                        "tools_needed": routing_decision.tools_needed,
                        "suggested_orchestrator": routing_decision.suggested_orchestrator,
                        "critique_rounds": routing_decision.critique_rounds,
                        "thinking_budget": routing_decision.thinking_budget,
                        "confidence": routing_decision.confidence,
                        "skills_needed": routing_decision.skills_needed,
                        "execution_mode": routing_decision.execution_mode,
                        "routing_rationale": routing_decision.routing_rationale,
                    }
                }

        # ====================================================================
        # Plan Generation and Bypass Mode Integration
        # ====================================================================
        # When plan generation is enabled, create ExecutionPlan from routing decision
        # and emit plan_generated SSE. If bypass mode, evaluate with BypassManager.
        from mcp_server_langgraph.core.feature_flags import feature_flags

        if feature_flags.enable_plan_generation and routing_decision is not None:
            from mcp_server_langgraph.core.models.execution_plan import ExecutionPlan
            from mcp_server_langgraph.execution.cost_estimator import estimate_execution_cost

            # Calculate estimated cost based on model and task characteristics
            executor_model = kwargs.get("model") or settings.model_name
            estimated_cost = estimate_execution_cost(
                model=executor_model,
                task_type=routing_decision.task_type,
                complexity=routing_decision.complexity,
                thinking_budget=routing_decision.thinking_budget,
            )

            # Create ExecutionPlan from RouterOutput
            # Plan mode forces approval regardless of risk level
            execution_plan = ExecutionPlan.from_router_output(
                router_output=routing_decision,
                session_id=session_id,
                message=last_user_message,
                executor_model=executor_model,
                estimated_cost=estimated_cost,
                force_approval=(execution_mode == "plan"),
            )

            # Emit plan_generated SSE with full 27-field payload
            # Uses plan_to_dict from serializers.py for consistency with REST API
            yield {"plan_generated": plan_to_dict(execution_plan)}

            # Bypass mode: evaluate risk and potentially auto-approve
            execution_mode = kwargs.get("execution_mode", "default")
            if execution_mode == "bypass":
                from mcp_server_langgraph.execution.bypass_manager import BypassManager

                bypass_manager = BypassManager()
                bypass_decision = bypass_manager.evaluate_plan(execution_plan)

                if bypass_decision.auto_approved:
                    # Auto-approve low-risk plan
                    approved_plan = execution_plan.approve(approved_by="system:bypass_auto")

                    # Audit logging: BYPASS_AUTO_APPROVED event (FedRAMP/SOC2 compliance)
                    from mcp_server_langgraph.audit.models import AuditEventType
                    from mcp_server_langgraph.execution.bypass_audit import log_bypass_audit_event

                    audit_service = kwargs.get("audit_service")
                    current_user = kwargs.get("current_user", {})

                    await log_bypass_audit_event(
                        audit_service=audit_service,
                        event_type=AuditEventType.BYPASS_AUTO_APPROVED,
                        current_user=current_user,
                        resource_type="execution_plan",
                        resource_id=approved_plan.plan_id,
                        action="Auto-approved low-risk plan in bypass mode",
                        details={
                            "risk_level": bypass_decision.risk_level,
                            "original_risk_level": bypass_decision.original_risk_level,
                            "complexity": bypass_decision.complexity,
                            "risk_factors": bypass_decision.risk_factors,
                            "tools_needed": execution_plan.tools_needed,
                        },
                    )

                    # Emit auto-approval event
                    yield {
                        "plan_auto_approved": {
                            "plan_id": approved_plan.plan_id,
                            "status": approved_plan.status,
                            "approved_by": approved_plan.approved_by,
                            "risk_level": bypass_decision.risk_level,
                            "original_risk_level": bypass_decision.original_risk_level,
                            "complexity": bypass_decision.complexity,
                            "risk_factors": bypass_decision.risk_factors,
                        }
                    }

                    logger.info(
                        f"Bypass mode auto-approved plan {approved_plan.plan_id}: "
                        f"risk={bypass_decision.risk_level}, complexity={bypass_decision.complexity}"
                    )
                else:
                    # Requires user approval even in bypass mode
                    yield {
                        "plan_requires_approval": {
                            "plan_id": execution_plan.plan_id,
                            "risk_level": bypass_decision.risk_level,
                            "original_risk_level": bypass_decision.original_risk_level,
                            "complexity": bypass_decision.complexity,
                            "risk_factors": bypass_decision.risk_factors,
                            "reason": "Risk level too high for auto-approval",
                        }
                    }

                    logger.info(
                        f"Bypass mode requires approval for plan {execution_plan.plan_id}: "
                        f"risk={bypass_decision.risk_level}, complexity={bypass_decision.complexity}"
                    )

        # ====================================================================
        # Critique Loop Integration (Executor+Critic Pattern)
        # ====================================================================
        # When routing indicates critique_rounds > 0 and critique loop is enabled,
        # use the CritiqueExecutor for multi-pass refinement.
        from mcp_server_langgraph.core.feature_flags import feature_flags

        use_critique_loop = (
            feature_flags.enable_critique_loop
            and routing_decision is not None
            and routing_decision.critique_rounds > 0
            and routing_decision.risk != "low"  # Skip critique for low-risk
        )

        if use_critique_loop:
            from mcp_server_langgraph.agents.critique_executor import CritiqueExecutor
            from mcp_server_langgraph.agents.router_agent import select_executor_critic

            try:
                # Select executor and critic models based on complexity/risk
                executor_model, critic_model = select_executor_critic(
                    complexity=routing_decision.complexity,
                    risk=routing_decision.risk,
                    prefer_same_vendor=not feature_flags.critique_cross_vendor,
                )

                logger.info(
                    f"Using critique loop: executor={executor_model}, "
                    f"critic={critic_model}, rounds={routing_decision.critique_rounds}"
                )

                # Create CritiqueExecutor with feature flag limits
                critique_executor = CritiqueExecutor(
                    executor_model=executor_model,
                    critic_model=critic_model,
                    max_rounds=min(
                        routing_decision.critique_rounds,
                        feature_flags.max_critique_rounds,
                    ),
                )

                # Execute with critique and stream results
                async for event in critique_executor.execute_with_critique(
                    messages=messages,
                    critique_rounds=routing_decision.critique_rounds,
                ):
                    # Map critique events to SSE format
                    if event["type"] == "executor_response":
                        # Stream initial/refined response as delta events
                        yield {"delta": {"content": event["content"]}}
                        if feature_flags.critique_streaming:
                            yield {
                                "critique_status": {
                                    "phase": "executed",
                                    "round": event["round"],
                                    "model": event.get("model"),
                                }
                            }
                    elif event["type"] == "critique":
                        # Emit critique result for frontend visibility
                        if feature_flags.critique_streaming:
                            yield {
                                "critique_status": {
                                    "phase": "critiqued",
                                    "round": event["round"],
                                    "approved": event["result"].approved,
                                    "feedback": event["result"].feedback,
                                    "confidence": event["result"].confidence,
                                    "model": event.get("model"),
                                }
                            }
                    elif event["type"] == "refined_response":
                        # Stream refined response
                        yield {"delta": {"content": event["content"]}}
                        if feature_flags.critique_streaming:
                            yield {
                                "critique_status": {
                                    "phase": "refined",
                                    "round": event["round"],
                                    "model": event.get("model"),
                                }
                            }

                # Critique loop completed successfully
                return

            except Exception as e:
                logger.warning(f"Critique loop failed, falling back to standard: {e}")
                # Emit fallback notice
                yield {
                    "context_unavailable": {
                        "reason": f"Critique loop error: {e}",
                        "fallback": "standard_streaming",
                    }
                }
                # Fall through to standard streaming

        # Try LangGraph agent if requested (via routing or explicit flag) and configured
        # Uses langgraph_agent property which lazily initializes if needed
        if use_langgraph and self.langgraph_agent is not None:
            try:
                async for chunk in self._stream_via_langgraph(session_id, messages, **kwargs):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"LangGraph streaming failed, falling back: {e}")
                # Emit context_unavailable notice for fail-soft visibility
                yield {
                    "context_unavailable": {
                        "reason": str(e),
                        "fallback": "llm_factory",
                    }
                }

        # Try MCP agent if configured
        if self.mcp_bridge and self.mcp_bridge.is_configured:
            try:
                async for chunk in self._stream_via_mcp(session_id, messages, **kwargs):
                    yield chunk
                return
            except ChatError as e:
                logger.warning(f"MCP streaming failed, falling back: {e}")

        # Use LLMFactory streaming (provides resilience patterns: circuit breaker, retry)
        async for chunk in self._stream_via_llm_factory(session_id, messages, **kwargs):
            yield chunk

    async def get_history(self, session_id: str) -> list[dict[str, Any]] | None:
        """
        Get chat history for a session.

        Args:
            session_id: Session ID to retrieve history for

        Returns:
            List of messages or None if session not found.
            Returns empty list if no storage configured (graceful fallback).
        """
        if self._session_storage is None:
            # No storage configured - return empty list as graceful fallback
            return []

        # Delegate to storage backend
        result = await self._session_storage.get_messages(session_id)
        return list(result) if result is not None else None


# Service singletons
_chat_service: ChatService | None = None
_session_repository: Any | None = None


def get_session_repository() -> Any:
    """
    Get the session repository instance for message history storage.

    Returns a SessionRepository that implements get_messages() for loading
    conversation history before LLM calls.

    Returns:
        InMemorySessionRepository by default, can be overridden via set_session_repository().
    """
    global _session_repository
    if _session_repository is None:
        from mcp_server_langgraph.storage import InMemorySessionRepository

        _session_repository = InMemorySessionRepository()
    return _session_repository


def set_session_repository(repository: Any) -> None:
    """Set the session repository instance (for testing/DI)."""
    global _session_repository
    _session_repository = repository


def reset_session_repository() -> None:
    """Reset the session repository singleton (for testing)."""
    global _session_repository
    _session_repository = None


# v8: Contextvar-based storage adapter singleton (Finding 55)
_session_storage: Any = None


def get_session_storage() -> Any:
    """
    Get the contextvar-based session storage adapter.

    v8: Replaces get_session_repository for user-scoped access (Finding 55).
    Returns a ContextvarSessionStorageAdapter that reads user_id from contextvar.

    Returns:
        ContextvarSessionStorageAdapter instance
    """
    global _session_storage
    if _session_storage is None:
        from mcp_server_langgraph.api.v1.sessions import get_session_service
        from mcp_server_langgraph.storage.session.adapter import ContextvarSessionStorageAdapter

        session_service = get_session_service()
        _session_storage = ContextvarSessionStorageAdapter(session_service=session_service)
    return _session_storage


def reset_session_storage() -> None:
    """Reset the session storage singleton (for testing)."""
    global _session_storage
    _session_storage = None


def get_chat_service() -> ChatService:
    """
    Get the chat service instance (returns ChatServiceImpl).

    The service is initialized with a session_storage backend so that
    conversation history can be loaded from storage before LLM calls.
    This ensures the LLM receives full conversation context, not just
    the current message.
    """
    global _chat_service
    if _chat_service is None:
        session_storage = get_session_storage()
        _chat_service = ChatServiceImpl(session_storage=session_storage)
    return _chat_service


def set_chat_service(service: ChatService) -> None:
    """Set the chat service instance (for testing/DI)."""
    global _chat_service
    _chat_service = service


def reset_chat_service() -> None:
    """Reset the chat service singleton (for testing)."""
    global _chat_service
    _chat_service = None
    # Also reset session storage/repository to ensure fresh state
    reset_session_storage()
    reset_session_repository()


# Endpoints


@chat_router.post("/chat/completions")
async def create_completion(
    request: ChatCompletionRequest,
    current_user: CurrentUser,
) -> ChatCompletionResponse:
    """
    Create a chat completion.

    Requires authentication. The user must be authenticated to create completions.

    Sends messages to the LLM and returns the assistant's response.

    Raises:
        HTTPException 401: When authentication is required
        HTTPException 428: When MCP requires user elicitation (authentication, consent)
        HTTPException 403: When permission is denied
        HTTPException 503: When MCP server is unavailable
    """
    from mcp_server_langgraph.api.v1.mcp_bridge import (
        MCPConnectionError,
        MCPElicitationRequiredError,
        MCPPermissionError,
    )

    service = get_chat_service()
    messages = [msg.model_dump() for msg in request.messages]
    user_id = _get_user_id(current_user)

    try:
        response = await service.create_completion(
            session_id=request.session_id,
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            resource_uris=request.resource_uris,
            reasoning_effort=request.reasoning_effort,
            enable_thinking=request.enable_thinking,
            user_id=user_id,
            kb_focus=request.kb_focus,  # ADR-0094: KB Focus Mode for non-stream path
        )
        return ChatCompletionResponse(**response)
    except MCPElicitationRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={"detail": str(e), "elicitations": e.elicitations},
        )
    except MCPPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {e}",
        )
    except MCPConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP connection failed: {e}",
        )


@chat_router.post("/chat/completions/stream")
async def create_stream(
    request: ChatCompletionRequest,
    current_user: CurrentUser,
    openfga_client: Any = Depends(get_openfga_client),
    audit_service: Any = Depends(get_audit_service),
) -> StreamingResponse:
    """
    Create a streaming chat completion.

    Requires authentication. The user must be authenticated to create streams.

    Sends messages to the LLM and streams the response as Server-Sent Events.

    Execution Modes:
    - default: Approval required for medium/high-risk plans
    - plan: All plans require approval
    - auto_accept: Auto-approve all plans (no modal)
    - bypass: Risk-aware auto-approval (requires bypass_executor permission)
    """
    # OpenFGA permission check for bypass mode (replaces RBAC admin check)
    if request.execution_mode == "bypass":
        # CRITICAL: current_user["user_id"] is ALREADY "user:alice" from jwt_utils.py
        user_id = current_user.get("user_id") or f"user:{current_user.get('preferred_username', 'anonymous')}"

        # Check bypass_executor permission via OpenFGA (fail-closed)
        has_bypass_permission = False
        if openfga_client is not None:
            try:
                has_bypass_permission = await openfga_client.check_permission(
                    user=user_id,
                    relation="bypass_executor",
                    object="system:global",
                    critical=True,
                )
            except Exception:
                # Fail-closed: deny on any error
                has_bypass_permission = False

        if not has_bypass_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bypass mode requires bypass_executor permission on system:global",
            )

        # Audit logging: BYPASS_ACTIVATED event (FedRAMP/SOC2 compliance)
        # Uses helper to reduce duplication (see execution-mode-patterns.md gotcha #6)
        from mcp_server_langgraph.audit.context import create_context_from_request
        from mcp_server_langgraph.audit.models import AuditEventType
        from mcp_server_langgraph.execution.bypass_audit import log_bypass_audit_event

        await log_bypass_audit_event(
            audit_service=audit_service,
            event_type=AuditEventType.BYPASS_ACTIVATED,
            current_user=current_user,
            resource_type="session",
            resource_id=request.session_id,
            action="Activated risk-aware bypass execution mode",
            details={
                "execution_mode": request.execution_mode,
                "session_id": request.session_id,
            },
            context=create_context_from_request(request),
        )

    service = get_chat_service()
    from mcp_server_langgraph.api.v1.sessions import get_session_service

    session_service = get_session_service()
    messages = [msg.model_dump() for msg in request.messages]
    user_id = _get_user_id(current_user)

    async def event_generator() -> AsyncIterator[str]:
        import json

        from mcp_server_langgraph.observability.telemetry import logger

        # ================================================================
        # Message Persistence: Save user message before streaming
        # ================================================================
        # Extract the last user message to persist (frontend sends only new message)
        last_user_msg = next(
            (msg for msg in reversed(messages) if msg.get("role") == "user"),
            None,
        )
        if last_user_msg and session_service is not None:
            content = last_user_msg.get("content", "")
            stored_messages: list[dict[str, Any]] | None = None
            skip_persist = False
            try:
                stored_messages = await session_service.get_session_messages(request.session_id, user_id)
            except Exception as e:
                logger.warning(f"Failed to check session messages for dedupe: {e}")

            if stored_messages:
                last_stored = stored_messages[-1]
                if last_stored.get("role") == "user" and last_stored.get("content") == content:
                    logger.debug(
                        "Skipping duplicate user message persistence",
                        extra={"session_id": request.session_id},
                    )
                    skip_persist = True

            if not skip_persist:
                try:
                    result = await session_service.add_message(
                        request.session_id,
                        user_id,
                        {
                            "role": "user",
                            "content": content,
                        },
                    )
                    if result is None:
                        logger.warning(
                            "User message not persisted (session missing or not owned)",
                            extra={"session_id": request.session_id},
                        )
                    else:
                        logger.debug(f"Persisted user message for session {request.session_id}")
                except Exception as e:
                    logger.warning(f"Failed to persist user message: {e}")

        # Accumulate assistant response content for persistence
        accumulated_content: list[str] = []
        accumulated_thinking: list[str] = []
        thinking_tokens: int | None = None
        model_name: str | None = None
        sources_collected: list[dict[str, Any]] = []

        async for chunk in service.create_stream(
            session_id=request.session_id,
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            resource_uris=request.resource_uris,
            reasoning_effort=request.reasoning_effort,
            enable_thinking=request.enable_thinking,
            kb_focus=request.kb_focus,
            user_id=user_id,
            execution_mode=request.execution_mode,
            audit_service=audit_service,
            current_user=current_user,
            # v7: Native tools integration parameters
            tool_preference=request.tool_preference,
            tool_selection_mode=request.tool_selection_mode,
            selected_tools=request.selected_tools,
        ):
            # Accumulate delta content for persistence
            if "delta" in chunk and "content" in chunk["delta"]:
                content = chunk["delta"]["content"]
                if content:
                    accumulated_content.append(content)

            # v8 Q11: Accumulate thinking content for persistence
            if "delta" in chunk and "thinking" in chunk["delta"]:
                thinking = chunk["delta"]["thinking"]
                if isinstance(thinking, dict):
                    # New object format: {content, tokens}
                    if thinking.get("content"):
                        accumulated_thinking.append(thinking["content"])
                    if thinking.get("tokens"):
                        thinking_tokens = thinking["tokens"]
                elif isinstance(thinking, str) and thinking:
                    # Legacy string format
                    accumulated_thinking.append(thinking)

            # Capture model from chunk
            if chunk.get("model"):
                model_name = chunk["model"]

            # Collect sources for persistence
            if "sources" in chunk:
                sources_collected.extend(chunk["sources"])

            # Format as SSE
            yield f"data: {json.dumps(chunk)}\n\n"

        # ================================================================
        # Message Persistence: Save assistant response after streaming
        # ================================================================
        if accumulated_content and session_service is not None:
            try:
                full_response = "".join(accumulated_content)
                full_thinking = "".join(accumulated_thinking) if accumulated_thinking else None

                message_data: dict[str, Any] = {
                    "role": "assistant",
                    "content": full_response,
                }
                if sources_collected:
                    message_data["sources"] = sources_collected

                # Store thinking as structured object (content and tokens)
                if full_thinking or thinking_tokens:
                    message_data["thinking"] = {
                        "content": full_thinking,
                        "tokens": thinking_tokens,
                    }

                if model_name:
                    message_data["model_name"] = model_name

                result = await session_service.add_message(
                    request.session_id,
                    user_id,
                    message_data,
                )
                if result is None:
                    logger.warning(
                        "Assistant response not persisted (session missing or not owned)",
                        extra={"session_id": request.session_id},
                    )
                else:
                    logger.debug(f"Persisted assistant response for session {request.session_id} ({len(full_response)} chars)")
            except Exception as e:
                logger.warning(f"Failed to persist assistant response: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@chat_router.get("/chat/{session_id}/history")
async def get_history(
    session_id: str,
    current_user: CurrentUser,
) -> list[dict[str, Any]]:
    """
    Get chat history for a session.

    Requires authentication. Returns all messages in chronological order.

    Note: Session storage enforces ownership (user-scoped access). Unauthorized
    access returns 404.
    """
    service = get_chat_service()
    history = await service.get_history(session_id)

    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    return history
