"""
Additional Unit Tests for Tokenizer Dict Methods Coverage

These tests specifically target uncovered code paths in tokenizer.py:
- tokenize_dict() - lines 141-167
- untokenize_dict() - lines 169-193

Coverage target: 63% → 75%+
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.pii, pytest.mark.coverage]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tokenizer_dict_basic")
class TestTokenizerDictBasic:
    """Test suite for tokenize_dict basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tokenize_dict_simple(self):
        """GIVEN a simple dict with PII
        WHEN calling tokenize_dict
        THEN PII should be tokenized
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data = {"email": "test@example.com"}

        result, lookup = tokenizer.tokenize_dict(data)

        assert "test@example.com" not in str(result)
        assert len(lookup) > 0
        assert "test@example.com" in lookup.values()

    def test_tokenize_dict_nested(self):
        """GIVEN a nested dict with PII
        WHEN calling tokenize_dict
        THEN all nested PII should be tokenized
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data = {
            "user": {
                "contact": {
                    "email": "deep@example.com",
                    "phone": "555-123-4567",
                }
            }
        }

        result, lookup = tokenizer.tokenize_dict(data)

        assert "deep@example.com" not in str(result)
        assert "555-123-4567" not in str(result)
        assert len(lookup) == 2

    def test_tokenize_dict_with_list(self):
        """GIVEN a dict containing lists with PII
        WHEN calling tokenize_dict
        THEN all list items should be tokenized
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data = {"emails": ["a@example.com", "b@example.com", "c@example.com"]}

        result, lookup = tokenizer.tokenize_dict(data)

        assert "a@example.com" not in str(result)
        assert "b@example.com" not in str(result)
        assert "c@example.com" not in str(result)
        assert len(lookup) == 3

    def test_tokenize_dict_with_list_of_dicts(self):
        """GIVEN a dict containing list of dicts with PII
        WHEN calling tokenize_dict
        THEN all nested dict PII should be tokenized
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data = {
            "users": [
                {"email": "user1@example.com"},
                {"email": "user2@example.com"},
            ]
        }

        result, lookup = tokenizer.tokenize_dict(data)

        assert isinstance(result["users"], list)
        assert len(result["users"]) == 2
        assert "user1@example.com" not in str(result)
        assert "user2@example.com" not in str(result)

    def test_tokenize_dict_preserves_non_strings(self):
        """GIVEN a dict with mixed types
        WHEN calling tokenize_dict
        THEN non-string types should be preserved
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data = {
            "count": 42,
            "active": True,
            "nothing": None,
            "ratio": 3.14,
            "email": "test@example.com",
        }

        result, lookup = tokenizer.tokenize_dict(data)

        assert result["count"] == 42
        assert result["active"] is True
        assert result["nothing"] is None
        assert result["ratio"] == 3.14
        assert "test@example.com" not in result["email"]

    def test_tokenize_dict_empty(self):
        """GIVEN an empty dict
        WHEN calling tokenize_dict
        THEN should return empty dict and lookup
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data: dict[str, str] = {}

        result, lookup = tokenizer.tokenize_dict(data)

        assert result == {}
        assert lookup == {}

    def test_tokenize_dict_no_pii(self):
        """GIVEN a dict with no PII
        WHEN calling tokenize_dict
        THEN should return unchanged dict and empty lookup
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data = {
            "message": "Hello world",
            "count": 5,
        }

        result, lookup = tokenizer.tokenize_dict(data)

        assert result == data
        assert lookup == {}


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tokenizer_untokenize_dict")
class TestTokenizerUntokenizeDict:
    """Test suite for untokenize_dict functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_untokenize_dict_simple(self):
        """GIVEN tokenized dict and lookup
        WHEN calling untokenize_dict
        THEN original values should be restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {"email": "test@example.com"}

        tokenized, lookup = tokenizer.tokenize_dict(original)
        restored = tokenizer.untokenize_dict(tokenized, lookup)

        assert restored == original

    def test_untokenize_dict_nested(self):
        """GIVEN nested tokenized dict
        WHEN calling untokenize_dict
        THEN all nested values should be restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {
            "user": {
                "contact": {
                    "email": "deep@example.com",
                    "phone": "555-123-4567",
                }
            }
        }

        tokenized, lookup = tokenizer.tokenize_dict(original)
        restored = tokenizer.untokenize_dict(tokenized, lookup)

        assert restored == original

    def test_untokenize_dict_with_list(self):
        """GIVEN tokenized dict with lists
        WHEN calling untokenize_dict
        THEN all list items should be restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {"emails": ["a@example.com", "b@example.com"]}

        tokenized, lookup = tokenizer.tokenize_dict(original)
        restored = tokenizer.untokenize_dict(tokenized, lookup)

        assert restored == original

    def test_untokenize_dict_with_list_of_dicts(self):
        """GIVEN tokenized list of dicts
        WHEN calling untokenize_dict
        THEN all nested dict values should be restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {
            "users": [
                {"email": "user1@example.com", "name": "User 1"},
                {"email": "user2@example.com", "name": "User 2"},
            ]
        }

        tokenized, lookup = tokenizer.tokenize_dict(original)
        restored = tokenizer.untokenize_dict(tokenized, lookup)

        assert restored == original

    def test_untokenize_dict_preserves_non_strings(self):
        """GIVEN tokenized dict with mixed types
        WHEN calling untokenize_dict
        THEN non-string types should be preserved
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {
            "count": 42,
            "active": True,
            "nothing": None,
            "email": "test@example.com",
        }

        tokenized, lookup = tokenizer.tokenize_dict(original)
        restored = tokenizer.untokenize_dict(tokenized, lookup)

        assert restored == original

    def test_untokenize_dict_empty_lookup(self):
        """GIVEN dict without tokens and empty lookup
        WHEN calling untokenize_dict
        THEN should return unchanged dict
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        data = {"message": "Hello world"}

        restored = tokenizer.untokenize_dict(data, {})

        assert restored == data


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tokenizer_dict_roundtrip")
class TestTokenizerDictRoundtrip:
    """Test suite for dict tokenize/untokenize roundtrip."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_roundtrip_complex_structure(self):
        """GIVEN a complex nested structure with PII
        WHEN tokenizing and untokenizing
        THEN original structure should be perfectly restored
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {
            "users": [
                {
                    "profile": {
                        "email": "john@example.com",
                        "phone": "555-111-1111",
                    },
                    "settings": {"active": True, "count": 5},
                },
                {
                    "profile": {
                        "email": "jane@example.com",
                        "phone": "555-222-2222",
                    },
                    "settings": {"active": False, "count": 10},
                },
            ],
            "metadata": {
                "ssn": "123-45-6789",
                "ip": "192.168.1.100",
            },
        }

        tokenized, lookup = tokenizer.tokenize_dict(original)

        # Verify all PII is tokenized
        tokenized_str = str(tokenized)
        assert "john@example.com" not in tokenized_str
        assert "jane@example.com" not in tokenized_str
        assert "555-111-1111" not in tokenized_str
        assert "555-222-2222" not in tokenized_str
        assert "123-45-6789" not in tokenized_str
        assert "192.168.1.100" not in tokenized_str

        # Verify restoration
        restored = tokenizer.untokenize_dict(tokenized, lookup)
        assert restored == original

    def test_roundtrip_with_duplicate_pii(self):
        """GIVEN a structure with duplicate PII values
        WHEN tokenizing and untokenizing
        THEN duplicates should be handled correctly
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {
            "primary_email": "same@example.com",
            "backup_email": "same@example.com",
            "contact": {"email": "same@example.com"},
        }

        tokenized, lookup = tokenizer.tokenize_dict(original)

        # Same value should create only one lookup entry
        email_values = [v for v in lookup.values() if v == "same@example.com"]
        assert len(email_values) == 1

        # But all occurrences should be restored
        restored = tokenizer.untokenize_dict(tokenized, lookup)
        assert restored == original

    def test_roundtrip_deeply_nested(self):
        """GIVEN a deeply nested structure
        WHEN tokenizing and untokenizing
        THEN all levels should be handled correctly
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = {"l1": {"l2": {"l3": {"l4": {"l5": {"email": "deep@example.com"}}}}}}

        tokenized, lookup = tokenizer.tokenize_dict(original)
        assert "deep@example.com" not in str(tokenized)

        restored = tokenizer.untokenize_dict(tokenized, lookup)
        assert restored == original


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_tokenizer_internal_methods")
class TestTokenizerInternalMethods:
    """Test suite for internal tokenizer methods."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generate_token_id_deterministic(self):
        """GIVEN the same value
        WHEN generating token ID multiple times
        THEN should produce same ID
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()

        id1 = tokenizer._generate_token_id("test@example.com")
        id2 = tokenizer._generate_token_id("test@example.com")

        assert id1 == id2
        assert len(id1) == 8  # 8 hex chars

    def test_generate_token_id_unique(self):
        """GIVEN different values
        WHEN generating token IDs
        THEN should produce different IDs
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()

        id1 = tokenizer._generate_token_id("a@example.com")
        id2 = tokenizer._generate_token_id("b@example.com")

        assert id1 != id2

    def test_create_token_format(self):
        """GIVEN a PII type and value
        WHEN creating token
        THEN should follow correct format
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()

        token = tokenizer._create_token("EMAIL", "test@example.com")

        assert token.startswith("<<PII_EMAIL_")
        assert token.endswith(">>")
        assert len(token) > 15  # <<PII_EMAIL_ + 8 hex + >>

    def test_token_pattern_matches_generated_tokens(self):
        """GIVEN a generated token
        WHEN matching against TOKEN_PATTERN
        THEN should match
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()

        token = tokenizer._create_token("EMAIL", "test@example.com")
        matches = tokenizer.TOKEN_PATTERN.findall(token)

        assert len(matches) == 1
        assert matches[0] == token
