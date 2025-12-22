"""
Model Selector

Three-tier model selection with graceful fallbacks and cross-vendor verification.

Tiers:
- Simple: Fast models for basic subtasks (Gemini Flash, Claude Haiku, GPT-4.1-nano)
- Complicated: Balanced models for analysis (Gemini 2.5 Flash, Claude Sonnet, GPT-4.1-mini)
- Complex: Powerful models for synthesis (Gemini Pro, Claude Opus, o3)

Usage:
    from mcp_server_langgraph.agents.model_selector import ModelSelector

    selector = ModelSelector()
    model = selector.select_model("complex")
    verifier = selector.select_verifier("auto")
"""

from __future__ import annotations

import os

from mcp_server_langgraph.agents.metrics import (
    record_cross_vendor_verification,
    record_model_selection,
)

# Model aliases for graceful upgrades (December 2025)
MODEL_TIERS = {
    "simple": {
        "google": "gemini-3-flash",
        "anthropic": "claude-haiku-4-5-20251001",
        "openai": "gpt-5.2",
        "vertex_ai_anthropic": "claude-haiku-4-5@20251001",
    },
    "complicated": {
        "google": "gemini-3-flash",  # Same as simple for cost efficiency
        "anthropic": "claude-sonnet-4-5-20250929",
        "openai": "gpt-5.2",  # Same as simple for cost efficiency
        "vertex_ai_anthropic": "claude-sonnet-4-5@20250929",
    },
    "complex": {
        "google": "gemini-3-pro",
        "anthropic": "claude-opus-4-5-20251101",
        "openai": "gpt-5.2-pro",
        "vertex_ai_anthropic": "claude-opus-4-5@20251101",
    },
}

# Vendor priority order (includes Vertex AI Anthropic for enterprise deployments)
VENDOR_PRIORITY = ["google", "anthropic", "openai", "vertex_ai_anthropic"]


class ModelSelector:
    """Three-tier model selection with cross-vendor verification.

    Selects appropriate models based on task complexity and
    supports graceful fallbacks when tiers are unavailable.
    """

    def __init__(
        self,
        available_vendors: list[str] | None = None,
        available_tiers: list[str] | None = None,
    ) -> None:
        """Initialize model selector.

        Args:
            available_vendors: List of available vendors (auto-detected if None)
            available_tiers: List of available tiers (all if None)
        """
        self.available_vendors = available_vendors or self._detect_vendors()
        self.available_tiers = available_tiers or ["simple", "complicated", "complex"]
        self.primary_vendor = self.available_vendors[0] if self.available_vendors else "google"

    def _detect_vendors(self) -> list[str]:
        """Auto-detect available vendors from environment.

        Returns:
            List of available vendor names in priority order
        """
        vendors = []

        # Google/Gemini is the primary execution vendor
        if os.environ.get("GOOGLE_API_KEY") or os.environ.get("VERTEX_AI_PROJECT"):
            vendors.append("google")

        # Anthropic/Claude is the default judge vendor
        if os.environ.get("ANTHROPIC_API_KEY"):
            vendors.append("anthropic")

        # OpenAI as fallback
        if os.environ.get("OPENAI_API_KEY"):
            vendors.append("openai")

        # Vertex AI Anthropic for enterprise deployments
        # Uses Workload Identity Federation (no API key), detected via VERTEXAI_PROJECT
        if os.environ.get("VERTEXAI_PROJECT") and os.environ.get("VERTEXAI_LOCATION"):
            vendors.append("vertex_ai_anthropic")

        # Default to google if nothing detected (for testing)
        return vendors or ["google"]

    def _fallback_tier(self, requested: str) -> str:
        """Map requested tier to available tier.

        Args:
            requested: Requested complexity tier

        Returns:
            Best available tier
        """
        if requested in self.available_tiers:
            return requested

        # Fallback: use closest available tier
        tier_order = ["simple", "complicated", "complex"]
        try:
            requested_idx = tier_order.index(requested)
        except ValueError:
            return self.available_tiers[-1]

        # Try to find closest tier going down
        for i in range(requested_idx, -1, -1):
            if tier_order[i] in self.available_tiers:
                return tier_order[i]

        # Use highest available
        return self.available_tiers[-1]

    def select_model(self, complexity: str) -> str:
        """Select model for given complexity.

        Args:
            complexity: Task complexity (simple, complicated, complex)

        Returns:
            Model identifier string
        """
        effective_tier = self._fallback_tier(complexity)
        is_fallback = effective_tier != complexity
        vendor = self.primary_vendor
        model = None

        if vendor in MODEL_TIERS[effective_tier]:
            model = MODEL_TIERS[effective_tier][vendor]
        else:
            # Fallback to first available vendor for this tier
            for v in VENDOR_PRIORITY:
                if v in self.available_vendors and v in MODEL_TIERS[effective_tier]:
                    model = MODEL_TIERS[effective_tier][v]
                    vendor = v
                    break

        # Ultimate fallback
        if model is None:
            model = MODEL_TIERS[effective_tier]["google"]
            vendor = "google"

        # Record model selection metrics
        record_model_selection(
            tier=effective_tier,
            vendor=vendor,
            model=model,
            is_fallback=is_fallback,
        )

        return model

    def select_verifier(self, verifier_vendor: str = "auto") -> str:
        """Select verifier model for cross-vendor verification.

        Args:
            verifier_vendor: Vendor preference (auto, same, anthropic, google, openai)

        Returns:
            Verifier model identifier
        """
        same_vendor_fallback = False
        actual_verifier_vendor = None
        verifier_model = None
        primary_model = MODEL_TIERS["complicated"].get(
            self.primary_vendor,
            MODEL_TIERS["complicated"]["google"],
        )

        if verifier_vendor == "same":
            # Use same vendor as primary (explicitly requested)
            same_vendor_fallback = True
            actual_verifier_vendor = self.primary_vendor
            verifier_model = self.select_model("complicated")

        elif verifier_vendor == "auto":
            # Prefer cross-vendor if available
            for vendor in self.available_vendors:
                if vendor != self.primary_vendor:
                    actual_verifier_vendor = vendor
                    verifier_model = MODEL_TIERS["complicated"].get(
                        vendor,
                        MODEL_TIERS["complicated"]["anthropic"],
                    )
                    break

            # Fallback to same vendor if no cross-vendor available
            if verifier_model is None:
                same_vendor_fallback = True
                actual_verifier_vendor = self.primary_vendor
                verifier_model = self.select_model("complicated")

        else:
            # Explicit vendor requested
            actual_verifier_vendor = verifier_vendor
            if verifier_vendor in MODEL_TIERS["complicated"]:
                verifier_model = MODEL_TIERS["complicated"][verifier_vendor]
            else:
                # Default to Anthropic for verification
                actual_verifier_vendor = "anthropic"
                verifier_model = MODEL_TIERS["complicated"]["anthropic"]

        # Record cross-vendor verification metrics
        # All branches above assign actual_verifier_vendor, assert for mypy
        assert actual_verifier_vendor is not None
        record_cross_vendor_verification(
            primary_vendor=self.primary_vendor,
            verifier_vendor=actual_verifier_vendor,
            primary_model=primary_model,
            verifier_model=verifier_model,
            success=True,  # Selection always succeeds
            same_vendor_fallback=same_vendor_fallback,
        )

        return verifier_model

    def get_model_for_task(self, task_complexity_score: int) -> str:
        """Select model based on numeric complexity score.

        Args:
            task_complexity_score: Score from 1-10

        Returns:
            Model identifier
        """
        if task_complexity_score <= 3:
            return self.select_model("simple")
        elif task_complexity_score <= 7:
            return self.select_model("complicated")
        else:
            return self.select_model("complex")

    def select_model_for_litellm(self, complexity: str) -> str:
        """Select model and return LiteLLM-compatible model ID.

        This method combines select_model with get_litellm_model_id to return
        a model string ready for use with LiteLLM.

        Args:
            complexity: Task complexity (simple, complicated, complex)

        Returns:
            LiteLLM-compatible model identifier with appropriate prefix
        """
        model = self.select_model(complexity)
        return get_litellm_model_id(model, self.primary_vendor)


# Vendor prefix mapping for LiteLLM compatibility
VENDOR_LITELLM_PREFIX = {
    "vertex_ai_anthropic": "vertex_ai/",
    "azure": "azure/",
    "bedrock": "bedrock/",
    "ollama": "ollama/",
    # These vendors don't need prefix:
    "anthropic": "",
    "openai": "",
    "google": "",
    "vertex_ai": "",  # Already prefixed in MODEL_TIERS
}


def get_litellm_model_id(model_name: str, vendor: str) -> str:
    """Convert vendor + model name to LiteLLM-compatible model ID.

    LiteLLM uses prefixes like 'vertex_ai/', 'azure/', 'bedrock/' for
    routing requests to different providers. This function adds the
    appropriate prefix based on the vendor.

    Args:
        model_name: The base model name (e.g., "claude-opus-4-5@20251101")
        vendor: The vendor name (e.g., "vertex_ai_anthropic", "anthropic")

    Returns:
        LiteLLM-compatible model identifier (e.g., "vertex_ai/claude-opus-4-5@20251101")

    Examples:
        >>> get_litellm_model_id("claude-opus-4-5@20251101", "vertex_ai_anthropic")
        "vertex_ai/claude-opus-4-5@20251101"

        >>> get_litellm_model_id("claude-opus-4-5-20251101", "anthropic")
        "claude-opus-4-5-20251101"

        >>> get_litellm_model_id("gpt-5.2", "azure")
        "azure/gpt-5.2"
    """
    # Get the prefix for this vendor
    prefix = VENDOR_LITELLM_PREFIX.get(vendor, "")

    # If model already has a prefix (e.g., "vertex_ai/gemini-3-pro"), don't add again
    if prefix and model_name.startswith(prefix.rstrip("/")):
        return model_name

    # Check if model already has any known prefix
    known_prefixes = ["vertex_ai/", "azure/", "bedrock/", "ollama/"]
    for known_prefix in known_prefixes:
        if model_name.startswith(known_prefix):
            return model_name

    return f"{prefix}{model_name}"
