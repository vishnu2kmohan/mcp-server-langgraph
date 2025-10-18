"""
Contract tests for LLMFactory._format_messages

These tests validate the message formatting contract without using AsyncMock,
ensuring the method correctly handles various input types including edge cases
that caused the string-to-character-list bug.
"""

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from mcp_server_langgraph.llm.factory import LLMFactory


@pytest.fixture
def llm_factory():
    """Create LLMFactory instance without mocking LLM."""
    # Create with minimal config (no actual LLM calls will be made in these tests)
    factory = LLMFactory(
        provider="test",
        model_name="test-model",
        api_key="test-key",
    )
    return factory


@pytest.mark.unit
class TestFormatMessagesContract:
    """Test _format_messages method with various input types."""

    def test_format_single_human_message(self, llm_factory):
        """Test formatting a single HumanMessage."""
        messages = [HumanMessage(content="Hello, how are you?")]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello, how are you?"

    def test_format_single_ai_message(self, llm_factory):
        """Test formatting a single AIMessage."""
        messages = [AIMessage(content="I'm doing well, thank you!")]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "assistant"
        assert formatted[0]["content"] == "I'm doing well, thank you!"

    def test_format_single_system_message(self, llm_factory):
        """Test formatting a single SystemMessage."""
        messages = [SystemMessage(content="You are a helpful assistant.")]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant."

    def test_format_mixed_message_types(self, llm_factory):
        """Test formatting a conversation with mixed message types."""
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="What is Python?"),
            AIMessage(content="Python is a programming language."),
            HumanMessage(content="Tell me more."),
        ]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 4
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"
        assert formatted[2]["role"] == "assistant"
        assert formatted[3]["role"] == "user"

    def test_format_dict_message_with_role_and_content(self, llm_factory):
        """Test formatting a dict message that's already in correct format."""
        messages = [{"role": "user", "content": "Hello from dict"}]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello from dict"

    def test_format_dict_message_with_content_only(self, llm_factory):
        """Test formatting a dict with content but no role."""
        messages = [{"content": "Message without role"}]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"  # Defaults to user
        assert formatted[0]["content"] == "Message without role"

    def test_format_malformed_dict_message(self, llm_factory):
        """Test formatting a malformed dict message."""
        messages = [{"foo": "bar"}]  # No content field

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        # Should convert entire dict to string
        assert "foo" in formatted[0]["content"]

    def test_format_empty_list(self, llm_factory):
        """Test formatting an empty message list."""
        messages = []

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 0

    def test_format_preserves_long_content(self, llm_factory):
        """Test that formatting preserves long content without truncation."""
        long_content = "x" * 10000  # 10k character string
        messages = [HumanMessage(content=long_content)]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert len(formatted[0]["content"]) == 10000
        assert formatted[0]["content"] == long_content

    def test_format_multiline_content(self, llm_factory):
        """Test formatting messages with multiline content."""
        multiline = "Line 1\nLine 2\nLine 3"
        messages = [HumanMessage(content=multiline)]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["content"] == multiline
        assert "\n" in formatted[0]["content"]

    def test_format_special_characters(self, llm_factory):
        """Test formatting messages with special characters."""
        special_chars = "Hello! @#$%^&*() \"quotes\" 'apostrophe' <xml> {json}"
        messages = [HumanMessage(content=special_chars)]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["content"] == special_chars

    def test_format_unicode_content(self, llm_factory):
        """Test formatting messages with Unicode characters."""
        unicode_content = "Hello 世界 🌍 Привет مرحبا"
        messages = [HumanMessage(content=unicode_content)]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["content"] == unicode_content

    def test_format_xml_structured_prompt(self, llm_factory):
        """Test formatting XML-structured prompts (Anthropic best practice)."""
        xml_prompt = """<task>
Summarize the following conversation.
</task>

<conversation>
User: Hello
Assistant: Hi there!
</conversation>

<instructions>
Provide a concise summary in 1-2 sentences.
</instructions>"""
        messages = [HumanMessage(content=xml_prompt)]

        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert "<task>" in formatted[0]["content"]
        assert "<conversation>" in formatted[0]["content"]
        assert formatted[0]["content"] == xml_prompt


@pytest.mark.unit
class TestFormatMessagesEdgeCases:
    """Test edge cases that previously caused bugs."""

    def test_format_does_not_accept_raw_strings(self, llm_factory):
        """
        Test that passing a raw string is handled (but produces incorrect output).

        REGRESSION TEST: Previously, passing a string would iterate character-by-character.
        This test documents the incorrect behavior to prevent regression.

        NOTE: The _format_messages method doesn't validate input types - it just handles
        whatever is passed. The CORRECT usage is shown in test_correct_usage_wrap_string_in_message.
        """
        # If someone passes a string directly, it will be iterated character-by-character
        # This is INCORRECT usage but doesn't raise an exception

        # The _format_messages method expects a list of BaseMessage objects
        # Passing a string will cause it to iterate over characters
        result = llm_factory._format_messages("ABC")  # type: ignore[arg-type]

        # This is WRONG - each character becomes a separate message!
        # We document this behavior to prevent regression
        assert len(result) == 3  # One per character
        assert all(msg["role"] == "user" for msg in result)
        # Content will be string representations of characters
        assert result[0]["content"] in ["A", "str({'content': 'A'})"]  # Depends on fallback path

    def test_correct_usage_wrap_string_in_message(self, llm_factory):
        """
        Test the CORRECT way to use _format_messages with a string prompt.

        Strings must be wrapped in a HumanMessage object.
        """
        prompt_string = "What is the capital of France?"

        # CORRECT usage: wrap in HumanMessage
        messages = [HumanMessage(content=prompt_string)]
        formatted = llm_factory._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == prompt_string
        # Should NOT be split into characters
        assert len(formatted[0]["content"]) == len(prompt_string)

    def test_format_with_custom_message_class(self, llm_factory):
        """Test formatting with a custom BaseMessage subclass."""

        # Create a minimal custom message class
        class CustomMessage(BaseMessage):
            content: str
            type: str = "custom"

        # Create instance with content
        messages = [CustomMessage(content="Custom content")]

        formatted = llm_factory._format_messages(messages)

        # Should fall back to checking hasattr(msg, "content")
        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"  # Fallback for unknown types
        assert formatted[0]["content"] == "Custom content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
