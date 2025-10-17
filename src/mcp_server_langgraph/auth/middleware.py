"""
Authentication and Authorization middleware with OpenFGA integration

Now supports:
- Pluggable user providers (InMemory, Keycloak, custom)
- Session management (Token-based or Session-based)
- Fine-grained authorization via OpenFGA
"""

from functools import wraps
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.session import SessionData, SessionStore
from mcp_server_langgraph.auth.user_provider import AuthResponse, InMemoryUserProvider, TokenVerification, UserProvider
from mcp_server_langgraph.observability.telemetry import logger, tracer

# ============================================================================
# Helper Functions
# ============================================================================


def normalize_user_id(user_id: str) -> str:
    """
    Normalize user_id to handle multiple formats.

    Accepts:
    - Plain usernames: "alice" → "alice"
    - Prefixed IDs: "user:alice" → "alice"
    - Other prefixes: "uid:123" → "123"

    This allows clients to use either format:
    - OpenFGA format (user:alice)
    - Simple username format (alice)

    Args:
        user_id: User identifier in any supported format

    Returns:
        Normalized username (without prefix)
    """
    if not user_id:
        return user_id

    # If contains colon, extract the part after the colon
    if ":" in user_id:
        return user_id.split(":", 1)[1]

    # Otherwise, return as-is
    return user_id


# ============================================================================
# Pydantic Models for Middleware Operations
# ============================================================================


class AuthorizationResult(BaseModel):
    """
    Type-safe authorization check result

    Returned from authorize() operations.
    """

    authorized: bool = Field(..., description="Whether access is authorized")
    user_id: str = Field(..., description="User identifier that was checked")
    relation: str = Field(..., description="Relation that was checked")
    resource: str = Field(..., description="Resource that was checked")
    reason: Optional[str] = Field(None, description="Reason for denial if not authorized")
    used_fallback: bool = Field(default=False, description="Whether fallback authorization was used")

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "authorized": True,
                "user_id": "user:alice",
                "relation": "executor",
                "resource": "tool:chat",
                "reason": None,
                "used_fallback": False,
            }
        },
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthorizationResult":
        """Create AuthorizationResult from dictionary"""
        return cls(**data)


class AuthMiddleware:
    """
    Authentication and authorization handler with OpenFGA

    Combines authentication (via pluggable user providers) with fine-grained
    relationship-based authorization using OpenFGA.

    Supports multiple authentication backends:
    - InMemoryUserProvider (development/testing)
    - KeycloakUserProvider (production)
    - Custom providers
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        openfga_client: Optional[OpenFGAClient] = None,
        user_provider: Optional[UserProvider] = None,
        session_store: Optional[SessionStore] = None,
    ):
        """
        Initialize AuthMiddleware

        Args:
            secret_key: Secret key for JWT tokens (used by InMemoryUserProvider).
                       Must be provided via environment variable or settings.
            openfga_client: OpenFGA client for authorization
            user_provider: User provider instance (defaults to InMemoryUserProvider for backward compatibility)
            session_store: Session store for session-based authentication (optional)
        """
        self.secret_key = secret_key
        self.openfga = openfga_client
        self.session_store = session_store

        # Use provided user provider or default to in-memory for backward compatibility
        if user_provider is None:
            logger.info("No user provider specified, defaulting to InMemoryUserProvider")
            user_provider = InMemoryUserProvider(secret_key=secret_key)

        self.user_provider = user_provider

        # For backward compatibility: expose users_db if using InMemoryUserProvider
        if isinstance(user_provider, InMemoryUserProvider):
            self.users_db = user_provider.users_db
        else:
            self.users_db = {}  # Empty dict for non-inmemory providers

        logger.info(
            "AuthMiddleware initialized",
            extra={
                "provider_type": type(user_provider).__name__,
                "openfga_enabled": openfga_client is not None,
                "session_enabled": session_store is not None,
            },
        )

    async def authenticate(self, username: str, password: Optional[str] = None) -> AuthResponse:
        """
        Authenticate user by username

        Args:
            username: Username to authenticate (accepts both "alice" and "user:alice" formats)
            password: Password (required for some providers like Keycloak)

        Returns:
            AuthResponse with authentication result
        """
        with tracer.start_as_current_span("auth.authenticate") as span:
            # Normalize username to handle both "alice" and "user:alice" formats
            normalized_username = normalize_user_id(username)
            span.set_attribute("auth.username", normalized_username)

            # Delegate to user provider (returns Pydantic AuthResponse)
            result = await self.user_provider.authenticate(normalized_username, password)

            if result.authorized:
                logger.info("User authenticated", extra={"username": username, "user_id": result.user_id})
            else:
                logger.warning("Authentication failed", extra={"username": username, "reason": result.reason})

            return result

    async def authorize(self, user_id: str, relation: str, resource: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if user is authorized using OpenFGA

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
                        user=user_id, relation=relation, object=resource, context=context
                    )

                    span.set_attribute("auth.authorized", authorized)
                    logger.info(
                        "Authorization check (OpenFGA)",
                        extra={"user_id": user_id, "relation": relation, "resource": resource, "authorized": authorized},
                    )

                    return authorized

                except Exception as e:
                    logger.error(
                        f"OpenFGA authorization check failed: {e}",
                        extra={"user_id": user_id, "relation": relation, "resource": resource},
                        exc_info=True,
                    )
                    # Fail closed - deny access on error
                    return False

            # Fallback: simple permission check
            logger.warning("OpenFGA not available, using fallback authorization")

            # Extract username from user_id
            username = user_id.split(":")[-1] if ":" in user_id else user_id

            if username not in self.users_db:
                return False

            user = self.users_db[username]

            # Admin users have access to everything
            if "admin" in user["roles"]:
                return True

            # Basic resource-based checks
            if relation == "executor" and resource.startswith("tool:"):
                return "premium" in user["roles"] or "user" in user["roles"]

            if relation == "viewer" and resource.startswith("conversation:"):
                # Users can view their own conversations
                return True

            return False

    async def list_accessible_resources(self, user_id: str, relation: str, resource_type: str) -> list[str]:
        """
        List all resources user has access to

        Args:
            user_id: User identifier
            relation: Relation to check (e.g., "executor", "viewer")
            resource_type: Type of resources (e.g., "tool", "conversation")

        Returns:
            List of accessible resource identifiers
        """
        if not self.openfga:
            logger.warning("OpenFGA not available for resource listing")
            return []

        try:
            resources = await self.openfga.list_objects(user=user_id, relation=relation, object_type=resource_type)

            logger.info(
                "Listed accessible resources",
                extra={"user_id": user_id, "relation": relation, "resource_type": resource_type, "count": len(resources)},
            )

            return resources

        except Exception as e:
            logger.error(f"Failed to list accessible resources: {e}", exc_info=True)
            return []

    def create_token(self, username: str, expires_in: int = 3600) -> str:
        """
        Create JWT token for user (InMemoryUserProvider only)

        For Keycloak provider, tokens are issued by Keycloak itself.

        Args:
            username: Username
            expires_in: Token expiration in seconds

        Returns:
            JWT token string

        Raises:
            ValueError: If user not found or provider doesn't support token creation
        """
        # Check if provider supports token creation
        if isinstance(self.user_provider, InMemoryUserProvider):
            return self.user_provider.create_token(username, expires_in)

        # For other providers, we can't create tokens
        raise ValueError(f"Token creation not supported for provider type: {type(self.user_provider).__name__}")

    async def verify_token(self, token: str) -> TokenVerification:
        """
        Verify and decode JWT token

        Supports both self-issued tokens (InMemoryUserProvider) and
        Keycloak-issued tokens (KeycloakUserProvider).

        Args:
            token: JWT token to verify

        Returns:
            TokenVerification with validation result
        """
        # Delegate to user provider (returns Pydantic TokenVerification)
        result = await self.user_provider.verify_token(token)

        if result.valid:
            logger.info("Token verified", extra={"sub": result.payload.get("sub") if result.payload else None})
        else:
            logger.warning("Token verification failed", extra={"error": result.error})

        return result

    # Session Management Methods

    async def create_session(
        self,
        user_id: str,
        username: str,
        roles: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> Optional[str]:
        """
        Create a new session

        Args:
            user_id: User identifier
            username: Username
            roles: User roles
            metadata: Additional session metadata
            ttl_seconds: Session TTL in seconds

        Returns:
            Session ID or None if session store not configured
        """
        if not self.session_store:
            logger.warning("Session store not configured, cannot create session")
            return None

        with tracer.start_as_current_span("auth.create_session") as span:
            span.set_attribute("user.id", user_id)

            session_id = await self.session_store.create(
                user_id=user_id, username=username, roles=roles, metadata=metadata, ttl_seconds=ttl_seconds
            )

            logger.info("Session created", extra={"session_id": session_id, "user_id": user_id})
            return session_id

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session data

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        if not self.session_store:
            return None

        with tracer.start_as_current_span("auth.get_session") as span:
            span.set_attribute("session.id", session_id)

            session = await self.session_store.get(session_id)

            if session:
                logger.debug(f"Session retrieved: {session_id}")
            else:
                logger.debug(f"Session not found or expired: {session_id}")

            return session

    async def refresh_session(self, session_id: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Refresh session expiration

        Args:
            session_id: Session identifier
            ttl_seconds: New TTL in seconds

        Returns:
            True if refreshed successfully
        """
        if not self.session_store:
            return False

        with tracer.start_as_current_span("auth.refresh_session") as span:
            span.set_attribute("session.id", session_id)

            refreshed = await self.session_store.refresh(session_id, ttl_seconds)

            if refreshed:
                logger.info(f"Session refreshed: {session_id}")
            else:
                logger.warning(f"Failed to refresh session: {session_id}")

            return refreshed

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke (delete) a session

        Args:
            session_id: Session identifier

        Returns:
            True if revoked successfully
        """
        if not self.session_store:
            return False

        with tracer.start_as_current_span("auth.revoke_session") as span:
            span.set_attribute("session.id", session_id)

            revoked = await self.session_store.delete(session_id)

            if revoked:
                logger.info(f"Session revoked: {session_id}")
            else:
                logger.warning(f"Session not found for revocation: {session_id}")

            return revoked

    async def list_user_sessions(self, user_id: str) -> List[SessionData]:
        """
        List all active sessions for a user

        Args:
            user_id: User identifier

        Returns:
            List of session data
        """
        if not self.session_store:
            return []

        with tracer.start_as_current_span("auth.list_user_sessions") as span:
            span.set_attribute("user.id", user_id)

            sessions = await self.session_store.list_user_sessions(user_id)

            logger.info(f"Listed {len(sessions)} sessions for user {user_id}")
            return sessions

    async def revoke_user_sessions(self, user_id: str) -> int:
        """
        Revoke all sessions for a user

        Args:
            user_id: User identifier

        Returns:
            Number of sessions revoked
        """
        if not self.session_store:
            return 0

        with tracer.start_as_current_span("auth.revoke_user_sessions") as span:
            span.set_attribute("user.id", user_id)

            count = await self.session_store.delete_user_sessions(user_id)

            logger.info(f"Revoked {count} sessions for user {user_id}")
            return count


def require_auth(
    relation: Optional[str] = None, resource: Optional[str] = None, openfga_client: Optional[OpenFGAClient] = None
):
    """
    Decorator for requiring authentication/authorization

    Args:
        relation: Required relation (e.g., "executor")
        resource: Resource to check access to
        openfga_client: OpenFGA client instance
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth = AuthMiddleware(openfga_client=openfga_client)
            username = kwargs.get("username")
            user_id = kwargs.get("user_id")

            if not username and not user_id:
                raise PermissionError("Authentication required")

            # Authenticate
            if username:
                auth_result = await auth.authenticate(username)
                if not auth_result.authorized:
                    raise PermissionError("Authentication failed")
                user_id = auth_result.user_id

            # Authorize if relation and resource specified
            if relation and resource:
                if not await auth.authorize(user_id, relation, resource):
                    raise PermissionError(f"Not authorized: {user_id} cannot {relation} {resource}")

            # Add user_id to kwargs if authenticated
            kwargs["user_id"] = user_id
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def verify_token(token: str, secret_key: Optional[str] = None) -> TokenVerification:
    """
    Standalone token verification function

    Args:
        token: JWT token to verify
        secret_key: Secret key for verification

    Returns:
        TokenVerification with validation result
    """
    auth = AuthMiddleware(secret_key=secret_key or "your-secret-key-change-in-production")
    return await auth.verify_token(token)
