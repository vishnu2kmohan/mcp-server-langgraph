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
from mcp_server_langgraph.core.dependencies import get_token_denylist
from mcp_server_langgraph.observability.telemetry import logger

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


class UserInfoResponse(BaseModel):
    """Current user information response."""

    user_id: str = Field(..., description="User identifier in OpenFGA format (user:username)")
    username: str = Field(..., description="Username")
    email: str | None = Field(None, description="Email address")
    roles: list[str] = Field(default_factory=list, description="User roles from Keycloak")
    persona: Literal["admin", "developer", "user"] = Field(..., description="Computed persona for frontend RBAC")
    keycloak_id: str | None = Field(None, description="Keycloak UUID (for admin operations)")


# ============================================================================
# Helper Functions
# ============================================================================


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

    The frontend uses this endpoint on mount to:
    1. Detect user's persona based on roles
    2. Configure sidebar navigation items
    3. Set up route access control
    """
    roles = user.get("roles", [])
    persona = compute_persona(roles)

    return UserInfoResponse(
        user_id=user.get("user_id", ""),
        username=user.get("username", ""),
        email=user.get("email"),
        roles=roles,
        persona=persona,
        keycloak_id=user.get("keycloak_id"),
    )


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

            user_info = UserInfoResponse(
                user_id=user_id,
                username=username,
                email=email,
                roles=roles,
                persona=persona,
                keycloak_id=payload.get("sub"),
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
