"""
Model Registry

Centralized registry for LLM model capabilities, context limits, and costs.
Provides capability-aware model selection for the multi-agent orchestrator.

Usage:
    from mcp_server_langgraph.agents.model_registry import (
        ModelRegistry,
        ModelCapabilities,
        get_default_registry,
    )

    registry = get_default_registry()
    caps = registry.get("claude-opus-4-5-20251101")
    print(f"Context limit: {caps.context_limit}")
    print(f"Effective limit: {caps.effective_limit}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Default context limit for unknown models (conservative)
DEFAULT_CONTEXT_LIMIT = 128_000
DEFAULT_EFFECTIVE_PERCENTAGE = 0.65

# Capability type literals
CapabilityType = Literal[
    "vision",
    "tools",
    "streaming",
    "extended_thinking",
    "effort_param",
]


@dataclass
class ModelCapabilities:
    """Model capabilities and limits.

    Tracks context window sizes, costs, and feature support for LLM models.
    Used for capability-aware routing and cost tracking.

    Attributes:
        model_id: Unique model identifier (e.g., "claude-opus-4-5-20251101")
        vendor: Provider name (anthropic, google, openai, vertex_ai_anthropic, azure)
        context_limit: Maximum context window in tokens
        effective_limit: Recommended limit before degradation (65% of context_limit)
        max_output_tokens: Maximum output tokens per response
        input_cost_per_1m: Cost per 1M input tokens in USD
        output_cost_per_1m: Cost per 1M output tokens in USD
        supports_vision: Whether model supports image inputs
        supports_tools: Whether model supports tool/function calling
        supports_streaming: Whether model supports streaming responses
        supports_extended_thinking: Whether model supports extended thinking mode
        supports_effort_param: Whether model supports effort parameter (Claude Opus 4.5 only)
    """

    model_id: str
    vendor: str
    context_limit: int
    max_output_tokens: int
    input_cost_per_1m: float
    output_cost_per_1m: float

    # Optional with defaults
    effective_limit: int | None = None
    supports_vision: bool = False
    supports_tools: bool = False
    supports_streaming: bool = False
    supports_extended_thinking: bool = False
    supports_effort_param: bool = False

    def __post_init__(self) -> None:
        """Calculate effective_limit if not provided."""
        if self.effective_limit is None:
            self.effective_limit = int(self.context_limit * DEFAULT_EFFECTIVE_PERCENTAGE)


@dataclass
class ModelRegistry:
    """Registry for LLM model capabilities.

    Provides lookup, registration, and capability checking for models.
    Pre-populated with built-in models for common LLM providers.
    """

    _models: dict[str, ModelCapabilities] = field(default_factory=dict)
    _initialized: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize with built-in models."""
        if not self._initialized:
            self._register_builtin_models()
            self._initialized = True

    def _register_builtin_models(self) -> None:
        """Register all built-in models."""
        # Anthropic models
        self._models["claude-opus-4-5-20251101"] = ModelCapabilities(
            model_id="claude-opus-4-5-20251101",
            vendor="anthropic",
            context_limit=200_000,
            effective_limit=130_000,
            max_output_tokens=64_000,
            input_cost_per_1m=5.00,
            output_cost_per_1m=25.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
            supports_effort_param=True,
        )

        self._models["claude-sonnet-4-5-20250929"] = ModelCapabilities(
            model_id="claude-sonnet-4-5-20250929",
            vendor="anthropic",
            context_limit=1_000_000,  # 1M beta
            effective_limit=650_000,
            max_output_tokens=64_000,
            input_cost_per_1m=3.00,
            output_cost_per_1m=15.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
            supports_effort_param=False,
        )

        self._models["claude-haiku-4-5-20251001"] = ModelCapabilities(
            model_id="claude-haiku-4-5-20251001",
            vendor="anthropic",
            context_limit=200_000,
            effective_limit=130_000,
            max_output_tokens=64_000,
            input_cost_per_1m=1.00,
            output_cost_per_1m=5.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=False,
            supports_effort_param=False,
        )

        # Google Gemini models
        self._models["gemini-3-flash"] = ModelCapabilities(
            model_id="gemini-3-flash",
            vendor="google",
            context_limit=1_000_000,
            effective_limit=650_000,
            max_output_tokens=65_000,
            input_cost_per_1m=0.10,
            output_cost_per_1m=0.40,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=False,
            supports_effort_param=False,
        )

        self._models["gemini-3-pro"] = ModelCapabilities(
            model_id="gemini-3-pro",
            vendor="google",
            context_limit=2_000_000,
            effective_limit=1_300_000,
            max_output_tokens=65_000,
            input_cost_per_1m=2.00,
            output_cost_per_1m=12.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,  # Deep Think
            supports_effort_param=False,
        )

        # For complicated tier (gemini-2.5-flash)
        self._models["gemini-2.5-flash"] = ModelCapabilities(
            model_id="gemini-2.5-flash",
            vendor="google",
            context_limit=1_000_000,
            effective_limit=650_000,
            max_output_tokens=65_000,
            input_cost_per_1m=0.15,
            output_cost_per_1m=0.60,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=False,
            supports_effort_param=False,
        )

        # OpenAI GPT-5 models
        self._models["gpt-5.2"] = ModelCapabilities(
            model_id="gpt-5.2",
            vendor="openai",
            context_limit=400_000,
            effective_limit=260_000,
            max_output_tokens=128_000,
            input_cost_per_1m=1.25,
            output_cost_per_1m=10.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=False,
            supports_effort_param=False,
        )

        self._models["gpt-5.2-pro"] = ModelCapabilities(
            model_id="gpt-5.2-pro",
            vendor="openai",
            context_limit=400_000,
            effective_limit=260_000,
            max_output_tokens=128_000,
            input_cost_per_1m=2.50,
            output_cost_per_1m=20.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
            supports_effort_param=False,
        )

        # Legacy OpenAI models for backward compatibility
        self._models["gpt-4.1-nano"] = ModelCapabilities(
            model_id="gpt-4.1-nano",
            vendor="openai",
            context_limit=128_000,
            effective_limit=83_000,
            max_output_tokens=32_000,
            input_cost_per_1m=0.10,
            output_cost_per_1m=0.40,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
        )

        self._models["gpt-4.1-mini"] = ModelCapabilities(
            model_id="gpt-4.1-mini",
            vendor="openai",
            context_limit=128_000,
            effective_limit=83_000,
            max_output_tokens=32_000,
            input_cost_per_1m=0.40,
            output_cost_per_1m=1.60,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
        )

        self._models["o3"] = ModelCapabilities(
            model_id="o3",
            vendor="openai",
            context_limit=200_000,
            effective_limit=130_000,
            max_output_tokens=100_000,
            input_cost_per_1m=10.00,
            output_cost_per_1m=40.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
        )

        # Vertex AI Anthropic models (use @ format)
        self._models["claude-opus-4-5@20251101"] = ModelCapabilities(
            model_id="claude-opus-4-5@20251101",
            vendor="vertex_ai_anthropic",
            context_limit=200_000,
            effective_limit=130_000,
            max_output_tokens=64_000,
            input_cost_per_1m=5.00,
            output_cost_per_1m=25.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
            supports_effort_param=True,
        )

        self._models["claude-sonnet-4-5@20250929"] = ModelCapabilities(
            model_id="claude-sonnet-4-5@20250929",
            vendor="vertex_ai_anthropic",
            context_limit=1_000_000,
            effective_limit=650_000,
            max_output_tokens=64_000,
            input_cost_per_1m=3.00,
            output_cost_per_1m=15.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
        )

        self._models["claude-haiku-4-5@20251001"] = ModelCapabilities(
            model_id="claude-haiku-4-5@20251001",
            vendor="vertex_ai_anthropic",
            context_limit=200_000,
            effective_limit=130_000,
            max_output_tokens=64_000,
            input_cost_per_1m=1.00,
            output_cost_per_1m=5.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
        )

        # Vertex AI Gemini models
        self._models["vertex_ai/gemini-3-flash"] = ModelCapabilities(
            model_id="vertex_ai/gemini-3-flash",
            vendor="vertex_ai",
            context_limit=1_000_000,
            effective_limit=650_000,
            max_output_tokens=65_000,
            input_cost_per_1m=0.10,
            output_cost_per_1m=0.40,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
        )

        self._models["vertex_ai/gemini-3-pro"] = ModelCapabilities(
            model_id="vertex_ai/gemini-3-pro",
            vendor="vertex_ai",
            context_limit=2_000_000,
            effective_limit=1_300_000,
            max_output_tokens=65_000,
            input_cost_per_1m=2.00,
            output_cost_per_1m=12.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
        )

        # Azure OpenAI models
        self._models["azure/gpt-5.2"] = ModelCapabilities(
            model_id="azure/gpt-5.2",
            vendor="azure",
            context_limit=400_000,
            effective_limit=260_000,
            max_output_tokens=128_000,
            input_cost_per_1m=1.25,
            output_cost_per_1m=10.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
        )

        self._models["azure/gpt-5.2-pro"] = ModelCapabilities(
            model_id="azure/gpt-5.2-pro",
            vendor="azure",
            context_limit=400_000,
            effective_limit=260_000,
            max_output_tokens=128_000,
            input_cost_per_1m=2.50,
            output_cost_per_1m=20.00,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_extended_thinking=True,
        )

    def _get_default_capabilities(self, model_id: str) -> ModelCapabilities:
        """Get default capabilities for unknown model.

        Args:
            model_id: Unknown model identifier

        Returns:
            Default ModelCapabilities with conservative limits
        """
        return ModelCapabilities(
            model_id="default",
            vendor="unknown",
            context_limit=DEFAULT_CONTEXT_LIMIT,
            effective_limit=int(DEFAULT_CONTEXT_LIMIT * DEFAULT_EFFECTIVE_PERCENTAGE),
            max_output_tokens=16_000,
            input_cost_per_1m=1.00,
            output_cost_per_1m=3.00,
            supports_vision=False,
            supports_tools=True,
            supports_streaming=True,
        )

    def get(self, model_id: str) -> ModelCapabilities:
        """Get capabilities for a model.

        Args:
            model_id: Model identifier

        Returns:
            ModelCapabilities for the model, or defaults for unknown models
        """
        if model_id in self._models:
            return self._models[model_id]

        # Return default for unknown models
        return self._get_default_capabilities(model_id)

    def get_context_limit(self, model_id: str) -> int:
        """Get context limit for a model.

        Args:
            model_id: Model identifier

        Returns:
            Context limit in tokens
        """
        return self.get(model_id).context_limit

    def get_effective_limit(self, model_id: str) -> int:
        """Get effective context limit for a model.

        Args:
            model_id: Model identifier

        Returns:
            Effective limit in tokens (65% of context_limit)
        """
        caps = self.get(model_id)
        return caps.effective_limit if caps.effective_limit else caps.context_limit

    def supports_capability(self, model_id: str, capability: str) -> bool:
        """Check if model supports a capability.

        Args:
            model_id: Model identifier
            capability: Capability name (vision, tools, streaming, extended_thinking, effort_param)

        Returns:
            True if model supports the capability
        """
        caps = self.get(model_id)

        capability_map = {
            "vision": caps.supports_vision,
            "tools": caps.supports_tools,
            "streaming": caps.supports_streaming,
            "extended_thinking": caps.supports_extended_thinking,
            "effort_param": caps.supports_effort_param,
        }

        return capability_map.get(capability, False)

    def register(self, capabilities: ModelCapabilities) -> None:
        """Register or update model capabilities.

        Args:
            capabilities: ModelCapabilities to register
        """
        self._models[capabilities.model_id] = capabilities

    def unregister(self, model_id: str) -> None:
        """Unregister a model.

        Args:
            model_id: Model identifier to remove
        """
        if model_id in self._models:
            del self._models[model_id]

    def list_models(
        self,
        vendor: str | None = None,
        capability: str | None = None,
    ) -> list[str]:
        """List registered model IDs.

        Args:
            vendor: Filter by vendor (optional)
            capability: Filter by capability (optional)

        Returns:
            List of model IDs matching filters
        """
        models = list(self._models.keys())

        if vendor:
            models = [m for m in models if self._models[m].vendor == vendor]

        if capability:
            models = [m for m in models if self.supports_capability(m, capability)]

        return models

    def calculate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for token usage.

        Args:
            model_id: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in USD
        """
        caps = self.get(model_id)

        input_cost = (input_tokens / 1_000_000) * caps.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * caps.output_cost_per_1m

        return input_cost + output_cost


# Singleton instance
_default_registry: ModelRegistry | None = None


def get_default_registry() -> ModelRegistry:
    """Get the default model registry singleton.

    Returns:
        Default ModelRegistry instance with built-in models
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ModelRegistry()
    return _default_registry
