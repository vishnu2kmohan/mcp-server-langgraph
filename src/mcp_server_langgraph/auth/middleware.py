"""
Authentication and Authorization middleware with OpenFGA integration

Now supports:
- Pluggable user providers (InMemory, Keycloak, custom)
- Session management (Token-based or Session-based)
- Fine-grained authorization via OpenFGA

Architecture (Phase 2.1 SRP decomposition):
- AuthorizationService: Handles authorization logic (auth/authorization.py)
- MockResourceGenerator: Handles mock data for dev/test (auth/mock_resources.py)
- AuthMiddleware: Facade coordinating authentication, authorization, and sessions
"""

from functools import wraps
from typing import Any, Optional, cast

from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.auth.authorization import AuthorizationService
from mcp_server_langgraph.auth.mock_resources import MockResourceGenerator
from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.auth.session import SessionData, SessionStore
from mcp_server_langgraph.auth.user_provider import AuthResponse, InMemoryUserProvider, TokenVerification, UserProvider
from mcp_server_langgraph.observability.telemetry import logger, tracer

# FastAPI imports for dependency injection (optional, only if using FastAPI endpoints)
try:
    from fastapi import Depends, HTTPException, Request, status  # noqa: F401 (Depends used at line 929, 970)
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

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
    reason: str | None = Field(None, description="Reason for denial if not authorized")
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthorizationResult":
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
        secret_key: str | None = None,
        openfga_client: OpenFGAClient | None = None,
        user_provider: UserProvider | None = None,
        session_store: SessionStore | None = None,
        settings: Any | None = None,
    ):
        """
        Initialize AuthMiddleware

        Args:
            secret_key: Secret key for JWT tokens (used by InMemoryUserProvider).
                       Must be provided via environment variable or settings.
            openfga_client: OpenFGA client for authorization
            user_provider: User provider instance (defaults to InMemoryUserProvider for backward compatibility)
            session_store: Session store for session-based authentication (optional)
            settings: Application settings (for authorization fallback control)
        """
        self.secret_key = secret_key
        self.openfga = openfga_client
        self.session_store = session_store
        self.settings = settings

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

        # Phase 2.1 SRP: Create authorization service (delegates to separate module)
        # Cast users_db to dict[str, dict[str, Any]] since UserDBEntry is structurally compatible
        self._authorization_service = AuthorizationService(
            openfga_client=openfga_client,
            settings=settings,
            user_provider=user_provider,
            users_db=cast(dict[str, dict[str, Any]], self.users_db),
        )

        # Phase 2.1 SRP: Create mock resource generator (delegates to separate module)
        self._mock_resource_generator = MockResourceGenerator()

        logger.info(
            "AuthMiddleware initialized",
            extra={
                "provider_type": type(user_provider).__name__,
                "openfga_enabled": openfga_client is not None,
                "session_enabled": session_store is not None,
                "allow_auth_fallback": getattr(settings, "allow_auth_fallback", None) if settings else None,
            },
        )

    async def authenticate(self, username: str, password: str | None = None) -> AuthResponse:
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
                from mcp_server_langgraph.core.security import sanitize_for_logging

                logger.info(
                    "User authenticated",
                    extra=sanitize_for_logging({"username": username, "user_id": result.user_id}),
                )
            else:
                from mcp_server_langgraph.core.security import sanitize_for_logging

                logger.warning(
                    "Authentication failed", extra=sanitize_for_logging({"username": username, "reason": result.reason})
                )

            return result

    async def authorize(self, user_id: str, relation: str, resource: str, context: dict[str, Any] | None = None) -> bool:
        """
        Check if user is authorized using OpenFGA

        Delegates to AuthorizationService (Phase 2.1 SRP decomposition).

        Args:
            user_id: User identifier (e.g., "user:alice")
            relation: Relation to check (e.g., "executor", "viewer")
            resource: Resource identifier (e.g., "tool:chat")
            context: Additional context for authorization

        Returns:
            True if authorized, False otherwise
        """
        # Delegate to AuthorizationService (Phase 2.1 SRP)
        return await self._authorization_service.authorize(
            user_id=user_id,
            relation=relation,
            resource=resource,
            context=context,
        )

    def _get_mock_resources(self, user_id: str, relation: str, resource_type: str) -> list[str]:
        """
        Get mock resources for development/testing when OpenFGA is not available.

        Delegates to MockResourceGenerator (Phase 2.1 SRP decomposition).

        Args:
            user_id: User identifier (used to scope conversation resources)
            relation: Relation to check (e.g., "executor", "viewer")
            resource_type: Type of resources (e.g., "tool", "conversation")

        Returns:
            List of mock resource identifiers scoped to the user
        """
        # Delegate to MockResourceGenerator (Phase 2.1 SRP)
        return self._mock_resource_generator.get_resources(
            user_id=user_id,
            relation=relation,
            resource_type=resource_type,
        )

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
            # In development mode, return mock data for better developer experience
            # SECURITY: Mock data only enabled when explicitly configured (defaults to dev-only)
            try:
                from mcp_server_langgraph.core.config import settings

                if settings.get_mock_authorization_enabled():
                    logger.info(
                        "OpenFGA not available, using mock resources",
                        extra={
                            "user_id": user_id,
                            "relation": relation,
                            "resource_type": resource_type,
                            "environment": settings.environment,
                        },
                    )
                    return self._get_mock_resources(user_id, relation, resource_type)
            except Exception:
                pass  # If settings not available, fall through to empty list

            logger.warning("OpenFGA not available for resource listing, no mock data enabled")
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
        msg = f"Token creation not supported for provider type: {type(self.user_provider).__name__}"
        raise ValueError(msg)

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
        roles: list[str],
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str | None:
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

    async def get_session(self, session_id: str) -> SessionData | None:
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

    async def refresh_session(self, session_id: str, ttl_seconds: int | None = None) -> bool:
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

    async def list_user_sessions(self, user_id: str) -> list[SessionData]:
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


def require_auth(  # type: ignore[no-untyped-def]
    relation: str | None = None,
    resource: str | None = None,
    openfga_client: OpenFGAClient | None = None,
    auth_middleware: Optional["AuthMiddleware"] = None,
):
    """
    Decorator for requiring authentication/authorization

    Args:
        relation: Required relation (e.g., "executor")
        resource: Resource to check access to
        openfga_client: OpenFGA client instance
        auth_middleware: Optional AuthMiddleware instance (for testing with pre-seeded users)
    """

    def decorator(func) -> None:  # type: ignore[no-untyped-def]
        @wraps(func)
        async def wrapper(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            # Use provided auth_middleware or create new instance
            auth = auth_middleware if auth_middleware is not None else AuthMiddleware(openfga_client=openfga_client)
            username = kwargs.get("username")
            password = kwargs.get("password")
            user_id = kwargs.get("user_id")

            if not username and not user_id:
                msg = "Authentication required"
                raise PermissionError(msg)

            # Authenticate
            if username:
                auth_result = await auth.authenticate(username, password)
                if not auth_result.authorized:
                    msg = "Authentication failed"
                    raise PermissionError(msg)
                user_id = auth_result.user_id

            # Authorize if relation and resource specified
            if relation and resource:
                if not await auth.authorize(user_id, relation, resource):  # type: ignore[arg-type]
                    msg = f"Not authorized: {user_id} cannot {relation} {resource}"
                    raise PermissionError(msg)

            # Add user_id to kwargs if authenticated
            kwargs["user_id"] = user_id
            return await func(*args, **kwargs)  # type: ignore[no-any-return]

        return wrapper  # type: ignore[return-value]

    return decorator


async def verify_token(token: str, secret_key: str | None = None) -> TokenVerification:
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


# ============================================================================
# FastAPI Dependency Injection Support
# ============================================================================

if FASTAPI_AVAILABLE:  # noqa: C901
    # Global auth middleware instance (set by application)
    _global_auth_middleware: AuthMiddleware | None = None

    def set_global_auth_middleware(auth: AuthMiddleware) -> None:
        """
        Set global auth middleware instance for FastAPI dependencies.

        This should be called during application startup.

        Args:
            auth: AuthMiddleware instance configured with user provider, OpenFGA, etc.
        """
        global _global_auth_middleware
        _global_auth_middleware = auth

    def get_auth_middleware() -> AuthMiddleware:
        """
        Get global auth middleware instance.

        Returns:
            AuthMiddleware instance

        Raises:
            RuntimeError: If auth middleware not initialized
        """
        if _global_auth_middleware is None:
            msg = "Auth middleware not initialized. Call set_global_auth_middleware() during app startup."
            raise RuntimeError(msg)
        return _global_auth_middleware

    # HTTP Bearer security scheme for JWT tokens
    bearer_scheme = HTTPBearer(auto_error=False)

    async def get_current_user(
        request: Request,
    ) -> dict[str, Any]:
        """
        FastAPI dependency for extracting authenticated user from request.

        Supports multiple authentication methods:
        1. JWT token in Authorization header (Bearer token)
        2. User already set in request.state.user (by middleware)

        Args:
            request: FastAPI request object

        Returns:
            User dict with user_id, username, roles, etc.

        Raises:
            HTTPException: If authentication fails (401)
        """
        # Check if user already set by middleware
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user  # type: ignore[no-any-return]

        # Extract bearer token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

        # Try to authenticate with Bearer token
        if token:
            auth = get_auth_middleware()
            verification = await auth.verify_token(token)

            if verification.valid and verification.payload:
                # Extract username: prefer preferred_username (Keycloak) over username over sub
                # Keycloak uses UUID in 'sub', but OpenFGA needs 'user:username' format
                # Extract Keycloak UUID from sub claim (required for Admin API calls)
                keycloak_id = verification.payload.get("sub")

                # Priority: preferred_username (Keycloak) > username (InMemory) > extract from sub (fallback)
                username = verification.payload.get("preferred_username") or verification.payload.get("username")
                if not username:
                    # Fallback to extracting username from sub (for non-Keycloak IdPs without username field)
                    sub = keycloak_id or "unknown"
                    # If sub is in "user:username" format, extract username
                    if sub.startswith("user:"):
                        id_part = sub.replace("user:", "")
                        # Handle worker-safe IDs (e.g., "user:test_gw0_charlie" → "charlie")
                        import re

                        match = re.match(r"test_gw\d+_(.*)", id_part)
                        username = match.group(1) if match else id_part
                    else:
                        username = sub

                # For user_id, use sub directly if it's already in "user:*" format, otherwise normalize from username
                # This preserves worker-safe IDs like "user:test_gw0_alice" from InMemoryUserProvider tokens
                if keycloak_id and keycloak_id.startswith("user:"):
                    user_id = keycloak_id  # Use sub directly (preserves worker-safe IDs)
                else:
                    # Normalize to "user:username" format for OpenFGA compatibility
                    user_id = f"user:{username}" if not username.startswith("user:") else username

                # Extract roles from Keycloak JWT structure
                # Keycloak can put roles in multiple places:
                # 1. realm_access.roles - realm-level roles
                # 2. resource_access.<client>.roles - client-level roles
                # 3. roles - sometimes mapped directly (InMemoryUserProvider)
                roles: list[str] = []
                payload = verification.payload

                # Check direct roles first (InMemoryUserProvider)
                if payload.get("roles"):
                    roles = payload.get("roles", [])
                else:
                    # Extract from Keycloak realm_access structure
                    realm_access = payload.get("realm_access", {})
                    if realm_access and isinstance(realm_access, dict):
                        roles.extend(realm_access.get("roles", []))

                    # Also check resource_access for client-specific roles
                    resource_access = payload.get("resource_access", {})
                    if resource_access and isinstance(resource_access, dict):
                        for client_roles in resource_access.values():
                            if isinstance(client_roles, dict):
                                roles.extend(client_roles.get("roles", []))

                user_data = {
                    "user_id": user_id,
                    "keycloak_id": keycloak_id,  # Raw UUID for Keycloak Admin API
                    "username": username,
                    "roles": roles,
                    "email": payload.get("email"),
                }
                # Cache in request state for subsequent calls
                request.state.user = user_data
                return user_data
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {verification.error}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # No authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def get_current_user_with_auth(
        user: dict[str, Any],
        relation: str | None = None,
        resource: str | None = None,
    ) -> dict[str, Any]:
        """
        FastAPI dependency for authenticated + authorized user.

        Use this when you need both authentication and authorization.

        Example:
            @app.get("/protected")
            async def protected_endpoint(
                user: Dict[str, Any] = Depends(
                    lambda: get_current_user_with_auth(relation="viewer", resource="tool:chat")
                )
            ):
                return {"user": user}

        Args:
            user: User dict from get_current_user dependency
            relation: Required relation (e.g., "executor", "viewer")
            resource: Resource to check access to (e.g., "tool:chat")

        Returns:
            User dict if authorized

        Raises:
            HTTPException: If authorization fails (403)
        """
        if relation and resource:
            auth = get_auth_middleware()
            user_id = user.get("user_id", "")

            authorized = await auth.authorize(user_id=user_id, relation=relation, resource=resource)

            if not authorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not authorized: {user_id} cannot {relation} {resource}",
                )

        return user

    def require_auth_dependency(relation: str | None = None, resource: str | None = None) -> None:
        """
        Create a FastAPI dependency for authentication + authorization.

        This replaces the @require_auth decorator for FastAPI routes.

        Example:
            from fastapi import Depends

            @app.get("/tools")
            async def list_tools(user: Dict = Depends(require_auth_dependency(relation="executor", resource="tool:*"))):
                return {"tools": [...]}

        Args:
            relation: Required relation (e.g., "executor")
            resource: Resource to check access to

        Returns:
            FastAPI dependency function
        """

        async def dependency(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = bearer_scheme,  # type: ignore[assignment]
        ) -> dict[str, Any]:
            # Get authenticated user
            user = await get_current_user(request)

            # Check authorization if required
            if relation and resource:
                auth = get_auth_middleware()
                authorized = await auth.authorize(user_id=user["user_id"], relation=relation, resource=resource)

                if not authorized:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not authorized: {user['user_id']} cannot {relation} {resource}",
                    )

            return user

        return dependency  # type: ignore[return-value]
