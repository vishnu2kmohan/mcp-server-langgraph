"""
Workflow Title Generator Module

Generates concise, descriptive titles for workflows based on description
and/or originating session context.

Uses LLMFactory for AI-powered title generation with fallback to simple extraction.

Uses LLMFactory for resilient LLM calls with SOLID compliance:
- Circuit breaker, retry, timeout, bulkhead patterns
- Dependency injection for testability

Related: title_generator.py (session titles - similar pattern)
"""

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class WorkflowTitleGenerator:
    """Generates titles for workflows from description and context.

    Uses LiteLLM to analyze the workflow description and/or session context
    to generate a short, descriptive title. Falls back to simple extraction
    when LLM is unavailable.

    Example:
        generator = WorkflowTitleGenerator()
        title = await generator.generate(
            description="Automated customer onboarding with email verification",
            session_context="Help me create a workflow for new customer signup"
        )
        # Returns: "Customer Onboarding Pipeline"
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        max_title_length: int = 60,
        enable_llm: bool = True,
        llm_factory: "LLMFactory | None" = None,
    ) -> None:
        """Initialize the workflow title generator.

        Args:
            model_name: The LLM model to use (fast model recommended)
            max_title_length: Maximum length of generated title
            enable_llm: Whether to use LLM (set False for testing)
            llm_factory: Optional LLMFactory for dependency injection.
                         If not provided, will be lazily initialized from settings.
        """
        self.model_name = model_name
        self.max_title_length = max_title_length
        self.enable_llm = enable_llm
        self._llm_factory = llm_factory

    def _get_llm_factory(self) -> Any:
        """Get or create the LLM factory (lazy initialization).

        Returns:
            LLMFactory instance with resilience patterns.
        """
        if self._llm_factory is None:
            from mcp_server_langgraph.core.config import settings
            from mcp_server_langgraph.llm.factory import create_llm_from_config

            self._llm_factory = create_llm_from_config(settings)
        return self._llm_factory

    async def generate(
        self,
        description: str | None = None,
        session_context: str | None = None,
    ) -> str:
        """Generate a title from workflow description and/or session context.

        Args:
            description: The workflow description
            session_context: Context from originating session (e.g., first message)

        Returns:
            A concise, descriptive title (max 60 chars)
        """
        # Combine available context
        context = self._build_context(description, session_context)

        if not context:
            return "New Workflow"

        # Try LLM first, fallback to heuristics
        if self.enable_llm:
            try:
                title = await self._generate_with_llm(context)
                if title:
                    return self._sanitize_title(title)
            except Exception as e:
                logger.debug("LLM title generation failed: %s", e)

        return self._generate_heuristic_title(context)

    def _build_context(
        self,
        description: str | None,
        session_context: str | None,
    ) -> str:
        """Build context string from available inputs.

        Args:
            description: Workflow description
            session_context: Session context

        Returns:
            Combined context string
        """
        parts = []

        if description and description.strip():
            parts.append(f"Description: {description.strip()}")

        if session_context and session_context.strip():
            parts.append(f"Session context: {session_context.strip()}")

        return "\n".join(parts)

    async def _generate_with_llm(self, context: str) -> str:
        """Generate title using LLM via LLMFactory with resilience patterns.

        Uses LLMFactory for circuit breaker, retry, timeout, and bulkhead
        patterns (SOLID compliance - ADR-0026).

        Args:
            context: Combined description and session context

        Returns:
            Generated title string
        """
        from langchain_core.messages import HumanMessage

        # Truncate very long context
        truncated = context[:800] if len(context) > 800 else context

        prompt = f"""Generate a short, descriptive title (2-6 words, max 60 characters) for a workflow based on this context:

{truncated}

Rules:
- Be concise and descriptive
- Use title case
- No quotes or punctuation at the end
- Capture the main purpose or function
- Make it sound like a workflow/pipeline name (e.g., "Customer Onboarding Pipeline", "Data Import Process")
- Return ONLY the title, nothing else

Title:"""

        # Use LLMFactory for resilient LLM calls
        factory = self._get_llm_factory()
        messages = [HumanMessage(content=prompt)]

        response = await factory.ainvoke(
            messages,
            temperature=0.3,  # Low temperature for consistent titles
            max_tokens=50,
        )

        content = response.content
        return content.strip() if content else ""

    def _generate_heuristic_title(self, context: str) -> str:
        """Generate title using simple heuristics.

        Extracts key words from the context to form a title.

        Args:
            context: Combined description and session context

        Returns:
            Extracted title string
        """
        # Try to extract from description first
        clean = context.strip()

        # Remove "Description:" prefix if present
        if clean.lower().startswith("description:"):
            clean = clean[12:].strip()

        # Remove "Session context:" if that's what remains
        if clean.lower().startswith("session context:"):
            clean = clean[16:].strip()

        # Take first line or sentence
        for sep in ["\n", ".", "?", "!", ",", " - "]:
            if sep in clean:
                clean = clean.split(sep)[0].strip()
                break

        # Remove common prefixes
        prefixes = [
            "create a workflow",
            "build a workflow",
            "make a workflow",
            "workflow for",
            "workflow to",
            "help me",
            "i want to",
            "i need to",
            "automate",
            "automated",
        ]
        lower = clean.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                clean = clean[len(prefix) :].strip()
                break

        # Capitalize and truncate
        if clean:
            words = clean.split()[:6]  # Max 6 words
            title = " ".join(word.capitalize() for word in words)

            # Add "Workflow" suffix if not present and title is short
            if "workflow" not in title.lower() and len(title) < 40:
                title = f"{title} Workflow"

            return self._sanitize_title(title)

        return "New Workflow"

    def _sanitize_title(self, title: str) -> str:
        """Clean and truncate the title.

        Args:
            title: Raw title string

        Returns:
            Sanitized title
        """
        # Remove quotes and extra whitespace
        title = title.strip().strip("\"'")

        # Remove leading/trailing punctuation
        title = re.sub(r"^[^\w]+|[^\w]+$", "", title)

        # Truncate to max length
        if len(title) > self.max_title_length:
            # Try to break at word boundary
            truncated = title[: self.max_title_length]
            last_space = truncated.rfind(" ")
            if last_space > 20:  # Only break if reasonable length
                truncated = truncated[:last_space]
            title = truncated.rstrip()

        return title if title else "New Workflow"


# Singleton instance
_workflow_title_generator: WorkflowTitleGenerator | None = None


def get_workflow_title_generator() -> WorkflowTitleGenerator:
    """Get the singleton workflow title generator instance."""
    global _workflow_title_generator
    if _workflow_title_generator is None:
        _workflow_title_generator = WorkflowTitleGenerator()
    return _workflow_title_generator


async def generate_workflow_title(
    description: str | None = None,
    session_context: str | None = None,
) -> str:
    """Generate a workflow title from description and/or session context.

    Convenience function that uses the singleton generator.

    Args:
        description: The workflow description
        session_context: Context from originating session

    Returns:
        Generated title string
    """
    generator = get_workflow_title_generator()
    return await generator.generate(description, session_context)
