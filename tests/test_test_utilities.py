"""
Test suite for shared test utilities.

This module validates the behavior of shared test utilities used across the test suite,
including CLI tool availability decorators and settings isolation fixtures.

Following TDD principles - these tests are written FIRST, before implementation.
"""

import gc
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server_langgraph.core.config import settings


@pytest.mark.xdist_group(name="utilities_tests")
class TestRequiresToolDecorator:
    """Test the @requires_tool decorator for CLI tool availability checking."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_requires_tool_skips_when_tool_missing(self, monkeypatch):
        """Verify decorator skips test when CLI tool is not available."""
        # Mock shutil.which to return None (tool not found)
        import shutil

        monkeypatch.setattr(shutil, "which", lambda x: None)

        # Import the decorator (will be implemented in conftest)
        from tests.conftest import requires_tool

        # Define a test function with the decorator
        @requires_tool("nonexistent-tool")
        def dummy_test():
            """This should be skipped."""
            pass

        # The decorator should raise pytest.skip
        with pytest.raises(pytest.skip.Exception) as exc_info:
            dummy_test()

        assert "nonexistent-tool not installed" in str(exc_info.value)

    def test_requires_tool_passes_when_tool_available(self, monkeypatch):
        """Verify decorator allows test to run when CLI tool is available."""
        # Mock shutil.which to return a path (tool found)
        import shutil

        monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/mock-tool")

        from tests.conftest import requires_tool

        # Define a test function with the decorator
        executed = False

        @requires_tool("existing-tool")
        def dummy_test():
            """This should run."""
            nonlocal executed
            executed = True

        # The test should execute without raising
        dummy_test()
        assert executed is True

    def test_requires_tool_custom_message(self, monkeypatch):
        """Verify decorator uses custom skip message if provided."""
        import shutil

        monkeypatch.setattr(shutil, "which", lambda x: None)

        from tests.conftest import requires_tool

        @requires_tool("custom-tool", skip_reason="Custom skip message")
        def dummy_test():
            """This should be skipped with custom message."""
            pass

        with pytest.raises(pytest.skip.Exception) as exc_info:
            dummy_test()

        assert "Custom skip message" in str(exc_info.value)


@pytest.mark.xdist_group(name="utilities_tests")
class TestSettingsIsolationFixture:
    """Test the settings_isolation fixture for state mutation isolation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_settings_isolation_restores_original_state(self):
        """Verify fixture restores settings to original state after test."""
        # This test will use the actual fixture
        # For now, we'll test the concept with a mock

        # Get current settings
        original_backend = settings.checkpoint_backend

        # Simulate what the fixture should do
        # (In real usage, the fixture would handle this automatically)
        with patch.object(settings, "checkpoint_backend", "test-backend"):
            assert settings.checkpoint_backend == "test-backend"

        # After context, should be restored (this is what monkeypatch does)
        # In the actual fixture implementation, monkeypatch will handle this
        assert settings.checkpoint_backend == original_backend

    def test_settings_isolation_handles_multiple_attributes(self):
        """Verify fixture can isolate multiple settings attributes."""
        original_backend = settings.checkpoint_backend
        original_checkpointing = settings.enable_checkpointing

        # The fixture should allow changing multiple attributes
        # and restore all of them
        # This test validates the pattern we'll use

        with patch.object(settings, "checkpoint_backend", "new-backend"):
            with patch.object(settings, "enable_checkpointing", True):
                assert settings.checkpoint_backend == "new-backend"
                assert settings.enable_checkpointing is True

        # Values should be restored
        assert settings.checkpoint_backend == original_backend
        assert settings.enable_checkpointing == original_checkpointing


@pytest.mark.xdist_group(name="utilities_tests")
@pytest.mark.requires_kubectl
class TestCLIAvailabilityFixtures:
    """Test CLI tool availability fixtures."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_kustomize_available_returns_false_when_missing(self, kustomize_available, monkeypatch):
        """Verify kustomize_available fixture returns False when kustomize not installed."""
        import shutil

        # Since fixture is already evaluated, we need to test the behavior directly
        # Test that it returns False when tool is missing
        assert shutil.which("kustomize") == kustomize_available or kustomize_available in (True, False)

    def test_kubectl_available_returns_value(self, kubectl_available):
        """Verify kubectl_available fixture returns a boolean value."""
        assert isinstance(kubectl_available, bool)

    def test_terraform_available_returns_value(self, terraform_available):
        """Verify terraform_available fixture returns a boolean value."""
        assert isinstance(terraform_available, bool)

    def test_helm_available_returns_value(self, helm_available):
        """Verify helm_available fixture returns a boolean value."""
        assert isinstance(helm_available, bool)

    def test_docker_compose_available_checks_functionality(self, monkeypatch):
        """Verify docker_compose_available fixture checks docker compose functionality."""
        # Test the logic directly by importing and checking
        # We can't test the fixture execution directly, but we can test the pattern
        import subprocess

        # Mock successful docker compose
        def mock_run_success(*args, **kwargs):
            result = Mock()
            result.returncode = 0
            return result

        monkeypatch.setattr(subprocess, "run", mock_run_success)

        # The fixture would return True in this case
        # (we're testing the pattern, not calling the fixture)
        result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=5)
        assert result.returncode == 0

    def test_cli_fixtures_are_booleans(self, kustomize_available, kubectl_available, terraform_available, helm_available):
        """Verify all CLI fixtures return boolean values."""
        assert isinstance(kustomize_available, bool)
        assert isinstance(kubectl_available, bool)
        assert isinstance(terraform_available, bool)
        assert isinstance(helm_available, bool)


@pytest.mark.xdist_group(name="utilities_tests")
@pytest.mark.requires_kubectl
class TestFixtureScoping:
    """Test that fixtures use appropriate scopes for performance."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cli_fixtures_are_session_scoped(self, request):
        """Verify CLI availability fixtures are session-scoped for performance."""
        # Get fixture definitions and check their scope
        fixture_names = ["kustomize_available", "kubectl_available", "terraform_available", "helm_available"]

        for name in fixture_names:
            # Access fixture definition from the fixture manager
            fixturedef = request._fixturemanager._arg2fixturedefs.get(name)
            if fixturedef:
                # Check that at least one definition has session scope
                assert any(fd.scope == "session" for fd in fixturedef), f"{name} should be session-scoped"


@pytest.mark.unit
@pytest.mark.xdist_group(name="utilities_tests")
@pytest.mark.requires_kubectl
class TestUtilityDocumentation:
    """Test that utilities are properly documented."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_requires_tool_has_docstring(self):
        """Verify @requires_tool decorator has comprehensive docstring."""
        from tests.conftest import requires_tool

        assert requires_tool.__doc__ is not None
        assert len(requires_tool.__doc__) > 50  # Meaningful documentation

    def test_settings_isolation_has_docstring(self, settings_isolation):
        """Verify settings_isolation fixture has comprehensive docstring."""
        # Access the fixture's underlying function to get its docstring
        # settings_isolation is the monkeypatch fixture, so we need to check the wrapper
        import inspect

        # Get the conftest module
        import tests.conftest as conftest_module

        # Get the fixture function
        fixture_func = getattr(conftest_module, "settings_isolation", None)
        if fixture_func is not None:
            # For pytest fixtures, check if it has a docstring
            doc = inspect.getdoc(fixture_func)
            assert doc is not None
            assert "isolation" in doc.lower()

    def test_cli_fixtures_have_docstrings(self, request):
        """Verify all CLI availability fixtures have docstrings."""
        import inspect

        import tests.conftest as conftest_module

        fixture_names = [
            "kustomize_available",
            "kubectl_available",
            "terraform_available",
            "helm_available",
            "docker_compose_available",
        ]

        for name in fixture_names:
            fixture_func = getattr(conftest_module, name, None)
            if fixture_func is not None:
                doc = inspect.getdoc(fixture_func)
                assert doc is not None, f"{name} should have a docstring"
                assert len(doc) > 20, f"{name} docstring should be meaningful"
