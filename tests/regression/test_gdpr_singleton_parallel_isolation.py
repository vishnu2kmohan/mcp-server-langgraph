"""
TDD Test: GDPR Singleton Parallel Execution Isolation

PURPOSE:
--------
This test validates that GDPR storage does NOT suffer from cross-worker
pollution when using pytest-xdist parallel execution.

EXPECTED BEHAVIOR (TDD RED -> GREEN):
--------------------------------------
🔴 RED: This test should FAIL with the current global singleton implementation
        because multiple pytest-xdist workers share the same global _gdpr_storage
        variable, causing cross-worker state pollution.

🟢 GREEN: After refactoring to request-scoped dependency injection, this test
          should PASS consistently because each request gets its own storage
          instance with no shared global state.

CURRENT ISSUE (from CODEX report):
-----------------------------------
- Tests pass 100% in serial mode
- Tests pass ~85% with parallel execution (8 workers)
- Root cause: Global singleton `_gdpr_storage` in factory.py:170-228
- Fixture resets only affect current worker, not other workers

VALIDATION:
-----------
Run this test with different worker counts to reproduce the issue:

# Serial (should PASS):
pytest tests/regression/test_gdpr_singleton_parallel_isolation.py -v

# Parallel 2 workers (should PASS ~95%):
pytest tests/regression/test_gdpr_singleton_parallel_isolation.py -n 2 -v

# Parallel 8 workers (should FAIL ~15% - current issue):
pytest tests/regression/test_gdpr_singleton_parallel_isolation.py -n 8 -v

SOLUTION:
---------
Refactor src/mcp_server_langgraph/compliance/gdpr/factory.py to use
request-scoped dependency injection instead of global singleton:

    from fastapi import Request, Depends

    async def get_gdpr_storage(request: Request) -> GDPRStorage:
        \"\"\"Get GDPR storage from request state (no global).\"\"\"
        if not hasattr(request.state, "gdpr_storage"):
            request.state.gdpr_storage = await create_gdpr_storage(
                backend="memory"  # or from config
            )
        return request.state.gdpr_storage

Reference:
----------
- CODEX_FINDINGS_VALIDATION_REPORT_2025-11-21.md
- tests/regression/test_fastapi_auth_override_sanity.py (related flakiness)
"""

import asyncio
import gc
import os
from datetime import datetime, UTC

import pytest

from mcp_server_langgraph.compliance.gdpr.factory import (
    get_gdpr_storage,
    initialize_gdpr_storage,
    reset_gdpr_storage,
)
from mcp_server_langgraph.compliance.gdpr.storage import UserProfile

# Mark as regression test for parallel execution
pytestmark = [pytest.mark.regression, pytest.mark.unit]


@pytest.mark.xdist_group(name="gdpr_singleton_isolation_tests")
class TestGDPRSingletonParallelIsolation:
    """
    TDD tests for GDPR singleton parallel execution isolation.

    These tests are designed to FAIL with the current global singleton
    implementation and PASS after refactoring to request-scoped state.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        reset_gdpr_storage()
        gc.collect()

    @pytest.mark.asyncio
    async def test_singleton_isolation_worker_specific_data_does_not_leak(self):
        """
        🔴 RED: This test should FAIL in parallel mode with global singleton.
        🟢 GREEN: Should PASS after refactoring to request-scoped storage.

        Test validates that data created by one worker doesn't leak to another.
        """
        # Get worker ID to create worker-specific data
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")

        # Initialize storage with worker-specific data
        await initialize_gdpr_storage(backend="memory")
        storage = get_gdpr_storage()

        # Create a user profile with worker-specific ID
        user_id = f"user:test_{worker_id}_isolation"
        profile = UserProfile(
            user_id=user_id,
            username=f"{worker_id}_testuser",
            email=f"{worker_id}@test.com",
            created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            last_updated=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            metadata={"worker": worker_id},
        )

        # Store the profile
        created = await storage.user_profiles.create(profile)
        assert created is True, f"Failed to create profile for {user_id}"

        # Retrieve and validate
        retrieved = await storage.user_profiles.get(user_id)
        assert retrieved is not None, f"Profile {user_id} should exist"
        assert retrieved.metadata.get("worker") == worker_id, (
            f"Worker ID mismatch: expected {worker_id}, got {retrieved.metadata.get('worker')}"
        )

        # CRITICAL VALIDATION: Check for cross-worker pollution
        # If global singleton is used, other workers' data might be visible
        other_workers = [f"gw{i}" for i in range(8) if f"gw{i}" != worker_id]
        for other_worker_id in other_workers:
            other_user_id = f"user:test_{other_worker_id}_isolation"
            other_profile = await storage.user_profiles.get(other_user_id)

            # This should be None because other workers should have separate storage
            # If this fails, it means we have cross-worker pollution via global singleton
            assert other_profile is None, (
                f"❌ CROSS-WORKER POLLUTION DETECTED: Worker {worker_id} can see "
                f"data from worker {other_worker_id}. This indicates global singleton "
                f"is being shared across pytest-xdist workers."
            )

    @pytest.mark.asyncio
    async def test_singleton_reset_only_affects_current_worker(self):
        """
        🔴 RED: This test demonstrates the current issue - reset only affects current worker.
        🟢 GREEN: After refactoring, this test should show proper isolation.

        Test validates that reset_gdpr_storage() only resets the current worker's storage.
        """
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")

        # Initialize and populate storage
        await initialize_gdpr_storage(backend="memory")
        storage = get_gdpr_storage()

        user_id = f"user:test_{worker_id}_reset"
        profile = UserProfile(
            user_id=user_id,
            username=f"{worker_id}_resettest",
            email=f"{worker_id}_reset@test.com",
            created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            last_updated=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

        await storage.user_profiles.create(profile)

        # Reset storage
        reset_gdpr_storage()

        # After reset, storage should be None for this worker
        with pytest.raises(RuntimeError, match="GDPR storage not initialized"):
            get_gdpr_storage()

        # Re-initialize
        await initialize_gdpr_storage(backend="memory")
        new_storage = get_gdpr_storage()

        # Data should be gone after reset
        retrieved = await new_storage.user_profiles.get(user_id)
        assert retrieved is None, (
            f"After reset and re-initialization, previous data should be gone. Found profile: {retrieved}"
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("PYTEST_XDIST_WORKER") is None, reason="This test only meaningful in parallel execution mode"
    )
    async def test_parallel_execution_creates_independent_storage_instances(self):
        """
        🔴 RED: This test should FAIL with global singleton (all workers share same instance).
        🟢 GREEN: Should PASS with request-scoped storage (each worker independent).

        Test validates that each pytest-xdist worker gets its own storage instance.
        """
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")

        # Initialize storage
        await initialize_gdpr_storage(backend="memory")
        storage1 = get_gdpr_storage()

        # Get storage again - should be same instance (within same worker)
        storage2 = get_gdpr_storage()

        # Within the same worker, should return same instance
        assert storage1 is storage2, "Within same worker, get_gdpr_storage() should return same instance"

        # Add worker-specific marker to storage
        # In the CURRENT implementation (global singleton), this will pollute other workers
        # In the FIXED implementation (request-scoped), this will be isolated
        user_id = f"user:marker_{worker_id}"
        profile = UserProfile(
            user_id=user_id,
            username=f"marker_{worker_id}",
            email=f"marker_{worker_id}@test.com",
            created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            last_updated=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            metadata={"marker": f"worker_{worker_id}", "timestamp": datetime.now(UTC).isoformat()},
        )

        await storage1.user_profiles.create(profile)

        # Validate it's there
        retrieved = await storage1.user_profiles.get(user_id)
        assert retrieved is not None, f"Marker profile should exist for {worker_id}"
        assert retrieved.metadata["marker"] == f"worker_{worker_id}"

    @pytest.mark.asyncio
    async def test_concurrent_storage_operations_do_not_conflict(self):
        """
        🔴 RED: May fail with global singleton due to race conditions.
        🟢 GREEN: Should pass with request-scoped storage (proper isolation).

        Test validates that concurrent operations on storage don't conflict.
        """
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")

        await initialize_gdpr_storage(backend="memory")
        storage = get_gdpr_storage()

        # Create multiple profiles concurrently
        async def create_profile(index: int) -> bool:
            user_id = f"user:concurrent_{worker_id}_{index}"
            profile = UserProfile(
                user_id=user_id,
                username=f"concurrent_{index}",
                email=f"concurrent_{index}@test.com",
                created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                last_updated=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                metadata={"index": index, "worker": worker_id},
            )
            return await storage.user_profiles.create(profile)

        # Create 10 profiles concurrently
        results = await asyncio.gather(*[create_profile(i) for i in range(10)])

        # All should succeed
        assert all(results), "All concurrent creates should succeed"

        # Verify all profiles exist and belong to this worker
        for i in range(10):
            user_id = f"user:concurrent_{worker_id}_{i}"
            profile = await storage.user_profiles.get(user_id)
            assert profile is not None, f"Profile {user_id} should exist"
            assert profile.metadata["worker"] == worker_id, (
                f"Profile should belong to worker {worker_id}, got {profile.metadata.get('worker')}"
            )
            assert profile.metadata["index"] == i, f"Profile index should be {i}, got {profile.metadata.get('index')}"


@pytest.mark.xdist_group(name="gdpr_singleton_stress_tests")
class TestGDPRSingletonStressTest:
    """
    Stress tests to expose singleton issues more reliably.

    These tests are more aggressive and should consistently FAIL with
    the global singleton implementation when run in parallel.
    """

    def teardown_method(self):
        """Force GC and cleanup."""
        reset_gdpr_storage()
        gc.collect()

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_rapid_initialize_reset_cycles_do_not_corrupt_state(self):
        """
        🔴 RED: Likely to fail with global singleton under parallel execution.
        🟢 GREEN: Should pass with proper isolation.

        Rapidly initialize and reset storage to expose race conditions.
        """
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")

        for cycle in range(5):
            # Initialize
            await initialize_gdpr_storage(backend="memory")
            storage = get_gdpr_storage()

            # Create data
            user_id = f"user:cycle_{worker_id}_{cycle}"
            profile = UserProfile(
                user_id=user_id,
                username=f"cycle_{cycle}",
                email=f"cycle_{cycle}@test.com",
                created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                last_updated=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                metadata={"cycle": cycle, "worker": worker_id},
            )

            created = await storage.user_profiles.create(profile)
            assert created, f"Failed to create profile in cycle {cycle}"

            # Verify
            retrieved = await storage.user_profiles.get(user_id)
            assert retrieved is not None, f"Profile should exist in cycle {cycle}"

            # Reset for next cycle
            reset_gdpr_storage()
