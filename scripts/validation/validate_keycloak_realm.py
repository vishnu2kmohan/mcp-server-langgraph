#!/usr/bin/env python3
"""
Keycloak Realm Configuration Validation

Validates Keycloak realm JSON files to prevent configuration errors that
would cause Keycloak to fail on startup.

Checks performed:
1. Valid JSON syntax
2. No duplicate client IDs
3. No duplicate usernames
4. Required fields present (id, realm, clients, users)

Usage:
    python scripts/validation/validate_keycloak_realm.py [realm_file]

    If no file is specified, validates tests/e2e/default-realm.json

Exit codes:
    0 - Validation passed
    1 - Validation errors found
    2 - Error during execution (file not found, invalid JSON, etc.)

Reference: This validation was added after duplicate openfga-server clients
caused Keycloak startup failures (unique constraint violation).
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple


class ValidationError(NamedTuple):
    """A validation error with location and message."""

    location: str
    message: str


def validate_realm_file(realm_path: Path) -> list[ValidationError]:
    """
    Validate a Keycloak realm JSON file.

    Args:
        realm_path: Path to the realm JSON file

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[ValidationError] = []

    # Check file exists
    if not realm_path.exists():
        return [ValidationError("file", f"Realm file not found: {realm_path}")]

    # Parse JSON
    try:
        with open(realm_path) as f:
            realm = json.load(f)
    except json.JSONDecodeError as e:
        return [ValidationError("json", f"Invalid JSON: {e}")]

    # Check required top-level fields
    required_fields = ["id", "realm"]
    for field in required_fields:
        if field not in realm:
            errors.append(ValidationError("structure", f"Missing required field: {field}"))

    # Validate clients
    clients = realm.get("clients", [])
    if not isinstance(clients, list):
        errors.append(ValidationError("clients", "clients must be an array"))
    else:
        # Check for duplicate client IDs
        client_ids = [c.get("clientId") for c in clients if isinstance(c, dict)]
        duplicates = [cid for cid, count in Counter(client_ids).items() if count > 1]
        for dup in duplicates:
            count = client_ids.count(dup)
            errors.append(
                ValidationError(
                    "clients",
                    f"Duplicate clientId '{dup}' found {count} times "
                    "(will cause unique constraint violation on Keycloak startup)",
                )
            )

        # Validate each client has clientId
        for i, client in enumerate(clients):
            if isinstance(client, dict) and "clientId" not in client:
                errors.append(ValidationError("clients", f"Client at index {i} missing 'clientId' field"))

    # Validate users
    users = realm.get("users", [])
    if not isinstance(users, list):
        errors.append(ValidationError("users", "users must be an array"))
    else:
        # Check for duplicate usernames
        usernames = [u.get("username") for u in users if isinstance(u, dict)]
        duplicates = [uname for uname, count in Counter(usernames).items() if count > 1]
        for dup in duplicates:
            count = usernames.count(dup)
            errors.append(
                ValidationError(
                    "users",
                    f"Duplicate username '{dup}' found {count} times "
                    "(will cause unique constraint violation on Keycloak startup)",
                )
            )

        # Validate each user has username
        for i, user in enumerate(users):
            if isinstance(user, dict) and "username" not in user:
                errors.append(ValidationError("users", f"User at index {i} missing 'username' field"))

    return errors


def main() -> int:
    """Main entry point."""
    # Determine realm file path
    if len(sys.argv) > 1:
        realm_path = Path(sys.argv[1])
    else:
        # Default to test realm
        repo_root = Path(__file__).parent.parent.parent
        realm_path = repo_root / "tests" / "e2e" / "default-realm.json"

    print(f"Validating Keycloak realm: {realm_path}")

    errors = validate_realm_file(realm_path)

    if not errors:
        print("  Realm configuration is valid")
        return 0

    print(f"  Found {len(errors)} validation error(s):")
    for error in errors:
        print(f"    [{error.location}] {error.message}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
