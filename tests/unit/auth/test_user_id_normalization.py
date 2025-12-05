"""
Test user_id normalization for handling multiple formats.

Ensures that both plain usernames and OpenFGA-prefixed IDs work correctly.
"""

import pytest

from mcp_server_langgraph.auth.middleware import normalize_user_id

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_normalize_plain_username():
    """Test normalization of plain username."""
    assert normalize_user_id("alice") == "alice"
    assert normalize_user_id("bob") == "bob"
    assert normalize_user_id("admin") == "admin"


@pytest.mark.unit
def test_normalize_openfga_user_format():
    """Test normalization of OpenFGA user:username format."""
    assert normalize_user_id("user:alice") == "alice"
    assert normalize_user_id("user:bob") == "bob"
    assert normalize_user_id("user:admin") == "admin"


@pytest.mark.unit
def test_normalize_other_prefixes():
    """Test normalization with other prefix formats."""
    assert normalize_user_id("uid:123") == "123"
    assert normalize_user_id("email:alice@example.com") == "alice@example.com"
    assert normalize_user_id("service:api-key") == "api-key"


@pytest.mark.unit
def test_normalize_multiple_colons():
    """Test normalization when ID contains multiple colons."""
    # Only split on first colon
    assert normalize_user_id("user:alice:admin") == "alice:admin"
    assert normalize_user_id("namespace:team:alice") == "team:alice"


@pytest.mark.unit
def test_normalize_empty_and_none():
    """Test normalization with edge cases."""
    assert normalize_user_id("") == ""
    # Note: None will cause AttributeError since we call .split() on it
    # This is expected - caller should validate input


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_accepts_both_formats():
    """Test that authenticate() accepts both username formats."""
    from mcp_server_langgraph.auth.middleware import AuthMiddleware
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    # Create provider with test user
    user_provider = InMemoryUserProvider(secret_key="test-secret", use_password_hashing=False)
    user_provider.add_user(username="alice", password="alice123", email="alice@test.com", roles=["user"])

    auth = AuthMiddleware(secret_key="test-secret", user_provider=user_provider)

    # Test with plain username
    result1 = await auth.authenticate("alice", "alice123")
    assert result1.authorized is True
    # InMemoryUserProvider returns user_id with "user:" prefix for OpenFGA compatibility
    assert result1.user_id == "user:alice"

    # Test with prefixed format - normalization strips prefix, then provider adds it back
    result2 = await auth.authenticate("user:alice", "alice123")
    assert result2.authorized is True
    assert result2.user_id == "user:alice"

    # Both should authenticate to the same user
    assert result1.user_id == result2.user_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_normalization_with_unknown_user():
    """Test that authentication fails correctly for unknown users in both formats."""
    from mcp_server_langgraph.auth.middleware import AuthMiddleware

    auth = AuthMiddleware(secret_key="test-secret")

    # Test with plain username
    result1 = await auth.authenticate("unknown_user")
    assert result1.authorized is False

    # Test with prefixed format
    result2 = await auth.authenticate("user:unknown_user")
    assert result2.authorized is False


@pytest.mark.unit
def test_normalize_user_id_idempotent():
    """Test that normalization is idempotent."""
    # Normalizing an already normalized ID should return the same value
    assert normalize_user_id(normalize_user_id("user:alice")) == "alice"
    assert normalize_user_id(normalize_user_id("alice")) == "alice"
