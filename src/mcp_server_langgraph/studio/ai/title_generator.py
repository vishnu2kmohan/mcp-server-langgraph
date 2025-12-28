"""
Title Generator Module

Generates concise, descriptive titles for chat sessions based on the first user message.
Uses LLMFactory for AI-powered title generation with fallback to simple extraction.

Uses LLMFactory for resilient LLM calls with SOLID compliance:
- Circuit breaker, retry, timeout, bulkhead patterns
- Dependency injection for testability
"""

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class SessionTitleGenerator:
    """Generates titles for chat sessions from user prompts.

    Uses LiteLLM to analyze the user's first message and generate
    a short, descriptive title. Falls back to simple extraction
    when LLM is unavailable.

    Example:
        generator = SessionTitleGenerator()
        title = await generator.generate("Help me write a Python function to sort a list")
        # Returns: "Python List Sorting"
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        max_title_length: int = 50,
        enable_llm: bool = True,
        llm_factory: "LLMFactory | None" = None,
    ) -> None:
        """Initialize the title generator.

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

    async def generate(self, message: str) -> str:
        """Generate a title from the user's message.

        Args:
            message: The user's first message in the session

        Returns:
            A concise, descriptive title (max 50 chars)
        """
        if not message or not message.strip():
            return "New Chat"

        # Try LLM first, fallback to heuristics
        if self.enable_llm:
            try:
                title = await self._generate_with_llm(message)
                if title:
                    return self._sanitize_title(title)
            except Exception as e:
                logger.debug("Operation failed: %s", e)

        return self._generate_heuristic_title(message)

    async def _generate_with_llm(self, message: str) -> str:
        """Generate title using LLM via LLMFactory with resilience patterns.

        Uses LLMFactory for circuit breaker, retry, timeout, and bulkhead
        patterns (SOLID compliance - ADR-0026).

        Args:
            message: The user's message

        Returns:
            Generated title string
        """
        from langchain_core.messages import HumanMessage

        # Truncate very long messages
        truncated = message[:500] if len(message) > 500 else message

        prompt = f"""Generate a short, descriptive title (3-6 words, max 50 characters) for a chat session that starts with this message:

"{truncated}"

Rules:
- Be concise and descriptive
- Use title case
- No quotes or punctuation at the end
- Capture the main topic or intent
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

    def _generate_heuristic_title(self, message: str) -> str:
        """Generate title using simple heuristics.

        Extracts key words from the message to form a title.

        Args:
            message: The user's message

        Returns:
            Extracted title string
        """
        # Clean the message
        clean = message.strip()

        # If it's a question, extract the key part
        if clean.endswith("?"):
            clean = clean[:-1]

        # Remove common prefixes
        prefixes = [
            "can you help me",
            "help me",
            "i want to",
            "i need to",
            "how do i",
            "how can i",
            "what is",
            "what are",
            "please",
            "could you",
            "can you",
        ]
        lower = clean.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                clean = clean[len(prefix) :].strip()
                break

        # Take first sentence or clause
        for sep in [".", "?", "!", "\n", ",", " - "]:
            if sep in clean:
                clean = clean.split(sep)[0].strip()
                break

        # Capitalize and truncate
        if clean:
            # Title case
            words = clean.split()[:6]  # Max 6 words
            title = " ".join(word.capitalize() for word in words)
            return self._sanitize_title(title)

        return "New Chat"

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

        return title if title else "New Chat"


# Singleton instance
_title_generator: SessionTitleGenerator | None = None


def get_title_generator() -> SessionTitleGenerator:
    """Get the singleton title generator instance."""
    global _title_generator  # noqa: PLW0603
    if _title_generator is None:
        _title_generator = SessionTitleGenerator()
    return _title_generator


async def generate_session_title(message: str) -> str:
    """Generate a session title from a user message.

    Convenience function that uses the singleton generator.

    Args:
        message: The user's first message

    Returns:
        Generated title string
    """
    generator = get_title_generator()
    return await generator.generate(message)
