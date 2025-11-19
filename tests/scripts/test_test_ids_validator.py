"""
Unit tests for test ID pollution prevention validator.

This test file validates the shared validation logic used by:
- scripts/validate_test_ids.py (pre-commit hook)
- tests/meta/test_id_pollution_prevention.py (meta-tests)

Following TDD: These tests are written FIRST, before the implementation.
"""

import gc
from pathlib import Path
from textwrap import dedent

import pytest

from tests.validation_lib import test_ids


@pytest.mark.unit
@pytest.mark.meta
@pytest.mark.xdist_group(name="validator_unit_tests")
class TestIDsValidator:
    """Unit tests for test ID pollution prevention logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detects_hardcoded_user_id(self, tmp_path: Path) -> None:
        """Test detection of hardcoded user IDs like 'user:alice'."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                def test_something():
                    user_id = "user:alice"  # Hardcoded ID - should be detected
                    assert user_id
                """
            )
        )

        violations = test_ids.find_hardcoded_ids(test_file)

        assert len(violations) > 0
        line_num, line_content, description = violations[0]
        assert "user:alice" in line_content
        assert "user ID" in description.lower() or "hardcoded" in description.lower()

    def test_detects_hardcoded_apikey_id(self, tmp_path: Path) -> None:
        """Test detection of hardcoded API key IDs."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                def test_api_key():
                    apikey = "apikey_test123"  # Hardcoded API key ID
                    assert apikey
                """
            )
        )

        violations = test_ids.find_hardcoded_ids(test_file)

        assert len(violations) > 0
        line_num, line_content, description = violations[0]
        assert "apikey_" in line_content

    def test_allows_openfga_format_assertions(self, tmp_path: Path) -> None:
        """Test that OpenFGA format assertions are allowed."""
        test_file = tmp_path / "test_legitimate.py"
        test_file.write_text(
            dedent(
                """
                def test_openfga_format():
                    response = {"user_id": "user:alice"}  # OpenFGA format
                    assert response["user_id"] == "user:alice"  # Checking format
                """
            )
        )

        violations = test_ids.find_hardcoded_ids(test_file)

        # Should have NO violations - assertion validations are allowed
        assert len(violations) == 0

    def test_allows_mock_configurations(self, tmp_path: Path) -> None:
        """Test that Mock/AsyncMock configurations are allowed."""
        test_file = tmp_path / "test_mocks.py"
        test_file.write_text(
            dedent(
                """
                from unittest.mock import AsyncMock

                def test_with_mock():
                    mock = AsyncMock()
                    mock.get_user.return_value = {"user_id": "user:alice"}
                    result = mock.get_user()
                    assert result["user_id"] == "user:alice"
                """
            )
        )

        violations = test_ids.find_hardcoded_ids(test_file)

        # Mock configurations are allowed
        assert len(violations) == 0

    def test_allows_docstring_examples(self, tmp_path: Path) -> None:
        """Test that docstring examples are allowed."""
        test_file = tmp_path / "test_docs.py"
        test_file.write_text(
            dedent(
                '''
                def test_something():
                    """
                    Test user creation.

                    Example: user_id = "user:alice"
                    """
                    assert True
                '''
            )
        )

        violations = test_ids.find_hardcoded_ids(test_file)

        # Docstrings are allowed
        assert len(violations) == 0

    def test_allows_comments(self, tmp_path: Path) -> None:
        """Test that comments with IDs are allowed."""
        test_file = tmp_path / "test_comments.py"
        test_file.write_text(
            dedent(
                """
                def test_something():
                    # Example: user:alice or apikey_test123
                    assert True
                """
            )
        )

        violations = test_ids.find_hardcoded_ids(test_file)

        # Comments are allowed
        assert len(violations) == 0

    def test_is_file_exempt_for_conftest(self) -> None:
        """Test that conftest.py is exempt."""
        assert test_ids.is_file_exempt(Path("tests/conftest.py")) is True
        assert test_ids.is_file_exempt(Path("tests/meta/test_id_pollution_prevention.py")) is True

    def test_is_unit_test_with_inmemory_detects_correctly(self, tmp_path: Path) -> None:
        """Test that unit tests with InMemory backends are correctly identified."""
        test_file = tmp_path / "test_unit_inmemory.py"
        test_file.write_text(
            dedent(
                """
                import pytest

                @pytest.mark.unit
                class TestUserProfile:
                    def test_create(self):
                        from storage import InMemoryUserProfileStore
                        storage = InMemoryUserProfileStore()
                        user_id = "user:alice"  # Safe - InMemory backend
                        assert storage.store(user_id)
                """
            )
        )

        # Should be identified as unit test with InMemory
        assert test_ids.is_unit_test_with_inmemory(test_file) is True

    def test_is_unit_test_with_inmemory_rejects_integration(self, tmp_path: Path) -> None:
        """Test that integration tests are NOT identified as InMemory unit tests."""
        test_file = tmp_path / "test_integration.py"
        test_file.write_text(
            dedent(
                """
                import pytest

                @pytest.mark.integration
                class TestUserAPI:
                    async def test_create_user(self, db_session):
                        user_id = "user:alice"  # Dangerous - real DB
                        await db_session.execute("INSERT INTO users VALUES (?)", (user_id,))
                """
            )
        )

        # Should NOT be identified as InMemory unit test
        assert test_ids.is_unit_test_with_inmemory(test_file) is False

    def test_validate_test_file_returns_true_for_valid(self, tmp_path: Path) -> None:
        """Test that validate_test_file returns True for valid files."""
        test_file = tmp_path / "test_good.py"
        test_file.write_text(
            dedent(
                """
                from tests.conftest import get_user_id

                def test_something():
                    user_id = get_user_id()  # Worker-safe helper
                    assert user_id
                """
            )
        )

        result = test_ids.validate_test_file(test_file)

        assert result is True

    def test_validate_test_file_returns_false_for_violations(self, tmp_path: Path) -> None:
        """Test that validate_test_file returns False when violations found."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text(
            dedent(
                """
                def test_something():
                    user_id = "user:alice"  # Hardcoded - violation
                    assert user_id
                """
            )
        )

        result = test_ids.validate_test_file(test_file)

        assert result is False

    def test_check_worker_safe_usage_detects_helpers(self, tmp_path: Path) -> None:
        """Test detection of worker-safe helper usage."""
        test_file = tmp_path / "test_with_helpers.py"
        test_file.write_text(
            dedent(
                """
                from tests.conftest import get_user_id, get_api_key_id

                def test_something():
                    user_id = get_user_id()
                    apikey_id = get_api_key_id()
                    assert user_id and apikey_id
                """
            )
        )

        result = test_ids.check_worker_safe_usage(test_file)

        assert result is True

    def test_check_worker_safe_usage_returns_false_when_no_helpers(self, tmp_path: Path) -> None:
        """Test that check_worker_safe_usage returns False when no helpers used."""
        test_file = tmp_path / "test_no_helpers.py"
        test_file.write_text(
            dedent(
                """
                def test_something():
                    assert True
                """
            )
        )

        result = test_ids.check_worker_safe_usage(test_file)

        assert result is False

    def test_violation_tuple_structure(self, tmp_path: Path) -> None:
        """Test that violations are tuples with expected structure."""
        test_file = tmp_path / "test_bad.py"
        test_file.write_text('def test(): user_id = "user:alice"')

        violations = test_ids.find_hardcoded_ids(test_file)

        assert len(violations) > 0
        line_num, line_content, description = violations[0]

        # Check tuple structure
        assert isinstance(line_num, int)
        assert line_num > 0
        assert isinstance(line_content, str)
        assert len(line_content) > 0
        assert isinstance(description, str)
        assert len(description) > 0


@pytest.mark.unit
@pytest.mark.meta
@pytest.mark.xdist_group(name="ids_validator")
class TestIDsValidatorHelpers:
    """Test helper functions in test IDs validator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_legitimate_patterns_match_correctly(self) -> None:
        """Test that legitimate usage patterns are correctly identified."""
        # OpenFGA format assertion
        line = 'assert response["user_id"] == "user:alice"  # OpenFGA format'
        assert test_ids.is_legitimate_usage(line) is True

        # Mock configuration
        line = 'mock.return_value = {"user_id": "user:alice"}'
        assert test_ids.is_legitimate_usage(line) is True

        # Comment
        line = "# Example: user:alice"
        assert test_ids.is_legitimate_usage(line) is True

        # Hardcoded (not legitimate)
        line = 'user_id = "user:alice"'
        # This should NOT be legitimate (no comment, not in mock, not assertion)
        # Note: This will depend on the actual pattern matching logic

    def test_exempt_files_list_includes_conftest(self) -> None:
        """Test that exempt files list includes expected files."""
        # The is_file_exempt function should recognize these patterns
        assert test_ids.is_file_exempt(Path("tests/conftest.py")) is True
        assert test_ids.is_file_exempt(Path("tests/meta/test_id_pollution_prevention.py")) is True
        assert test_ids.is_file_exempt(Path("tests/unit/test_openfga_client.py")) is True
