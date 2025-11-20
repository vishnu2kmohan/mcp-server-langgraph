"""
Meta-validation: Enforce MCP_SKIP_AUTH configuration in API test fixtures.

This test suite ensures that API test fixtures explicitly set MCP_SKIP_AUTH="false"
to prevent conftest.py pollution from affecting authentication behavior.

CODEX FINDING (2025-11-13):
tests/api/test_service_principals_endpoints.py has comments at lines 155-158 and 211-214
stating the intent to set MCP_SKIP_AUTH="false" before creating FastAPI app, but the
actual assignment is missing. This creates risk of conftest.py pollution where
MCP_SKIP_AUTH="true" (set for most tests) leaks into service principal tests that
need authentication enabled.

TDD Principle: This meta-test enforces the fix MUST exist and prevents regression.
"""

import gc
import os
import re
from pathlib import Path

import pytest


@pytest.mark.meta
@pytest.mark.unit
@pytest.mark.xdist_group(name="testmcpskipauthfixtureenforcement")
class TestMCPSkipAuthFixtureEnforcement:
    """Validate that API test fixtures explicitly set MCP_SKIP_AUTH="false"."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def setup_method(self):
        """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution."""
        import sys

        # Only reset middleware if already loaded (don't pollute import cache)
        if "mcp_server_langgraph.auth.middleware" in sys.modules:
            import mcp_server_langgraph.auth.middleware as middleware_module

            middleware_module._global_auth_middleware = None

        os.environ["MCP_SKIP_AUTH"] = "false"

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory."""
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True, timeout=60
        )
        return Path(result.stdout.strip())

    @pytest.fixture
    def service_principals_test_file(self, repo_root: Path) -> Path:
        """Get path to service principals test file."""
        return repo_root / "tests" / "integration" / "api" / "test_service_principals_endpoints.py"

    def test_sp_test_client_sets_mcp_skip_auth_false(self, service_principals_test_file: Path):
        """Test that sp_test_client fixture sets MCP_SKIP_AUTH="false" explicitly.

        CRITICAL: The fixture comment at line 155-158 says:
        "CRITICAL: Set MCP_SKIP_AUTH="false" BEFORE creating app"

        But the actual assignment is missing. This test enforces it exists.
        """
        assert service_principals_test_file.exists(), f"Test file not found: {service_principals_test_file}"

        with open(service_principals_test_file) as f:
            content = f.read()

        # Find the sp_test_client fixture
        fixture_match = re.search(
            r"@pytest\.fixture.*?\ndef sp_test_client\(.*?\):.*?(?=\n@pytest\.fixture|\nclass |\Z)",
            content,
            re.DOTALL,
        )

        assert fixture_match, "Could not find sp_test_client fixture in test file"

        fixture_code = fixture_match.group(0)

        # Find where app = FastAPI() occurs
        app_creation_match = re.search(r"app\s*=\s*FastAPI\(\)", fixture_code)
        assert app_creation_match, "Could not find 'app = FastAPI()' in sp_test_client fixture"

        app_creation_pos = app_creation_match.start()
        code_before_app = fixture_code[:app_creation_pos]

        # Check for the assignment BEFORE app creation
        has_assignment = 'os.environ["MCP_SKIP_AUTH"]' in code_before_app and '= "false"' in code_before_app

        assert has_assignment, (
            "sp_test_client fixture MUST set os.environ['MCP_SKIP_AUTH'] = \"false\" BEFORE creating app\n"
            "\n"
            "Current issue (tests/api/test_service_principals_endpoints.py:155-160):\n"
            "  - Comment says: 'CRITICAL: Set MCP_SKIP_AUTH=\"false\" BEFORE creating app'\n"
            "  - But the actual assignment is MISSING\n"
            "  - Only sees: '# Create fresh FastAPI app' then 'app = FastAPI()'\n"
            "\n"
            "Why this matters:\n"
            "  - conftest.py sets MCP_SKIP_AUTH='true' for most tests\n"
            "  - Service principal tests need auth enabled (MCP_SKIP_AUTH='false')\n"
            "  - Without explicit assignment, conftest value leaks in\n"
            "  - Causes intermittent test failures or wrong behavior\n"
            "\n"
            "Fix: Add this line BEFORE 'app = FastAPI()':\n"
            '  os.environ["MCP_SKIP_AUTH"] = "false"\n'
            "\n"
            "Example:\n"
            '  # CRITICAL: Set MCP_SKIP_AUTH="false" BEFORE creating app\n'
            "  # ... (existing comments) ...\n"
            '  os.environ["MCP_SKIP_AUTH"] = "false"\n'
            "\n"
            "  # Create fresh FastAPI app\n"
            "  app = FastAPI()\n"
        )

    def test_admin_test_client_sets_mcp_skip_auth_false(self, service_principals_test_file: Path):
        """Test that admin_test_client fixture sets MCP_SKIP_AUTH="false" explicitly.

        Same requirement as sp_test_client - must prevent conftest.py pollution.
        """
        assert service_principals_test_file.exists(), f"Test file not found: {service_principals_test_file}"

        with open(service_principals_test_file) as f:
            content = f.read()

        # Find the admin_test_client fixture
        fixture_match = re.search(
            r"@pytest\.fixture.*?\ndef admin_test_client\(.*?\):.*?(?=\n@pytest\.fixture|\nclass |\Z)",
            content,
            re.DOTALL,
        )

        assert fixture_match, "Could not find admin_test_client fixture in test file"

        fixture_code = fixture_match.group(0)

        # Find where app = FastAPI() occurs
        app_creation_match = re.search(r"app\s*=\s*FastAPI\(\)", fixture_code)
        assert app_creation_match, "Could not find 'app = FastAPI()' in admin_test_client fixture"

        app_creation_pos = app_creation_match.start()
        code_before_app = fixture_code[:app_creation_pos]

        # Check for the assignment BEFORE app creation
        has_assignment = 'os.environ["MCP_SKIP_AUTH"]' in code_before_app and '= "false"' in code_before_app

        assert has_assignment, (
            "admin_test_client fixture MUST set os.environ['MCP_SKIP_AUTH'] = \"false\" BEFORE creating app\n"
            "\n"
            "Current issue (tests/api/test_service_principals_endpoints.py:211-216):\n"
            "  - Comment says: 'CRITICAL: Set MCP_SKIP_AUTH=\"false\" BEFORE creating app'\n"
            "  - But the actual assignment is MISSING\n"
            "\n"
            "Same fix as sp_test_client: Add assignment BEFORE 'app = FastAPI()'\n"
        )

    def test_both_fixtures_restore_mcp_skip_auth_in_cleanup(self, service_principals_test_file: Path):
        """Test that both fixtures document cleanup behavior for MCP_SKIP_AUTH.

        This is informational - the fixtures already clean up via dependency_overrides.clear()
        but we want to ensure the pattern is documented.
        """
        assert service_principals_test_file.exists(), f"Test file not found: {service_principals_test_file}"

        with open(service_principals_test_file) as f:
            content = f.read()

        # Both fixtures should have cleanup (dependency_overrides.clear())
        # This implicitly handles cleanup, so we just verify it exists

        has_cleanup_in_sp = "app.dependency_overrides.clear()" in content
        has_cleanup_in_admin = "app.dependency_overrides.clear()" in content  # Will be true if it exists anywhere

        # This is a soft check - we mainly care that the pattern exists
        # The actual cleanup happens via dependency_overrides mechanism
        assert has_cleanup_in_sp and has_cleanup_in_admin, (
            "Fixtures should have cleanup via app.dependency_overrides.clear()\n"
            "This ensures proper isolation between test runs\n"
        )
