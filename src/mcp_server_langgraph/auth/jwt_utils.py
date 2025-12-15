"""Shared JWT utilities for consistent token handling across all services.

This module provides a single source of truth for extracting user information
from JWT payloads, ensuring consistency between middleware components.

Supports both:
- Keycloak tokens (preferred_username, realm_access, resource_access)
- InMemoryUserProvider tokens (username, roles)
"""

from __future__ import annotations

import re
from typing import Any


def extract_user_from_jwt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract user information from JWT payload.

    Handles both InMemory tokens and Keycloak tokens with proper field mapping.
    This is the single source of truth for user extraction logic.

    Args:
        payload: JWT token payload (decoded)

    Returns:
        User data dict with:
        - user_id: OpenFGA-compatible user ID (e.g., "user:alice")
        - keycloak_id: Raw UUID from sub claim (for Keycloak Admin API)
        - username: Extracted username
        - roles: List of user roles (combined from all sources)
        - email: Email address (if present)

    Examples:
        >>> # Keycloak token
        >>> payload = {
        ...     "sub": "550e8400-e29b-41d4-a716-446655440000",
        ...     "preferred_username": "alice",
        ...     "realm_access": {"roles": ["user"]},
        ... }
        >>> result = extract_user_from_jwt_payload(payload)
        >>> result["username"]
        'alice'
        >>> result["user_id"]
        'user:alice'

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

    return {
        "user_id": user_id,
        "keycloak_id": keycloak_id,  # Raw UUID for Keycloak Admin API
        "username": username,
        "roles": roles,
        "email": payload.get("email"),
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
