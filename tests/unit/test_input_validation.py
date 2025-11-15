"""Unit tests for input validation to prevent CWE-20 vulnerabilities.

This module tests validation of user-controlled identifiers that flow into
critical systems like OpenFGA, Redis, and application logs.
"""

import gc

import pytest
from pydantic import ValidationError

from mcp_server_langgraph.mcp.server_streamable import ChatInput, SearchConversationsInput


@pytest.mark.xdist_group(name="testthreadidvalidation")
class TestThreadIdValidation:
    """Test suite for thread_id validation to prevent CWE-20"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_thread_id_accepts_valid_alphanumeric(self):
        """Test that valid alphanumeric thread_id is accepted"""
        # GIVEN: Valid thread_id with alphanumeric and hyphens
        valid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv_abc123-xyz",
        }

        # WHEN: Validating with ChatInput
        chat_input = ChatInput.model_validate(valid_input)

        # THEN: Should be accepted
        assert chat_input.thread_id == "conv_abc123-xyz"

    def test_thread_id_accepts_underscores(self):
        """Test that underscores are allowed in thread_id"""
        # GIVEN: Valid thread_id with underscores
        valid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv_user_123",
        }

        # WHEN: Validating with ChatInput
        chat_input = ChatInput.model_validate(valid_input)

        # THEN: Should be accepted
        assert chat_input.thread_id == "conv_user_123"

    def test_thread_id_rejects_newline_characters(self):
        """Test that newline characters are rejected"""
        # GIVEN: Malicious thread_id with newline (log injection)
        malicious_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv\nFAKE LOG: User authenticated as admin",
        }

        # WHEN: Validating with ChatInput
        # THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(malicious_input)

        # Verify error mentions thread_id
        assert "thread_id" in str(exc_info.value)

    def test_thread_id_rejects_carriage_return(self):
        """Test that carriage return characters are rejected"""
        # GIVEN: Malicious thread_id with CR
        malicious_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv\rmalicious",
        }

        # WHEN/THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(malicious_input)

        assert "thread_id" in str(exc_info.value)

    def test_thread_id_rejects_null_bytes(self):
        """Test that null bytes are rejected"""
        # GIVEN: Malicious thread_id with null byte (Redis key corruption)
        malicious_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv\x00admin",
        }

        # WHEN/THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(malicious_input)

        assert "thread_id" in str(exc_info.value)

    def test_thread_id_rejects_colon_for_openfga_safety(self):
        """Test that colon is rejected to prevent OpenFGA resource confusion"""
        # GIVEN: Malicious thread_id with colon (OpenFGA namespace injection)
        malicious_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv:user:admin",
        }

        # WHEN/THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(malicious_input)

        assert "thread_id" in str(exc_info.value)

    def test_thread_id_rejects_path_traversal(self):
        """Test that path traversal sequences are rejected"""
        # GIVEN: Malicious thread_id with path traversal
        malicious_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "../../../admin",
        }

        # WHEN/THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(malicious_input)

        assert "thread_id" in str(exc_info.value)

    def test_thread_id_rejects_excessive_length(self):
        """Test that excessively long thread_id is rejected (DoS prevention)"""
        # GIVEN: Very long thread_id (>128 chars)
        malicious_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv_" + "a" * 200,
        }

        # WHEN/THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(malicious_input)

        assert "thread_id" in str(exc_info.value)

    def test_thread_id_accepts_none(self):
        """Test that None thread_id is accepted (uses default)"""
        # GIVEN: Input without thread_id
        valid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
        }

        # WHEN: Validating with ChatInput
        chat_input = ChatInput.model_validate(valid_input)

        # THEN: Should be accepted with None
        assert chat_input.thread_id is None

    def test_thread_id_rejects_empty_string(self):
        """Test that empty string is rejected (forces None or valid ID)"""
        # GIVEN: Empty thread_id
        invalid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "",
        }

        # WHEN/THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(invalid_input)

        assert "thread_id" in str(exc_info.value)

    def test_thread_id_rejects_spaces(self):
        """Test that spaces are rejected"""
        # GIVEN: thread_id with spaces
        invalid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv 123 test",
        }

        # WHEN/THEN: Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ChatInput.model_validate(invalid_input)

        assert "thread_id" in str(exc_info.value)

    def test_thread_id_with_search_conversations_input(self):
        """Test that thread_id validation applies to SearchConversationsInput"""
        # GIVEN: SearchConversationsInput with malicious thread_id
        # Note: SearchConversationsInput doesn't have thread_id field currently
        # This test documents expected behavior if thread_id is added

        # For now, test that query validation works
        valid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "query": "test search",
        }

        # WHEN: Validating
        search_input = SearchConversationsInput.model_validate(valid_input)

        # THEN: Should succeed
        assert search_input.query == "test search"


@pytest.mark.xdist_group(name="testconversationidusageincode")
class TestConversationIdUsageInCode:
    """Integration tests verifying thread_id doesn't corrupt downstream systems"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_thread_id_in_openfga_resource(self):
        """Test that valid thread_id creates safe OpenFGA resource string"""
        # GIVEN: Valid thread_id
        valid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv_abc123",
        }

        chat_input = ChatInput.model_validate(valid_input)

        # WHEN: Creating OpenFGA resource (simulating server_streamable.py:499)
        thread_id = chat_input.thread_id or "default"
        conversation_resource = f"conversation:{thread_id}"

        # THEN: Resource should have expected format
        assert conversation_resource == "conversation:conv_abc123"
        assert conversation_resource.count(":") == 1  # Only one separator

    def test_malicious_thread_id_would_corrupt_openfga(self):
        """Test that validation prevents OpenFGA resource corruption"""
        # GIVEN: Malicious thread_id that would create nested resource
        malicious_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv:user:admin",  # Would become "conversation:conv:user:admin"
        }

        # WHEN/THEN: Validation should prevent this
        with pytest.raises(ValidationError):
            ChatInput.model_validate(malicious_input)

    def test_thread_id_in_span_attribute(self):
        """Test that valid thread_id is safe for OpenTelemetry span attributes"""
        # GIVEN: Valid thread_id
        valid_input = {
            "token": "test_token",
            "user_id": "user:alice",
            "message": "Hello",
            "thread_id": "conv_abc123",
        }

        chat_input = ChatInput.model_validate(valid_input)

        # WHEN: Setting span attribute (simulating server_streamable.py:492)
        thread_id = chat_input.thread_id or "default"

        # THEN: Should be safe string (no control chars)
        assert "\n" not in thread_id
        assert "\r" not in thread_id
        assert "\x00" not in thread_id
