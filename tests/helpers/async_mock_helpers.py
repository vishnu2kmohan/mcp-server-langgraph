"""
Safe AsyncMock factory functions for test fixtures.

This module provides pre-configured AsyncMock factories that prevent security
vulnerabilities from unconfigured mocks.

Security Context:
    Unconfigured AsyncMock() instances return truthy MagicMock objects when awaited,
    causing authorization checks to incorrectly pass. This was the root cause of a
    SCIM security vulnerability (commit abb04a6a).

    Example of the vulnerability:
        # WRONG: Returns truthy MagicMock
        mock_openfga = AsyncMock()
        if await mock_openfga.check_permission(...):  # Always True!
            grant_access()  # Security bypass!

        # CORRECT: Explicit configuration
        mock_openfga = configured_async_mock_deny()
        if await mock_openfga.check_permission(...):  # Always False
            grant_access()  # Safe default: deny

Usage:
    from tests.helpers.async_mock_helpers import (
        configured_async_mock,
        configured_async_mock_deny,
        configured_async_mock_raise,
    )

    # Safe default (returns None)
    mock_api = configured_async_mock()
    result = await mock_api.fetch_data()  # Returns None

    # Authorization denial (security-safe default)
    mock_authz = configured_async_mock_deny()
    can_access = await mock_authz.check_permission(...)  # Returns False

    # Error simulation
    mock_failing_api = configured_async_mock_raise(ConnectionError("Service down"))
    await mock_failing_api.call()  # Raises ConnectionError

Enforcement:
    Pre-commit hook: scripts/check_async_mock_configuration.py
    Meta-test: tests/meta/test_async_mock_configuration.py

Related ADRs:
    - ADR-0042: Test Safety Patterns
    - ADR-0043: Authorization Testing Standards

Author: Claude Code (Sonnet 4.5)
Created: 2025-11-15
"""

from typing import Any
from unittest.mock import AsyncMock


def configured_async_mock(
    return_value: Any = None, side_effect: Any | None = None, spec: type | None = None, **kwargs: Any
) -> AsyncMock:
    """
    Create an AsyncMock with explicit return_value configuration.

    This factory ensures AsyncMock instances are always configured with an
    explicit return_value, preventing security vulnerabilities from truthy
    unconfigured mocks.

    Args:
        return_value: Value to return when mock is awaited (default: None)
        side_effect: Exception or callable to use as side effect
        spec: Class or instance to use as spec (enforces attribute access)
        **kwargs: Additional arguments passed to AsyncMock constructor

    Returns:
        AsyncMock instance with explicit configuration

    Examples:
        >>> # Safe default (returns None)
        >>> mock = configured_async_mock()
        >>> await mock()  # Returns None
        None

        >>> # Custom return value
        >>> mock = configured_async_mock(return_value={"user_id": "123"})
        >>> await mock()
        {'user_id': '123'}

        >>> # Boolean False is preserved (critical for auth checks)
        >>> mock = configured_async_mock(return_value=False)
        >>> await mock()
        False

        >>> # With spec for type safety
        >>> class UserService:
        ...     async def get_user(self, user_id: str) -> dict:
        ...         pass
        >>> mock = configured_async_mock(
        ...     return_value={"name": "Alice"},
        ...     spec=UserService
        ... )
        >>> await mock.get_user("123")
        {'name': 'Alice'}

    Security:
        Always use this factory instead of bare AsyncMock() to prevent
        authorization bypass vulnerabilities.
    """
    if spec is not None:
        kwargs["spec"] = spec

    if side_effect is not None:
        kwargs["side_effect"] = side_effect
    else:
        kwargs["return_value"] = return_value

    return AsyncMock(**kwargs)


def configured_async_mock_deny(spec: type | None = None, **kwargs: Any) -> AsyncMock:
    """
    Create an AsyncMock that always returns False (authorization denial).

    This is a security-safe default for authorization mocks. Use this factory
    for any mock representing an authorization check to ensure tests default
    to denying access rather than granting it.

    Args:
        spec: Class or instance to use as spec (enforces attribute access)
        **kwargs: Additional arguments passed to AsyncMock constructor

    Returns:
        AsyncMock instance configured to return False

    Examples:
        >>> # Authorization check (safe default: deny)
        >>> from tests.conftest import get_user_id
        >>> mock_openfga = configured_async_mock_deny()
        >>> user = get_user_id()  # Worker-safe ID
        >>> await mock_openfga.check_permission(
        ...     user=user,
        ...     relation="viewer",
        ...     object="document:secret"
        ... )
        False

        >>> # With spec for type safety
        >>> class AuthzClient:
        ...     async def check_permission(self, user, relation, obj) -> bool:
        ...         pass
        >>> mock_authz = configured_async_mock_deny(spec=AuthzClient)
        >>> await mock_authz.check_permission(get_user_id(), "editor", "doc:1")
        False

    Security:
        This factory provides "deny by default" semantics, preventing
        security bypasses when mocks are accidentally left unconfigured.

        When testing authorization grants, explicitly override:
            mock_authz.check_permission.return_value = True  # Explicit grant
    """
    if spec is not None:
        kwargs["spec"] = spec

    kwargs["return_value"] = False

    return AsyncMock(**kwargs)


def configured_async_mock_raise(exception: Exception, spec: type | None = None, **kwargs: Any) -> AsyncMock:
    """
    Create an AsyncMock that raises an exception when called.

    This factory simplifies error scenario testing by pre-configuring mocks
    to raise specific exceptions.

    Args:
        exception: Exception instance to raise when mock is awaited
        spec: Class or instance to use as spec (enforces attribute access)
        **kwargs: Additional arguments passed to AsyncMock constructor

    Returns:
        AsyncMock instance configured to raise exception

    Examples:
        >>> # Network error simulation
        >>> mock_api = configured_async_mock_raise(
        ...     ConnectionError("API unavailable")
        ... )
        >>> await mock_api.fetch_data()  # Raises ConnectionError
        Traceback (most recent call last):
        ...
        ConnectionError: API unavailable

        >>> # Permission denied simulation
        >>> mock_api = configured_async_mock_raise(
        ...     PermissionError("Insufficient privileges")
        ... )
        >>> await mock_api.delete_resource()  # Raises PermissionError
        Traceback (most recent call last):
        ...
        PermissionError: Insufficient privileges

        >>> # With spec for type safety
        >>> class ExternalAPI:
        ...     async def call(self) -> dict:
        ...         pass
        >>> mock_api = configured_async_mock_raise(
        ...     TimeoutError("Request timeout"),
        ...     spec=ExternalAPI
        ... )
        >>> await mock_api.call()  # Raises TimeoutError
        Traceback (most recent call last):
        ...
        TimeoutError: Request timeout

    Testing:
        Use pytest.raises context manager to verify exception handling:
            with pytest.raises(ConnectionError, match="API unavailable"):
                await service.call_api()
    """
    if spec is not None:
        kwargs["spec"] = spec

    kwargs["side_effect"] = exception

    return AsyncMock(**kwargs)


# Export all factory functions
__all__ = [
    "configured_async_mock",
    "configured_async_mock_deny",
    "configured_async_mock_raise",
]
