"""
User Factory for Test Data Generation.

Provides factory functions for creating test user objects.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4


class UserFactory:
    """Factory for creating test user objects."""

    @staticmethod
    def create(
        username: str = "test_user",
        email: str | None = None,
        roles: list[str] | None = None,
        tier: str = "standard",
        organization: str = "test-org",
        keycloak_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a test user dictionary.

        Args:
            username: Username for the user
            email: Email address (defaults to {username}@example.com)
            roles: List of roles (defaults to ["user"])
            tier: User tier (default: "standard")
            organization: Organization name
            keycloak_id: Keycloak UUID (auto-generated if not provided)

        Returns:
            Dictionary with user data
        """
        return {
            "username": username,
            "email": email or f"{username}@example.com",
            "roles": roles or ["user"],
            "tier": tier,
            "organization": organization,
            "keycloak_id": keycloak_id or str(uuid4()),
            "user_id": f"user:{username}",
        }

    @staticmethod
    def create_admin(username: str = "admin") -> dict[str, Any]:
        """Create an admin user."""
        return UserFactory.create(
            username=username,
            roles=["admin", "user"],
            tier="premium",
        )

    @staticmethod
    def create_jwt_payload(
        sub: str = "test_user",
        exp_hours: float = 1.0,
        additional_claims: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a JWT payload for testing.

        Args:
            sub: Subject claim (usually username)
            exp_hours: Hours until expiration
            additional_claims: Extra claims to include

        Returns:
            JWT payload dictionary
        """
        now = datetime.now(UTC)
        payload = {
            "sub": sub,
            "iat": now,
            "exp": now + timedelta(hours=exp_hours),
        }
        if additional_claims:
            payload.update(additional_claims)
        return payload


# Convenience instances
alice = UserFactory.create(
    username="alice",
    roles=["admin", "user"],
    tier="premium",
    organization="acme",
)

bob = UserFactory.create(
    username="bob",
    roles=["user"],
    tier="standard",
    organization="acme",
)
