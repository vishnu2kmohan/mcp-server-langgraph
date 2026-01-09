"""
User API

Provides /me, /login, /logout endpoints for authentication.

This endpoint is critical for the frontend persona detection system.
The frontend calls this on mount to detect the user's persona based on roles.

Authentication Flow:
- POST /login: Direct username/password authentication (ROPC flow)
- POST /logout: Token revocation (invalidates access/refresh tokens)
- GET /me: Get current user info with computed persona

Security:
- Logout adds token to denylist for immediate invalidation (OWASP best practice)
"""

from datetime import UTC, datetime
from typing import Any, Literal

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.middleware import get_current_user
from mcp_server_langgraph.auth.token_denylist import TokenDenylist
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.core.dependencies import get_openfga_client, get_token_denylist
from mcp_server_langgraph.observability.telemetry import logger

# WebSocket authorization requirements mapping
# Maps frontend permission key to (object_type, object_id, required_relation)
# These correspond to WebSocketConfig settings in ws_router.py
WEBSOCKET_PERMISSIONS_MAP: dict[str, tuple[str, str, str]] = {
    "alerts": ("dashboard", "alerts", "admin"),  # Admin only
    "notifications": ("chat", "notifications", "viewer"),
    "devtools": ("dashboard", "devtools", "viewer"),
    "audit": ("logs", "audit", "viewer"),
    "mcp_tasks": ("mcp", "websocket", "user"),
    "mcp_aggregated": ("mcp", "aggregated-capabilities", "viewer"),
    "connections_health": ("mcp_connection", "health", "viewer"),
    "connections_realtime": ("mcp_connection", "realtime", "viewer"),
    "heart_metrics": ("observability", "heart", "viewer"),
    "cost_tracking": ("cost", "usage", "viewer"),
    "budget_alerts": ("cost", "budget", "viewer"),
    "agent_requests": ("workflow", "hitl", "editor"),
    "ai_suggestions": ("ai", "suggestions", "user"),
    "orchestrator_status": ("ai", "orchestrator", "viewer"),
    "traces": ("traces", "stream", "viewer"),
}

user_router = APIRouter(tags=["user"])


# ============================================================================
# Request/Response Models
# ============================================================================


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    """Token response from login."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str | None = Field(None, description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: "UserInfoResponse" = Field(..., description="User information")


class LogoutRequest(BaseModel):
    """Logout request with optional refresh token."""

    refresh_token: str | None = Field(None, description="Refresh token to revoke (optional)")


class LogoutResponse(BaseModel):
    """Logout response."""

    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Status message")


class WebSocketPermissions(BaseModel):
    """
    WebSocket endpoint permissions for the current user.

    Contains boolean permissions for each WebSocket endpoint, determined via
    OpenFGA batch check. Enables frontend to conditionally connect only to
    authorized WebSocket endpoints, preventing unnecessary connection attempts.

    Reference: GitHub issue - Chat doesn't load due to alert WS auth failure
    """

    # Dashboard WebSockets
    alerts: bool = Field(default=False, description="Admin-only alert stream (/ws/alerts)")
    devtools: bool = Field(default=False, description="DevTools panel (/ws/devtools)")

    # Chat WebSockets
    notifications: bool = Field(default=False, description="Notifications stream (/ws/notifications)")

    # Audit/Logs WebSockets
    audit: bool = Field(default=False, description="Audit event stream (/ws/audit)")

    # MCP WebSockets
    mcp_tasks: bool = Field(default=False, description="MCP task updates (/ws/mcp/tasks)")
    mcp_aggregated: bool = Field(default=False, description="MCP capability changes (/ws/mcp/aggregated)")

    # Connection WebSockets
    connections_health: bool = Field(default=False, description="Connection health (/ws/connections/health)")
    connections_realtime: bool = Field(default=False, description="Connection realtime (/ws/connections/realtime)")

    # Observability WebSockets
    heart_metrics: bool = Field(default=False, description="HEART metrics stream (/ws/metrics/heart)")
    traces: bool = Field(default=False, description="Trace span stream (/ws/traces)")

    # Cost WebSockets
    cost_tracking: bool = Field(default=False, description="Cost tracking (/ws/usage/cost)")
    budget_alerts: bool = Field(default=False, description="Budget alerts (/ws/budget/alerts)")

    # Agent WebSockets
    agent_requests: bool = Field(default=False, description="HITL agent requests (/ws/agents/requests)")

    # AI WebSockets
    ai_suggestions: bool = Field(default=False, description="AI suggestions (/ws/ai/suggestions)")
    orchestrator_status: bool = Field(default=False, description="Orchestrator status (/ws/orchestrator/status)")


class WebSocketPermissionsResponse(BaseModel):
    """
    Container for WebSocket permissions with metadata.

    Includes caching information to enable frontend to cache permissions
    and reduce OpenFGA load.
    """

    websocket_permissions: WebSocketPermissions = Field(
        default_factory=WebSocketPermissions,
        description="Permission flags for each WebSocket endpoint",
    )
    cached: bool = Field(default=False, description="Whether result was served from cache")
    expires_at: str | None = Field(None, description="ISO8601 timestamp when permissions expire")


class UserInfoResponse(BaseModel):
    """
    Current user information response.

    Extended in Sprint 4 to include persona-related fields for frontend RBAC:
    - api_version: For client compatibility detection
    - sub_persona: Specific persona variant (alice-builder, etc.)
    - visible_modules: List of modules this persona can access
    - feature_flags: Feature flags for this user/persona

    Extended to include websocket_permissions for frontend-aware WebSocket auth:
    - websocket_permissions: Boolean permissions for each WebSocket endpoint
    """

    user_id: str = Field(..., description="User identifier in OpenFGA format (user:username)")
    username: str = Field(..., description="Username")
    email: str | None = Field(None, description="Email address")
    first_name: str | None = Field(None, description="First name from Keycloak (given_name claim)")
    last_name: str | None = Field(None, description="Last name from Keycloak (family_name claim)")
    display_name: str | None = Field(None, description="Full display name from Keycloak (name claim)")
    roles: list[str] = Field(default_factory=list, description="User roles from Keycloak")
    persona: Literal["admin", "developer", "user"] = Field(..., description="Computed persona for frontend RBAC")
    keycloak_id: str | None = Field(None, description="Keycloak UUID (for admin operations)")

    # Sprint 4: Extended persona fields (backward compatible - all optional with defaults)
    api_version: str = Field(default="2", description="API version for client compatibility detection")
    sub_persona: str | None = Field(None, description="Specific persona variant (alice-builder, alice-analyst, etc.)")
    visible_modules: list[str] = Field(default_factory=list, description="List of modules this persona can access")
    feature_flags: dict[str, bool] = Field(default_factory=dict, description="Feature flags for this user/persona")

    # WebSocket permissions (enables frontend to only connect to authorized endpoints)
    websocket_permissions: WebSocketPermissions | None = Field(
        default=None,
        description="Permissions for each WebSocket endpoint (prevents unauthorized connection attempts)",
    )


class PersonaPreferencesUpdate(BaseModel):
    """
    Model for updating persona-related preferences.

    Used by PATCH /me/preferences endpoint.
    """

    sub_persona: str | None = Field(None, description="New sub-persona selection")
    feature_flags: dict[str, bool] | None = Field(None, description="Feature flag updates")


# ============================================================================
# Persona/Module Mappings
# ============================================================================

# Mapping of sub-persona to visible modules
# This is the server-side source of truth, mirroring frontend ActivityBar NAV_ITEMS
# Must use normalized IDs that match frontend for consistent RBAC
# Module IDs: cost (not costs), workflows (not flows)
PERSONA_VISIBLE_MODULES: dict[str, list[str]] = {
    # === ADMIN PERSONAS (full platform access) ===
    "admin": [
        # Core Work
        "projects",
        "chat",
        "workflows",
        # AI & Data
        "agents",
        "mcp",
        "vectors",
        "files",
        "skills",
        # Observability
        "traces",
        "observability",
        "cost",
        # Admin
        "admin",
        "audit",
        "compliance",
        # Bottom items
        "settings",
        "help",
    ],
    "security-admin": [
        # Admin-focused access
        "admin",
        "audit",
        "compliance",
        "settings",
        "help",
    ],
    "auditor": [
        # Audit-only access
        "audit",
        "compliance",
        "help",
    ],
    # === ALICE PERSONAS (developer variants) ===
    "alice-builder": [
        # Core Work
        "projects",
        "chat",
        "workflows",
        # AI & Data
        "agents",
        "mcp",
        "vectors",
        "files",
        "skills",
        # Observability
        "traces",
        "cost",
        # Bottom items
        "settings",
        "help",
    ],
    "alice-analyst": [
        # Core Work
        "projects",
        "chat",
        # Observability focus
        "traces",
        "observability",
        "cost",
        # Bottom items
        "settings",
        "help",
    ],
    "alice-devops": [
        # Core Work
        "projects",
        "chat",
        # Infrastructure focus
        "agents",
        "mcp",
        "connections",
        "traces",
        # Bottom items
        "settings",
        "help",
    ],
    # === BOB PERSONAS (end user) ===
    "compliance-officer": [
        # Compliance-focused access
        "audit",
        "compliance",
        "help",
    ],
    "bob": [
        # Core Work only - limited access
        "projects",
        "chat",
        "workflows",
        # Skills - read-only browsing (viewer access via OpenFGA)
        "skills",
        "help",
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================


def get_visible_modules_for_persona(persona: str) -> list[str]:
    """
    Get the list of visible modules for a given persona.

    Args:
        persona: The sub-persona identifier (e.g., 'admin', 'alice-builder', 'bob')

    Returns:
        List of module names this persona can access, or empty list if unknown persona
    """
    return PERSONA_VISIBLE_MODULES.get(persona, [])


# Deprecated module ID mappings (for backward compatibility)
# These IDs should not be used in new code
DEPRECATED_MODULE_ID_MAP: dict[str, str] = {
    "flows": "workflows",
    "costs": "cost",
    "metrics": "observability",
}


def normalize_module_id(module_id: str) -> str:
    """
    Normalize a module ID to the canonical form.

    Converts deprecated module IDs to their normalized equivalents:
    - 'flows' -> 'workflows'
    - 'costs' -> 'cost'
    - 'metrics' -> 'observability'

    Args:
        module_id: The module ID to normalize

    Returns:
        The normalized module ID

    Example:
        >>> normalize_module_id("flows")
        "workflows"
        >>> normalize_module_id("chat")
        "chat"
    """
    normalized = DEPRECATED_MODULE_ID_MAP.get(module_id, module_id)
    if normalized != module_id:
        logger.warning(
            f"Deprecated module ID '{module_id}' used, normalized to '{normalized}'",
            extra={
                "deprecated_id": module_id,
                "normalized_id": normalized,
                "hint": "Use normalized module IDs: workflows, cost, observability",
            },
        )
    return normalized


# Mapping of base persona to allowed sub-personas
# Higher tiers can use lower tier personas (admin can use all, developer can use user tier)
BASE_TO_SUB_PERSONAS: dict[str, list[str]] = {
    "admin": [
        # Admin tier
        "admin",
        "security-admin",
        "auditor",
        # Developer tier (admin can use these too)
        "alice-builder",
        "alice-analyst",
        "alice-devops",
        # User tier
        "bob",
        "compliance-officer",
    ],
    "developer": [
        # Developer tier
        "alice-builder",
        "alice-analyst",
        "alice-devops",
        # User tier
        "bob",
        "compliance-officer",
    ],
    "user": [
        # User tier only
        "bob",
        "compliance-officer",
    ],
}


def get_sub_personas_for_base(base_persona: str) -> list[str]:
    """
    Get the list of valid sub-personas for a base persona.

    Higher-tier personas have access to lower-tier sub-personas:
    - admin: can use admin, developer, and user sub-personas
    - developer: can use developer and user sub-personas
    - user: can only use user sub-personas

    Args:
        base_persona: The base persona (admin, developer, user)

    Returns:
        List of valid sub-persona identifiers
    """
    return BASE_TO_SUB_PERSONAS.get(base_persona, [])


def is_valid_sub_persona(base_persona: str, sub_persona: str) -> bool:
    """
    Check if a sub-persona is valid for a given base persona.

    Args:
        base_persona: The base persona (admin, developer, user)
        sub_persona: The sub-persona to validate

    Returns:
        True if the sub-persona is valid for the base persona
    """
    valid_subs = get_sub_personas_for_base(base_persona)
    return sub_persona in valid_subs


def compute_persona(roles: list[str]) -> Literal["admin", "developer", "user"]:
    """
    Compute persona from user roles.

    Priority: admin > developer > user

    This mirrors the frontend personaStore.detectPersona() logic to ensure
    consistent persona detection between backend and frontend.

    Args:
        roles: List of user roles from Keycloak JWT

    Returns:
        Computed persona: admin, developer, or user
    """
    if "admin" in roles:
        return "admin"
    if "developer" in roles:
        return "developer"
    return "user"


# ============================================================================
# Endpoints
# ============================================================================


# In-memory fallback for testing (when database is not available)
_persona_preferences_store: dict[str, dict[str, Any]] = {}
_use_database_store: bool = True  # Set to False in tests without database


def get_persona_preferences_store() -> dict[str, dict[str, Any]]:
    """Get the persona preferences store (for testing/fallback)."""
    return _persona_preferences_store


def set_persona_preferences_store(store: dict[str, dict[str, Any]] | None) -> None:
    """Set the persona preferences store (for testing)."""
    global _persona_preferences_store
    _persona_preferences_store = store if store is not None else {}


def set_use_database_store(use_db: bool) -> None:
    """Set whether to use database store (for testing)."""
    global _use_database_store
    _use_database_store = use_db


async def get_user_preferences_from_db(user_id: str) -> dict[str, Any]:
    """
    Get user preferences from PostgreSQL database.

    Falls back to in-memory store if database is not available.

    Args:
        user_id: User ID in OpenFGA format.

    Returns:
        Dict with sub_persona and feature_flags.
    """
    if not _use_database_store:
        # Use in-memory fallback for testing
        return _persona_preferences_store.get(user_id, {})

    try:
        from mcp_server_langgraph.core.dependencies import get_async_session
        from mcp_server_langgraph.storage.user.repository import UserPreferencesRepository

        async for session in get_async_session():
            repo = UserPreferencesRepository(session)
            prefs = await repo.get_preferences(user_id)
            if prefs:
                return {
                    "sub_persona": prefs.sub_persona,
                    "feature_flags": prefs.feature_flags,
                }
            return {}
    except Exception as e:
        # Fall back to in-memory store if database fails
        logger.warning(
            f"Failed to get preferences from database, using fallback: {e}",
            extra={"user_id": user_id},
        )
        return _persona_preferences_store.get(user_id, {})


async def save_user_preferences_to_db(
    user_id: str,
    sub_persona: str | None,
    feature_flags: dict[str, bool],
) -> None:
    """
    Save user preferences to PostgreSQL database.

    Falls back to in-memory store if database is not available.

    Args:
        user_id: User ID in OpenFGA format.
        sub_persona: Selected sub-persona.
        feature_flags: Feature flag overrides.
    """
    if not _use_database_store:
        # Use in-memory fallback for testing
        _persona_preferences_store[user_id] = {
            "sub_persona": sub_persona,
            "feature_flags": feature_flags,
        }
        return

    try:
        from mcp_server_langgraph.core.dependencies import get_async_session
        from mcp_server_langgraph.storage.user.models import UserPreferences
        from mcp_server_langgraph.storage.user.repository import UserPreferencesRepository

        async for session in get_async_session():
            repo = UserPreferencesRepository(session)
            prefs = UserPreferences(
                user_id=user_id,
                sub_persona=sub_persona,
                feature_flags=feature_flags,
            )
            await repo.upsert_preferences(prefs)
            return
    except Exception as e:
        # Fall back to in-memory store if database fails
        logger.warning(
            f"Failed to save preferences to database, using fallback: {e}",
            extra={"user_id": user_id},
        )
        _persona_preferences_store[user_id] = {
            "sub_persona": sub_persona,
            "feature_flags": feature_flags,
        }


async def get_websocket_permissions(user_id: str) -> WebSocketPermissions:
    """
    Get WebSocket permissions for a user via OpenFGA batch check.

    Checks all WebSocket endpoint permissions in parallel for efficiency.
    Falls back to fail-closed (all False) if OpenFGA is unavailable.

    Args:
        user_id: User identifier in OpenFGA format (e.g., "user:alice")

    Returns:
        WebSocketPermissions with boolean flags for each WebSocket endpoint.

    Example:
        >>> perms = await get_websocket_permissions("user:alice")
        >>> perms.alerts  # False (alice lacks admin on dashboard:alerts)
        >>> perms.notifications  # True (alice has viewer on chat:notifications)
    """
    import asyncio

    try:
        openfga_client = get_openfga_client()
    except Exception as e:
        logger.warning(
            f"OpenFGA client unavailable, returning fail-closed permissions: {e}",
            extra={"user_id": user_id},
        )
        return WebSocketPermissions()

    permissions: dict[str, bool] = {}

    async def check_single_permission(key: str, object_type: str, object_id: str, relation: str) -> tuple[str, bool]:
        """Check a single permission and return (key, result)."""
        try:
            resource = f"{object_type}:{object_id}"
            allowed = await openfga_client.check_permission(
                user=user_id,
                relation=relation,
                object=resource,
                critical=False,  # Fail-open for individual checks (resilience)
            )
            return (key, allowed)
        except Exception as e:
            logger.debug(
                f"Permission check failed for {key}, defaulting to False: {e}",
                extra={"user_id": user_id, "resource": f"{object_type}:{object_id}"},
            )
            return (key, False)

    # Run all permission checks in parallel
    tasks = [
        check_single_permission(key, object_type, object_id, relation)
        for key, (object_type, object_id, relation) in WEBSOCKET_PERMISSIONS_MAP.items()
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Permission check exception: {result}")
            continue
        key, allowed = result
        permissions[key] = allowed

    logger.info(
        "WebSocket permissions checked",
        extra={
            "user_id": user_id,
            "permissions": permissions,
            "allowed_count": sum(1 for v in permissions.values() if v),
            "total_count": len(WEBSOCKET_PERMISSIONS_MAP),
        },
    )

    return WebSocketPermissions(**permissions)


@user_router.get("/me")
async def get_me(
    user: dict[str, Any] = Depends(get_current_user),
) -> UserInfoResponse:
    """
    Get current authenticated user information.

    Returns the current user's info including:
    - user_id: OpenFGA-compatible user ID
    - username: Display username
    - email: Email address (if available)
    - roles: Keycloak roles
    - persona: Computed persona for frontend RBAC (admin/developer/user)
    - sub_persona: Selected sub-persona variant (Sprint 4)
    - visible_modules: Modules accessible to this persona (Sprint 4)
    - feature_flags: Feature flags for this user (Sprint 4)
    - api_version: API version for client compatibility (Sprint 4)
    - websocket_permissions: WebSocket endpoint permissions (Sprint 5)

    The frontend uses this endpoint on mount to:
    1. Detect user's persona based on roles
    2. Configure sidebar navigation items
    3. Enable/disable WebSocket connections based on permissions
    3. Set up route access control
    """
    roles = user.get("roles", [])
    persona = compute_persona(roles)
    user_id = user.get("user_id", "")

    # Get stored persona preferences from database
    prefs = await get_user_preferences_from_db(user_id)

    # Get sub_persona from preferences, or default based on base persona
    sub_persona = prefs.get("sub_persona")
    if not sub_persona:
        # Default sub-persona based on base persona
        sub_persona = {
            "admin": "admin",
            "developer": "alice-builder",
            "user": "bob",
        }.get(persona, "bob")

    # Get visible modules for the effective sub-persona
    visible_modules = get_visible_modules_for_persona(sub_persona)

    # Get feature flags from preferences
    feature_flags = prefs.get("feature_flags", {})

    # Get WebSocket permissions via OpenFGA batch check
    websocket_permissions = await get_websocket_permissions(user_id)

    return UserInfoResponse(
        user_id=user_id,
        username=user.get("username", ""),
        email=user.get("email"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        display_name=user.get("display_name"),
        roles=roles,
        persona=persona,
        keycloak_id=user.get("keycloak_id"),
        # Sprint 4 extended fields
        api_version="2",
        sub_persona=sub_persona,
        visible_modules=visible_modules,
        feature_flags=feature_flags,
        # Sprint 5: WebSocket permissions (enables frontend-aware auth)
        websocket_permissions=websocket_permissions,
    )


@user_router.patch("/me/preferences")
async def update_persona_preferences(
    updates: PersonaPreferencesUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> UserInfoResponse:
    """
    Update persona-related preferences.

    Allows users to:
    - Switch their sub-persona (within allowed options for their base persona)
    - Update feature flags

    The sub_persona must be valid for the user's base persona:
    - admin: can use admin, security-admin, auditor, alice-*, bob, compliance-officer
    - developer: can use alice-*, bob, compliance-officer
    - user: can use bob, compliance-officer

    Returns the full UserInfoResponse with updated values.
    """
    roles = user.get("roles", [])
    base_persona = compute_persona(roles)
    user_id = user.get("user_id", "")

    # Validate sub_persona if provided
    if updates.sub_persona:
        if not is_valid_sub_persona(base_persona, updates.sub_persona):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sub_persona '{updates.sub_persona}' for base persona '{base_persona}'. "
                f"Valid options: {get_sub_personas_for_base(base_persona)}",
            )

    # Get existing preferences from database
    prefs = await get_user_preferences_from_db(user_id)

    # Apply updates
    new_sub_persona = updates.sub_persona if updates.sub_persona is not None else prefs.get("sub_persona")
    new_feature_flags = prefs.get("feature_flags", {})
    if updates.feature_flags is not None:
        new_feature_flags.update(updates.feature_flags)

    # Store updated preferences to database
    await save_user_preferences_to_db(user_id, new_sub_persona, new_feature_flags)

    logger.info(
        "Updated persona preferences",
        extra={
            "user_id": user_id,
            "sub_persona": new_sub_persona,
            "feature_flags_updated": list(updates.feature_flags.keys()) if updates.feature_flags else [],
        },
    )

    # Return updated user info
    return await get_me(user)


@user_router.post("/login", deprecated=True)
async def login(body: LoginRequest) -> LoginResponse:
    """
    DEPRECATED: Authenticate user with username and password (ROPC flow).

    WARNING: This endpoint uses Resource Owner Password Credentials (ROPC) grant type,
    which is deprecated per RFC 9700 (OAuth 2.0 Security Best Practice).

    Migration: Use GET /api/v1/auth/login for OAuth2 Authorization Code + PKCE flow.
    This endpoint will be removed in a future major version.

    Uses Keycloak's Resource Owner Password Credentials (ROPC) grant type
    to exchange credentials for tokens without requiring browser redirect.

    Note: This requires the Keycloak client to have "Direct Access Grants" enabled.

    Returns:
        LoginResponse with access_token, refresh_token, and user info
    """
    # Log deprecation warning
    logger.warning(
        "ROPC login endpoint used - deprecated per RFC 9700. "
        "Use GET /api/v1/auth/login for OAuth2 Authorization Code + PKCE flow."
    )

    # Build Keycloak token endpoint URL
    token_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Request token using password grant
            response = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret or "",
                    "username": body.username,
                    "password": body.password,
                    "scope": "openid profile email",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error_description", "Invalid credentials")
                logger.warning(
                    "Login failed",
                    extra={"username": body.username, "error": error_msg},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg,
                )

            token_data = response.json()
            access_token = token_data["access_token"]

            # Decode JWT to get user info (without verification - Keycloak already verified)
            # Security Note: Signature verification is handled by Keycloak during token exchange.
            # This decode is only to extract user info from an already-trusted token.
            import jwt

            # nosemgrep: python.jwt.security.unverified-jwt-decode.unverified-jwt-decode
            payload = jwt.decode(access_token, options={"verify_signature": False})

            # Extract user info from token
            user_id = f"user:{payload.get('preferred_username', body.username)}"
            username = payload.get("preferred_username", body.username)
            email = payload.get("email")
            roles: list[str] = []

            # Extract roles from realm_access
            realm_access = payload.get("realm_access", {})
            if isinstance(realm_access, dict):
                roles.extend(realm_access.get("roles", []))

            persona = compute_persona(roles)

            # Compute default sub_persona for login
            default_sub_persona = {
                "admin": "admin",
                "developer": "alice-builder",
                "user": "bob",
            }.get(persona, "bob")

            user_info = UserInfoResponse(
                user_id=user_id,
                username=username,
                email=email,
                first_name=payload.get("given_name"),
                last_name=payload.get("family_name"),
                display_name=payload.get("name"),
                roles=roles,
                persona=persona,
                keycloak_id=payload.get("sub"),
                # Sprint 4 extended fields
                api_version="2",
                sub_persona=default_sub_persona,
                visible_modules=get_visible_modules_for_persona(default_sub_persona),
                feature_flags={},
            )

            logger.info("Login successful", extra={"username": username, "persona": persona})

            return LoginResponse(
                access_token=access_token,
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 300),
                user=user_info,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable",
        ) from e


@user_router.post("/logout")
async def logout(
    request: Request,
    body: LogoutRequest | None = None,
    denylist: TokenDenylist = Depends(get_token_denylist),
) -> LogoutResponse:
    """
    Logout and revoke tokens.

    Revokes the access token (and optionally refresh token) with Keycloak.
    This is a native logout that doesn't redirect to Keycloak UI.

    Security (OWASP best practice):
    - Adds token JTI to denylist for immediate invalidation
    - Token will be rejected even before Keycloak revocation propagates

    The client should:
    1. Call this endpoint
    2. Clear local token storage
    3. Redirect to login page
    """
    # Get access token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    access_token = None

    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]

    if not access_token:
        return LogoutResponse(success=True, message="No active session")

    # Add token to denylist for immediate invalidation (OWASP Session Management)
    # Decode token without verification to extract jti and exp claims
    # (Token was already verified by auth middleware before reaching this endpoint)
    try:
        # Decode without verification - we just need the claims
        payload = jwt.decode(access_token, options={"verify_signature": False})
        jti = payload.get("jti")
        exp = payload.get("exp")

        if jti and exp:
            # Convert exp to datetime and add to denylist
            expires_at = datetime.fromtimestamp(exp, tz=UTC)
            await denylist.add(jti, expires_at)
            logger.info(
                "Token added to denylist on logout",
                extra={"jti": jti[:8] + "..." if len(jti) > 8 else jti},
            )
    except jwt.DecodeError as e:
        # Log but continue - Keycloak revocation will still happen
        logger.warning(f"Could not decode token for denylist: {e}")

    # Build Keycloak logout/revoke endpoint URL
    revoke_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/revoke"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Revoke access token
            response = await client.post(
                revoke_url,
                data={
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret or "",
                    "token": access_token,
                    "token_type_hint": "access_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            # Also revoke refresh token if provided
            if body and body.refresh_token:
                await client.post(
                    revoke_url,
                    data={
                        "client_id": settings.keycloak_client_id,
                        "client_secret": settings.keycloak_client_secret or "",
                        "token": body.refresh_token,
                        "token_type_hint": "refresh_token",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            if response.status_code in (200, 204):
                logger.info("Logout successful")
                return LogoutResponse(success=True, message="Logged out successfully")
            else:
                # Token revocation failed but we still consider it a successful logout
                # The token may already be expired or revoked
                logger.warning(
                    "Token revocation returned non-success status",
                    extra={"status": response.status_code},
                )
                return LogoutResponse(success=True, message="Logged out (token may already be expired)")

    except Exception as e:
        logger.error("Logout error", extra={"error": str(e)})
        # Return success anyway - client should clear local state
        return LogoutResponse(success=True, message="Logged out locally")
