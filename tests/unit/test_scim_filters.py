"""
Unit tests for SCIM filter parsing

TDD Regression Tests: These tests validate the SCIM filter parsing logic
to prevent regression of the missing 'startsWith' operator implementation.

Tests cover:
- userName eq (equals) - exact match
- userName sw (startsWith) - prefix match
- email eq (equals) - exact match
- email sw (startsWith) - prefix match
- Malformed filters (error handling)

References:
- RFC 7644: SCIM Protocol
- OpenAI Codex finding: Missing startsWith operator support
"""

import gc
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.api.scim import list_users
from tests.helpers.async_mock_helpers import configured_async_mock


@pytest.mark.xdist_group(name="unit_scim_filters_tests")
class TestSCIMFilterParsing:
    """Unit tests for SCIM filter parsing logic"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_username_equals_filter_uses_exact_match(self):
        """
        TDD: Test that 'userName eq' filter uses exact match in Keycloak query

        GIVEN: SCIM filter with 'userName eq "alice"'
        WHEN: list_users endpoint is called
        THEN: Keycloak search_users is called with exact=true flag
        """
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(
            return_value=[
                {
                    "id": "user-123",
                    "username": "alice",
                    "email": "alice@example.com",
                    "firstName": "Alice",
                    "lastName": "Smith",
                    "enabled": True,
                }
            ]
        )
        result = await list_users(
            filter='userName eq "alice"', startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        mock_keycloak.search_users.assert_called_once()
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query["username"] == "alice"
        assert query["exact"] == "true", "userName eq should use exact match"
        assert result.totalResults == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_username_startswith_filter_uses_prefix_match(self):
        """
        TDD REGRESSION TEST: Test that 'userName sw' filter uses prefix match

        This test validates the fix for the missing startsWith operator.

        GIVEN: SCIM filter with 'userName sw "ali"'
        WHEN: list_users endpoint is called
        THEN: Keycloak search_users is called WITHOUT exact flag (prefix search)
        """
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(
            return_value=[
                {
                    "id": "user-123",
                    "username": "alice",
                    "email": "alice@example.com",
                    "firstName": "Alice",
                    "lastName": "Smith",
                    "enabled": True,
                },
                {
                    "id": "user-124",
                    "username": "alice_admin",
                    "email": "alice.admin@example.com",
                    "firstName": "Alice",
                    "lastName": "Admin",
                    "enabled": True,
                },
            ]
        )
        result = await list_users(
            filter='userName sw "ali"', startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        mock_keycloak.search_users.assert_called_once()
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query["username"] == "ali"
        assert "exact" not in query, "userName sw should NOT use exact flag for prefix search"
        assert result.totalResults == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_email_equals_filter_uses_exact_match(self):
        """
        TDD: Test that 'email eq' filter uses exact match

        GIVEN: SCIM filter with 'email eq "alice@example.com"'
        WHEN: list_users endpoint is called
        THEN: Keycloak search_users is called with exact=true flag
        """
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(
            return_value=[
                {
                    "id": "user-123",
                    "username": "alice",
                    "email": "alice@example.com",
                    "firstName": "Alice",
                    "lastName": "Smith",
                    "enabled": True,
                }
            ]
        )
        await list_users(
            filter='email eq "alice@example.com"', startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        mock_keycloak.search_users.assert_called_once()
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query["email"] == "alice@example.com"
        assert query["exact"] == "true", "email eq should use exact match"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_email_startswith_filter_uses_prefix_match(self):
        """
        TDD REGRESSION TEST: Test that 'email sw' filter uses prefix match

        GIVEN: SCIM filter with 'email sw "alice@"'
        WHEN: list_users endpoint is called
        THEN: Keycloak search_users is called WITHOUT exact flag (prefix search)
        """
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(
            return_value=[
                {
                    "id": "user-123",
                    "username": "alice",
                    "email": "alice@example.com",
                    "firstName": "Alice",
                    "lastName": "Smith",
                    "enabled": True,
                },
                {
                    "id": "user-124",
                    "username": "alice2",
                    "email": "alice@test.com",
                    "firstName": "Alice",
                    "lastName": "Test",
                    "enabled": True,
                },
            ]
        )
        result = await list_users(
            filter='email sw "alice@"', startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        mock_keycloak.search_users.assert_called_once()
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query["email"] == "alice@"
        assert "exact" not in query, "email sw should NOT use exact flag for prefix search"
        assert result.totalResults == 2

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_malformed_filter_returns_all_users(self):
        """
        TDD: Test that malformed filters fail-safe by returning all users

        GIVEN: Malformed SCIM filter
        WHEN: list_users endpoint is called
        THEN: All users are returned (fail-safe behavior)
        """
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(
            return_value=[
                {
                    "id": "user-123",
                    "username": "alice",
                    "email": "alice@example.com",
                    "firstName": "Alice",
                    "lastName": "Smith",
                    "enabled": True,
                }
            ]
        )
        await list_users(
            filter="userName eq alice", startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        mock_keycloak.search_users.assert_called_once()
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query == {}, "Malformed filter should result in empty query (fail-safe)"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_filter_returns_all_users(self):
        """
        TDD: Test that missing filter returns all users

        GIVEN: No SCIM filter provided
        WHEN: list_users endpoint is called
        THEN: All users are returned
        """
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(
            return_value=[
                {
                    "id": "user-123",
                    "username": "alice",
                    "email": "alice@example.com",
                    "firstName": "Alice",
                    "lastName": "Smith",
                    "enabled": True,
                },
                {
                    "id": "user-124",
                    "username": "bob",
                    "email": "bob@example.com",
                    "firstName": "Bob",
                    "lastName": "Jones",
                    "enabled": True,
                },
            ]
        )
        result = await list_users(filter=None, startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak)
        mock_keycloak.search_users.assert_called_once()
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query == {}, "No filter should result in empty query (return all)"
        assert result.totalResults == 2


@pytest.mark.xdist_group(name="unit_scim_filters_tests")
class TestSCIMFilterEdgeCases:
    """Edge case tests for SCIM filter parsing"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_filter_with_spaces_in_value(self):
        """Test filter with spaces in the search value"""
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(return_value=[])
        await list_users(
            filter='userName eq "Alice Smith"', startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query["username"] == "Alice Smith"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_filter_with_special_characters(self):
        """Test filter with special characters in email"""
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(return_value=[])
        await list_users(
            filter='email sw "user+test@"', startIndex=1, count=100, current_user=current_user, keycloak=mock_keycloak
        )
        call_args = mock_keycloak.search_users.call_args
        query = call_args.kwargs["query"]
        assert query["email"] == "user+test@"
        assert "exact" not in query

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_pagination_parameters_passed_correctly(self):
        """Test that pagination parameters are passed to Keycloak correctly"""
        current_user = {"user_id": "admin:test", "username": "admin", "roles": ["admin"]}
        mock_keycloak = configured_async_mock(return_value=None)
        mock_keycloak.search_users = AsyncMock(return_value=[])
        await list_users(
            filter='userName sw "ali"', startIndex=51, count=25, current_user=current_user, keycloak=mock_keycloak
        )
        call_args = mock_keycloak.search_users.call_args
        assert call_args.kwargs["first"] == 50
        assert call_args.kwargs["max"] == 25
