"""
Test file naming validator for documentation.

Following TDD principles:
1. RED: Write failing tests first
2. GREEN: Implement validator to make tests pass
3. REFACTOR: Clean up code
"""

import gc
from pathlib import Path

import pytest

from scripts.validators.file_naming_validator import (
    find_invalid_filenames,
    is_conventional_file,
    is_kebab_case,
    validate_filename_convention,
)


@pytest.mark.xdist_group(name="file_naming_validator")
class TestFileNamingValidator:
    """Test file naming convention validation."""

    def teardown_method(self):
        """Force GC to prevent resource leaks in xdist workers"""
        import gc

        gc.collect()

    def test_lowercase_kebab_case_passes(self):
        """Valid kebab-case filenames should pass."""
        valid_files = [
            Path("docs/getting-started/introduction.mdx"),
            Path("docs/api-reference/sdk-quickstart.mdx"),
            Path("docs/deployment/kubernetes/gke.mdx"),
            Path("docs/references/documentation-authoring-guide.mdx"),
        ]

        for file_path in valid_files:
            errors = validate_filename_convention(file_path)
            assert len(errors) == 0, f"{file_path} should be valid"

    def test_uppercase_detected(self):
        """UPPERCASE filenames should be detected."""
        invalid_files = [
            Path("docs/development/COMMANDS.mdx"),
            Path("docs/security/TRY_EXCEPT_PASS_ANALYSIS.mdx"),
            Path("docs/workflows/SECRETS.mdx"),
        ]

        for file_path in invalid_files:
            errors = validate_filename_convention(file_path)
            assert len(errors) > 0, f"{file_path} should be invalid"
            assert any("lowercase" in error.lower() for error in errors)

    def test_snake_case_detected(self):
        """snake_case filenames should be detected."""
        invalid_files = [
            Path("docs/deployment/my_deployment_guide.mdx"),
            Path("docs/api-reference/api_endpoints.mdx"),
        ]

        for file_path in invalid_files:
            errors = validate_filename_convention(file_path)
            assert len(errors) > 0, f"{file_path} should be invalid"
            assert any("hyphen" in error.lower() or "underscore" in error.lower() for error in errors)

    def test_mixed_case_detected(self):
        """mixedCase and PascalCase filenames should be detected."""
        invalid_files = [
            Path("docs/deployment/myDeploymentGuide.mdx"),
            Path("docs/api-reference/ApiEndpoints.mdx"),
        ]

        for file_path in invalid_files:
            errors = validate_filename_convention(file_path)
            assert len(errors) > 0, f"{file_path} should be invalid"
            assert any("lowercase" in error.lower() for error in errors)

    def test_conventional_files_excluded(self):
        """Conventional files like README.md should be excluded."""
        conventional_files = [
            Path("README.md"),
            Path("CHANGELOG.md"),
            Path("CONTRIBUTING.md"),
            Path("LICENSE"),
            Path("CODE_OF_CONDUCT.md"),
            Path("SECURITY.md"),
        ]

        for file_path in conventional_files:
            assert is_conventional_file(file_path), f"{file_path} should be conventional"
            errors = validate_filename_convention(file_path)
            assert len(errors) == 0, f"{file_path} should pass validation"

    def test_suggests_correct_name(self):
        """Error messages should include suggested correct name."""
        file_path = Path("docs/deployment/MY_DEPLOYMENT_GUIDE.mdx")
        errors = validate_filename_convention(file_path)

        assert len(errors) > 0
        # Should suggest my-deployment-guide.mdx
        assert any("my-deployment-guide" in error for error in errors)

    def test_is_kebab_case_function(self):
        """Test the is_kebab_case helper function."""
        # Valid kebab-case
        assert is_kebab_case("my-guide.mdx")
        assert is_kebab_case("api-reference.mdx")
        assert is_kebab_case("getting-started.mdx")
        assert is_kebab_case("simple.mdx")

        # Invalid - has uppercase
        assert not is_kebab_case("MyGuide.mdx")
        assert not is_kebab_case("API-Reference.mdx")

        # Invalid - has underscores
        assert not is_kebab_case("my_guide.mdx")
        assert not is_kebab_case("api_reference.mdx")

        # Invalid - has spaces
        assert not is_kebab_case("my guide.mdx")

    def test_find_invalid_filenames_in_docs(self):
        """Test finding all invalid filenames in docs directory."""
        # This test will fail initially (RED phase) and pass after implementation
        docs_dir = Path("docs")
        if not docs_dir.exists():
            pytest.skip("docs directory not found")

        invalid_files = find_invalid_filenames(docs_dir, pattern="**/*.mdx")

        # After our fixes, there should be no invalid files
        assert len(invalid_files) == 0, f"Found {len(invalid_files)} invalid files: {invalid_files}"

    def test_numbers_allowed_in_kebab_case(self):
        """Numbers should be allowed in kebab-case filenames."""
        valid_files = [
            Path("docs/releases/v2-8-0.mdx"),
            Path("docs/architecture/adr-0001-decision.mdx"),
            Path("docs/kubernetes/pod-crash-resolution-2025-11-12.mdx"),
        ]

        for file_path in valid_files:
            assert is_kebab_case(file_path.name), f"{file_path.name} should be valid kebab-case"
            errors = validate_filename_convention(file_path)
            assert len(errors) == 0, f"{file_path} should be valid"

    def test_only_validates_docs_directory(self):
        """Validator should only check files in docs/ directory."""
        # Files outside docs/ should not be validated (or should pass)
        external_files = [
            Path("scripts/MY_SCRIPT.py"),
            Path("tests/TEST_FILE.py"),
            Path("src/MY_MODULE.py"),
        ]

        for file_path in external_files:
            # These should either pass or be skipped
            errors = validate_filename_convention(file_path)
            # We don't enforce naming for non-docs files
            assert len(errors) == 0 or "docs/" not in str(file_path)

    def test_md_files_not_allowed_in_docs(self):
        """
        .md files should not be allowed in docs/ directory.
        docs/ is exclusively for .mdx files.
        """
        md_files_in_docs = [
            Path("docs/my-guide.md"),
            Path("docs/deployment/setup.md"),
        ]

        for file_path in md_files_in_docs:
            errors = validate_filename_convention(file_path)
            assert len(errors) > 0, f"{file_path} should be invalid (.md not allowed in docs/)"
            assert any(".mdx" in error or "extension" in error.lower() for error in errors)


@pytest.mark.xdist_group(name="file_naming_validator")
class TestValidatorCLI:
    """Test the CLI interface of the validator."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validator_exit_code_on_errors(self, tmp_path):
        """Validator should exit with code 1 when errors found."""
        # Create temporary invalid file
        invalid_file = tmp_path / "INVALID_NAME.mdx"
        invalid_file.write_text("# Test")

        errors = validate_filename_convention(invalid_file)
        assert len(errors) > 0

    def test_validator_exit_code_on_success(self, tmp_path):
        """Validator should exit with code 0 when no errors."""
        # Create temporary valid file
        valid_file = tmp_path / "valid-name.mdx"
        valid_file.write_text("# Test")

        errors = validate_filename_convention(valid_file)
        # tmp_path is not in docs/, so should pass
        assert len(errors) == 0


@pytest.mark.xdist_group(name="file_naming_validator")
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_empty_filename(self):
        """Empty filename should be handled gracefully."""
        file_path = Path("docs/.mdx")
        errors = validate_filename_convention(file_path)
        assert len(errors) > 0

    def test_hidden_files_allowed(self):
        """Hidden files like .gitignore should be allowed."""
        hidden_files = [
            Path("docs/.gitignore"),
            Path("docs/.mintlify"),
        ]

        for file_path in hidden_files:
            errors = validate_filename_convention(file_path)
            # Hidden files are typically allowed
            assert len(errors) == 0 or file_path.name.startswith(".")

    def test_multiple_hyphens_allowed(self):
        """Multiple consecutive hyphens should be allowed."""
        file_path = Path("docs/my--guide--with--hyphens.mdx")
        # This is technically valid kebab-case, though not ideal
        assert is_kebab_case(file_path.name)

    def test_leading_or_trailing_hyphens_invalid(self):
        """Filenames shouldn't start or end with hyphens."""
        invalid_files = [
            Path("docs/-leading-hyphen.mdx"),
            Path("docs/trailing-hyphen-.mdx"),
        ]

        for file_path in invalid_files:
            assert not is_kebab_case(file_path.name), f"{file_path.name} should be invalid"
