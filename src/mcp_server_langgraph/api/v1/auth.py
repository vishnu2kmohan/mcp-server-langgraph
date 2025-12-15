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

from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from mcp_server_langgraph.auth.oauth2 import (
    build_authorization_url,
    generate_code_challenge,
    generate_code_verifier,
    generate_state,
)
from mcp_server_langgraph.auth.device_auth import (
    DeviceAuthClient,
    AuthorizationPending,
    SlowDown,
    ExpiredToken,
    AccessDenied,
    DeviceAuthError,
)
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger

# Note: Rate limiting for auth endpoints is configured in the main application
# via setup_rate_limiting() in middleware/rate_limiter.py. This allows for
# proper Redis connection management and makes endpoints easier to unit test.

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


# ============================================================================
# OAuth2 Endpoints
# ============================================================================


@auth_router.get("/login")
async def oauth2_login(
    request: Request,
    redirect_uri: str | None = Query(None, description="Optional custom redirect URI"),
) -> RedirectResponse:
    """
    Initiate OAuth2 Authorization Code + PKCE flow.

    This endpoint:
    1. Generates PKCE code verifier and challenge
    2. Generates state parameter for CSRF protection
    3. Stores verifier and state in session (cookie)
    4. Redirects user to Keycloak authorization endpoint

    After successful authentication, Keycloak redirects to /auth/callback.
    """
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
    keycloak_public_url = settings.keycloak_public_url or settings.keycloak_server_url
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
            return RedirectResponse(
                url=f"{frontend_url}/auth/callback#{fragment}",
                status_code=status.HTTP_302_FOUND,
            )

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


@auth_router.post("/refresh", response_model=TokenResponse)
async def oauth2_refresh(request: Request, body: RefreshTokenRequest) -> dict[str, Any]:
    """
    Refresh access token using refresh token.

    This endpoint exchanges a valid refresh token for a new access token.
    Used when the access token expires but the refresh token is still valid.
    """
    # Build token endpoint URL
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

            # Audit: Token refresh success
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
