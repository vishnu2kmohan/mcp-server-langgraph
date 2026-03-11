"""Shared JWT utilities for consistent token handling across all services.

This module provides a single source of truth for extracting user information
from JWT payloads, ensuring consistency between middleware components.

Supports both:
- Keycloak tokens (preferred_username, realm_access, resource_access)
- InMemoryUserProvider tokens (username, roles)

OpenFGA User ID Format
======================

IMPORTANT: This module normalizes user IDs to OpenFGA's required format: "user:<username>"

This is a critical design decision with the following implications:

1. **user_id Format**: All user IDs are returned as "user:alice" (NOT raw UUIDs like
   "550e8400-e29b-41d4-a716-446655440000"). OpenFGA requires this format for
   relationship tuples (e.g., "user:alice can view document:123").

2. **Username Priority**: We use `preferred_username` (Keycloak) or `username` (InMemory)
   as the basis for user_id, NOT the `sub` claim. This is because:
   - OpenFGA relationship queries use human-readable usernames, not UUIDs
   - The `sub` claim in Keycloak contains a UUID (not suitable for OpenFGA)
   - For debugging/auditing, human-readable IDs are preferable

3. **keycloak_id Field**: The raw `sub` claim (Keycloak UUID) is preserved separately
   as `keycloak_id` for cases where you need to call the Keycloak Admin API.

4. **InMemoryUserProvider**: For testing, InMemoryUserProvider tokens may have
   `sub` already in "user:*" format. These are preserved as-is to maintain
   worker-safe IDs like "user:test_gw0_alice" during parallel test execution.

Example Transformations:
    Keycloak: {"sub": "uuid-123", "preferred_username": "alice"} → user_id: "user:alice"
    InMemory: {"sub": "user:bob", "username": "bob"}            → user_id: "user:bob"
    Fallback: {"sub": "alice"}                                  → user_id: "user:alice"
    Empty:    {}                                                → user_id: "user:unknown"
"""

from __future__ import annotations

import logging
import re
from typing import Any

import jwt

logger = logging.getLogger(__name__)


def decode_jwt_token(token: str, options: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """
    Decode a JWT token without verification for WebSocket auth.

    This function decodes the token to extract claims without verifying the signature.
    It's intended for initial claim extraction in WebSocket connections where
    full verification happens through the AuthMiddleware.

    SECURITY NOTE: This does NOT verify the token signature!
    For production use, always use AuthMiddleware.verify_token() for full validation.
    This is only safe for extracting non-sensitive claims before full verification.

    Args:
        token: JWT token string
        options: Optional decode options (passed to PyJWT)

    Returns:
        Token payload dict if decode succeeds, None otherwise.
    """
    if not token:
        return None

    default_options = {
        "verify_signature": False,  # nosemgrep: unverified-jwt-decode — extracting claims only
        "verify_exp": True,  # Still check expiration
        "verify_aud": False,  # Audience varies
    }
    if options:
        default_options.update(options)

    try:
        payload = jwt.decode(token, options=default_options)
        return dict(payload)
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("Invalid token: %s", e)
        return None


def extract_user_from_jwt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract user information from JWT payload.

    Handles both InMemory tokens and Keycloak tokens with proper field mapping.
    This is the single source of truth for user extraction logic.

    IMPORTANT: See module docstring for OpenFGA User ID Format documentation.
    The user_id is normalized to "user:<username>" format for OpenFGA compatibility.

    Args:
        payload: JWT token payload (decoded)

    Returns:
        User data dict with:
        - user_id: OpenFGA-compatible user ID (e.g., "user:alice"). See module docstring.
        - keycloak_id: Raw UUID from sub claim (for Keycloak Admin API)
        - username: Extracted username (preferred_username > username > sub)
        - roles: List of user roles (from roles/realm_access/resource_access)
        - email: Email address (if present)
        - first_name, last_name, display_name: OIDC standard name claims
        - organization_id, project_id, team_id: Organizational hierarchy for cost attribution

    Note:
        The username extraction priority is:
        1. preferred_username (Keycloak standard claim)
        2. username (InMemoryUserProvider)
        3. sub claim (fallback, extracted if in "user:*" format)
        4. "unknown" (last resort)

    Examples:
        >>> # Keycloak token - preferred_username takes priority, NOT sub
        >>> payload = {
        ...     "sub": "550e8400-e29b-41d4-a716-446655440000",
        ...     "preferred_username": "alice",
        ...     "realm_access": {"roles": ["user"]},
        ... }
        >>> result = extract_user_from_jwt_payload(payload)
        >>> result["username"]
        'alice'
        >>> result["user_id"]  # Normalized for OpenFGA
        'user:alice'
        >>> result["keycloak_id"]  # Raw UUID preserved
        '550e8400-e29b-41d4-a716-446655440000'

        >>> # InMemoryUserProvider token
        >>> payload = {"sub": "user:bob", "username": "bob", "roles": ["admin"]}
        >>> result = extract_user_from_jwt_payload(payload)
        >>> result["user_id"]
        'user:bob'
    """
    # Extract Keycloak UUID from sub claim (if present)
    keycloak_id = payload.get("sub")

    # Priority: preferred_username (Keycloak) > username (InMemory) > extract from sub (fallback)
    username = payload.get("preferred_username") or payload.get("username")

    if not username:
        # Fallback to extracting username from sub
        sub = keycloak_id or "unknown"

        # If sub is in "user:username" format, extract username
        if sub.startswith("user:"):
            id_part = sub.replace("user:", "")

            # Handle worker-safe IDs (e.g., "user:test_gw0_charlie" → "charlie")
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

    # Extract roles from JWT structure
    roles = _extract_roles_from_payload(payload)

    # Extract organizational hierarchy for cost attribution
    org_hierarchy = _extract_organizational_hierarchy(payload)

    return {
        "user_id": user_id,
        "keycloak_id": keycloak_id,  # Raw UUID for Keycloak Admin API
        "username": username,
        "roles": roles,
        "email": payload.get("email"),
        # OIDC standard claims for name fields
        "first_name": payload.get("given_name"),
        "last_name": payload.get("family_name"),
        "display_name": payload.get("name"),  # Full display name
        # Organizational hierarchy for cost attribution
        "organization_id": org_hierarchy.get("organization_id"),
        "project_id": org_hierarchy.get("project_id"),
        "team_id": org_hierarchy.get("team_id"),
    }


def _extract_roles_from_payload(payload: dict[str, Any]) -> list[str]:
    """
    Extract roles from Keycloak JWT structure.

    Keycloak can put roles in multiple places:
    1. roles - sometimes mapped directly (InMemoryUserProvider)
    2. realm_access.roles - realm-level roles
    3. resource_access.<client>.roles - client-level roles

    Args:
        payload: JWT token payload

    Returns:
        List of role strings, combined from all sources
    """
    roles: list[str] = []

    # Check direct roles first (InMemoryUserProvider)
    if payload.get("roles"):
        direct_roles = payload.get("roles", [])
        return list(direct_roles) if isinstance(direct_roles, list) else []

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

    return roles


def _extract_organizational_hierarchy(payload: dict[str, Any]) -> dict[str, str | None]:
    """
    Extract organizational hierarchy from JWT payload for cost attribution.

    Supports extraction from:
    1. Direct claims: organization_id, org_id, project_id, team_id
    2. Keycloak groups: /org/<name>, /organization/<name>, /project/<name>, /team/<name>

    Direct claims take precedence over group paths.

    Args:
        payload: JWT token payload

    Returns:
        Dict with organization_id, project_id, team_id (normalized with prefixes)
    """
    result: dict[str, str | None] = {
        "organization_id": None,
        "project_id": None,
        "team_id": None,
    }

    # 1. Try direct claims first (take precedence)
    org_id = payload.get("organization_id") or payload.get("org_id")
    if org_id:
        result["organization_id"] = _normalize_id(org_id, "organization")

    project_id = payload.get("project_id")
    if project_id:
        result["project_id"] = _normalize_id(project_id, "project")

    team_id = payload.get("team_id")
    if team_id:
        result["team_id"] = _normalize_id(team_id, "team")

    # 2. Fall back to parsing groups (only for missing values)
    groups = payload.get("groups", [])
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, str):
                continue

            # Parse organization from groups
            if result["organization_id"] is None:
                org_match = re.match(r"^/?(?:org|organization)/([^/]+)$", group)
                if org_match:
                    result["organization_id"] = f"organization:{org_match.group(1)}"

            # Parse project from groups
            if result["project_id"] is None:
                project_match = re.match(r"^/?(?:project|projects)/([^/]+)$", group)
                if project_match:
                    result["project_id"] = f"project:{project_match.group(1)}"

            # Parse team from groups
            if result["team_id"] is None:
                team_match = re.match(r"^/?(?:team|teams)/([^/]+)$", group)
                if team_match:
                    result["team_id"] = f"team:{team_match.group(1)}"

    return result


def _normalize_id(value: str, prefix: str) -> str:
    """
    Normalize an ID with a prefix if not already present.

    Args:
        value: The ID value (may or may not have prefix)
        prefix: The expected prefix (e.g., "organization", "project", "team")

    Returns:
        Normalized ID with prefix (e.g., "organization:acme")
    """
    if value.startswith(f"{prefix}:"):
        return value
    return f"{prefix}:{value}"
