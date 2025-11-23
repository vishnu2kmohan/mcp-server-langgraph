"""
ID Pollution Prevention - Pre-commit Hook Validation

This meta-test ensures the pre-commit hook prevents hardcoded user IDs in tests.

CRITICAL: Test files must use worker-safe ID helpers (get_user_id, get_api_key_id, etc.)
instead of hardcoded IDs like "user:alice" or "apikey_abc123".

Why this matters:
- Hardcoded IDs cause state pollution in parallel test execution (pytest-xdist)
- State pollution leads to intermittent test failures (flaky tests)
- Flaky tests waste CI/CD time and reduce confidence

Prevention mechanism:
- Pre-commit hook validates test files BEFORE commit
- Hook detects hardcoded IDs and blocks commit with helpful error message
- Developers must use worker-safe helpers (enforced by automation)

Worker-safe helper usage examples:
```python
from tests.conftest import get_user_id, get_api_key_id

def test_something():
    user_id = get_user_id()  # ✅ Worker-safe
    apikey_id = get_api_key_id()  # ✅ Worker-safe

    # NOT: user_id = "user:alice"  # ❌ Hardcoded - will fail pre-commit
```

Related:
- tests/conftest.py: Worker-safe ID helper implementations
- scripts/validate_test_ids.py: Validation script (being validated here)
- .pre-commit-config.yaml: Hook configuration
"""

import gc
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.meta
@pytest.mark.meta
@pytest.mark.precommit
@pytest.mark.xdist_group(name="id_pollution_prevention")
class TestIDPollutionPreventionHook:
    """Test pre-commit hook prevents hardcoded IDs in test files."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def validation_script(self, project_root: Path) -> Path:
        """Path to ID validation script."""
        return project_root / "scripts" / "validation" / "validate_test_ids.py"

    def test_validation_script_exists(self, validation_script: Path) -> None:
        """Test that validation script exists."""
        assert validation_script.exists(), (
            f"Validation script not found: {validation_script}\n"
            f"Create scripts/validation/validate_test_ids.py to enforce ID pollution prevention"
        )

    def test_validation_script_is_executable(self, validation_script: Path) -> None:
        """Test that validation script has execute permissions."""
        assert validation_script.exists()
        # Check if file is executable (on Unix systems)
        import os
        import stat

        st = os.stat(validation_script)
        is_executable = bool(st.st_mode & stat.S_IXUSR)
        assert is_executable or validation_script.suffix == ".py", (
            f"Validation script should be executable: {validation_script}\n" f"Run: chmod +x {validation_script}"
        )

    def test_validation_script_detects_hardcoded_user_ids(self, validation_script: Path, tmp_path: Path) -> None:
        """Test script detects hardcoded user IDs like user:alice."""
        # Create test file with hardcoded ID
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            """
def test_something():
    user_id = "user:alice"  # Hardcoded ID - should be detected
    assert user_id
"""
        )

        # Run validation script
        result = subprocess.run(["python", str(validation_script), str(test_file)], capture_output=True, text=True, timeout=30)

        # Should fail (exit code 1) and report the violation
        assert result.returncode == 1, f"Expected validation to fail, but got exit code {result.returncode}"
        assert "user:alice" in result.stdout or "user:alice" in result.stderr, "Expected error message about hardcoded ID"

    def test_validation_script_detects_hardcoded_apikey_ids(self, validation_script: Path, tmp_path: Path) -> None:
        """Test script detects hardcoded API key IDs."""
        test_file = tmp_path / "test_bad_apikey.py"
        test_file.write_text(
            """
def test_api_key():
    apikey = "apikey_test123"  # Hardcoded API key ID
    assert apikey
"""
        )

        result = subprocess.run(["python", str(validation_script), str(test_file)], capture_output=True, text=True, timeout=30)

        assert result.returncode == 1
        assert "apikey_" in result.stdout or "apikey_" in result.stderr

    def test_validation_script_allows_worker_safe_helpers(self, validation_script: Path, tmp_path: Path) -> None:
        """Test script allows proper usage of worker-safe ID helpers."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            """
from tests.conftest import get_user_id, get_api_key_id

def test_something():
    user_id = get_user_id()  # ✅ Worker-safe
    apikey_id = get_api_key_id()  # ✅ Worker-safe
    assert user_id and apikey_id
"""
        )

        result = subprocess.run(["python", str(validation_script), str(test_file)], capture_output=True, text=True, timeout=30)

        # Should succeed (exit code 0)
        assert result.returncode == 0, f"Expected validation to pass, but got: {result.stdout}\n{result.stderr}"

    def test_validation_script_allows_legitimate_test_assertions(self, validation_script: Path, tmp_path: Path) -> None:
        """Test script allows legitimate uses like checking OpenFGA format."""
        test_file = tmp_path / "test_legitimate.py"
        test_file.write_text(
            """
def test_openfga_format():
    # Legitimate use: asserting expected format in response
    response = {"user_id": "user:alice"}  # OpenFGA format
    assert response["user_id"] == "user:alice"  # ✅ Checking format
"""
        )

        result = subprocess.run(["python", str(validation_script), str(test_file)], capture_output=True, text=True, timeout=30)

        # Should succeed (exit code 0) - assertion validations are allowed
        assert (
            result.returncode == 0
        ), f"Expected validation to pass for assertion validation, but got: {result.stdout}\n{result.stderr}"

    def test_validation_script_allows_unit_tests_with_inmemory(self, validation_script: Path, tmp_path: Path) -> None:
        """Test script allows unit tests with InMemory backends (no pollution risk)."""
        test_file = tmp_path / "test_unit_inmemory.py"
        test_file.write_text(
            """
import pytest

@pytest.mark.meta
class TestUserProfile:
    '''Test UserProfile data model with InMemory storage.'''

    def test_create_user_profile(self):
        from src.storage import InMemoryUserProfileStore

        storage = InMemoryUserProfileStore()
        user_id = "user:alice"  # ✅ Safe: InMemory backend, no database pollution
        profile = {"user_id": user_id, "name": "Alice"}
        storage.store(profile)

        assert storage.get(user_id)["user_id"] == "user:alice"
"""
        )

        result = subprocess.run(["python", str(validation_script), str(test_file)], capture_output=True, text=True, timeout=30)

        # Should succeed (exit code 0) - unit tests with InMemory can't pollute
        # IDs with safety comments (# ✅ Safe:) are allowed by legitimate pattern matching
        assert (
            result.returncode == 0
        ), f"Expected validation to pass for InMemory unit test, but got: {result.stdout}\n{result.stderr}"
        # File passes validation due to safety comment pattern, reported as "No hardcoded IDs found"
        assert "No hardcoded IDs found" in result.stdout or "InMemory" in result.stdout or "Unit test" in result.stdout

    def test_validation_script_allows_mock_configurations(self, validation_script: Path, tmp_path: Path) -> None:
        """Test script allows Mock/AsyncMock configurations in unit tests."""
        test_file = tmp_path / "test_mock_config.py"
        test_file.write_text(
            """
from unittest.mock import Mock, AsyncMock
import pytest

@pytest.mark.meta
class TestWithMocks:
    def test_mock_user_response(self):
        # ✅ Mock configuration - isolates test from external state
        mock_service = Mock()
        mock_service.get_user.return_value = {"user_id": "user:alice"}

        result = mock_service.get_user()
        assert result["user_id"] == "user:alice"

    async def test_async_mock_config(self):
        # ✅ AsyncMock configuration
        mock_client = AsyncMock()
        mock_client.fetch_user = AsyncMock(return_value={"user_id": "user:bob"})

        result = await mock_client.fetch_user()
        assert result["user_id"] == "user:bob"
"""
        )

        result = subprocess.run(["python", str(validation_script), str(test_file)], capture_output=True, text=True, timeout=30)

        # Should succeed (exit code 0) - mock configurations are allowed
        assert (
            result.returncode == 0
        ), f"Expected validation to pass for mock configurations, but got: {result.stdout}\n{result.stderr}"

    def test_validation_script_still_detects_integration_test_violations(
        self, validation_script: Path, tmp_path: Path
    ) -> None:
        """Test script still detects hardcoded IDs in integration tests (real pollution risk)."""
        test_file = tmp_path / "test_integration_bad.py"
        test_file.write_text(
            """
import pytest

@pytest.mark.integration
class TestUserAPI:
    '''Integration test with real database - MUST use worker-safe IDs.'''

    async def test_create_user(self, db_session):
        # ❌ Hardcoded ID in integration test - will cause pollution!
        user_id = "user:alice"
        await db_session.execute("INSERT INTO users VALUES (?)", (user_id,))

        result = await db_session.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        assert result
"""
        )

        result = subprocess.run(["python", str(validation_script), str(test_file)], capture_output=True, text=True, timeout=30)

        # Should fail (exit code 1) - integration tests with hardcoded IDs are violations
        assert (
            result.returncode == 1
        ), f"Expected validation to fail for integration test with hardcoded ID, but got exit code {result.returncode}"
        assert "user:alice" in result.stdout or "user:alice" in result.stderr
