"""
Regression Test: Worker-Safe Test ID Generation

This test validates that the worker-safe ID generation utilities prevent
database record pollution when tests run in parallel with pytest-xdist.

Root Cause Being Prevented:
- Hardcoded user IDs like "user:alice" cause database constraint violations
  when multiple pytest-xdist workers create records simultaneously
- Solution: Generate worker-scoped IDs that include worker ID

Golden Rules Being Enforced:
1. "Each test should be an island" - Worker-scoped IDs ensure test isolation
2. "Deterministic test data" - Seed with worker ID for reproducibility
3. "No shared state between tests" - Each worker gets unique namespace

CRITICAL: This test must run BEFORE implementing the utilities (RED phase).
Expected to FAIL initially, proving the test works correctly.

After implementing utilities, test should PASS (GREEN phase).

Reference: /tmp/pollution_audit_summary.md
"""

import gc
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.regression


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.xdist_group(name="worker_safe_ids")
class TestWorkerSafeIDGeneration:
    """
    Test suite for worker-safe ID generation utilities

    These utilities prevent database record pollution in pytest-xdist parallel execution
    by generating unique IDs per worker.
    """

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_worker_scoped_user_id_with_default_worker(self):
        """
        🔴 RED: Test worker-scoped user ID generation (default worker)

        When: No PYTEST_XDIST_WORKER env var is set (single-worker mode)
        Then: Should generate ID with default worker 'gw0'
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_user_id

        # Simulate no xdist worker (single-threaded mode)
        with patch.dict(os.environ, {}, clear=False):
            if "PYTEST_XDIST_WORKER" in os.environ:
                del os.environ["PYTEST_XDIST_WORKER"]

            user_id = get_worker_scoped_user_id("alice")

            assert user_id == "user:alice_gw0", (
                f"Expected 'user:alice_gw0' for default worker, got '{user_id}'. "
                f"Worker-scoped IDs must include worker suffix even in single-worker mode."
            )

    def test_get_worker_scoped_user_id_with_multiple_workers(self):
        """
        🔴 RED: Test worker-scoped user ID generation (multiple workers)

        When: PYTEST_XDIST_WORKER is set to different worker IDs
        Then: Should generate unique IDs per worker
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_user_id

        # Test with worker gw3
        with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": "gw3"}):
            user_id = get_worker_scoped_user_id("alice")
            assert user_id == "user:alice_gw3", (
                f"Expected 'user:alice_gw3' for worker gw3, got '{user_id}'. "
                f"Worker-scoped IDs must include actual worker ID from environment."
            )

        # Test with worker gw7
        with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": "gw7"}):
            user_id = get_worker_scoped_user_id("bob")
            assert user_id == "user:bob_gw7", (
                f"Expected 'user:bob_gw7' for worker gw7, got '{user_id}'. "
                f"Different base users should still get worker-scoped IDs."
            )

    def test_get_worker_scoped_user_id_uniqueness_across_workers(self):
        """
        🔴 RED: Test that different workers generate different IDs for same user

        When: Multiple workers (gw0, gw1, gw2) all create "alice" user
        Then: Each worker gets a unique ID to prevent database conflicts
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_user_id

        worker_ids = ["gw0", "gw1", "gw2", "gw3", "gw4", "gw5", "gw6", "gw7"]
        generated_ids = set()

        for worker in worker_ids:
            with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": worker}):
                user_id = get_worker_scoped_user_id("alice")
                generated_ids.add(user_id)

        # Verify all IDs are unique
        assert len(generated_ids) == len(worker_ids), (
            f"Expected {len(worker_ids)} unique IDs, got {len(generated_ids)}. "
            f"IDs generated: {generated_ids}. "
            f"Worker-scoped IDs must be unique across all workers to prevent collisions."
        )

        # Verify expected format
        expected_ids = {f"user:alice_{worker}" for worker in worker_ids}
        assert generated_ids == expected_ids, (
            f"Generated IDs don't match expected format. " f"Expected: {expected_ids}, Got: {generated_ids}"
        )

    def test_get_worker_scoped_email_with_default_worker(self):
        """
        🔴 RED: Test worker-scoped email generation (default worker)

        When: No PYTEST_XDIST_WORKER env var is set
        Then: Should generate email with default worker 'gw0'
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_email

        with patch.dict(os.environ, {}, clear=False):
            if "PYTEST_XDIST_WORKER" in os.environ:
                del os.environ["PYTEST_XDIST_WORKER"]

            email = get_worker_scoped_email("alice", "acme.com")

            assert email == "alice_gw0@acme.com", (
                f"Expected 'alice_gw0@acme.com' for default worker, got '{email}'. "
                f"Worker-scoped emails must include worker suffix before @ symbol."
            )

    def test_get_worker_scoped_email_with_multiple_workers(self):
        """
        🔴 RED: Test worker-scoped email generation (multiple workers)

        When: PYTEST_XDIST_WORKER is set to different worker IDs
        Then: Should generate unique emails per worker
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_email

        # Test with worker gw3
        with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": "gw3"}):
            email = get_worker_scoped_email("alice", "acme.com")
            assert email == "alice_gw3@acme.com", f"Expected 'alice_gw3@acme.com' for worker gw3, got '{email}'"

        # Test with worker gw7
        with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": "gw7"}):
            email = get_worker_scoped_email("bob", "test.com")
            assert email == "bob_gw7@test.com", f"Expected 'bob_gw7@test.com' for worker gw7, got '{email}'"

    def test_get_worker_scoped_service_principal_id_with_default_worker(self):
        """
        🔴 RED: Test worker-scoped service principal ID generation

        When: No PYTEST_XDIST_WORKER env var is set
        Then: Should generate service principal ID with default worker 'gw0'
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_service_principal_id

        with patch.dict(os.environ, {}, clear=False):
            if "PYTEST_XDIST_WORKER" in os.environ:
                del os.environ["PYTEST_XDIST_WORKER"]

            sp_id = get_worker_scoped_service_principal_id("batch-etl-job")

            assert sp_id == "batch-etl-job_gw0", (
                f"Expected 'batch-etl-job_gw0' for default worker, got '{sp_id}'. "
                f"Worker-scoped service principal IDs must include worker suffix."
            )

    def test_get_worker_scoped_service_principal_id_with_multiple_workers(self):
        """
        🔴 RED: Test worker-scoped service principal ID generation (multiple workers)

        When: PYTEST_XDIST_WORKER is set to different worker IDs
        Then: Should generate unique service principal IDs per worker
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_service_principal_id

        # Test with worker gw2
        with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": "gw2"}):
            sp_id = get_worker_scoped_service_principal_id("data-pipeline")
            assert sp_id == "data-pipeline_gw2", f"Expected 'data-pipeline_gw2' for worker gw2, got '{sp_id}'"

    def test_worker_safe_utilities_prevent_database_conflicts(self):
        """
        🔴 RED: Integration test - verify worker-safe IDs prevent collisions

        Scenario: Simulate 8 pytest-xdist workers all creating "alice" user simultaneously
        Expected: Each worker gets unique ID namespace, no database conflicts

        This is the CRITICAL test that validates the entire approach.
        """
        from tests.utils.worker_safe_ids import get_worker_scoped_email, get_worker_scoped_user_id

        workers = [f"gw{i}" for i in range(8)]  # Simulate 8 workers
        all_user_ids = set()
        all_emails = set()

        # Simulate each worker creating "alice" user
        for worker in workers:
            with patch.dict(os.environ, {"PYTEST_XDIST_WORKER": worker}):
                user_id = get_worker_scoped_user_id("alice")
                email = get_worker_scoped_email("alice", "acme.com")

                # Verify no duplicates (would cause database constraint violations)
                assert user_id not in all_user_ids, (
                    f"DUPLICATE user_id '{user_id}' detected for worker {worker}! "
                    f"This would cause database constraint violation in parallel tests."
                )
                assert email not in all_emails, (
                    f"DUPLICATE email '{email}' detected for worker {worker}! "
                    f"This would cause database constraint violation in parallel tests."
                )

                all_user_ids.add(user_id)
                all_emails.add(email)

        # Verify we got 8 unique IDs (one per worker)
        assert len(all_user_ids) == 8, f"Expected 8 unique user IDs, got {len(all_user_ids)}. " f"IDs: {all_user_ids}"
        assert len(all_emails) == 8, f"Expected 8 unique emails, got {len(all_emails)}. " f"Emails: {all_emails}"


@pytest.mark.unit
@pytest.mark.regression
def test_worker_safe_id_documentation():
    """
    Meta-test: Verify that worker-safe ID utilities are properly documented

    This ensures future developers understand why these utilities exist
    and when to use them.
    """
    from pathlib import Path

    utils_file = Path(__file__).parent.parent / "utils" / "worker_safe_ids.py"

    # File should exist
    assert utils_file.exists(), (
        f"Worker-safe ID utilities file not found: {utils_file}. "
        f"These utilities are CRITICAL for preventing database pollution in pytest-xdist."
    )

    content = utils_file.read_text()

    # Should have comprehensive docstrings
    assert '"""' in content, "Module should have docstring explaining purpose"
    assert "pytest-xdist" in content.lower(), "Documentation should mention pytest-xdist"
    assert "worker" in content.lower(), "Documentation should explain worker concept"
    assert (
        "database" in content.lower() or "collision" in content.lower()
    ), "Documentation should explain why this prevents database issues"

    # Should have examples
    assert "Example" in content or "example" in content, "Documentation should include usage examples"
