"""
Worker-Safe Test ID Generation Utilities

This module provides utilities for generating worker-scoped test IDs that prevent
database record pollution when tests run in parallel with pytest-xdist.

Problem Statement:
------------------
When running tests in parallel with pytest-xdist, multiple worker processes may
attempt to create database records with the same hardcoded IDs simultaneously,
causing:

1. Database constraint violations (unique key conflicts)
2. Test interference (workers overwriting each other's data)
3. Flaky tests (pass in isolation, fail in parallel)
4. Data corruption (tests reading wrong data from other workers)

Example of the Problem:
-----------------------
# BAD - Causes worker collisions
def test_create_user(api_client):
    user_id = "user:alice"  # ❌ All 8 workers try to create same ID!
    response = api_client.post("/users/", json={"user_id": user_id})
    # ^ FAILS with database constraint violation in parallel mode

Solution:
---------
These utilities generate worker-scoped IDs by appending the pytest-xdist worker ID
to the base identifier, ensuring each worker operates in its own namespace.

Example Usage:
--------------
# GOOD - Worker-safe test
from tests.utils.worker_safe_ids import get_worker_scoped_user_id

def test_create_user(api_client):
    user_id = get_worker_scoped_user_id("alice")  # ✅ "user:alice_gw3" for worker gw3
    response = api_client.post("/users/", json={"user_id": user_id})
    # ^ PASSES - each worker has unique ID!

Worker ID Mapping:
------------------
- Worker 0: gw0 -> "user:alice_gw0"
- Worker 1: gw1 -> "user:alice_gw1"
- Worker 2: gw2 -> "user:alice_gw2"
- ...
- Worker 7: gw7 -> "user:alice_gw7"

Each worker creates database records in its own namespace, preventing conflicts.

Golden Rules Enforced:
----------------------
1. ✅ "Each test should be an island" - Worker-scoped IDs ensure test isolation
2. ✅ "Deterministic test data" - Seed with worker ID for reproducibility
3. ✅ "No shared state between tests" - Each worker gets unique namespace
4. ✅ "Use unique file paths" - Similar concept applied to database IDs

References:
-----------
- Audit Report: /tmp/pollution_audit_summary.md
- Existing Pattern: tests/regression/test_pytest_xdist_worker_database_isolation.py
- Validation Test: tests/regression/test_worker_safe_test_ids.py

CRITICAL: Use these utilities for ALL test data that creates database records,
especially user IDs, emails, and service principal IDs.
"""

import os


def get_worker_scoped_user_id(base_user: str) -> str:
    """
    Generate a worker-scoped user ID to prevent parallel test collisions.

    Args:
        base_user: The base username (e.g., "alice", "bob", "admin")

    Returns:
        Worker-scoped user ID in OpenFGA format (e.g., "user:alice_gw3")

    Example:
        >>> # In worker gw0:
        >>> get_worker_scoped_user_id("alice")
        'user:alice_gw0'

        >>> # In worker gw3:
        >>> get_worker_scoped_user_id("alice")
        'user:alice_gw3'

    Note:
        If PYTEST_XDIST_WORKER is not set (single-worker mode), defaults to "gw0".
        This ensures consistent behavior whether running tests in parallel or not.
    """
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    return f"user:{base_user}_{worker_id}"


def get_worker_scoped_email(username: str, domain: str) -> str:
    """
    Generate a worker-scoped email address to prevent parallel test collisions.

    Args:
        username: The base username (e.g., "alice", "bob")
        domain: The email domain (e.g., "acme.com", "example.com")

    Returns:
        Worker-scoped email address (e.g., "alice_gw3@acme.com")

    Example:
        >>> # In worker gw0:
        >>> get_worker_scoped_email("alice", "acme.com")
        'alice_gw0@acme.com'

        >>> # In worker gw5:
        >>> get_worker_scoped_email("bob", "test.com")
        'bob_gw5@test.com'

    Note:
        The worker ID is inserted before the @ symbol to maintain valid email format.
    """
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    return f"{username}_{worker_id}@{domain}"


def get_worker_scoped_service_principal_id(base_id: str) -> str:
    """
    Generate a worker-scoped service principal ID to prevent parallel test collisions.

    Args:
        base_id: The base service principal identifier (e.g., "batch-etl-job", "api-gateway")

    Returns:
        Worker-scoped service principal ID (e.g., "batch-etl-job_gw2")

    Example:
        >>> # In worker gw0:
        >>> get_worker_scoped_service_principal_id("data-pipeline")
        'data-pipeline_gw0'

        >>> # In worker gw4:
        >>> get_worker_scoped_service_principal_id("batch-etl-job")
        'batch-etl-job_gw4'

    Note:
        Service principals are created per worker to prevent conflicts when multiple
        workers run integration tests that create service principals simultaneously.
    """
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    return f"{base_id}_{worker_id}"


def get_worker_id() -> str:
    """
    Get the current pytest-xdist worker ID.

    Returns:
        Worker ID (e.g., "gw0", "gw3", "gw7"), defaults to "gw0" if not in xdist mode

    Example:
        >>> # In worker gw3:
        >>> get_worker_id()
        'gw3'

        >>> # In single-worker mode:
        >>> get_worker_id()
        'gw0'

    Note:
        Useful when you need to create custom worker-scoped identifiers beyond
        the standard user/email/service principal patterns.
    """
    return os.getenv("PYTEST_XDIST_WORKER", "gw0")


# Convenience exports
__all__ = [
    "get_worker_scoped_user_id",
    "get_worker_scoped_email",
    "get_worker_scoped_service_principal_id",
    "get_worker_id",
]
