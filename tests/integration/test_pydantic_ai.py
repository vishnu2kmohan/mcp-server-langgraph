"""
Tests for Pydantic AI integration

Covers type-safe agent responses, validation, and streaming.
"""

import gc
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage


# Test fixtures
@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("mcp_server_langgraph.llm.pydantic_agent.settings") as mock:
        mock.model_name = "gemini-2.5-flash"
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
    with patch("mcp_server_langgraph.llm.pydantic_agent.Agent") as mock_agent_class:
        yield mock_agent_class


# Tests for PydanticAIAgentWrapper
@pytest.mark.unit
def test_pydantic_agent_wrapper_initialization(mock_settings, mock_pydantic_agent_class):
    """Test Pydantic AI agent wrapper initializes correctly."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper()

    assert wrapper.model_name == "gemini-2.5-flash"
    assert wrapper.provider == "google"
    assert wrapper.pydantic_model_name == "google-gla:gemini-2.5-flash"


@pytest.mark.unit
def test_get_pydantic_model_name_google(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for Google provider."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper(provider="google")
    assert wrapper.pydantic_model_name == "google-gla:gemini-2.5-flash"


@pytest.mark.unit
def test_get_pydantic_model_name_anthropic(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for Anthropic provider."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    mock_settings.llm_provider = "anthropic"
    mock_settings.model_name = "claude-3-5-sonnet-20241022"

    wrapper = PydanticAIAgentWrapper(provider="anthropic", model_name="claude-3-5-sonnet-20241022")

    assert wrapper.pydantic_model_name == "anthropic:claude-3-5-sonnet-20241022"


@pytest.mark.unit
def test_get_pydantic_model_name_openai(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for OpenAI provider."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper(provider="openai", model_name="gpt-5")

    assert wrapper.pydantic_model_name == "openai:gpt-5"


@pytest.mark.unit
def test_get_pydantic_model_name_gemini(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for Gemini provider (alternative name for google)."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper(provider="gemini", model_name="gemini-2.5-pro")

    assert wrapper.pydantic_model_name == "google-gla:gemini-2.5-pro"


@pytest.mark.unit
def test_get_pydantic_model_name_unknown_provider(mock_settings, mock_pydantic_agent_class):
    """Test model name mapping for unknown provider falls back to model name."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper(provider="unknown", model_name="some-model")

    # Unknown providers get provider:model prefix format (pydantic-ai v0.0.14+ requirement)
    assert wrapper.pydantic_model_name == "unknown:some-model"


@pytest.mark.unit
def test_format_conversation(mock_settings, mock_pydantic_agent_class):
    """Test conversation formatting."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper()

    messages = [HumanMessage(content="Hello"), AIMessage(content="Hi there!"), HumanMessage(content="How are you?")]

    formatted = wrapper._format_conversation(messages)

    assert "User: Hello" in formatted
    assert "Assistant: Hi there!" in formatted
    assert "User: How are you?" in formatted


@pytest.mark.unit
def test_format_conversation_with_system_message(mock_settings, mock_pydantic_agent_class):
    """Test conversation formatting with system messages."""
    from langchain_core.messages import SystemMessage

    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    wrapper = PydanticAIAgentWrapper()

    messages = [
        SystemMessage(content="You are a helpful assistant"),
        HumanMessage(content="Hello"),
        AIMessage(content="Hi!"),
    ]

    formatted = wrapper._format_conversation(messages)

    assert "System: You are a helpful assistant" in formatted
    assert "User: Hello" in formatted
    assert "Assistant: Hi!" in formatted


# Tests for route_message method
@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_message_success(mock_settings, mock_pydantic_agent_class):
    """Test successful message routing."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper, RouterDecision

    # Mock agent response
    mock_result = Mock()
    mock_result.data = RouterDecision(action="use_tools", reasoning="User wants to search", tool_name="search", confidence=0.9)

    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=mock_result)
    mock_pydantic_agent_class.return_value = mock_agent_instance

    wrapper = PydanticAIAgentWrapper()
    wrapper.router_agent = mock_agent_instance

    decision = await wrapper.route_message("Find me information about Python")

    assert decision.action == "use_tools"
    assert decision.tool_name == "search"
    assert decision.confidence == 0.9
    assert "search" in decision.reasoning.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_message_with_context(mock_settings, mock_pydantic_agent_class):
    """Test message routing with context."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper, RouterDecision

    mock_result = Mock()
    mock_result.data = RouterDecision(action="respond", reasoning="Direct answer", confidence=0.95)

    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=mock_result)
    mock_pydantic_agent_class.return_value = mock_agent_instance

    wrapper = PydanticAIAgentWrapper()
    wrapper.router_agent = mock_agent_instance

    context = {"user_tier": "premium", "previous_action": "search"}
    decision = await wrapper.route_message("What did you find?", context=context)  # noqa: F841

    # Verify context was included in the prompt
    call_args = mock_agent_instance.run.call_args
    prompt = call_args[0][0]
    assert "user_tier" in prompt
    assert "premium" in prompt
    assert "What did you find?" in prompt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_message_error_handling(mock_settings, mock_pydantic_agent_class):
    """Test route_message handles errors gracefully."""
    pytest.importorskip("pydantic_ai", reason="pydantic-ai is an optional dependency")
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    # Mock agent that raises an error
    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(side_effect=Exception("API error"))
    mock_pydantic_agent_class.return_value = mock_agent_instance

    wrapper = PydanticAIAgentWrapper()
    wrapper.router_agent = mock_agent_instance

    with pytest.raises(Exception) as exc_info:
        await wrapper.route_message("test message")

    assert "API error" in str(exc_info.value)


# Tests for generate_response method
@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_response_success(mock_settings, mock_pydantic_agent_class):
    """Test successful response generation."""
    from mcp_server_langgraph.llm.pydantic_agent import AgentResponse, PydanticAIAgentWrapper

    # Mock agent response
    mock_result = Mock()
    mock_result.data = AgentResponse(
        content="Here is your answer about Python",
        confidence=0.88,
        requires_clarification=False,
        sources=["python.org", "docs.python.org"],
    )

    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=mock_result)
    mock_pydantic_agent_class.return_value = mock_agent_instance

    wrapper = PydanticAIAgentWrapper()
    wrapper.response_agent = mock_agent_instance

    messages = [HumanMessage(content="Tell me about Python")]
    response = await wrapper.generate_response(messages)

    assert "Python" in response.content
    assert response.confidence == 0.88
    assert not response.requires_clarification
    assert len(response.sources) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_response_with_context(mock_settings, mock_pydantic_agent_class):
    """Test response generation with context."""
    from mcp_server_langgraph.llm.pydantic_agent import AgentResponse, PydanticAIAgentWrapper

    mock_result = Mock()
    mock_result.data = AgentResponse(content="Context-aware response", confidence=0.9)

    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=mock_result)
    mock_pydantic_agent_class.return_value = mock_agent_instance

    wrapper = PydanticAIAgentWrapper()
    wrapper.response_agent = mock_agent_instance

    messages = [HumanMessage(content="Test")]
    context = {"conversation_id": "conv-123", "user_preferences": {"verbosity": "concise"}}

    response = await wrapper.generate_response(messages, context=context)  # noqa: F841

    # Verify context was included
    call_args = mock_agent_instance.run.call_args
    prompt = call_args[0][0]
    assert "conversation_id" in prompt
    assert "conv-123" in prompt


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_response_requires_clarification(mock_settings, mock_pydantic_agent_class):
    """Test response generation when clarification is needed."""
    from mcp_server_langgraph.llm.pydantic_agent import AgentResponse, PydanticAIAgentWrapper

    mock_result = Mock()
    mock_result.data = AgentResponse(
        content="I need more information",
        confidence=0.5,
        requires_clarification=True,
        clarification_question="Which Python version are you asking about?",
    )

    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(return_value=mock_result)
    mock_pydantic_agent_class.return_value = mock_agent_instance

    wrapper = PydanticAIAgentWrapper()
    wrapper.response_agent = mock_agent_instance

    messages = [HumanMessage(content="How do I install Python?")]
    response = await wrapper.generate_response(messages)

    assert response.requires_clarification
    assert response.clarification_question is not None
    assert "version" in response.clarification_question.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_response_error_handling(mock_settings, mock_pydantic_agent_class):
    """Test generate_response handles errors."""
    from mcp_server_langgraph.llm.pydantic_agent import PydanticAIAgentWrapper

    mock_agent_instance = Mock()
    mock_agent_instance.run = AsyncMock(side_effect=Exception("LLM timeout"))
    mock_pydantic_agent_class.return_value = mock_agent_instance

    wrapper = PydanticAIAgentWrapper()
    wrapper.response_agent = mock_agent_instance

    with pytest.raises(Exception) as exc_info:
        await wrapper.generate_response([HumanMessage(content="test")])

    assert "LLM timeout" in str(exc_info.value)


# Tests for create_pydantic_agent factory
@pytest.mark.unit
def test_create_pydantic_agent_factory(mock_settings, mock_pydantic_agent_class):
    """Test create_pydantic_agent factory function."""
    pytest.importorskip("pydantic_ai", reason="pydantic-ai is an optional dependency")
    from mcp_server_langgraph.llm.pydantic_agent import create_pydantic_agent

    agent = create_pydantic_agent()

    assert agent is not None
    assert agent.provider == "google"


@pytest.mark.unit
def test_create_pydantic_agent_custom_params(mock_settings, mock_pydantic_agent_class):
    """Test create_pydantic_agent with custom parameters."""
    pytest.importorskip("pydantic_ai", reason="pydantic-ai is an optional dependency")
    from mcp_server_langgraph.llm.pydantic_agent import create_pydantic_agent

    agent = create_pydantic_agent(provider="anthropic", model_name="claude-opus-4-1-20250805")

    assert agent.provider == "anthropic"
    assert agent.model_name == "claude-opus-4-1-20250805"


@pytest.mark.unit
def test_create_pydantic_agent_unavailable():
    """Test create_pydantic_agent when pydantic-ai is not available."""
    from mcp_server_langgraph.llm import pydantic_agent

    # Temporarily set PYDANTIC_AI_AVAILABLE to False
    original_value = pydantic_agent.PYDANTIC_AI_AVAILABLE
    pydantic_agent.PYDANTIC_AI_AVAILABLE = False

    try:
        with pytest.raises(ImportError) as exc_info:
            pydantic_agent.create_pydantic_agent()

        assert "pydantic-ai is not installed" in str(exc_info.value)
    finally:
        # Restore original value
        pydantic_agent.PYDANTIC_AI_AVAILABLE = original_value


# Tests for RouterDecision
@pytest.mark.unit
def test_router_decision_model():
    """Test RouterDecision Pydantic model."""
    from mcp_server_langgraph.llm.pydantic_agent import RouterDecision

    decision = RouterDecision(action="use_tools", reasoning="User requested a search", tool_name="search", confidence=0.9)

    assert decision.action == "use_tools"
    assert decision.reasoning == "User requested a search"
    assert decision.tool_name == "search"
    assert decision.confidence == 0.9


@pytest.mark.unit
def test_router_decision_validation():
    """Test RouterDecision validates confidence range."""
    from pydantic import ValidationError

    from mcp_server_langgraph.llm.pydantic_agent import RouterDecision

    # Valid confidence
    decision = RouterDecision(action="respond", reasoning="Direct answer", confidence=0.5)
    assert decision.confidence == 0.5

    # Invalid confidence (too high)
    with pytest.raises(ValidationError):
        RouterDecision(action="respond", reasoning="Direct answer", confidence=1.5)  # > 1.0

    # Invalid confidence (too low)
    with pytest.raises(ValidationError):
        RouterDecision(action="respond", reasoning="Direct answer", confidence=-0.1)  # < 0.0


# Tests for AgentResponse
@pytest.mark.unit
def test_agent_response_model():
    """Test AgentResponse Pydantic model."""
    from mcp_server_langgraph.llm.pydantic_agent import AgentResponse

    response = AgentResponse(
        content="Here is your answer",
        confidence=0.85,
        requires_clarification=False,
        sources=["source1", "source2"],
        metadata={"key": "value"},
    )

    assert response.content == "Here is your answer"
    assert response.confidence == 0.85
    assert not response.requires_clarification
    assert len(response.sources) == 2
    assert response.metadata["key"] == "value"


@pytest.mark.unit
def test_agent_response_defaults():
    """Test AgentResponse has sensible defaults."""
    from mcp_server_langgraph.llm.pydantic_agent import AgentResponse

    response = AgentResponse(content="Simple response", confidence=0.7)

    assert response.requires_clarification is False
    assert response.clarification_question is None
    assert response.sources == []
    assert response.metadata == {}


# Tests for LLM Validators
@pytest.mark.unit
def test_validated_response():
    """Test ValidatedResponse container."""
    from mcp_server_langgraph.llm.pydantic_agent import AgentResponse
    from mcp_server_langgraph.llm.validators import ValidatedResponse

    data = AgentResponse(content="test", confidence=0.9)

    validated = ValidatedResponse(data=data, raw_content="test content", validation_success=True)

    assert validated.is_valid()
    assert validated.data.content == "test"
    assert validated.raw_content == "test content"
    assert len(validated.get_errors()) == 0


@pytest.mark.unit
def test_validated_response_with_errors():
    """Test ValidatedResponse with errors."""
    from mcp_server_langgraph.llm.validators import ValidatedResponse

    validated = ValidatedResponse(
        data=None, raw_content="invalid", validation_success=False, validation_errors=["Error 1", "Error 2"]
    )

    assert not validated.is_valid()
    assert len(validated.get_errors()) == 2
    assert "Error 1" in validated.get_errors()


@pytest.mark.unit
def test_entity_extraction_model():
    """Test EntityExtraction model."""
    from mcp_server_langgraph.llm.validators import EntityExtraction

    extraction = EntityExtraction(
        entities=[{"type": "person", "value": "John"}, {"type": "organization", "value": "Acme Corp"}], confidence=0.95
    )

    assert len(extraction.entities) == 2
    assert extraction.confidence == 0.95
    assert extraction.entities[0]["type"] == "person"


@pytest.mark.unit
def test_intent_classification_model():
    """Test IntentClassification model."""
    from mcp_server_langgraph.llm.validators import IntentClassification

    intent = IntentClassification(
        intent="search_query",
        confidence=0.88,
        sub_intents=["general_search", "product_search"],
        parameters={"query": "best laptops", "category": "electronics"},
    )

    assert intent.intent == "search_query"
    assert intent.confidence == 0.88
    assert len(intent.sub_intents) == 2
    assert intent.parameters["query"] == "best laptops"


@pytest.mark.unit
def test_sentiment_analysis_model():
    """Test SentimentAnalysis model."""
    from mcp_server_langgraph.llm.validators import SentimentAnalysis

    sentiment = SentimentAnalysis(sentiment="positive", score=0.75, emotions=["joy", "excitement"])

    assert sentiment.sentiment == "positive"
    assert sentiment.score == 0.75
    assert "joy" in sentiment.emotions


@pytest.mark.unit
def test_summary_extraction_model():
    """Test SummaryExtraction model."""
    from mcp_server_langgraph.llm.validators import SummaryExtraction

    summary = SummaryExtraction(
        summary="This is a summary", key_points=["Point 1", "Point 2", "Point 3"], length=19, compression_ratio=0.25
    )

    assert summary.summary == "This is a summary"
    assert len(summary.key_points) == 3
    assert summary.length == 19
    assert summary.compression_ratio == 0.25


# Tests for Streaming
@pytest.mark.unit
def test_stream_chunk_model():
    """Test StreamChunk model."""
    from mcp_server_langgraph.mcp.streaming import StreamChunk

    chunk = StreamChunk(content="Hello", chunk_index=0, is_final=False, metadata={"stream_id": "test"})

    assert chunk.content == "Hello"
    assert chunk.chunk_index == 0
    assert not chunk.is_final
    assert chunk.metadata["stream_id"] == "test"


@pytest.mark.unit
def test_streamed_response_model():
    """Test StreamedResponse model."""
    from mcp_server_langgraph.mcp.streaming import StreamChunk, StreamedResponse

    chunks = [
        StreamChunk(content="Hello", chunk_index=0, is_final=False),
        StreamChunk(content=" world", chunk_index=1, is_final=True),
    ]

    response = StreamedResponse(chunks=chunks, total_length=11, chunk_count=2, is_complete=True)

    assert response.total_length == 11
    assert response.chunk_count == 2
    assert response.is_complete
    assert response.get_full_content() == "Hello world"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_validator():
    """Test MCPStreamingValidator."""
    from mcp_server_langgraph.mcp.streaming import MCPStreamingValidator

    validator = MCPStreamingValidator()

    # Validate first chunk
    chunk1 = await validator.validate_chunk({"content": "Hello", "chunk_index": 0, "is_final": False}, "stream-1")

    assert chunk1 is not None
    assert chunk1.content == "Hello"
    assert chunk1.chunk_index == 0

    # Validate second chunk
    chunk2 = await validator.validate_chunk({"content": " world", "chunk_index": 1, "is_final": True}, "stream-1")

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
    import json

    from mcp_server_langgraph.mcp.streaming import stream_validated_response

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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_validator_validation_error():
    """Test MCPStreamingValidator with validation error."""
    from mcp_server_langgraph.mcp.streaming import MCPStreamingValidator

    validator = MCPStreamingValidator()

    # Invalid chunk data (missing required fields)
    invalid_chunk = {"content": "test"}  # Missing chunk_index and is_final

    result = await validator.validate_chunk(invalid_chunk, "stream-error")

    # Should return None on validation error
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streaming_validator_finalize_unknown_stream():
    """Test finalizing an unknown stream."""
    from mcp_server_langgraph.mcp.streaming import MCPStreamingValidator

    validator = MCPStreamingValidator()

    # Finalize a stream that was never created
    response = await validator.finalize_stream("unknown-stream")

    # Should return incomplete response with error
    assert not response.is_complete
    assert response.chunk_count == 0
    assert len(response.chunks) == 0
    assert response.error_message == "Stream not found"


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


# Tests for LLMValidator.validate_response
@pytest.mark.unit
def test_llm_validator_with_json_response():
    """Test LLMValidator.validate_response with JSON input."""
    import json

    from mcp_server_langgraph.llm.validators import EntityExtraction, LLMValidator

    response_data = {"entities": [{"type": "person", "value": "Alice"}], "confidence": 0.95}
    json_response = json.dumps(response_data)

    validated = LLMValidator.validate_response(json_response, EntityExtraction, strict=False)

    assert validated.is_valid()
    assert validated.data.confidence == 0.95
    assert len(validated.data.entities) == 1


@pytest.mark.unit
def test_llm_validator_with_aimessage():
    """Test LLMValidator.validate_response with AIMessage."""
    import json

    from langchain_core.messages import AIMessage

    from mcp_server_langgraph.llm.validators import LLMValidator, SentimentAnalysis

    response_data = {"sentiment": "positive", "score": 0.8, "emotions": ["joy"]}
    message = AIMessage(content=json.dumps(response_data))

    validated = LLMValidator.validate_response(message, SentimentAnalysis, strict=False)

    assert validated.is_valid()
    assert validated.data.sentiment == "positive"
    assert validated.data.score == 0.8


@pytest.mark.unit
def test_llm_validator_validation_error_non_strict():
    """Test LLMValidator.validate_response with validation error in non-strict mode."""
    from mcp_server_langgraph.llm.validators import EntityExtraction, LLMValidator

    # Invalid JSON
    invalid_response = "not valid json"

    validated = LLMValidator.validate_response(invalid_response, EntityExtraction, strict=False)

    assert not validated.is_valid()
    assert len(validated.get_errors()) > 0


@pytest.mark.unit
def test_llm_validator_validation_error_strict():
    """Test LLMValidator.validate_response with validation error in strict mode."""
    from mcp_server_langgraph.llm.validators import EntityExtraction, LLMValidator

    invalid_response = "not valid json"

    # In strict mode, it should raise ValueError for non-JSON, non-parseable content
    with pytest.raises(ValueError):
        LLMValidator.validate_response(invalid_response, EntityExtraction, strict=True)


@pytest.mark.unit
def test_llm_validator_unexpected_error_non_strict():
    """Test LLMValidator.validate_response with unexpected error in non-strict mode."""
    from mcp_server_langgraph.llm.validators import LLMValidator

    # Create a response that will cause an unexpected error during parsing
    class BrokenModel:
        def __init__(self, **kwargs):
            raise RuntimeError("Unexpected error")

    validated = LLMValidator.validate_response("{}", BrokenModel, strict=False)

    assert not validated.is_valid()


@pytest.mark.unit
def test_llm_validator_extract_entities():
    """Test LLMValidator.extract_entities convenience method."""
    import json

    from mcp_server_langgraph.llm.validators import LLMValidator

    response_data = {
        "entities": [{"type": "person", "value": "Bob"}, {"type": "location", "value": "NYC"}],
        "confidence": 0.88,
    }
    response = json.dumps(response_data)

    result = LLMValidator.extract_entities(response)

    assert result.is_valid()
    assert len(result.data.entities) == 2


@pytest.mark.unit
def test_llm_validator_classify_intent():
    """Test LLMValidator.classify_intent convenience method."""
    import json

    from mcp_server_langgraph.llm.validators import LLMValidator

    response_data = {
        "intent": "search_query",
        "confidence": 0.92,
        "sub_intents": ["web_search"],
        "parameters": {"query": "test"},
    }
    response = json.dumps(response_data)

    result = LLMValidator.classify_intent(response)

    assert result.is_valid()
    assert result.data.intent == "search_query"


@pytest.mark.unit
def test_llm_validator_analyze_sentiment():
    """Test LLMValidator.analyze_sentiment convenience method."""
    import json

    from mcp_server_langgraph.llm.validators import LLMValidator

    response_data = {"sentiment": "negative", "score": 0.75, "emotions": ["anger", "frustration"]}
    response = json.dumps(response_data)

    result = LLMValidator.analyze_sentiment(response)

    assert result.is_valid()
    assert result.data.sentiment == "negative"


@pytest.mark.unit
def test_llm_validator_extract_summary():
    """Test LLMValidator.extract_summary convenience method."""
    import json

    from mcp_server_langgraph.llm.validators import LLMValidator

    response_data = {
        "summary": "This is a summary",
        "key_points": ["Point 1", "Point 2"],
        "length": 18,
        "compression_ratio": 0.2,
    }
    response = json.dumps(response_data)

    result = LLMValidator.extract_summary(response)

    assert result.is_valid()
    assert result.data.summary == "This is a summary"
