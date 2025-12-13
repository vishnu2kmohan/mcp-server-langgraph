"""
Unit tests for ExtractionStrategy pattern.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 2.5 KISS - Testing extraction strategies for context extraction.

Reference: Plan - Phase 2.5 KISS: Strategy Pattern for Context Extraction
"""

import gc

import pytest
from langchain_core.messages import AIMessage, HumanMessage


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.core,
]


@pytest.mark.xdist_group(name="test_extraction_strategies")
class TestRuleBasedExtractor:
    """Test RuleBasedExtractor for keyword-based extraction."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_extracts_decisions(self):
        """
        GIVEN: Messages containing decision language
        WHEN: Extracting key information
        THEN: Should categorize as decisions
        """
        from mcp_server_langgraph.core.extraction_strategies import RuleBasedExtractor

        # Arrange
        extractor = RuleBasedExtractor()
        messages = [
            HumanMessage(content="We need to choose a database"),
            AIMessage(content="We decided to use PostgreSQL for persistence"),
        ]

        # Act
        result = await extractor.extract(messages)

        # Assert
        assert "decisions" in result
        assert any("decided" in item.lower() or "postgresql" in item.lower() for item in result["decisions"])

    @pytest.mark.asyncio
    async def test_extracts_requirements(self):
        """
        GIVEN: Messages containing requirement language
        WHEN: Extracting key information
        THEN: Should categorize as requirements
        """
        from mcp_server_langgraph.core.extraction_strategies import RuleBasedExtractor

        # Arrange
        extractor = RuleBasedExtractor()
        messages = [
            HumanMessage(content="We need to support 1000 concurrent users"),
            AIMessage(content="The system must handle high traffic"),
        ]

        # Act
        result = await extractor.extract(messages)

        # Assert
        assert "requirements" in result
        assert len(result["requirements"]) > 0

    @pytest.mark.asyncio
    async def test_extracts_questions(self):
        """
        GIVEN: Messages containing questions
        WHEN: Extracting key information
        THEN: Should categorize as questions
        """
        from mcp_server_langgraph.core.extraction_strategies import RuleBasedExtractor

        # Arrange
        extractor = RuleBasedExtractor()
        messages = [
            HumanMessage(content="What is the best approach for caching?"),
            AIMessage(content="How should we implement the API?"),
        ]

        # Act
        result = await extractor.extract(messages)

        # Assert
        assert "questions" in result
        assert len(result["questions"]) > 0

    @pytest.mark.asyncio
    async def test_returns_all_categories(self):
        """
        GIVEN: RuleBasedExtractor
        WHEN: Extracting from any messages
        THEN: Should return all category keys
        """
        from mcp_server_langgraph.core.extraction_strategies import RuleBasedExtractor

        # Arrange
        extractor = RuleBasedExtractor()
        messages = [HumanMessage(content="Hello world")]

        # Act
        result = await extractor.extract(messages)

        # Assert - should have all expected categories
        expected_categories = ["decisions", "requirements", "facts", "questions", "action_items", "constraints"]
        for category in expected_categories:
            assert category in result

    @pytest.mark.asyncio
    async def test_handles_empty_messages(self):
        """
        GIVEN: Empty message list
        WHEN: Extracting key information
        THEN: Should return empty categories
        """
        from mcp_server_langgraph.core.extraction_strategies import RuleBasedExtractor

        # Arrange
        extractor = RuleBasedExtractor()
        messages: list = []

        # Act
        result = await extractor.extract(messages)

        # Assert
        assert isinstance(result, dict)
        assert all(len(items) == 0 for items in result.values())


@pytest.mark.xdist_group(name="test_extraction_strategies")
class TestExtractionStrategyProtocol:
    """Test ExtractionStrategy protocol compliance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rule_based_implements_protocol(self):
        """
        GIVEN: RuleBasedExtractor class
        WHEN: Checking protocol compliance
        THEN: Should be a valid ExtractionStrategy implementation
        """
        from mcp_server_langgraph.core.extraction_strategies import (
            ExtractionStrategy,
            RuleBasedExtractor,
        )

        # Assert
        extractor = RuleBasedExtractor()
        assert isinstance(extractor, ExtractionStrategy)

    def test_protocol_is_runtime_checkable(self):
        """
        GIVEN: ExtractionStrategy protocol
        WHEN: Checking if it's runtime checkable
        THEN: Should be usable with isinstance()
        """
        from mcp_server_langgraph.core.extraction_strategies import ExtractionStrategy

        # Assert - protocol should be runtime checkable
        assert hasattr(ExtractionStrategy, "__protocol_attrs__") or hasattr(ExtractionStrategy, "_is_protocol")


@pytest.mark.xdist_group(name="test_extraction_strategies")
class TestExtractionStrategyFactory:
    """Test factory function for creating extractors."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_rule_based_extractor(self):
        """
        GIVEN: Factory function
        WHEN: Requesting rule-based extractor
        THEN: Should return RuleBasedExtractor instance
        """
        from mcp_server_langgraph.core.extraction_strategies import (
            RuleBasedExtractor,
            get_extractor,
        )

        # Act
        extractor = get_extractor("rule_based")

        # Assert
        assert isinstance(extractor, RuleBasedExtractor)

    def test_get_default_extractor(self):
        """
        GIVEN: Factory function
        WHEN: Requesting default extractor
        THEN: Should return RuleBasedExtractor (fast default)
        """
        from mcp_server_langgraph.core.extraction_strategies import (
            RuleBasedExtractor,
            get_extractor,
        )

        # Act
        extractor = get_extractor()

        # Assert
        assert isinstance(extractor, RuleBasedExtractor)
