"""
Unit tests for PII Tokenization

Tests the PII tokenization and untokenization for protecting sensitive
data before LLM exposure. Required for GDPR, HIPAA, and SOC2 compliance.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.pii]


@pytest.mark.unit
class TestPIITokenizerBasic:
    """Test suite for basic tokenization functionality"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tokenizer_class_exists(self):
        """GIVEN the privacy module
        WHEN importing PIITokenizer
        THEN it should be a class
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        assert tokenizer is not None

    def test_tokenize_returns_tuple(self):
        """GIVEN text with PII
        WHEN tokenizing
        THEN it should return tuple of (tokenized_text, lookup_table)
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email: test@example.com"

        result = tokenizer.tokenize(text)

        assert isinstance(result, tuple)
        assert len(result) == 2
        tokenized_text, lookup_table = result
        assert isinstance(tokenized_text, str)
        assert isinstance(lookup_table, dict)

    def test_tokenized_text_contains_token_not_original(self):
        """GIVEN text with PII
        WHEN tokenizing
        THEN tokenized text should contain token, not original PII
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email: test@example.com"

        tokenized_text, _ = tokenizer.tokenize(text)

        assert "test@example.com" not in tokenized_text
        assert "<<" in tokenized_text  # Token format: <<PII_TYPE_ID>>

    def test_lookup_table_maps_token_to_original(self):
        """GIVEN text with PII
        WHEN tokenizing
        THEN lookup table should map token to original value
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email: test@example.com"

        _, lookup_table = tokenizer.tokenize(text)

        assert len(lookup_table) > 0
        # At least one value should be the original email
        assert "test@example.com" in lookup_table.values()


@pytest.mark.unit
class TestPIITokenizerUntokenize:
    """Test suite for untokenization (restoration)"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_untokenize_restores_original_text(self):
        """GIVEN tokenized text and lookup table
        WHEN untokenizing
        THEN original text should be restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original_text = "Email: test@example.com"

        tokenized_text, lookup_table = tokenizer.tokenize(original_text)
        restored_text = tokenizer.untokenize(tokenized_text, lookup_table)

        assert restored_text == original_text

    def test_untokenize_with_multiple_pii(self):
        """GIVEN tokenized text with multiple PII
        WHEN untokenizing
        THEN all original values should be restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original_text = "Contact john@example.com at 555-123-4567"

        tokenized_text, lookup_table = tokenizer.tokenize(original_text)
        restored_text = tokenizer.untokenize(tokenized_text, lookup_table)

        assert restored_text == original_text

    def test_untokenize_with_empty_lookup_returns_original(self):
        """GIVEN tokenized text and empty lookup table
        WHEN untokenizing
        THEN text should be returned unchanged
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Some text with <<PII_EMAIL_abc123>>"

        restored = tokenizer.untokenize(text, {})

        # With empty lookup, text is returned as-is
        assert restored == text


@pytest.mark.unit
class TestPIITokenizerRoundtrip:
    """Test suite for tokenize/untokenize roundtrip"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_roundtrip_preserves_text_with_no_pii(self):
        """GIVEN text with no PII
        WHEN tokenizing and untokenizing
        THEN original text should be preserved
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = "This is a regular sentence."

        tokenized, lookup = tokenizer.tokenize(original)
        restored = tokenizer.untokenize(tokenized, lookup)

        assert restored == original
        assert len(lookup) == 0

    def test_roundtrip_with_complex_text(self):
        """GIVEN complex text with mixed content and PII
        WHEN tokenizing and untokenizing
        THEN original text should be perfectly restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = """
        Customer: John Doe
        Email: john.doe@company.com
        Phone: (555) 123-4567
        SSN: 123-45-6789
        Card: 4111-1111-1111-1111
        IP: 192.168.1.100
        DOB: 1990-05-15
        """

        tokenized, lookup = tokenizer.tokenize(original)
        restored = tokenizer.untokenize(tokenized, lookup)

        assert restored == original


@pytest.mark.unit
class TestPIITokenizerTokenFormat:
    """Test suite for token format and structure"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_token_format_includes_pii_type(self):
        """GIVEN text with PII
        WHEN tokenizing
        THEN tokens should include PII type for context
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email: test@example.com"

        tokenized_text, _ = tokenizer.tokenize(text)

        # Token should indicate it's an email for LLM context
        assert "EMAIL" in tokenized_text

    def test_tokens_are_unique(self):
        """GIVEN text with same PII value twice
        WHEN tokenizing
        THEN same value should get same token
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email test@example.com and also test@example.com"

        tokenized_text, lookup = tokenizer.tokenize(text)

        # Same email should map to same token
        # Count occurrences of the token in lookup
        email_tokens = [k for k, v in lookup.items() if v == "test@example.com"]
        assert len(email_tokens) == 1  # Only one lookup entry

    def test_different_values_get_different_tokens(self):
        """GIVEN text with different PII values
        WHEN tokenizing
        THEN each value should get unique token
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email a@example.com and b@example.com"

        _, lookup = tokenizer.tokenize(text)

        # Should have 2 different tokens
        assert len(lookup) == 2


@pytest.mark.unit
class TestPIITokenizerEdgeCases:
    """Test suite for edge cases and error handling"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tokenize_empty_text(self):
        """GIVEN empty text
        WHEN tokenizing
        THEN should return empty text and empty lookup
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()

        tokenized, lookup = tokenizer.tokenize("")

        assert tokenized == ""
        assert lookup == {}

    def test_tokenize_none_text(self):
        """GIVEN None as text
        WHEN tokenizing
        THEN should handle gracefully
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()

        tokenized, lookup = tokenizer.tokenize(None)  # type: ignore[arg-type]

        assert tokenized == ""
        assert lookup == {}

    def test_tokenize_preserves_whitespace(self):
        """GIVEN text with specific whitespace formatting
        WHEN tokenizing and untokenizing
        THEN whitespace should be preserved
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = "Email:\n\ttest@example.com\n\nPhone: 555-123-4567"

        tokenized, lookup = tokenizer.tokenize(original)
        restored = tokenizer.untokenize(tokenized, lookup)

        assert restored == original


@pytest.mark.unit
class TestPIILookupTable:
    """Test suite for encrypted lookup table storage"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_lookup_table_can_be_serialized(self):
        """GIVEN a lookup table
        WHEN serializing to JSON
        THEN it should serialize without error
        """
        import json

        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        _, lookup = tokenizer.tokenize("Email: test@example.com")

        # Should be JSON serializable
        serialized = json.dumps(lookup)
        assert isinstance(serialized, str)

        # Should deserialize correctly
        deserialized = json.loads(serialized)
        assert deserialized == lookup

    def test_encrypted_lookup_table_exists(self):
        """GIVEN the privacy module
        WHEN importing EncryptedLookupTable
        THEN it should be available
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        assert table is not None

    def test_encrypted_lookup_stores_and_retrieves(self):
        """GIVEN an encrypted lookup table
        WHEN storing and retrieving values
        THEN values should be correctly retrieved
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()

        table.store("token1", "secret_value")
        retrieved = table.retrieve("token1")

        assert retrieved == "secret_value"

    def test_encrypted_lookup_returns_none_for_missing(self):
        """GIVEN an encrypted lookup table
        WHEN retrieving non-existent key
        THEN None should be returned
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()

        retrieved = table.retrieve("nonexistent")

        assert retrieved is None

    def test_encrypted_lookup_can_export_and_import(self):
        """GIVEN an encrypted lookup table with data
        WHEN exporting and importing
        THEN data should be preserved
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        table.store("token1", "value1")
        table.store("token2", "value2")

        exported = table.export_encrypted()
        new_table = EncryptedLookupTable.from_encrypted(exported)

        assert new_table.retrieve("token1") == "value1"
        assert new_table.retrieve("token2") == "value2"
