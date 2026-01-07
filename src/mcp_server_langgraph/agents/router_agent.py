"""
Router Agent for Orchestration Routing

Classifies incoming requests to determine:
- Complexity level (simple, complicated, complex)
- Risk level (low, medium, high)
- Task type (chat, code, analysis, data, ops, other)
- Suggested orchestrator (standard, swarm, studio, ux, alert)
- Critique rounds needed (0-3)
- Thinking budget (none, light, medium, deep)

Also provides executor/critic model selection with cross-vendor diversity.

Usage:
    from mcp_server_langgraph.agents.router_agent import (
        RouterAgent,
        RouterOutput,
        select_executor_critic,
    )

    agent = RouterAgent(llm_factory=get_llm_factory())
    output = await agent.route(message="Help me analyze this code")
    executor, critic = select_executor_critic(output.complexity, output.risk)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp_server_langgraph.repositories.plan_template import PlanTemplateRepository


class EmbeddingService(Protocol):
    """Protocol for embedding services."""

    async def embed(self, text: str) -> list[float]:
        """Embed text into a vector.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        ...


logger = logging.getLogger(__name__)


class RouterOutput(BaseModel):
    """Orchestration routing decision.

    This is distinct from the action-based RouterDecision in llm/pydantic_agent.py.
    RouterOutput focuses on orchestration strategy, not action selection.

    Attributes:
        complexity: Task complexity level matching model tier naming
        risk: Risk level for approval workflow
        task_type: Category of task
        tools_needed: List of tools the task may need
        suggested_orchestrator: Recommended orchestrator pattern
        critique_rounds: Number of critique/revision rounds (0-3)
        thinking_budget: Extended thinking budget level
        confidence: Confidence in classification (0.0-1.0)
        skills_needed: List of skills the task may need (ADR-0092)
        execution_mode: Execution mode selection (ADR-0092)
        routing_rationale: Explanation for routing decision (ADR-0092)
    """

    model_config = {"extra": "ignore"}  # Ignore unknown fields for forward compat

    complexity: Literal["simple", "complicated", "complex"]
    risk: Literal["low", "medium", "high"]
    task_type: Literal["chat", "code", "analysis", "data", "ops", "other"]
    tools_needed: list[str]
    suggested_orchestrator: Literal["standard", "swarm", "studio", "ux", "alert"]
    critique_rounds: int = Field(ge=0, le=3)
    thinking_budget: Literal["none", "light", "medium", "deep"]
    confidence: float = Field(ge=0.0, le=1.0)

    # ADR-0092: New fields for Hierarchical Capability Architecture
    skills_needed: list[str] = Field(default_factory=list)
    execution_mode: Literal["pure_llm", "tool_calling", "react", "programmatic", "orchestrator"] = "tool_calling"
    routing_rationale: str = ""


class TemplateSuggestion(BaseModel):
    """A suggested template based on semantic similarity.

    Attributes:
        template_id: The template's unique identifier
        name: Template name for display
        similarity: Cosine similarity score (0.0-1.0)
    """

    template_id: str
    name: str
    similarity: float = Field(ge=0.0, le=1.0)


class RouterOutputWithTemplates(RouterOutput):
    """RouterOutput extended with template suggestions.

    This model extends the base RouterOutput with a list of template
    suggestions that match the user's request based on semantic similarity.

    Attributes:
        suggested_templates: List of matching templates sorted by similarity
    """

    suggested_templates: list[TemplateSuggestion] = Field(default_factory=list)


# Default fallback for parse errors or low confidence
DEFAULT_ROUTER_OUTPUT = RouterOutput(
    complexity="complicated",
    risk="medium",
    task_type="other",
    tools_needed=[],
    suggested_orchestrator="standard",
    critique_rounds=1,
    thinking_budget="light",
    confidence=0.5,
    # ADR-0092: New fields with backward-compatible defaults
    skills_needed=[],
    execution_mode="tool_calling",
    routing_rationale="",
)

# Import centralized orchestration router prompt with dynamic template support
# See: core/prompts/orchestration_router_prompt.py
# Migration: ADR-0089 Prompt Architecture Centralization
from mcp_server_langgraph.core.prompts import get_orchestration_router_prompt


class RouterAgent:
    """Agent for classifying requests and determining orchestration strategy.

    Uses a fast LLM (e.g., gemini-3-flash) to classify requests quickly.
    Results can be cached for repeated similar requests.

    Attributes:
        llm_factory: Factory for creating LLM completions
        model_id: Fast model for routing (default: None = use factory default)
        cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
    """

    def __init__(
        self,
        llm_factory: Any,
        model_id: str | None = None,
        cache_ttl: int = 3600,
    ) -> None:
        """Initialize RouterAgent.

        Args:
            llm_factory: LLMFactory for creating completions
            model_id: Optional fast model ID (e.g., "gemini-3-flash-preview")
            cache_ttl: Cache TTL in seconds (default 1 hour)
        """
        self.llm_factory = llm_factory
        self.model_id = model_id
        self.cache_ttl = cache_ttl

    async def route(
        self,
        message: str,
        tools_available: list[str] | None = None,
        persona: str | None = None,
    ) -> RouterOutput:
        """Classify a request for routing.

        Args:
            message: User message to classify
            tools_available: List of available tools (optional)
            persona: Current persona context (optional)

        Returns:
            RouterOutput with classification and recommendations
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        try:
            # Build messages for classification using LangChain message types
            # Use dynamic template with available tools injected at runtime
            system_prompt = get_orchestration_router_prompt(available_tools=tools_available or [])
            langchain_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message),
            ]

            # Build kwargs for ainvoke
            kwargs: dict[str, Any] = {}
            if self.model_id:
                kwargs["model"] = self.model_id

            # Call LLM for classification using ainvoke (returns AIMessage)
            response = await self.llm_factory.ainvoke(langchain_messages, **kwargs)

            # Extract content from AIMessage
            content = response.content or ""

            # Parse JSON response
            try:
                data = json.loads(content)
                return RouterOutput(**data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse router response: {e}")
                return DEFAULT_ROUTER_OUTPUT

        except Exception:
            logger.exception("Router error")
            return DEFAULT_ROUTER_OUTPUT

    async def route_with_template_suggestion(
        self,
        message: str,
        embedding_service: EmbeddingService,
        template_repo: PlanTemplateRepository,
        tools_available: list[str] | None = None,
        persona: str | None = None,
        min_similarity: float = 0.7,
        max_suggestions: int = 5,
    ) -> RouterOutputWithTemplates:
        """Route a request with template suggestions.

        This method:
        1. Runs normal router classification
        2. Embeds the user message
        3. Finds similar templates (cosine similarity > min_similarity)
        4. Returns router decision + suggested templates

        Args:
            message: User message to classify
            embedding_service: Service for creating embeddings
            template_repo: Repository for template lookup
            tools_available: List of available tools (optional)
            persona: Current persona context (optional)
            min_similarity: Minimum cosine similarity threshold (default 0.7)
            max_suggestions: Maximum number of template suggestions (default 5)

        Returns:
            RouterOutputWithTemplates with classification and template suggestions
        """
        # Run normal routing
        router_output = await self.route(
            message=message,
            tools_available=tools_available,
            persona=persona,
        )

        # Embed the user message
        try:
            query_embedding = await embedding_service.embed(message)

            # Find similar templates
            similar_templates = await template_repo.find_similar(
                query_embedding=query_embedding,
                min_similarity=min_similarity,
                limit=max_suggestions,
            )

            # Convert to suggestions
            suggestions = [
                TemplateSuggestion(
                    template_id=t.template_id,
                    name=t.name,
                    similarity=self._calculate_similarity(query_embedding, t.description_embedding or []),
                )
                for t in similar_templates
            ]

        except Exception as e:
            logger.warning(f"Template suggestion failed: {e}")
            suggestions = []

        # Return combined output
        return RouterOutputWithTemplates(
            complexity=router_output.complexity,
            risk=router_output.risk,
            task_type=router_output.task_type,
            tools_needed=router_output.tools_needed,
            suggested_orchestrator=router_output.suggested_orchestrator,
            critique_rounds=router_output.critique_rounds,
            thinking_budget=router_output.thinking_budget,
            confidence=router_output.confidence,
            suggested_templates=suggestions,
        )

    @staticmethod
    def _calculate_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score between 0 and 1
        """
        import math

        if len(vec1) != len(vec2) or len(vec1) == 0:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return max(0.0, dot_product / (magnitude1 * magnitude2))


# Model tier mapping for executor/critic selection
# Supports both vendor-native API names and Vertex AI model names
# Note: gemini-3 models are in preview, so Vertex AI uses -preview suffix
TIER_MODELS = {
    # Vendor-native API model names (direct API access)
    "google": {
        "simple": "gemini-3-flash",
        "complicated": "gemini-3-flash",
        "complex": "gemini-3-pro",
    },
    "anthropic": {
        "simple": "claude-haiku-4-5-20251001",
        "complicated": "claude-sonnet-4-5-20250929",
        "complex": "claude-opus-4-5-20251101",
    },
    "openai": {
        "simple": "gpt-5.2",
        "complicated": "gpt-5.2",
        "complex": "gpt-5.2-pro",
    },
    # Vertex AI model names (Google Cloud unified access)
    # Gemini models via Vertex AI (preview suffix required for gemini-3)
    "vertex_ai": {
        "simple": "vertex_ai/gemini-3-flash-preview",
        "complicated": "vertex_ai/gemini-3-flash-preview",
        "complex": "vertex_ai/gemini-3-pro-preview",
    },
    # Claude models via Vertex AI (uses @ version format)
    "vertex_ai_anthropic": {
        "simple": "vertex_ai/claude-haiku-4-5@20251001",
        "complicated": "vertex_ai/claude-sonnet-4-5@20250929",
        "complex": "vertex_ai/claude-opus-4-5@20251101",
    },
    # Azure OpenAI model names
    "azure": {
        "simple": "azure/gpt-5.2",
        "complicated": "azure/gpt-5.2",
        "complex": "azure/gpt-5.2-pro",
    },
}

# Default vendors for cross-vendor diversity
# Uses Vertex AI for unified billing and credential management
DEFAULT_EXECUTOR_VENDOR = "vertex_ai"
DEFAULT_CRITIC_VENDOR = "vertex_ai_anthropic"


def select_executor_critic(
    complexity: str,
    risk: str,
    prefer_same_vendor: bool = False,
    executor_vendor: str = DEFAULT_EXECUTOR_VENDOR,
    critic_vendor: str = DEFAULT_CRITIC_VENDOR,
) -> tuple[str, str | None]:
    """Select executor and critic models based on complexity and risk.

    Default behavior: Cross-vendor diversity (Gemini executor + Claude critic)
    Override: Same-vendor when cost optimization preferred

    Args:
        complexity: Task complexity (simple, complicated, complex)
        risk: Task risk level (low, medium, high)
        prefer_same_vendor: If True, use same vendor for both (cost optimization)
        executor_vendor: Vendor for executor (default: google)
        critic_vendor: Vendor for critic (default: anthropic)

    Returns:
        Tuple of (executor_model_id, critic_model_id or None)
    """
    # Select executor based on complexity tier
    executor = TIER_MODELS.get(executor_vendor, TIER_MODELS["google"]).get(complexity, TIER_MODELS["google"]["complicated"])

    # Determine if critic is needed
    if risk == "low":
        # No critique needed for low-risk tasks
        return (executor, None)

    # Select critic
    if prefer_same_vendor:
        # Cost optimization: use same vendor, lower tier for critic
        critic_tier = "simple" if complexity != "complex" else "complicated"
        critic = TIER_MODELS.get(executor_vendor, TIER_MODELS["google"]).get(critic_tier, TIER_MODELS["google"]["simple"])
    else:
        # Cross-vendor diversity: use different vendor for critic
        critic_tier = "simple" if risk == "medium" else "complicated"
        critic = TIER_MODELS.get(critic_vendor, TIER_MODELS["anthropic"]).get(critic_tier, TIER_MODELS["anthropic"]["simple"])

    return (executor, critic)
