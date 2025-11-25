"""
Unit tests for SessionData Pydantic model validation.

Tests the SessionData model validators and serialization methods.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="session_data_model")
class TestSessionDataValidation:
    """Test SessionData model field validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_valid_session_data_creation(self):
        """Test creating valid SessionData."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()
        expires = (datetime.now(timezone.utc)).isoformat()

        session = SessionData(
            session_id="a" * 32,  # 32 char minimum
            user_id="user:alice",
            username="alice",
            roles=["user", "admin"],
            metadata={"ip": "192.168.1.1"},
            created_at=now,
            last_accessed=now,
            expires_at=expires,
        )

        assert session.session_id == "a" * 32
        assert session.user_id == "user:alice"
        assert session.username == "alice"
        assert "admin" in session.roles

    @pytest.mark.unit
    def test_session_id_too_short_raises_error(self):
        """Test that short session ID raises validation error."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        with pytest.raises(ValidationError) as exc_info:
            SessionData(
                session_id="short",  # Less than 32 chars
                user_id="user:alice",
                username="alice",
                roles=[],
                metadata={},
                created_at=now,
                last_accessed=now,
                expires_at=now,
            )

        assert "session_id" in str(exc_info.value).lower() or "32" in str(exc_info.value)

    @pytest.mark.unit
    def test_empty_user_id_raises_error(self):
        """Test that empty user_id raises validation error."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        with pytest.raises(ValidationError):
            SessionData(
                session_id="a" * 32,
                user_id="",  # Empty user_id
                username="alice",
                roles=[],
                metadata={},
                created_at=now,
                last_accessed=now,
                expires_at=now,
            )

    @pytest.mark.unit
    def test_invalid_timestamp_format_raises_error(self):
        """Test that invalid timestamp format raises validation error."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        with pytest.raises(ValidationError):
            SessionData(
                session_id="a" * 32,
                user_id="user:alice",
                username="alice",
                roles=[],
                metadata={},
                created_at="not-a-valid-timestamp",  # Invalid format
                last_accessed=now,
                expires_at=now,
            )

    @pytest.mark.unit
    def test_zulu_time_normalization(self):
        """Test that Zulu time (Z suffix) is normalized to +00:00."""
        from mcp_server_langgraph.auth.session import SessionData

        # Create with Zulu time format
        session = SessionData(
            session_id="a" * 32,
            user_id="user:alice",
            username="alice",
            roles=[],
            metadata={},
            created_at="2025-01-01T00:00:00Z",  # Zulu time
            last_accessed="2025-01-01T00:00:00Z",
            expires_at="2025-01-01T00:00:00Z",
        )

        # Should be normalized to +00:00
        assert session.created_at == "2025-01-01T00:00:00+00:00"
        assert session.last_accessed == "2025-01-01T00:00:00+00:00"
        assert session.expires_at == "2025-01-01T00:00:00+00:00"


@pytest.mark.xdist_group(name="session_data_model")
class TestSessionDataSerialization:
    """Test SessionData serialization methods."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_to_dict_returns_dictionary(self):
        """Test that to_dict returns a proper dictionary."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        session = SessionData(
            session_id="a" * 32,
            user_id="user:alice",
            username="alice",
            roles=["user"],
            metadata={"key": "value"},
            created_at=now,
            last_accessed=now,
            expires_at=now,
        )

        result = session.to_dict()

        assert isinstance(result, dict)
        assert result["session_id"] == "a" * 32
        assert result["user_id"] == "user:alice"
        assert result["username"] == "alice"
        assert result["roles"] == ["user"]
        assert result["metadata"] == {"key": "value"}

    @pytest.mark.unit
    def test_from_dict_creates_session_data(self):
        """Test that from_dict creates SessionData from dictionary."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        data = {
            "session_id": "b" * 32,
            "user_id": "user:bob",
            "username": "bob",
            "roles": ["admin"],
            "metadata": {},
            "created_at": now,
            "last_accessed": now,
            "expires_at": now,
        }

        session = SessionData.from_dict(data)

        assert session.session_id == "b" * 32
        assert session.user_id == "user:bob"
        assert session.username == "bob"
        assert session.roles == ["admin"]

    @pytest.mark.unit
    def test_to_dict_from_dict_roundtrip_preserves_all_fields(self):
        """Test that to_dict and from_dict are inverse operations."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        original = SessionData(
            session_id="c" * 32,
            user_id="user:charlie",
            username="charlie",
            roles=["user", "viewer"],
            metadata={"key": "value", "count": 42},
            created_at=now,
            last_accessed=now,
            expires_at=now,
        )

        # Round-trip
        data = original.to_dict()
        restored = SessionData.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.user_id == original.user_id
        assert restored.username == original.username
        assert restored.roles == original.roles
        assert restored.metadata == original.metadata


@pytest.mark.xdist_group(name="session_data_model")
class TestSessionDataDefaults:
    """Test SessionData default values and optional fields."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_default_roles_empty_list(self):
        """Test that roles defaults to empty list."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        session = SessionData(
            session_id="d" * 32,
            user_id="user:dave",
            username="dave",
            # roles not specified
            metadata={},
            created_at=now,
            last_accessed=now,
            expires_at=now,
        )

        assert session.roles == []

    @pytest.mark.unit
    def test_default_metadata_empty_dict(self):
        """Test that metadata defaults to empty dict."""
        from mcp_server_langgraph.auth.session import SessionData

        now = datetime.now(timezone.utc).isoformat()

        session = SessionData(
            session_id="e" * 32,
            user_id="user:eve",
            username="eve",
            roles=[],
            # metadata not specified
            created_at=now,
            last_accessed=now,
            expires_at=now,
        )

        assert session.metadata == {}
