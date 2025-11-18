"""
Unit tests for pytest marker validator.

TDD Context:
- RED (2025-11-12): E2E tests failed - missing 'staging' marker
- GREEN: Added marker, created validator
- REFACTOR: These tests ensure validator catches unregistered markers

Following TDD: Tests ensure validator prevents marker registration issues.
"""

import gc
import sys
import tempfile
from pathlib import Path

import pytest


# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


from validate_pytest_markers import get_registered_markers, get_used_markers  # noqa: E402


# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testmarkerregistration")
@pytest.mark.requires_kubectl
class TestMarkerRegistration:
    """Test that marker registration detection works correctly"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_used_markers_are_registered(self):
        """
        Verify all currently used markers in the codebase are registered.

        This is a regression test that will fail if someone adds an unregistered marker.
        """
        registered = get_registered_markers()
        used = get_used_markers()

        # Markers that are in comments/docs (false positives)
        # These should be ignored by the validator
        allowed_unregistered = {"foo"}  # Used in test documentation

        unregistered = used - registered - allowed_unregistered

        assert not unregistered, (
            f"Found unregistered markers: {sorted(unregistered)}. "
            f"Add them to pyproject.toml [tool.pytest.ini_options.markers]"
        )

    def test_critical_markers_are_registered(self):
        """Ensure all critical markers from the original failure are registered"""
        registered = get_registered_markers()

        # The marker that caused the original E2E test failure
        assert "staging" in registered, "staging marker must be registered"

        # Other deployment-related markers
        assert "deployment" in registered, "deployment marker must be registered"

        # Environment markers
        assert "unit" in registered
        assert "integration" in registered
        assert "e2e" in registered

    def test_service_specific_markers_registered(self):
        """Ensure service-specific markers are registered"""
        registered = get_registered_markers()

        service_markers = [
            "openfga",
            "infisical",
            "mcp",
            "llm",
            "scim",
        ]

        for marker in service_markers:
            assert marker in registered, f"{marker} marker should be registered"

    def test_compliance_markers_registered(self):
        """Ensure compliance and regulatory markers are registered"""
        registered = get_registered_markers()

        compliance_markers = [
            "gdpr",
            "soc2",
            "security",
        ]

        for marker in compliance_markers:
            assert marker in registered, f"{marker} marker should be registered"

    def test_infrastructure_markers_registered(self):
        """Ensure infrastructure markers are registered"""
        registered = get_registered_markers()

        infra_markers = [
            "kubernetes",
            "terraform",
            "requires_kustomize",
            "requires_kubectl",
            "requires_helm",
        ]

        for marker in infra_markers:
            assert marker in registered, f"{marker} marker should be registered"


@pytest.mark.xdist_group(name="testregressionprevention")
class TestRegressionPrevention:
    """
    Regression tests for the specific failure we encountered.

    Ensures the 'staging' marker incident cannot recur.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_prevent_staging_marker_regression(self):
        """
        Prevent regression of missing 'staging' marker.

        Original failure (Run #19310965242):
        ERROR collecting tests/deployment/test_staging_deployment_requirements.py
        'staging' not found in `markers` configuration option
        """
        registered = get_registered_markers()

        assert "staging" in registered, (
            "REGRESSION: staging marker is missing! "
            "This was the root cause of E2E test failure (Run #19310965242). "
            "Add to pyproject.toml: 'staging: Staging environment deployment tests'"
        )

    def test_deployment_marker_exists(self):
        """Ensure deployment marker exists (used as alternative to staging)"""
        registered = get_registered_markers()

        assert "deployment" in registered, "deployment marker should exist as it's related to staging tests"


@pytest.mark.xdist_group(name="testmarkervalidatorbehavior")
class TestMarkerValidatorBehavior:
    """Test the behavior of the marker validator script"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_registered_markers_not_empty(self):
        """Validator should find registered markers in pyproject.toml"""
        registered = get_registered_markers()

        assert len(registered) > 0, "Should find registered markers"
        assert len(registered) > 30, "Should have many markers registered (we have 39+)"

    def test_used_markers_not_empty(self):
        """Validator should find markers used in test files"""
        used = get_used_markers()

        assert len(used) > 0, "Should find markers used in tests"

    def test_built_in_markers_excluded(self):
        """Built-in pytest markers should not be counted as 'used'"""
        used = get_used_markers()

        # Built-in markers that should be excluded
        built_in = {"parametrize", "skip", "skipif", "xfail", "usefixtures", "filterwarnings"}

        for marker in built_in:
            assert marker not in used, f"Built-in marker {marker} should be excluded"


@pytest.mark.xdist_group(name="testspecificmarkercategories")
class TestSpecificMarkerCategories:
    """Test that specific categories of markers are properly registered"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_test_type_markers(self):
        """Test type classification markers"""
        registered = get_registered_markers()

        test_types = [
            "unit",
            "integration",
            "e2e",
            "smoke",
            "benchmark",
            "property",
            "contract",
            "regression",
            "mutation",
        ]

        for marker in test_types:
            assert marker in registered, f"Test type marker '{marker}' should be registered"

    def test_performance_markers(self):
        """Performance-related markers"""
        registered = get_registered_markers()

        perf_markers = [
            "slow",
            "performance",
            "sla",
            "benchmark",
        ]

        for marker in perf_markers:
            assert marker in registered, f"Performance marker '{marker}' should be registered"

    def test_environment_markers(self):
        """Environment-specific markers"""
        registered = get_registered_markers()

        env_markers = [
            "staging",  # The one that caused the failure
            "deployment",
            "infrastructure",
            "ci",
        ]

        for marker in env_markers:
            assert marker in registered, f"Environment marker '{marker}' should be registered"


@pytest.mark.xdist_group(name="testmarkercount")
class TestMarkerCount:
    """Test that we have the expected number of markers"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_minimum_marker_count(self):
        """Ensure we have at least the expected number of registered markers"""
        registered = get_registered_markers()

        # We currently have 39 markers registered (as of the fix)
        # This test ensures we don't accidentally remove markers
        min_expected = 35

        assert len(registered) >= min_expected, (
            f"Expected at least {min_expected} registered markers, "
            f"but found {len(registered)}. Did someone remove markers from pyproject.toml?"
        )

    def test_specific_count_regression(self):
        """
        Regression test: Ensure we have exactly the expected markers.

        After adding 'staging' marker, we should have 39+ markers.
        """
        registered = get_registered_markers()

        # After the fix, we have 39 markers
        # This will fail if someone removes markers
        assert len(registered) >= 39, f"Expected 39+ markers after adding 'staging', but found {len(registered)}"
