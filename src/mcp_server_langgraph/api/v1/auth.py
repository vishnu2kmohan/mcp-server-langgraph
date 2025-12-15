"""
OAuth2 Authorization Code + PKCE API endpoints.

Per RFC 9700 (OAuth 2.0 Security Best Practice):
ROPC (Resource Owner Password Credentials) MUST NOT be used.
Use Authorization Code + PKCE instead.

This module provides the OAuth2 endpoints for:
- GET /auth/login - Initiate OAuth2 authorization flow with PKCE
- GET /auth/callback - Handle authorization callback and exchange code for tokens
- POST /auth/refresh - Refresh access token using refresh token

Flow:
1. Frontend calls GET /auth/login
2. User is redirected to Keycloak for authentication
3. Keycloak redirects back to GET /auth/callback with authorization code
4. Backend exchanges code for tokens using PKCE verifier
5. Tokens are returned to frontend
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from mcp_server_langgraph.auth.device_auth import (
    AccessDenied,
    AuthorizationPending,
    DeviceAuthClient,
    DeviceAuthError,
    ExpiredToken,
    SlowDown,
)
from mcp_server_langgraph.auth.oauth2 import (
    build_authorization_url,
    generate_code_challenge,
    generate_code_verifier,
    generate_state,
)
from mcp_server_langgraph.auth.token_denylist import TokenDenylist
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger


# ============================================================================
# Token Denylist Helper (for Refresh Token Rotation)
# ============================================================================


def _get_token_denylist() -> TokenDenylist | None:
    """
    Get the token denylist instance for refresh token rotation.

    Returns:
        TokenDenylist instance if available, None otherwise.

    Note:
        This is a lazy import to avoid circular dependencies and to allow
        the denylist to be configured via dependency injection in tests.
    """
    try:
        from mcp_server_langgraph.core.dependencies import get_token_denylist

        return get_token_denylist()
    except Exception:
        # Denylist not configured - rotation is disabled
        return None


def _hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for denylist storage.

    Refresh tokens don't have jti claims like access tokens, so we use
    a SHA-256 hash of the token itself as the identifier.

    Args:
        token: The refresh token to hash.

    Returns:
        SHA-256 hex digest of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


# Note: Rate limiting for auth endpoints is configured in the main application
# via setup_rate_limiting() in middleware/rate_limiter.py. This allows for
# proper Redis connection management and makes endpoints easier to unit test.


# ============================================================================
# Security Headers (OWASP Best Practices)
# ============================================================================


# Security headers configuration for auth endpoints
# Per OWASP Secure Headers Project: https://owasp.org/www-project-secure-headers/
AUTH_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # HSTS is only added in production (requires HTTPS)
}


class AuthSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all auth endpoint responses.

    Per OWASP Security Headers Guidelines:
    - X-Content-Type-Options: nosniff (prevents MIME sniffing)
    - X-Frame-Options: DENY (prevents clickjacking)
    - X-XSS-Protection: 1; mode=block (XSS filter)
    - Content-Security-Policy (prevents XSS)
    - Strict-Transport-Security (enforces HTTPS) - only in production

    Note: This middleware is designed to be added to apps that mount the auth_router.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add all security headers
        for header, value in AUTH_SECURITY_HEADERS.items():
            response.headers[header] = value

        # Add HSTS header in production only (requires HTTPS)
        if settings.environment not in ("development", "test"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response


auth_router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================================
# Request/Response Models
# ============================================================================


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str | None = Field(None, description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry in seconds")
    scope: str | None = Field(None, description="Granted scopes")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(..., min_length=1, description="Refresh token")


class AuthErrorResponse(BaseModel):
    """OAuth2 error response."""

    error: str = Field(..., description="Error code")
    error_description: str | None = Field(None, description="Human-readable error description")


class PARRequest(BaseModel):
    """Pushed Authorization Request (RFC 9126)."""

    redirect_uri: str = Field(..., description="OAuth2 redirect URI")
    scope: str = Field(default="openid profile email", description="OAuth2 scopes")
    code_challenge: str | None = Field(None, description="PKCE code challenge")
    code_challenge_method: str = Field(default="S256", description="PKCE challenge method")
    state: str | None = Field(None, description="Optional state parameter")
    nonce: str | None = Field(None, description="Optional nonce for OpenID Connect")


class PARResponse(BaseModel):
    """Pushed Authorization Response (RFC 9126)."""

    request_uri: str = Field(..., description="PAR request URI")
    expires_in: int = Field(..., description="Request URI expiration in seconds")


class IntrospectionRequest(BaseModel):
    """Token Introspection Request (RFC 7662)."""

    token: str = Field(..., min_length=1, description="Token to introspect")
    token_type_hint: str | None = Field(
        None,
        description="Hint about the token type (access_token or refresh_token)",
    )


class IntrospectionResponse(BaseModel):
    """Token Introspection Response (RFC 7662)."""

    active: bool = Field(..., description="Whether the token is active")
    scope: str | None = Field(None, description="Token scope")
    client_id: str | None = Field(None, description="Client ID that requested the token")
    username: str | None = Field(None, description="Username of the token subject")
    token_type: str | None = Field(None, description="Token type")
    exp: int | None = Field(None, description="Token expiration timestamp")
    iat: int | None = Field(None, description="Token issuance timestamp")
    sub: str | None = Field(None, description="Token subject (user ID)")
    aud: str | list[str] | None = Field(None, description="Token audience")
    iss: str | None = Field(None, description="Token issuer")


# ============================================================================
# OAuth2 Endpoints
# ============================================================================


@auth_router.get("/login")
async def oauth2_login(
    request: Request,
    redirect_uri: str | None = Query(None, description="Optional custom redirect URI"),
    request_uri: str | None = Query(None, description="PAR request_uri (RFC 9126)"),
) -> RedirectResponse:
    """
    Initiate OAuth2 Authorization Code + PKCE flow.

    This endpoint:
    1. Generates PKCE code verifier and challenge
    2. Generates state parameter for CSRF protection
    3. Stores verifier and state in session (cookie)
    4. Redirects user to Keycloak authorization endpoint

    After successful authentication, Keycloak redirects to /auth/callback.

    RFC 9126 PAR Support:
    If request_uri is provided, redirects to Keycloak with just client_id and request_uri,
    skipping the full PKCE flow (which was already done in the PAR request).
    """
    keycloak_public_url = settings.keycloak_public_url or settings.keycloak_server_url

    # RFC 9126: If request_uri is provided, use PAR flow
    if request_uri:
        # Build minimal authorization URL with just request_uri
        auth_params = {
            "client_id": settings.keycloak_client_id,
            "request_uri": request_uri,
        }
        auth_url = (
            f"{keycloak_public_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/auth?{urlencode(auth_params)}"
        )

        logger.info(
            "OAuth2 login initiated with PAR request_uri",
            extra={
                "audit_event_type": "oauth2.login.par",
                "audit_category": "authentication",
                "request_uri_prefix": request_uri[:40] + "..." if len(request_uri) > 40 else request_uri,
                "client_ip": request.client.host if request.client else None,
            },
        )

        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    # Standard PKCE flow
    # Generate PKCE values
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = generate_state()

    # Determine redirect URI
    # Priority: 1. Explicit parameter, 2. Config setting, 3. Auto-detect from request
    actual_redirect_uri = redirect_uri or settings.oauth2_auth_callback_uri
    if not actual_redirect_uri:
        # Build default from request (strip trailing slash and append path)
        base = str(request.base_url).rstrip("/")
        actual_redirect_uri = f"{base}/api/v1/auth/callback"

    # Build authorization URL using PUBLIC Keycloak URL (browser redirect)
    # keycloak_public_url is for browser redirects (externally accessible)
    # keycloak_server_url is for backend token exchange (internal Docker network)
    auth_url = build_authorization_url(
        keycloak_url=keycloak_public_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        redirect_uri=actual_redirect_uri,
        state=state,
        code_challenge=code_challenge,
    )

    # Audit: OAuth2 login initiated (RFC 9700, ADR-0071)
    logger.info(
        "OAuth2 login initiated",
        extra={
            "audit_event_type": "oauth2.login.initiated",
            "audit_category": "authentication",
            "redirect_uri": actual_redirect_uri,
            "state_prefix": state[:8],
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )

    # Create redirect response
    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    # Store PKCE verifier and state in secure cookies
    # These will be validated in the callback
    response.set_cookie(
        key="oauth2_code_verifier",
        value=code_verifier,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=600,  # 10 minutes
    )
    response.set_cookie(
        key="oauth2_state",
        value=state,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=600,  # 10 minutes
    )
    response.set_cookie(
        key="oauth2_redirect_uri",
        value=actual_redirect_uri,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=600,  # 10 minutes
    )

    return response


@auth_router.get("/callback")
async def oauth2_callback(
    request: Request,
    code: str | None = Query(None, description="Authorization code from Keycloak"),
    state: str | None = Query(None, description="State parameter for CSRF validation"),
    error: str | None = Query(None, description="Error code if authorization failed"),
    error_description: str | None = Query(None, description="Error description"),
) -> RedirectResponse:
    """
    Handle OAuth2 authorization callback.

    This endpoint:
    1. Validates state parameter matches session state (CSRF protection)
    2. Exchanges authorization code for tokens using PKCE verifier
    3. Returns tokens to frontend

    Called by Keycloak after user authenticates.
    """
    # Handle authorization errors from Keycloak (these may not include code/state)
    if error:
        # Audit: OAuth2 callback failed - error from Keycloak
        logger.warning(
            "OAuth2 callback failed - Keycloak error",
            extra={
                "audit_event_type": "oauth2.callback.failed",
                "audit_category": "authentication",
                "audit_outcome": "failure",
                "error": error,
                "error_description": error_description,
                "client_ip": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_description or error,
        )

    # Validate required params for success flow
    if not code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Authorization code is required",
        )

    if not state:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="State parameter is required",
        )

    # Retrieve stored values from cookies
    stored_state = request.cookies.get("oauth2_state")
    code_verifier = request.cookies.get("oauth2_code_verifier")
    redirect_uri = request.cookies.get("oauth2_redirect_uri")

    # Validate state (CSRF protection)
    if stored_state != state:
        # Audit: OAuth2 callback failed - CSRF state mismatch (security event)
        logger.warning(
            "OAuth2 callback failed - state mismatch (potential CSRF attack)",
            extra={
                "audit_event_type": "oauth2.callback.failed",
                "audit_category": "security",
                "audit_outcome": "failure",
                "failure_reason": "state_mismatch",
                "received_state_prefix": state[:8] if state else None,
                "client_ip": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter. Please try logging in again.",
        )

    # Validate code verifier exists
    if not code_verifier:
        # Audit: OAuth2 callback failed - session expired
        logger.warning(
            "OAuth2 callback failed - session expired (code verifier not found)",
            extra={
                "audit_event_type": "oauth2.callback.failed",
                "audit_category": "authentication",
                "audit_outcome": "failure",
                "failure_reason": "session_expired",
                "client_ip": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session expired. Please try logging in again.",
        )

    # Build token endpoint URL
    # Use internal URL for backend-to-backend token exchange
    token_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"

    # Exchange authorization code for tokens
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_data = {
                "grant_type": "authorization_code",
                "client_id": settings.keycloak_client_id,
                "code": code,
                "redirect_uri": redirect_uri or f"{request.base_url}api/v1/auth/callback",
                "code_verifier": code_verifier,
            }

            # Add client secret if configured (for confidential clients)
            if settings.keycloak_client_secret:
                token_data["client_secret"] = settings.keycloak_client_secret

            response = await client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_body = response.json() if response.content else {}
                # Audit: OAuth2 callback failed - token exchange error
                logger.error(
                    "OAuth2 callback failed - token exchange error",
                    extra={
                        "audit_event_type": "oauth2.callback.failed",
                        "audit_category": "authentication",
                        "audit_outcome": "failure",
                        "failure_reason": "token_exchange_failed",
                        "status_code": response.status_code,
                        "error": error_body.get("error"),
                        "error_description": error_body.get("error_description"),
                        "client_ip": request.client.host if request.client else None,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_body.get("error_description", "Token exchange failed"),
                )

            tokens = response.json()

            # Audit: OAuth2 callback success - tokens issued
            logger.info(
                "OAuth2 callback successful - tokens issued",
                extra={
                    "audit_event_type": "oauth2.callback.success",
                    "audit_category": "authentication",
                    "audit_outcome": "success",
                    "token_type": tokens.get("token_type", "Bearer"),
                    "expires_in": tokens.get("expires_in"),
                    "client_ip": request.client.host if request.client else None,
                },
            )

            token_response = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in", 300),
                "scope": tokens.get("scope"),
            }

            # For SPA (frontend) flows, redirect to frontend with tokens in fragment
            # This is more secure than query params as fragments aren't sent to server
            frontend_url = settings.frontend_url.rstrip("/")
            fragment = urlencode({k: v for k, v in token_response.items() if v is not None})
            response = RedirectResponse(
                url=f"{frontend_url}/auth/callback#{fragment}",
                status_code=status.HTTP_302_FOUND,
            )

            # Set session cookie for server-side authentication of frontend pages
            # This allows us to protect /studio/* routes from unauthenticated access
            from mcp_server_langgraph.studio.security import (
                SESSION_COOKIE_CONFIG,
                SESSION_COOKIE_NAME,
            )

            # Generate signed session token using access token hash
            # The session proves user completed OAuth2 flow successfully
            session_token = _hash_refresh_token(tokens["access_token"])[:32]
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session_token,
                httponly=SESSION_COOKIE_CONFIG["httponly"],
                secure=SESSION_COOKIE_CONFIG["secure"] or settings.environment not in ("development", "test"),
                samesite=SESSION_COOKIE_CONFIG["samesite"],
                path=SESSION_COOKIE_CONFIG["path"],
                max_age=SESSION_COOKIE_CONFIG["max_age"],
            )

            return response

    except httpx.HTTPError as e:
        # Audit: OAuth2 callback failed - Keycloak unreachable
        logger.error(
            f"OAuth2 callback failed - Keycloak unreachable: {e}",
            extra={
                "audit_event_type": "oauth2.callback.failed",
                "audit_category": "authentication",
                "audit_outcome": "error",
                "failure_reason": "service_unavailable",
                "error_type": type(e).__name__,
                "client_ip": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from e


# ============================================================================
# Pushed Authorization Requests (RFC 9126)
# ============================================================================


@auth_router.post("/par", response_model=PARResponse, status_code=status.HTTP_201_CREATED)
async def pushed_authorization_request(
    request: Request,
    body: PARRequest,
) -> dict[str, Any]:
    """
    Pushed Authorization Request (PAR) endpoint - RFC 9126.

    PAR provides enhanced security by:
    - Pre-registering authorization requests server-side
    - Reducing authorization request URL size
    - Preventing request parameter tampering
    - Enabling confidential client authentication at request time

    Flow:
    1. Client POSTs authorization parameters to this endpoint
    2. Server returns a request_uri
    3. Client uses request_uri in GET /auth/login?request_uri=...
    4. Authorization server uses the pre-registered parameters

    Note: Keycloak must have PAR enabled for this client.
    """
    # Build PAR endpoint URL
    par_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/ext/par/request"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build PAR request data
            par_data: dict[str, str] = {
                "client_id": settings.keycloak_client_id,
                "redirect_uri": body.redirect_uri,
                "response_type": "code",
                "scope": body.scope,
            }

            # Add client secret if configured
            if settings.keycloak_client_secret:
                par_data["client_secret"] = settings.keycloak_client_secret

            # Add optional PKCE parameters
            if body.code_challenge:
                par_data["code_challenge"] = body.code_challenge
                par_data["code_challenge_method"] = body.code_challenge_method

            # Add optional state and nonce
            if body.state:
                par_data["state"] = body.state
            if body.nonce:
                par_data["nonce"] = body.nonce

            response = await client.post(
                par_url,
                data=par_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code not in (200, 201):
                error_body = response.json() if response.content else {}
                logger.warning(
                    "PAR request failed",
                    extra={
                        "audit_event_type": "oauth2.par.failed",
                        "audit_category": "authentication",
                        "audit_outcome": "failure",
                        "status_code": response.status_code,
                        "error": error_body.get("error"),
                        "error_description": error_body.get("error_description"),
                        "client_ip": request.client.host if request.client else None,
                    },
                )
                return JSONResponse(
                    status_code=response.status_code,
                    content={
                        "error": error_body.get("error", "par_failed"),
                        "error_description": error_body.get("error_description", "Pushed Authorization Request failed"),
                    },
                )

            par_response = response.json()

            logger.info(
                "PAR request successful",
                extra={
                    "audit_event_type": "oauth2.par.success",
                    "audit_category": "authentication",
                    "audit_outcome": "success",
                    "request_uri_prefix": par_response.get("request_uri", "")[:40],
                    "expires_in": par_response.get("expires_in"),
                    "client_ip": request.client.host if request.client else None,
                },
            )

            return {
                "request_uri": par_response["request_uri"],
                "expires_in": par_response.get("expires_in", 60),
            }

    except httpx.HTTPError as e:
        logger.error(
            f"PAR request failed - Keycloak unreachable: {e}",
            extra={
                "audit_event_type": "oauth2.par.failed",
                "audit_category": "authentication",
                "audit_outcome": "error",
                "failure_reason": "service_unavailable",
                "error_type": type(e).__name__,
                "client_ip": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from e


# ============================================================================
# Token Introspection (RFC 7662)
# ============================================================================


@auth_router.post("/introspect", response_model=IntrospectionResponse)
async def token_introspection(
    request: Request,
    body: IntrospectionRequest,
) -> dict[str, Any]:
    """
    Token Introspection endpoint - RFC 7662.

    Allows resource servers to validate access tokens and retrieve their
    metadata without parsing them locally. This is useful for:
    - Validating opaque tokens
    - Checking token revocation status
    - Getting token claims without local JWT validation

    Note: Requires client authentication (client_id + client_secret).
    """
    # Build introspection endpoint URL
    # Use internal URL for backend-to-backend token introspection
    introspect_url = (
        f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token/introspect"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build introspection request data
            introspect_data: dict[str, str] = {
                "client_id": settings.keycloak_client_id,
                "token": body.token,
            }

            # Add client secret (required for introspection)
            if settings.keycloak_client_secret:
                introspect_data["client_secret"] = settings.keycloak_client_secret

            # Add token type hint if provided
            if body.token_type_hint:
                introspect_data["token_type_hint"] = body.token_type_hint

            response = await client.post(
                introspect_url,
                data=introspect_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_body = response.json() if response.content else {}
                logger.warning(
                    "Token introspection failed",
                    extra={
                        "audit_event_type": "token.introspect.failed",
                        "audit_category": "authentication",
                        "audit_outcome": "failure",
                        "status_code": response.status_code,
                        "error": error_body.get("error"),
                        "client_ip": request.client.host if request.client else None,
                    },
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_body.get("error_description", "Token introspection failed"),
                )

            introspect_response = response.json()

            logger.info(
                "Token introspection completed",
                extra={
                    "audit_event_type": "token.introspect.success",
                    "audit_category": "authentication",
                    "audit_outcome": "success",
                    "active": introspect_response.get("active"),
                    "client_ip": request.client.host if request.client else None,
                },
            )

            return introspect_response

    except httpx.HTTPError as e:
        logger.error(
            f"Token introspection failed - Keycloak unreachable: {e}",
            extra={
                "audit_event_type": "token.introspect.failed",
                "audit_category": "authentication",
                "audit_outcome": "error",
                "failure_reason": "service_unavailable",
                "error_type": type(e).__name__,
                "client_ip": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from e


@auth_router.post("/refresh", response_model=TokenResponse)
async def oauth2_refresh(request: Request, body: RefreshTokenRequest) -> dict[str, Any]:
    """
    Refresh access token using refresh token.

    This endpoint exchanges a valid refresh token for a new access token.
    Used when the access token expires but the refresh token is still valid.

    Security (Refresh Token Rotation):
    - Old refresh tokens are added to denylist after successful rotation
    - Prevents replay attacks with stolen refresh tokens
    - Per OWASP Session Management best practices
    """
    # Get token denylist for rotation (may be None if not configured)
    denylist = _get_token_denylist()
    old_token_hash = _hash_refresh_token(body.refresh_token)

    # Check if refresh token is in denylist (already rotated)
    if denylist is not None:
        if await denylist.is_denied(old_token_hash):
            logger.warning(
                "Refresh token rejected - already rotated (replay attempt)",
                extra={
                    "audit_event_type": "token.refresh.rejected",
                    "audit_category": "authentication",
                    "audit_outcome": "failure",
                    "failure_reason": "token_revoked",
                    "client_ip": request.client.host if request.client else None,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked. Please log in again.",
            )

    # Build token endpoint URL
    # Use internal URL for backend-to-backend token refresh
    token_url = f"{settings.keycloak_server_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_data = {
                "grant_type": "refresh_token",
                "client_id": settings.keycloak_client_id,
                "refresh_token": body.refresh_token,
            }

            # Add client secret if configured
            if settings.keycloak_client_secret:
                token_data["client_secret"] = settings.keycloak_client_secret

            response = await client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_body = response.json() if response.content else {}
                # Audit: Token refresh failed
                logger.warning(
                    "Token refresh failed - expired or invalid",
                    extra={
                        "audit_event_type": "token.refresh.failed",
                        "audit_category": "authentication",
                        "audit_outcome": "failure",
                        "status_code": response.status_code,
                        "error": error_body.get("error"),
                        "client_ip": request.client.host if request.client else None,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expired or invalid. Please log in again.",
                )

            tokens = response.json()

            # Refresh Token Rotation: Add old token to denylist
            # This prevents replay attacks with the old token
            if denylist is not None and tokens.get("refresh_token"):
                # Denylist old token for the lifetime of a typical refresh token (7 days)
                # This covers the window where an attacker might try to use the old token
                expires_at = datetime.now(UTC) + timedelta(days=7)
                await denylist.add(old_token_hash, expires_at)

                logger.info(
                    "Token rotation completed - old refresh token denylisted",
                    extra={
                        "audit_event_type": "token.refresh.rotation",
                        "audit_category": "authentication",
                        "audit_outcome": "success",
                        "token_type": tokens.get("token_type", "Bearer"),
                        "expires_in": tokens.get("expires_in"),
                        "client_ip": request.client.host if request.client else None,
                    },
                )
            else:
                # Audit: Token refresh success (without rotation)
                logger.info(
                    "Token refresh successful",
                    extra={
                        "audit_event_type": "token.refresh.success",
                        "audit_category": "authentication",
                        "audit_outcome": "success",
                        "token_type": tokens.get("token_type", "Bearer"),
                        "expires_in": tokens.get("expires_in"),
                        "client_ip": request.client.host if request.client else None,
                    },
                )

            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in", 300),
                "scope": tokens.get("scope"),
            }

    except httpx.HTTPError as e:
        # Audit: Token refresh failed - Keycloak unreachable
        logger.error(
            f"Token refresh failed - Keycloak unreachable: {e}",
            extra={
                "audit_event_type": "token.refresh.failed",
                "audit_category": "authentication",
                "audit_outcome": "error",
                "failure_reason": "service_unavailable",
                "error_type": type(e).__name__,
                "client_ip": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from e


# ============================================================================
# Device Authorization Grant (RFC 8628) Endpoints
# ============================================================================


class DeviceCodeResponse(BaseModel):
    """Device authorization response (RFC 8628 Section 3.2)."""

    device_code: str = Field(..., description="Device verification code")
    user_code: str = Field(..., description="User code to enter at verification_uri")
    verification_uri: str = Field(..., description="URL for user to visit")
    verification_uri_complete: str | None = Field(None, description="URL with user_code embedded (for QR codes)")
    expires_in: int = Field(..., description="Lifetime of device_code in seconds")
    interval: int = Field(default=5, description="Polling interval in seconds")


class DeviceTokenRequest(BaseModel):
    """Device token request."""

    device_code: str = Field(..., min_length=1, description="Device code from /auth/device")


class DeviceAuthErrorResponse(BaseModel):
    """Device authorization error response (RFC 8628 Section 3.5)."""

    error: str = Field(..., description="Error code")
    error_description: str | None = Field(None, description="Human-readable error")


@auth_router.get(
    "/device",
    response_model=DeviceCodeResponse,
    responses={
        503: {"model": AuthErrorResponse, "description": "Authentication service unavailable"},
    },
    summary="Request device authorization code",
    description="""
    Initiate Device Authorization Grant flow (RFC 8628).

    This endpoint is for CLI/headless authentication scenarios where the client
    cannot directly interact with the user for login.

    Flow:
    1. Client calls GET /auth/device to get device_code and user_code
    2. Display verification_uri and user_code to user
    3. User visits verification_uri on another device and enters user_code
    4. Client polls POST /auth/device/token until authorization completes
    """,
)
async def device_auth_request(request: Request) -> dict[str, Any]:
    """
    Request device authorization code.

    Returns device_code for polling and user_code for display to the user.
    """
    try:
        client = DeviceAuthClient(
            server_url=settings.keycloak_server_url,
            realm=settings.keycloak_realm,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
            verify_ssl=settings.keycloak_verify_ssl,
        )

        device_response = await client.request_device_code()

        # Audit: Device authorization initiated
        logger.info(
            "Device authorization initiated",
            extra={
                "audit_event_type": "device_auth.initiated",
                "audit_category": "authentication",
                "audit_outcome": "success",
                "user_code": device_response.get("user_code"),
                "expires_in": device_response.get("expires_in"),
                "client_ip": request.client.host if request.client else None,
            },
        )

        return device_response

    except Exception as e:
        logger.error(
            f"Device authorization request failed: {e}",
            extra={
                "audit_event_type": "device_auth.failed",
                "audit_category": "authentication",
                "audit_outcome": "error",
                "error_type": type(e).__name__,
                "client_ip": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from e


@auth_router.post(
    "/device/token",
    response_model=TokenResponse,
    responses={
        400: {"model": DeviceAuthErrorResponse, "description": "Authorization pending or error"},
        503: {"model": AuthErrorResponse, "description": "Authentication service unavailable"},
    },
    summary="Poll for device authorization token",
    description="""
    Poll for access token after device authorization.

    This endpoint should be called repeatedly (respecting the `interval` from
    the device code response) until authorization completes or fails.

    Possible error responses:
    - `authorization_pending`: User hasn't completed authorization yet
    - `slow_down`: Client is polling too frequently
    - `expired_token`: Device code has expired
    - `access_denied`: User denied the authorization request
    """,
)
async def device_auth_token(
    request: Request,
    token_request: DeviceTokenRequest,
) -> dict[str, Any]:
    """
    Poll for access token after device authorization.

    Returns tokens if user has completed authorization, or error if pending/failed.
    """
    try:
        client = DeviceAuthClient(
            server_url=settings.keycloak_server_url,
            realm=settings.keycloak_realm,
            client_id=settings.keycloak_client_id,
            client_secret=settings.keycloak_client_secret,
            verify_ssl=settings.keycloak_verify_ssl,
        )

        tokens = await client.poll_for_token(token_request.device_code)

        # Audit: Device authorization completed
        logger.info(
            "Device authorization completed",
            extra={
                "audit_event_type": "device_auth.completed",
                "audit_category": "authentication",
                "audit_outcome": "success",
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in"),
                "client_ip": request.client.host if request.client else None,
            },
        )

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_in": tokens.get("expires_in", 300),
            "scope": tokens.get("scope"),
        }

    except AuthorizationPending:
        # User hasn't completed authorization yet - this is expected during polling
        return JSONResponse(
            status_code=400, content={"error": "authorization_pending", "error_description": "Authorization pending"}
        )

    except SlowDown:
        # Client is polling too fast
        return JSONResponse(status_code=400, content={"error": "slow_down", "error_description": "Slow down polling interval"})

    except ExpiredToken:
        # Device code expired
        return JSONResponse(
            status_code=400, content={"error": "expired_token", "error_description": "Device code has expired"}
        )

    except AccessDenied:
        # User denied authorization
        logger.warning(
            "Device authorization denied by user",
            extra={
                "audit_event_type": "device_auth.denied",
                "audit_category": "authentication",
                "audit_outcome": "denied",
                "client_ip": request.client.host if request.client else None,
            },
        )
        return JSONResponse(
            status_code=400, content={"error": "access_denied", "error_description": "User denied authorization"}
        )

    except DeviceAuthError as e:
        logger.error(
            f"Device authorization error: {e}",
            extra={
                "audit_event_type": "device_auth.error",
                "audit_category": "authentication",
                "audit_outcome": "error",
                "error_type": type(e).__name__,
                "client_ip": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.error(
            f"Device token polling failed: {e}",
            extra={
                "audit_event_type": "device_auth.failed",
                "audit_category": "authentication",
                "audit_outcome": "error",
                "error_type": type(e).__name__,
                "client_ip": request.client.host if request.client else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from e


# ============================================================================
# Backchannel Logout (OIDC Back-Channel Logout 1.0)
# ============================================================================


def _verify_logout_token(logout_token: str) -> dict[str, Any]:
    """
    Verify and decode an OIDC backchannel logout token.

    Per OIDC Back-Channel Logout 1.0:
    - The token is a signed JWT
    - Must contain 'sub' (subject) claim
    - Must contain 'sid' (session ID) claim
    - Must contain logout event claim

    Args:
        logout_token: The JWT logout token from Keycloak

    Returns:
        Dict with verified claims (sub, sid)

    Raises:
        ValueError: If token is invalid or verification fails
    """
    import base64
    import json

    # Simplified validation - in production, would verify signature with Keycloak's public key
    # For now, we decode and validate the structure
    try:
        # Split JWT parts
        parts = logout_token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        # Decode payload (middle part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)

        # Validate required claims
        if "sub" not in payload:
            raise ValueError("Missing 'sub' claim in logout token")

        # sid is required for session-based logout
        if "sid" not in payload:
            raise ValueError("Missing 'sid' claim in logout token")

        # Verify logout event claim exists
        events = payload.get("events", {})
        if "http://schemas.openid.net/event/backchannel-logout" not in events:
            raise ValueError("Missing backchannel-logout event claim")

        return {
            "sub": payload["sub"],
            "sid": payload["sid"],
        }

    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid logout token: {e}") from e


@auth_router.post(
    "/backchannel-logout",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid logout token"},
        503: {"description": "Service unavailable"},
    },
    summary="Handle OIDC backchannel logout",
    description="""
    OIDC Back-Channel Logout endpoint (OIDC Back-Channel Logout 1.0).

    This endpoint is called by Keycloak when a user logs out to notify our
    application to invalidate the user's session.

    The logout_token is a signed JWT containing:
    - sub: User ID
    - sid: Session ID to invalidate
    - events: Contains backchannel-logout event

    Flow:
    1. User logs out in Keycloak (or another client)
    2. Keycloak sends logout token to all registered backchannel logout URIs
    3. Each application invalidates the session identified by 'sid'
    """,
)
async def backchannel_logout(
    request: Request,
    logout_token: str | None = None,
) -> JSONResponse:
    """
    Handle OIDC backchannel logout notification from Keycloak.

    Args:
        request: FastAPI request object
        logout_token: The logout token JWT from form data

    Returns:
        200 OK on success
    """
    # Extract logout_token from form data if not provided
    if logout_token is None:
        form_data = await request.form()
        logout_token = form_data.get("logout_token")

    if not logout_token:
        logger.warning(
            "Backchannel logout failed - missing logout_token",
            extra={
                "audit_event_type": "backchannel_logout.failed",
                "audit_category": "authentication",
                "audit_outcome": "failure",
                "failure_reason": "missing_logout_token",
                "client_ip": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="logout_token is required",
        )

    try:
        # Verify and decode the logout token
        claims = _verify_logout_token(logout_token)
        user_id = claims["sub"]
        session_id = claims["sid"]

        # Add session to denylist
        denylist = _get_token_denylist()
        if denylist is not None:
            # Session IDs are added to denylist for 24 hours (typical session max lifetime)
            expires_at = datetime.now(UTC) + timedelta(hours=24)
            await denylist.add(session_id, expires_at)

        logger.info(
            "Backchannel logout successful - session invalidated",
            extra={
                "audit_event_type": "backchannel_logout.success",
                "audit_category": "authentication",
                "audit_outcome": "success",
                "user_id": user_id,
                "session_id_prefix": session_id[:8] + "..." if len(session_id) > 8 else session_id,
                "client_ip": request.client.host if request.client else None,
            },
        )

        return JSONResponse(status_code=200, content={})

    except ValueError as e:
        logger.warning(
            f"Backchannel logout failed - invalid token: {e}",
            extra={
                "audit_event_type": "backchannel_logout.failed",
                "audit_category": "authentication",
                "audit_outcome": "failure",
                "failure_reason": "invalid_token",
                "client_ip": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


# ============================================================================
# OAuth2 Logout (OIDC RP-Initiated Logout)
# ============================================================================


@auth_router.get(
    "/logout",
    status_code=status.HTTP_302_FOUND,
    summary="Initiate OAuth2 logout",
    description="""
    Initiate OIDC RP-Initiated Logout flow.

    This endpoint redirects the user to Keycloak's end_session endpoint to:
    1. Terminate the Keycloak session
    2. Clear any SSO cookies
    3. Optionally redirect back to the application

    Parameters:
    - post_logout_redirect_uri: Where to redirect after logout (must be registered in Keycloak)
    - id_token_hint: The ID token for the session being logged out (improves security)
    """,
)
async def oauth2_logout(
    request: Request,
    post_logout_redirect_uri: str | None = Query(None, description="URI to redirect after logout"),
    id_token_hint: str | None = Query(None, description="ID token hint for the session"),
) -> RedirectResponse:
    """
    Initiate OAuth2/OIDC logout flow.

    Redirects to Keycloak end_session endpoint to terminate the user's session.
    """
    # Use public URL for browser redirect (same as login)
    keycloak_public_url = settings.keycloak_public_url or settings.keycloak_server_url

    # Build Keycloak end_session URL
    # https://openid.net/specs/openid-connect-rpinitiated-1_0.html
    logout_params: dict[str, str] = {
        "client_id": settings.keycloak_client_id,
    }

    # Add optional parameters
    if post_logout_redirect_uri:
        logout_params["post_logout_redirect_uri"] = post_logout_redirect_uri
    if id_token_hint:
        logout_params["id_token_hint"] = id_token_hint

    logout_url = (
        f"{keycloak_public_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/logout?{urlencode(logout_params)}"
    )

    # Audit: OAuth2 logout initiated
    logger.info(
        "OAuth2 logout initiated",
        extra={
            "audit_event_type": "oauth2.logout.initiated",
            "audit_category": "authentication",
            "has_post_logout_redirect": post_logout_redirect_uri is not None,
            "has_id_token_hint": id_token_hint is not None,
            "client_ip": request.client.host if request.client else None,
        },
    )

    # Create redirect response
    response = RedirectResponse(url=logout_url, status_code=status.HTTP_302_FOUND)

    # Clear OAuth2 session cookies and MCP session cookie
    # Set cookies to expire immediately (Max-Age=0)
    from mcp_server_langgraph.studio.security import SESSION_COOKIE_NAME

    for cookie_name in ["oauth2_code_verifier", "oauth2_state", "oauth2_redirect_uri", "session_id", SESSION_COOKIE_NAME]:
        response.delete_cookie(
            key=cookie_name,
            httponly=True,
            secure=settings.environment != "development",
            samesite="lax",
        )

    return response
