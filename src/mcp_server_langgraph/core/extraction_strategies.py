"""
ExtractionStrategy - Strategy pattern for context extraction.

Created as part of Phase 2.5 KISS refactoring.

Responsibilities:
- Protocol definition for extraction strategies
- Rule-based extraction implementation
- Factory function for strategy selection

Reference: Plan - Phase 2.5 KISS: Strategy Pattern for Context Extraction
"""

from typing import Any, Protocol, runtime_checkable

from langchain_core.messages import BaseMessage

from mcp_server_langgraph.core.constants import MESSAGE_PREVIEW_LENGTH
from mcp_server_langgraph.core.context_manager import EXTRACTION_KEYWORDS


@runtime_checkable
class ExtractionStrategy(Protocol):
    """
    Protocol for extraction strategies.

    Defines the interface for extracting key information from messages.
    Implementations can use rule-based, LLM-based, or hybrid approaches.
    """

    async def extract(self, messages: list[BaseMessage]) -> dict[str, list[str]]:
        """
        Extract key information from messages.

        Args:
            messages: List of conversation messages

        Returns:
            Dictionary with categorized key information
        """
        ...


class RuleBasedExtractor:
    """
    Rule-based extraction using keyword matching.

    Fast, deterministic extraction suitable for:
    - High-volume processing
    - Latency-sensitive applications
    - Fallback when LLM unavailable
    """

    def __init__(
        self,
        keywords: dict[str, list[str]] | None = None,
        preview_length: int = MESSAGE_PREVIEW_LENGTH,
    ) -> None:
        """
        Initialize rule-based extractor.

        Args:
            keywords: Custom keyword categories (defaults to EXTRACTION_KEYWORDS)
            preview_length: Max characters to include in extracted items
        """
        self._keywords = keywords or EXTRACTION_KEYWORDS
        self._preview_length = preview_length

    async def extract(self, messages: list[BaseMessage]) -> dict[str, list[str]]:
        """
        Extract key information using keyword matching.

        Args:
            messages: List of conversation messages

        Returns:
            Dictionary with categorized key information
        """
        # Initialize all categories
        key_info: dict[str, list[str]] = {category: [] for category in self._keywords}

        for msg in messages:
            # Skip empty messages or those without content
            if not hasattr(msg, "content") or not msg.content:
                continue

            msg_content = str(msg.content)
            content_lower = msg_content.lower()

            # Check each category using keyword matching
            for category, keywords in self._keywords.items():
                if self._matches_category(content_lower, keywords):
                    key_info[category].append(msg_content[: self._preview_length])

        return key_info

    def _matches_category(self, content_lower: str, keywords: list[str]) -> bool:
        """
        Check if content matches any keyword in category.

        Args:
            content_lower: Lowercase content to check
            keywords: List of keywords for the category

        Returns:
            True if any keyword matches
        """
        return any(kw.lower() in content_lower for kw in keywords)


def get_extractor(
    strategy: str = "rule_based",
    **kwargs: Any,
) -> ExtractionStrategy:
    """
    Factory function for creating extractors.

    Args:
        strategy: Strategy type ("rule_based" or "llm_based")
        **kwargs: Additional arguments for the extractor

    Returns:
        ExtractionStrategy implementation

    Raises:
        ValueError: If unknown strategy type
    """
    if strategy == "rule_based":
        return RuleBasedExtractor(**kwargs)

    # Default to rule-based for unknown strategies (fail-safe)
    return RuleBasedExtractor(**kwargs)
