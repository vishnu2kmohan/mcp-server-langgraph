import gc
import os


"""
Unit tests for ContextManager LLM-based extraction

Tests enhanced structured note-taking with LLM extraction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from mcp_server_langgraph.core.context_manager import ContextManager


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = MagicMock()

    # Mock ainvoke to return structured extraction
    async def mock_ainvoke(prompt):
        # Return formatted extraction response
        response = MagicMock()
        response.content = """DECISIONS:
- Decided to use Qdrant for vector storage
- Chose all-MiniLM-L6-v2 as embedding model

REQUIREMENTS:
- System must support semantic search
- Must maintain backward compatibility

FACTS:
- Qdrant runs on port 6333
- SentenceTransformers provides embeddings

ACTION_ITEMS:
- Create unit tests for all modules
- Update documentation

ISSUES:
- Redis checkpointer has connection timeout

PREFERENCES:
- User prefers structured output format
"""
        return response

    llm.ainvoke = AsyncMock(side_effect=mock_ainvoke)
    return llm


@pytest.fixture
def context_manager(mock_llm):
    """Create ContextManager instance with mocked LLM"""
    # Patch the factory function that ContextManager actually uses
    with patch("mcp_server_langgraph.llm.factory.create_summarization_model", return_value=mock_llm):
        manager = ContextManager(
            compaction_threshold=8000,
            target_after_compaction=4000,
            recent_message_count=5,
        )
        # LLM should already be set by __init__, but ensure our mock is used
        manager.llm = mock_llm
        return manager


@pytest.mark.xdist_group(name="context_manager_llm_tests")
class TestEnhancedNoteExtraction:
    """Test suite for LLM-based key information extraction"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extract_key_information_llm_success(self, context_manager, mock_llm):
        """Test successful LLM-based extraction"""
        messages = [
            HumanMessage(content="We should use Qdrant for vector storage"),
            AIMessage(content="Good choice. Qdrant is excellent for semantic search."),
            HumanMessage(content="I prefer structured output format"),
            AIMessage(content="The system must maintain backward compatibility"),
        ]

        result = await context_manager.extract_key_information_llm(messages)

        # Verify all categories are present
        assert "decisions" in result
        assert "requirements" in result
        assert "facts" in result
        assert "action_items" in result
        assert "issues" in result
        assert "preferences" in result

        # Verify content extraction
        assert len(result["decisions"]) == 2
        assert any("Qdrant" in d for d in result["decisions"])
        assert any("embedding model" in d for d in result["decisions"])

        assert len(result["requirements"]) == 2
        assert any("semantic search" in r for r in result["requirements"])

        assert len(result["facts"]) == 2
        assert any("6333" in f for f in result["facts"])

        assert len(result["action_items"]) == 2
        assert any("unit tests" in a for a in result["action_items"])

        assert len(result["issues"]) == 1
        assert any("timeout" in i for i in result["issues"])

        assert len(result["preferences"]) == 1
        assert any("structured output" in p for p in result["preferences"])

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extract_key_information_llm_empty_categories(self, context_manager):
        """Test extraction when some categories are empty"""

        # Mock LLM to return response with "None" for some categories
        async def mock_ainvoke_empty(prompt):
            response = MagicMock()
            response.content = """DECISIONS:
- Use Python 3.11

REQUIREMENTS:
- None

FACTS:
- None

ACTION_ITEMS:
- Write tests

ISSUES:
- None

PREFERENCES:
- None
"""
            return response

        context_manager.llm.ainvoke = mock_ainvoke_empty

        messages = [
            HumanMessage(content="Let's use Python 3.11"),
            AIMessage(content="Sure, I'll write tests for that"),
        ]

        result = await context_manager.extract_key_information_llm(messages)

        # Verify only populated categories have items
        assert len(result["decisions"]) == 1
        assert len(result["requirements"]) == 0  # "None" should be filtered out
        assert len(result["facts"]) == 0
        assert len(result["action_items"]) == 1
        assert len(result["issues"]) == 0
        assert len(result["preferences"]) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extract_key_information_llm_fallback_on_error(self, context_manager):
        """Test fallback to rule-based extraction on LLM error"""
        # Make LLM raise an exception
        context_manager.llm.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        messages = [
            HumanMessage(content="We decided to use Redis for caching"),
            AIMessage(content="That's a good decision for performance"),
            HumanMessage(content="There's an error in the connection handling"),
        ]

        # Should fall back to rule-based extraction
        result = await context_manager.extract_key_information_llm(messages)

        # Verify fallback still returns valid structure
        assert "decisions" in result
        assert "requirements" in result
        assert "facts" in result
        assert "action_items" in result
        assert "issues" in result
        assert "preferences" in result

        # Rule-based extraction should find the decision keyword
        assert len(result["decisions"]) > 0
        # And the error keyword
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_extraction_response(self, context_manager):
        """Test parsing of LLM extraction response"""
        response_text = """Here is the analysis:

DECISIONS:
- Use microservices architecture
- Deploy on Kubernetes

REQUIREMENTS:
- High availability (99.9% uptime)
- Support 10K concurrent users

FACTS:
- Current load is 1K users
- Database is PostgreSQL 14

ACTION_ITEMS:
- Set up monitoring dashboards
- Configure auto-scaling

ISSUES:
- Memory leak in worker process
- Slow query on users table

PREFERENCES:
- Prefer REST over GraphQL for APIs
"""

        result = context_manager._parse_extraction_response(response_text)

        # Verify all categories parsed correctly
        assert len(result["decisions"]) == 2
        assert "microservices" in result["decisions"][0]

        assert len(result["requirements"]) == 2
        assert "99.9%" in result["requirements"][0]

        assert len(result["facts"]) == 2
        assert "PostgreSQL" in result["facts"][1]

        assert len(result["action_items"]) == 2
        assert "monitoring" in result["action_items"][0]

        assert len(result["issues"]) == 2
        assert "Memory leak" in result["issues"][0]

        assert len(result["preferences"]) == 1
        assert "REST" in result["preferences"][0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parse_extraction_multiline_items(self, context_manager):
        """Test parsing multi-line items (should handle gracefully)"""
        response_text = """DECISIONS:
- Use PostgreSQL for primary database
  with connection pooling enabled

REQUIREMENTS:
- Support data export to CSV
  and JSON formats

FACTS:
- None

ACTION_ITEMS:
- Review security policies

ISSUES:
- None

PREFERENCES:
- None
"""

        result = context_manager._parse_extraction_response(response_text)

        # First line of multi-line items should be captured
        assert len(result["decisions"]) == 1
        assert "PostgreSQL" in result["decisions"][0]

        assert len(result["requirements"]) == 1
        assert "CSV" in result["requirements"][0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extract_prompt_format(self, context_manager, mock_llm):
        """Test that extraction prompt follows XML structure"""
        messages = [
            HumanMessage(content="Test message"),
        ]

        await context_manager.extract_key_information_llm(messages)

        # Verify LLM was called
        assert mock_llm.ainvoke.called

        # Get the prompt that was passed
        call_args = mock_llm.ainvoke.call_args
        prompt_messages = call_args[0][0]
        # Extract the content from the HumanMessage
        prompt = prompt_messages[0].content if isinstance(prompt_messages, list) else prompt_messages.content

        # Verify XML structure
        assert "<task>" in prompt
        assert "</task>" in prompt
        assert "<categories>" in prompt
        assert "</categories>" in prompt
        assert "<conversation>" in prompt
        assert "</conversation>" in prompt
        assert "<instructions>" in prompt
        assert "</instructions>" in prompt
        assert "<output_format>" in prompt
        assert "</output_format>" in prompt

        # Verify all 6 categories are mentioned
        assert "DECISIONS:" in prompt
        assert "REQUIREMENTS:" in prompt
        assert "FACTS:" in prompt
        assert "ACTION_ITEMS:" in prompt
        assert "ISSUES:" in prompt
        assert "PREFERENCES:" in prompt

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extraction_categories_complete(self, context_manager):
        """Test that all 6 categories are extracted"""
        response_text = """DECISIONS:
- Item 1

REQUIREMENTS:
- Item 2

FACTS:
- Item 3

ACTION_ITEMS:
- Item 4

ISSUES:
- Item 5

PREFERENCES:
- Item 6
"""

        result = context_manager._parse_extraction_response(response_text)

        # All 6 categories should have exactly 1 item
        assert len(result["decisions"]) == 1
        assert len(result["requirements"]) == 1
        assert len(result["facts"]) == 1
        assert len(result["action_items"]) == 1
        assert len(result["issues"]) == 1
        assert len(result["preferences"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extraction_case_insensitive_headers(self, context_manager):
        """Test that category headers are case-insensitive"""
        response_text = """decisions:
- Lower case header

REQUIREMENTS:
- Upper case header

Facts:
- Title case header

action items:
- Lower with space

ISSUES:
- Standard

preferences:
- Mixed
"""

        result = context_manager._parse_extraction_response(response_text)

        # Should parse all regardless of case
        assert len(result["decisions"]) == 1
        assert len(result["requirements"]) == 1
        assert len(result["facts"]) == 1
        assert len(result["action_items"]) == 1
        assert len(result["issues"]) == 1
        assert len(result["preferences"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extract_with_system_messages(self, context_manager, mock_llm):
        """Test extraction works with system messages in conversation"""
        messages = [
            SystemMessage(content="You are a helpful assistant"),
            HumanMessage(content="We decided to implement feature X"),
            AIMessage(content="Good choice, I'll help with that"),
            HumanMessage(content="We need to ensure security compliance"),
        ]

        result = await context_manager.extract_key_information_llm(messages)

        # Should extract from all message types
        assert len(result["decisions"]) > 0
        assert len(result["requirements"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extraction_metrics_logged(self, context_manager, mock_llm):
        """Test that extraction logs metrics"""
        with patch("mcp_server_langgraph.core.context_manager.metrics") as mock_metrics:
            messages = [
                HumanMessage(content="Test extraction"),
            ]

            await context_manager.extract_key_information_llm(messages)

            # Verify success metric was recorded
            mock_metrics.successful_calls.add.assert_called_once_with(1, {"operation": "extract_key_info_llm"})

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_extraction_error_metrics_logged(self, context_manager):
        """Test that extraction errors are logged in metrics"""
        context_manager.llm.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        with patch("mcp_server_langgraph.core.context_manager.metrics") as mock_metrics:
            messages = [HumanMessage(content="Test")]

            # Should fall back without raising
            result = await context_manager.extract_key_information_llm(messages)

            # Verify failure metric was recorded
            mock_metrics.failed_calls.add.assert_called_once_with(1, {"operation": "extract_key_info_llm"})

            # But still returns valid result (fallback)
            assert "decisions" in result


@pytest.mark.xdist_group(name="context_manager_llm_tests")
class TestRuleBasedExtraction:
    """Test suite for rule-based extraction (fallback)"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_extract_key_information_decisions(self):
        """Test rule-based extraction of decisions"""
        manager = ContextManager()

        messages = [
            HumanMessage(content="We decided to use PostgreSQL"),
            AIMessage(content="That's agreed upon"),
            HumanMessage(content="We chose Docker for deployment"),
        ]

        result = manager.extract_key_information(messages)

        assert len(result["decisions"]) >= 2
        assert any("PostgreSQL" in d for d in result["decisions"])
        assert any("Docker" in d for d in result["decisions"])

    @pytest.mark.unit
    def test_extract_key_information_requirements(self):
        """Test rule-based extraction of requirements"""
        manager = ContextManager()

        messages = [
            HumanMessage(content="The system must support 10K users"),
            AIMessage(content="We need high availability"),
            HumanMessage(content="Performance should be sub-100ms"),
        ]

        result = manager.extract_key_information(messages)

        assert len(result["requirements"]) >= 3

    @pytest.mark.unit
    def test_extract_key_information_issues(self):
        """Test rule-based extraction of issues"""
        manager = ContextManager()

        messages = [
            HumanMessage(content="There's an error in the login flow"),
            AIMessage(content="The database connection failed"),
            HumanMessage(content="We have a problem with the cache"),
        ]

        result = manager.extract_key_information(messages)

        assert len(result["issues"]) >= 3

    @pytest.mark.unit
    def test_extract_key_information_truncation(self):
        """Test that extracted items are truncated to 200 chars"""
        manager = ContextManager()

        long_message = "We decided to " + ("x" * 300)  # 313 chars total
        messages = [HumanMessage(content=long_message)]

        result = manager.extract_key_information(messages)

        # Should be truncated to 200 chars
        assert all(len(item) <= 200 for item in result["decisions"])


@pytest.mark.integration
@pytest.mark.xdist_group(name="context_manager_llm_tests")
class TestContextManagerLLMIntegration:
    """Integration tests for LLM extraction"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="Requires ANTHROPIC_API_KEY")
    @pytest.mark.asyncio
    async def test_full_extraction_workflow(self):
        """
        Test complete extraction workflow with real LLM.

        Runs only when ANTHROPIC_API_KEY environment variable is set.
        Tests the LLM-based extraction with actual API calls.
        """
        manager = ContextManager()

        messages = [
            HumanMessage(content="We've decided to implement a new caching layer using Redis"),
            AIMessage(content="That's a good decision for performance. We'll need to ensure it's properly configured."),
            HumanMessage(content="The system must support at least 100K requests per second"),
            AIMessage(content="I discovered that our current infrastructure can handle about 50K RPS"),
            HumanMessage(content="There's an issue with the connection pool exhaustion"),
            AIMessage(content="I prefer using connection pooling with a max of 100 connections"),
        ]

        result = await manager.extract_key_information_llm(messages)

        # Should extract from all categories
        assert len(result["decisions"]) > 0  # Redis caching
        assert len(result["requirements"]) > 0  # 100K RPS
        assert len(result["facts"]) > 0  # Current 50K RPS
        assert len(result["issues"]) > 0  # Connection pool exhaustion
        assert len(result["preferences"]) > 0  # Connection pooling preference
