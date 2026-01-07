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
        supports_json_mode: Whether model supports structured JSON output
        tier: Model tier for complexity routing (simple, complicated, complex)
        max_thinking_tokens: Maximum thinking tokens for extended thinking (None if not supported)
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
    supports_json_mode: bool = False
    tier: Literal["simple", "complicated", "complex"] = "complicated"
    max_thinking_tokens: int | None = None

    def __post_init__(self) -> None:
        """Calculate effective_limit if not provided."""
        if self.effective_limit is None:
            self.effective_limit = int(self.context_limit * DEFAULT_EFFECTIVE_PERCENTAGE)

    @property
    def capabilities(self) -> set[str]:
        """Aggregate capability set for filtering.

        Returns:
            Set of enabled capability names.
        """
        caps: set[str] = set()
        if self.supports_vision:
            caps.add("vision")
        if self.supports_tools:
            caps.add("tools")
        if self.supports_streaming:
            caps.add("streaming")
        if self.supports_extended_thinking:
            caps.add("extended_thinking")
        if self.supports_effort_param:
            caps.add("effort_param")
        if self.supports_json_mode:
            caps.add("json_mode")
        return caps


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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=65536,  # ULTRA level
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
            supports_json_mode=True,
            tier="complicated",
            max_thinking_tokens=32768,  # HIGH level
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
            supports_json_mode=True,
            tier="simple",
            max_thinking_tokens=None,  # No extended thinking
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
            supports_json_mode=True,
            tier="simple",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=65536,  # Deep Think budget
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
            supports_json_mode=True,
            tier="complicated",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="complicated",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=65536,
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
            supports_json_mode=True,
            tier="simple",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="simple",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=100_000,  # o3 has high thinking capacity
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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=65536,
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
            supports_extended_thinking=True,
            supports_json_mode=True,
            tier="complicated",
            max_thinking_tokens=32768,
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
            supports_json_mode=True,
            tier="simple",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="simple",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=65536,
        )

        # Vertex AI Gemini preview models (gemini-3 is currently in preview)
        self._models["vertex_ai/gemini-3-flash-preview"] = ModelCapabilities(
            model_id="vertex_ai/gemini-3-flash-preview",
            vendor="vertex_ai",
            context_limit=1_000_000,
            effective_limit=650_000,
            max_output_tokens=65_000,
            input_cost_per_1m=0.10,
            output_cost_per_1m=0.40,
            supports_vision=True,
            supports_tools=True,
            supports_streaming=True,
            supports_json_mode=True,
            tier="simple",
            max_thinking_tokens=None,
        )

        self._models["vertex_ai/gemini-3-pro-preview"] = ModelCapabilities(
            model_id="vertex_ai/gemini-3-pro-preview",
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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=65536,
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
            supports_json_mode=True,
            tier="complicated",
            max_thinking_tokens=None,
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
            supports_json_mode=True,
            tier="complex",
            max_thinking_tokens=65536,
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
            capability: Capability name (vision, tools, streaming, extended_thinking, effort_param, json_mode)

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
            "json_mode": caps.supports_json_mode,
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
        tier: str | None = None,
    ) -> list[str]:
        """List registered model IDs.

        Args:
            vendor: Filter by vendor (optional)
            capability: Filter by capability (optional)
            tier: Filter by tier - simple, complicated, complex (optional)

        Returns:
            List of model IDs matching filters
        """
        models = list(self._models.keys())

        if vendor:
            models = [m for m in models if self._models[m].vendor == vendor]

        if capability:
            models = [m for m in models if self.supports_capability(m, capability)]

        if tier:
            models = [m for m in models if self._models[m].tier == tier]

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

    def get_model_for_tier(
        self,
        vendor: str,
        tier: Literal["simple", "complicated", "complex"],
    ) -> str:
        """Get the preferred model for a specific vendor and tier.

        This method encapsulates the business logic for tier-based model selection:
        - Returns the most appropriate model for the given tier
        - Handles cost-efficiency mappings (e.g., Google uses gemini-3-flash for
          both simple and complicated tiers)
        - Falls back to any available model for the vendor if exact tier not found

        Args:
            vendor: Vendor name (google, anthropic, openai, vertex_ai_anthropic, etc.)
            tier: Complexity tier (simple, complicated, complex)

        Returns:
            Model identifier string

        Raises:
            KeyError: If no model is registered for the vendor
        """
        # Tier preference mapping for cost efficiency
        # Supports both vendor-native API names and Vertex AI model names
        # Note: gemini-3 models are in preview, so Vertex AI uses -preview suffix
        tier_preferences: dict[str, dict[str, str]] = {
            # Vendor-native API model names (direct API access)
            "google": {
                "simple": "gemini-3-flash",
                "complicated": "gemini-3-flash",  # Cost efficiency
                "complex": "gemini-3-pro",
            },
            "anthropic": {
                "simple": "claude-haiku-4-5-20251001",
                "complicated": "claude-sonnet-4-5-20250929",
                "complex": "claude-opus-4-5-20251101",
            },
            "openai": {
                "simple": "gpt-5.2",
                "complicated": "gpt-5.2",  # Cost efficiency
                "complex": "gpt-5.2-pro",
            },
            # Vertex AI model names (Google Cloud unified access)
            "vertex_ai": {
                "simple": "vertex_ai/gemini-3-flash-preview",
                "complicated": "vertex_ai/gemini-3-flash-preview",  # Cost efficiency
                "complex": "vertex_ai/gemini-3-pro-preview",
            },
            "vertex_ai_anthropic": {
                "simple": "vertex_ai/claude-haiku-4-5@20251001",
                "complicated": "vertex_ai/claude-sonnet-4-5@20250929",
                "complex": "vertex_ai/claude-opus-4-5@20251101",
            },
            # Azure OpenAI model names
            "azure": {
                "simple": "azure/gpt-5.2",
                "complicated": "azure/gpt-5.2",  # Cost efficiency
                "complex": "azure/gpt-5.2-pro",
            },
        }

        # Try vendor-specific preference mapping first
        if vendor in tier_preferences:
            preferred_model = tier_preferences[vendor].get(tier)
            if preferred_model and preferred_model in self._models:
                return preferred_model

        # Fall back to listing models by vendor and tier from registry
        models = self.list_models(vendor=vendor, tier=tier)
        if models:
            return models[0]

        # Last resort: any model for this vendor
        vendor_models = self.list_models(vendor=vendor)
        if vendor_models:
            return vendor_models[0]

        raise KeyError(f"No model registered for vendor: {vendor}")


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
