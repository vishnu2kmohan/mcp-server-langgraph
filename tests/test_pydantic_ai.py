"""
Tests for Pydantic AI integration

Covers type-safe agent responses, validation, and streaming.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage

# Test fixtures
@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("pydantic_ai_agent.settings") as mock:
        mock.model_name = "gemini-2.5-flash-002"
        mock.llm_provider = "google"
        yield mock


@pytest.fixture
def mock_agent():
    """Mock Pydantic AI agent."""
    mock = Mock()
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_pydantic_agent_class():
    """Mock Pydantic AI Agent class to avoid API key requirements."""
    with patch("pydantic_ai_agent.Agent") as mock_agent_class:
        yield mock_agent_class


# Tests for PydanticAIAgentWrapper
@pytest.mark.unit
def test_pydantic_agent_wrapper_initialization(mock_settings, mock_pydantic_agent_class):
    """Test Pydantic AI agent wrapper initializes correctly."""
    from pydantic_ai_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper()

    assert wrapper.model_name == "gemini-2.5-flash-002"
    assert wrapper.provider == "google"
    assert wrapper.pydantic_model_name == "gemini-2.5-flash-002"


@pytest.mark.unit
def test_get_pydantic_model_name_google(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for Google provider."""
    from pydantic_ai_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper(provider="google")
    assert wrapper.pydantic_model_name == "gemini-2.5-flash-002"


@pytest.mark.unit
def test_get_pydantic_model_name_anthropic(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for Anthropic provider."""
    from pydantic_ai_agent import PydanticAIAgentWrapper

    mock_settings.llm_provider = "anthropic"
    mock_settings.model_name = "claude-3-5-sonnet-20241022"

    wrapper = PydanticAIAgentWrapper(
        provider="anthropic",
        model_name="claude-3-5-sonnet-20241022"
    )

    assert wrapper.pydantic_model_name == "anthropic:claude-3-5-sonnet-20241022"


@pytest.mark.unit
def test_get_pydantic_model_name_openai(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for OpenAI provider."""
    from pydantic_ai_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper(
        provider="openai",
        model_name="gpt-4o"
    )

    assert wrapper.pydantic_model_name == "openai:gpt-4o"


@pytest.mark.unit
def test_format_conversation(mock_settings, mock_pydantic_agent_class):
    """Test conversation formatting."""
    from pydantic_ai_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper()

    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
        HumanMessage(content="How are you?")
    ]

    formatted = wrapper._format_conversation(messages)

    assert "User: Hello" in formatted
    assert "Assistant: Hi there!" in formatted
    assert "User: How are you?" in formatted


# Tests for RouterDecision
@pytest.mark.unit
def test_router_decision_model():
    """Test RouterDecision Pydantic model."""
    from pydantic_ai_agent import RouterDecision

    decision = RouterDecision(
        action="use_tools",
        reasoning="User requested a search",
        tool_name="search",
        confidence=0.9
    )

    assert decision.action == "use_tools"
    assert decision.reasoning == "User requested a search"
    assert decision.tool_name == "search"
    assert decision.confidence == 0.9


@pytest.mark.unit
def test_router_decision_validation():
    """Test RouterDecision validates confidence range."""
    from pydantic_ai_agent import RouterDecision
    from pydantic import ValidationError

    # Valid confidence
    decision = RouterDecision(
        action="respond",
        reasoning="Direct answer",
        confidence=0.5
    )
    assert decision.confidence == 0.5

    # Invalid confidence (too high)
    with pytest.raises(ValidationError):
        RouterDecision(
            action="respond",
            reasoning="Direct answer",
            confidence=1.5  # > 1.0
        )

    # Invalid confidence (too low)
    with pytest.raises(ValidationError):
        RouterDecision(
            action="respond",
            reasoning="Direct answer",
            confidence=-0.1  # < 0.0
        )


# Tests for AgentResponse
@pytest.mark.unit
def test_agent_response_model():
    """Test AgentResponse Pydantic model."""
    from pydantic_ai_agent import AgentResponse

    response = AgentResponse(
        content="Here is your answer",
        confidence=0.85,
        requires_clarification=False,
        sources=["source1", "source2"],
        metadata={"key": "value"}
    )

    assert response.content == "Here is your answer"
    assert response.confidence == 0.85
    assert not response.requires_clarification
    assert len(response.sources) == 2
    assert response.metadata["key"] == "value"


@pytest.mark.unit
def test_agent_response_defaults():
    """Test AgentResponse has sensible defaults."""
    from pydantic_ai_agent import AgentResponse

    response = AgentResponse(
        content="Simple response",
        confidence=0.7
    )

    assert response.requires_clarification is False
    assert response.clarification_question is None
    assert response.sources == []
    assert response.metadata == {}


# Tests for LLM Validators
@pytest.mark.unit
def test_validated_response():
    """Test ValidatedResponse container."""
    from llm_validators import ValidatedResponse
    from pydantic_ai_agent import AgentResponse

    data = AgentResponse(content="test", confidence=0.9)

    validated = ValidatedResponse(
        data=data,
        raw_content="test content",
        validation_success=True
    )

    assert validated.is_valid()
    assert validated.data.content == "test"
    assert validated.raw_content == "test content"
    assert len(validated.get_errors()) == 0


@pytest.mark.unit
def test_validated_response_with_errors():
    """Test ValidatedResponse with errors."""
    from llm_validators import ValidatedResponse

    validated = ValidatedResponse(
        data=None,
        raw_content="invalid",
        validation_success=False,
        validation_errors=["Error 1", "Error 2"]
    )

    assert not validated.is_valid()
    assert len(validated.get_errors()) == 2
    assert "Error 1" in validated.get_errors()


@pytest.mark.unit
def test_entity_extraction_model():
    """Test EntityExtraction model."""
    from llm_validators import EntityExtraction

    extraction = EntityExtraction(
        entities=[
            {"type": "person", "value": "John"},
            {"type": "organization", "value": "Acme Corp"}
        ],
        confidence=0.95
    )

    assert len(extraction.entities) == 2
    assert extraction.confidence == 0.95
    assert extraction.entities[0]["type"] == "person"


@pytest.mark.unit
def test_intent_classification_model():
    """Test IntentClassification model."""
    from llm_validators import IntentClassification

    intent = IntentClassification(
        intent="search_query",
        confidence=0.88,
        sub_intents=["general_search", "product_search"],
        parameters={"query": "best laptops", "category": "electronics"}
    )

    assert intent.intent == "search_query"
    assert intent.confidence == 0.88
    assert len(intent.sub_intents) == 2
    assert intent.parameters["query"] == "best laptops"


@pytest.mark.unit
def test_sentiment_analysis_model():
    """Test SentimentAnalysis model."""
    from llm_validators import SentimentAnalysis

    sentiment = SentimentAnalysis(
        sentiment="positive",
        score=0.75,
        emotions=["joy", "excitement"]
    )

    assert sentiment.sentiment == "positive"
    assert sentiment.score == 0.75
    assert "joy" in sentiment.emotions


@pytest.mark.unit
def test_summary_extraction_model():
    """Test SummaryExtraction model."""
    from llm_validators import SummaryExtraction

    summary = SummaryExtraction(
        summary="This is a summary",
        key_points=["Point 1", "Point 2", "Point 3"],
        length=19,
        compression_ratio=0.25
    )

    assert summary.summary == "This is a summary"
    assert len(summary.key_points) == 3
    assert summary.length == 19
    assert summary.compression_ratio == 0.25


# Tests for Streaming
@pytest.mark.unit
def test_stream_chunk_model():
    """Test StreamChunk model."""
    from mcp_streaming import StreamChunk

    chunk = StreamChunk(
        content="Hello",
        chunk_index=0,
        is_final=False,
        metadata={"stream_id": "test"}
    )

    assert chunk.content == "Hello"
    assert chunk.chunk_index == 0
    assert not chunk.is_final
    assert chunk.metadata["stream_id"] == "test"


@pytest.mark.unit
def test_streamed_response_model():
    """Test StreamedResponse model."""
    from mcp_streaming import StreamedResponse, StreamChunk

    chunks = [
        StreamChunk(content="Hello", chunk_index=0, is_final=False),
        StreamChunk(content=" world", chunk_index=1, is_final=True)
    ]

    response = StreamedResponse(
        chunks=chunks,
        total_length=11,
        chunk_count=2,
        is_complete=True
    )

    assert response.total_length == 11
    assert response.chunk_count == 2
    assert response.is_complete
    assert response.get_full_content() == "Hello world"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_validator():
    """Test MCPStreamingValidator."""
    from mcp_streaming import MCPStreamingValidator

    validator = MCPStreamingValidator()

    # Validate first chunk
    chunk1 = await validator.validate_chunk(
        {"content": "Hello", "chunk_index": 0, "is_final": False},
        "stream-1"
    )

    assert chunk1 is not None
    assert chunk1.content == "Hello"
    assert chunk1.chunk_index == 0

    # Validate second chunk
    chunk2 = await validator.validate_chunk(
        {"content": " world", "chunk_index": 1, "is_final": True},
        "stream-1"
    )

    assert chunk2 is not None
    assert chunk2.content == " world"
    assert chunk2.is_final

    # Finalize stream
    response = await validator.finalize_stream("stream-1")

    assert response.is_complete
    assert response.chunk_count == 2
    assert response.get_full_content() == "Hello world"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_validated_response():
    """Test stream_validated_response function."""
    from mcp_streaming import stream_validated_response
    import json

    content = "Test content"
    chunks = []

    async for chunk_json in stream_validated_response(content, chunk_size=5, stream_id="test"):
        chunk_data = json.loads(chunk_json.strip())
        chunks.append(chunk_data)

    assert len(chunks) > 0

    # Check first chunk
    first_chunk = chunks[0]
    assert first_chunk["chunk_index"] == 0
    assert not first_chunk["is_final"]

    # Check last chunk
    last_chunk = chunks[-1]
    assert last_chunk["is_final"]

    # Reconstruct content
    full_content = "".join(c["content"] for c in chunks)
    assert full_content == content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_with_pydantic_routing():
    """Test agent with Pydantic AI routing (integration test)."""
    # This would require actual Pydantic AI agent
    # Skipped in unit tests, run with -m integration
    pytest.skip("Requires Pydantic AI agent initialization")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_response_generation():
    """Test agent response generation with Pydantic AI."""
    # This would require actual LLM calls
    # Skipped in unit tests, run with -m integration
    pytest.skip("Requires live LLM connection")
