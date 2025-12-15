"""
OAuth2 Authorization Code + PKCE flow utilities.

Per RFC 9700 (OAuth 2.0 Security Best Practice):
ROPC (Resource Owner Password Credentials) MUST NOT be used.
Use Authorization Code + PKCE instead.

This module provides utilities for:
- PKCE code verifier and challenge generation (RFC 7636)
- OAuth2 authorization URL construction
- State parameter generation for CSRF protection

Usage:
    from mcp_server_langgraph.auth.oauth2 import (
        generate_code_verifier,
        generate_code_challenge,
        generate_state,
        build_authorization_url,
    )

    # Generate PKCE values
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = generate_state()

    # Build authorization URL
    auth_url = build_authorization_url(
        keycloak_url="https://keycloak.example.com",
        realm="my-realm",
        client_id="my-client",
        redirect_uri="https://app.example.com/callback",
        state=state,
        code_challenge=code_challenge,
    )

References:
    - RFC 9700: OAuth 2.0 Security Best Current Practice
    - RFC 7636: Proof Key for Code Exchange (PKCE)
    - RFC 6749: The OAuth 2.0 Authorization Framework
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode


def generate_code_verifier() -> str:
    """
    Generate a cryptographically random PKCE code verifier.

    Per RFC 7636 Section 4.1:
    - code_verifier must be between 43-128 characters
    - Must use only unreserved URI characters: [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"

    Returns:
        Cryptographically random code verifier string (86 characters)
    """
    # Generate 64 random bytes, then base64url encode (no padding)
    # This produces ~86 characters, well within the 43-128 range
    random_bytes = secrets.token_bytes(64)
    verifier = base64.urlsafe_b64encode(random_bytes).decode("ascii").rstrip("=")
    return verifier


def generate_code_challenge(code_verifier: str) -> str:
    """
    Generate a PKCE code challenge from a code verifier using S256 method.

    Per RFC 7636 Section 4.2:
    - code_challenge = BASE64URL(SHA256(code_verifier))
    - S256 method is REQUIRED for security (plain method is deprecated)

    Args:
        code_verifier: The code verifier string

    Returns:
        Base64URL-encoded SHA256 hash of the verifier (without padding)
    """
    # Compute SHA256 hash of the code verifier
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()

    # Base64URL encode (no padding)
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    return challenge


def generate_state() -> str:
    """
    Generate a cryptographically random state parameter for CSRF protection.

    Per OAuth 2.0 spec, the state parameter:
    - Prevents CSRF attacks on the authorization flow
    - Should be cryptographically random and unguessable
    - Is returned unchanged in the authorization callback

    Returns:
        Cryptographically random URL-safe state string (32 characters)
    """
    return secrets.token_urlsafe(24)


def build_authorization_url(
    keycloak_url: str,
    realm: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scope: str = "openid profile email",
) -> str:
    """
    Build Keycloak OAuth2 authorization URL with PKCE.

    Constructs the URL for the first step of the Authorization Code + PKCE flow.
    The client should redirect the user's browser to this URL to initiate authentication.

    Args:
        keycloak_url: Keycloak base URL (e.g., "https://keycloak.example.com")
        realm: Keycloak realm name
        client_id: OAuth2 client ID
        redirect_uri: URI to redirect to after authorization
        state: Random state parameter for CSRF protection
        code_challenge: PKCE code challenge (S256)
        scope: OAuth2 scopes to request (default: "openid profile email")

    Returns:
        Complete authorization URL ready for browser redirect

    Example:
        >>> url = build_authorization_url(
        ...     keycloak_url="https://keycloak.example.com",
        ...     realm="my-realm",
        ...     client_id="my-app",
        ...     redirect_uri="https://app.example.com/callback",
        ...     state="random-state",
        ...     code_challenge="challenge-hash",
        ... )
        >>> # Returns: https://keycloak.example.com/realms/my-realm/protocol/openid-connect/auth?...
    """
    # Keycloak authorization endpoint
    auth_endpoint = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/auth"

    # OAuth2 + PKCE parameters
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    # Build URL with query parameters
    query_string = urlencode(params)
    return f"{auth_endpoint}?{query_string}"
