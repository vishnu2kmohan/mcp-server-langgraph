"""
AuthorizationService - Single Responsibility authorization logic.

Extracted from AuthMiddleware as part of Phase 2.1 SRP decomposition.

Responsibilities:
- OpenFGA authorization checks
- Fallback role-based authorization (dev/test only)
- Security controls for production environments

Reference: Plan - Phase 2.1 SRP: Decompose AuthMiddleware
"""

import re
from typing import Any

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.user_provider import UserProvider
from mcp_server_langgraph.observability.telemetry import logger, tracer


class AuthorizationService:
    """
    Service for authorization checks using OpenFGA.

    Provides fine-grained relationship-based authorization with
    fallback support for development/testing environments.

    Security:
    - Production always uses OpenFGA (no fallback allowed)
    - Fallback only enabled when explicitly configured in non-production
    - Fails closed on errors (deny access)
    """

    def __init__(
        self,
        openfga_client: OpenFGAClient | None = None,
        settings: Any | None = None,
        user_provider: UserProvider | None = None,
        users_db: dict[str, dict[str, Any]] | None = None,
    ):
        """
        Initialize AuthorizationService.

        Args:
            openfga_client: OpenFGA client for authorization checks
            settings: Application settings (for fallback control)
            user_provider: User provider for fallback user lookups
            users_db: In-memory users database (for InMemoryUserProvider fallback)
        """
        self.openfga = openfga_client
        self.settings = settings
        self.user_provider = user_provider
        self.users_db = users_db or {}

    async def authorize(
        self,
        user_id: str,
        relation: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Check if user is authorized using OpenFGA.

        Args:
            user_id: User identifier (e.g., "user:alice")
            relation: Relation to check (e.g., "executor", "viewer")
            resource: Resource identifier (e.g., "tool:chat")
            context: Additional context for authorization

        Returns:
            True if authorized, False otherwise
        """
        with tracer.start_as_current_span("auth.authorize") as span:
            span.set_attribute("user.id", user_id)
            span.set_attribute("auth.relation", relation)
            span.set_attribute("auth.resource", resource)

            # Use OpenFGA if available
            if self.openfga:
                try:
                    authorized = await self.openfga.check_permission(
                        user=user_id,
                        relation=relation,
                        object=resource,
                        context=context,
                    )

                    span.set_attribute("auth.authorized", authorized)
                    logger.info(
                        "Authorization check (OpenFGA)",
                        extra={
                            "user_id": user_id,
                            "relation": relation,
                            "resource": resource,
                            "authorized": authorized,
                        },
                    )

                    return authorized

                except Exception as e:
                    logger.error(
                        f"OpenFGA authorization check failed: {e}",
                        extra={
                            "user_id": user_id,
                            "relation": relation,
                            "resource": resource,
                        },
                        exc_info=True,
                    )
                    # Fail closed - deny access on error
                    return False

            # Fallback authorization when OpenFGA not available
            return await self._fallback_authorize(user_id, relation, resource)

    async def _fallback_authorize(
        self,
        user_id: str,
        relation: str,
        resource: str,
    ) -> bool:
        """
        Fallback role-based authorization when OpenFGA unavailable.

        Security controls:
        - Never allowed in production environment
        - Must be explicitly enabled via settings
        - Scopes resource access by user ownership

        Args:
            user_id: User identifier
            relation: Relation to check
            resource: Resource identifier

        Returns:
            True if authorized, False otherwise
        """
        # Check if fallback authorization is allowed
        allow_fallback = getattr(self.settings, "allow_auth_fallback", False) if self.settings else False
        environment = getattr(self.settings, "environment", "production") if self.settings else "production"

        # SECURITY: NEVER allow fallback in production
        if environment == "production":
            logger.error(
                "Authorization DENIED: OpenFGA unavailable in production environment. "
                "Fallback authorization is not permitted in production for security reasons.",
                extra={
                    "user_id": user_id,
                    "relation": relation,
                    "resource": resource,
                    "environment": environment,
                    "allow_auth_fallback": allow_fallback,
                },
            )
            return False

        # Check if fallback is explicitly enabled
        if not allow_fallback:
            logger.warning(
                "Authorization DENIED: OpenFGA unavailable and fallback authorization is disabled. "
                "Set ALLOW_AUTH_FALLBACK=true to enable role-based fallback in development/test.",
                extra={
                    "user_id": user_id,
                    "relation": relation,
                    "resource": resource,
                    "allow_auth_fallback": allow_fallback,
                    "environment": environment,
                },
            )
            return False

        logger.warning(
            "OpenFGA not available, using fallback authorization (explicitly enabled)",
            extra={
                "allow_auth_fallback": allow_fallback,
                "environment": environment,
            },
        )

        # Extract username from user_id
        username = self._extract_username(user_id)

        # Get user roles
        user_roles = await self._get_user_roles(user_id, username)
        if user_roles is None:
            return False

        # Check authorization rules
        return self._check_fallback_rules(user_id, username, relation, resource, user_roles)

    def _extract_username(self, user_id: str) -> str:
        """Extract username from user_id, handling worker-safe IDs."""
        if ":" in user_id:
            id_part = user_id.split(":", 1)[1]
            # Handle worker-safe IDs (e.g., "test_gw0_alice" → "alice")
            match = re.match(r"test_gw\d+_(.*)", id_part)
            return match.group(1) if match else id_part
        return user_id

    async def _get_user_roles(
        self,
        user_id: str,
        username: str,
    ) -> list[str] | None:
        """Get user roles from provider or in-memory database."""
        # Try in-memory database first (for InMemoryUserProvider)
        if username in self.users_db:
            roles: list[str] = self.users_db[username]["roles"]
            return roles

        # Try user provider
        if self.user_provider:
            try:
                user_data = await self.user_provider.get_user_by_username(username)
                if not user_data:
                    logger.warning(
                        "Fallback authorization denied - user not found in provider",
                        extra={
                            "user_id": user_id,
                            "username": username,
                            "provider": type(self.user_provider).__name__,
                        },
                    )
                    return None
                logger.info(
                    "Fetched user from provider for fallback authorization",
                    extra={
                        "user_id": user_id,
                        "username": username,
                        "provider": type(self.user_provider).__name__,
                        "roles": user_data.roles,
                    },
                )
                return user_data.roles
            except Exception as e:
                logger.error(
                    f"Failed to fetch user from provider for fallback authorization: {e}",
                    extra={
                        "user_id": user_id,
                        "username": username,
                        "provider": type(self.user_provider).__name__,
                    },
                    exc_info=True,
                )
                return None

        logger.warning(
            "Fallback authorization denied - user not found",
            extra={"user_id": user_id, "username": username},
        )
        return None

    def _check_fallback_rules(
        self,
        user_id: str,
        username: str,
        relation: str,
        resource: str,
        user_roles: list[str],
    ) -> bool:
        """Apply fallback authorization rules."""
        # Admin users have access to everything
        if "admin" in user_roles:
            logger.info(
                "Fallback authorization granted - admin user",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "relation": relation,
                    "resource": resource,
                },
            )
            return True

        # Tool executor check
        if relation == "executor" and resource.startswith("tool:"):
            authorized = "premium" in user_roles or "user" in user_roles
            if authorized:
                logger.info(
                    "Fallback authorization granted - tool executor",
                    extra={
                        "user_id": user_id,
                        "username": username,
                        "relation": relation,
                        "resource": resource,
                        "roles": user_roles,
                    },
                )
            return authorized

        # Conversation access check
        if relation in ("viewer", "editor") and resource.startswith("conversation:"):
            return self._check_conversation_access(user_id, username, relation, resource)

        # Default deny
        logger.warning(
            "Fallback authorization denied - no matching rule",
            extra={
                "user_id": user_id,
                "username": username,
                "relation": relation,
                "resource": resource,
                "roles": user_roles,
            },
        )
        return False

    def _check_conversation_access(
        self,
        user_id: str,
        username: str,
        relation: str,
        resource: str,
    ) -> bool:
        """Check conversation access with ownership scoping."""
        thread_id = resource.split(":", 1)[1] if ":" in resource else ""

        # Allow default/empty thread
        if thread_id in ("default", ""):
            logger.info(
                "Fallback authorization granted - default conversation",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "relation": relation,
                    "resource": resource,
                },
            )
            return True

        # Check user ownership
        if thread_id.startswith(f"{username}_"):
            logger.info(
                "Fallback authorization granted - user-owned conversation",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "relation": relation,
                    "resource": resource,
                },
            )
            return True

        # Also support user:username prefix in thread_id
        user_id_normalized = user_id.split(":")[-1] if ":" in user_id else user_id
        if thread_id.startswith(f"{user_id_normalized}_"):
            logger.info(
                "Fallback authorization granted - user-owned conversation (normalized)",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "relation": relation,
                    "resource": resource,
                },
            )
            return True

        # Deny access to other users' conversations
        logger.warning(
            "Fallback authorization denied conversation access",
            extra={
                "user_id": user_id,
                "username": username,
                "thread_id": thread_id,
                "relation": relation,
                "reason": "conversation_not_owned_by_user",
            },
        )
        return False
