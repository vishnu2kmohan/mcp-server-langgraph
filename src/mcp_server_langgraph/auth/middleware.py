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
from mcp_server_langgraph.auth.token_denylist import TokenDenylist
from mcp_server_langgraph.auth.user_provider import AuthResponse, InMemoryUserProvider, TokenVerification, UserProvider
from mcp_server_langgraph.auth.dpop import DPoPReplayCache, verify_dpop_proof
from mcp_server_langgraph.observability.telemetry import logger, tracer

# FastAPI imports for dependency injection (optional, only if using FastAPI endpoints)

try:
    from fastapi import Depends  # noqa: F401 (used in type hints)

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
        token_denylist: TokenDenylist | None = None,
        dpop_replay_cache: DPoPReplayCache | None = None,
        dpop_required: bool = False,
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
            token_denylist: Token denylist for immediate JWT revocation (OWASP best practice)
            dpop_replay_cache: DPoP jti replay cache for replay protection (RFC 9449)
            dpop_required: If True, ALL tokens require DPoP proof (strict mode, RFC 9449 Section 10).
                          If False (default), only tokens with cnf.jkt claim require DPoP.
        """
        self.secret_key = secret_key
        self.openfga = openfga_client
        self.session_store = session_store
        self.settings = settings
        self.token_denylist = token_denylist
        self.dpop_replay_cache = dpop_replay_cache
        self.dpop_required = dpop_required

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
                "denylist_enabled": token_denylist is not None,
                "dpop_enabled": dpop_replay_cache is not None,
                "dpop_required": dpop_required,
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
            except Exception as e:
                logger.debug("Operation failed: %s", e)

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

        Security:
        - Checks token denylist for immediate revocation (OWASP best practice)
        - Tokens added to denylist on logout are rejected here

        Args:
            token: JWT token to verify

        Returns:
            TokenVerification with validation result
        """
        # Delegate to user provider (returns Pydantic TokenVerification)
        result = await self.user_provider.verify_token(token)

        if result.valid and result.payload:
            # Check token denylist for immediate revocation (OWASP Session Management)
            if self.token_denylist:
                jti = result.payload.get("jti")
                if jti and await self.token_denylist.is_denied(jti):
                    logger.warning(
                        "Token rejected (in denylist)",
                        extra={"jti": jti[:8] + "..." if len(jti) > 8 else jti},
                    )
                    return TokenVerification(valid=False, error="Token has been revoked")

            logger.info("Token verified", extra={"sub": result.payload.get("sub")})
        else:
            logger.warning("Token verification failed", extra={"error": result.error})

        return result

    async def verify_token_with_dpop(
        self,
        token: str,
        dpop_proof: str | None,
        http_method: str,
        http_uri: str,
    ) -> TokenVerification:
        """
        Verify JWT token with optional DPoP (RFC 9449) sender-constraint verification.

        DPoP provides token binding by requiring clients to prove possession of a
        private key. This prevents token theft and replay attacks.

        Behavior (depends on self.dpop_required):
        - If dpop_required=True: ALL tokens require DPoP proof (strict mode)
        - If dpop_required=False (default):
          - Tokens with cnf.jkt claim (DPoP-bound): DPoP proof is REQUIRED
          - Tokens without cnf claim: DPoP proof is optional (verified if provided)

        Args:
            token: JWT access token to verify
            dpop_proof: DPoP proof JWT from request header (may be None)
            http_method: HTTP method of the request (GET, POST, etc.)
            http_uri: Full HTTP URI of the request

        Returns:
            TokenVerification with validation result
        """
        import hashlib
        import base64
        import json

        # First, verify the token itself
        result = await self.verify_token(token)
        if not result.valid or not result.payload:
            return result

        # Check if token is DPoP-bound (has cnf.jkt claim)
        cnf = result.payload.get("cnf")
        is_dpop_bound = cnf is not None and "jkt" in cnf

        # Check if DPoP is required (either by enforcement mode or token binding)
        dpop_required_for_this_request = self.dpop_required or is_dpop_bound

        if dpop_required_for_this_request and not dpop_proof:
            # DPoP is required (by enforcement or token binding) but no proof provided - reject
            reason = "enforcement mode" if self.dpop_required else "sender-constrained token"
            logger.warning(
                f"DPoP proof required ({reason}) but not provided",
                extra={
                    "sub": result.payload.get("sub"),
                    "dpop_required": self.dpop_required,
                    "is_dpop_bound": is_dpop_bound,
                },
            )
            return TokenVerification(
                valid=False,
                error=f"DPoP proof required ({reason})",
            )

        if dpop_proof:
            # Verify the DPoP proof
            dpop_result = verify_dpop_proof(
                proof=dpop_proof,
                http_method=http_method,
                http_uri=http_uri,
                access_token=token if is_dpop_bound else None,
                jti_cache=self.dpop_replay_cache,
            )

            if not dpop_result["valid"]:
                logger.warning(
                    "DPoP proof verification failed",
                    extra={
                        "error": dpop_result.get("error"),
                        "sub": result.payload.get("sub"),
                    },
                )
                return TokenVerification(
                    valid=False,
                    error=f"DPoP verification failed: {dpop_result.get('error', 'Unknown error')}",
                )

            # If token is DPoP-bound, verify the key thumbprint matches
            if is_dpop_bound and cnf:
                expected_jkt = cnf["jkt"]
                proof_jwk = dpop_result.get("jwk")

                if proof_jwk:
                    # Calculate thumbprint of the proof's JWK
                    canonical = json.dumps(
                        {
                            "crv": proof_jwk["crv"],
                            "kty": proof_jwk["kty"],
                            "x": proof_jwk["x"],
                            "y": proof_jwk["y"],
                        },
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    thumbprint = hashlib.sha256(canonical.encode()).digest()
                    actual_jkt = base64.urlsafe_b64encode(thumbprint).rstrip(b"=").decode()

                    if actual_jkt != expected_jkt:
                        logger.warning(
                            "DPoP key thumbprint mismatch",
                            extra={
                                "expected": expected_jkt[:8] + "...",
                                "actual": actual_jkt[:8] + "...",
                                "sub": result.payload.get("sub"),
                            },
                        )
                        return TokenVerification(
                            valid=False,
                            error="DPoP key thumbprint does not match token binding",
                        )

            logger.info(
                "Token verified with DPoP",
                extra={
                    "sub": result.payload.get("sub"),
                    "dpop_bound": is_dpop_bound,
                },
            )

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
# FastAPI Dependency Injection Support (Re-exports from dependencies.py)
# ============================================================================
# Phase 2.2 SRP decomposition: FastAPI dependencies extracted to dependencies.py
# Re-exported here for backward compatibility

if FASTAPI_AVAILABLE:
    from mcp_server_langgraph.auth.dependencies import (
        bearer_scheme,
        get_auth_middleware,
        get_current_user,
        get_current_user_with_auth,
        require_auth_dependency,
        set_global_auth_middleware,
    )

    __all__ = [
        "AuthMiddleware",
        "AuthorizationResult",
        "normalize_user_id",
        "require_auth",
        "verify_token",
        "set_global_auth_middleware",
        "get_auth_middleware",
        "get_current_user",
        "get_current_user_with_auth",
        "require_auth_dependency",
        "bearer_scheme",
    ]
else:
    __all__ = [
        "AuthMiddleware",
        "AuthorizationResult",
        "normalize_user_id",
        "require_auth",
        "verify_token",
    ]
