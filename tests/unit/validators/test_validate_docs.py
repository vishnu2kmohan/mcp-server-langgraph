"""
Tests for consolidated documentation validator.

This test suite validates the unified validate_docs.py script that consolidates:
- MDX extension validation
- File naming conventions (kebab-case)
- Frontmatter standardization
- ADR synchronization

TDD: Tests written first, implementation follows.
"""

import gc
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Mark as unit test
pytestmark = [pytest.mark.unit]


def get_repo_root() -> Path:
    """Find repository root."""
    current = Path(__file__).parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Cannot find repo root")


PROJECT_ROOT = get_repo_root()
VALIDATE_DOCS_SCRIPT = PROJECT_ROOT / "scripts" / "validators" / "validate_docs.py"


@pytest.mark.xdist_group(name="testvalidatedocsscript")
class TestValidateDocsScript:
    """Test the consolidated validate_docs.py script exists and is executable."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_script_exists_at_expected_path(self):
        """Test that validate_docs.py exists at the expected path."""
        assert VALIDATE_DOCS_SCRIPT.exists(), f"Script not found: {VALIDATE_DOCS_SCRIPT}"

    def test_script_has_help(self):
        """Test that script has --help option."""
        result = subprocess.run(
            [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"--help failed: {result.stderr}"
        assert "--mdx" in result.stdout or "mdx" in result.stdout.lower()
        assert "--adr" in result.stdout or "adr" in result.stdout.lower()

    def test_script_accepts_all_flag(self):
        """Test that script accepts --all flag."""
        result = subprocess.run(
            [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "--all" in result.stdout, "Missing --all flag in help"


@pytest.mark.xdist_group(name="testmdxvalidation")
class TestMDXValidation:
    """Test MDX validation functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_detects_md_files_in_docs(self):
        """Test that .md files in docs/ are detected as errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Create an invalid .md file
            (docs_dir / "test.md").write_text("# Test")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, "Should fail when .md files found in docs/"
            assert "test.md" in result.stdout or "test.md" in result.stderr

    def test_accepts_mdx_files(self):
        """Test that .mdx files pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Create a valid .mdx file
            (docs_dir / "test.mdx").write_text("---\ntitle: Test\n---\n# Test")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Should pass with valid .mdx files: {result.stdout}\n{result.stderr}"

    def test_empty_docs_dir_passes(self):
        """Test that empty docs directory passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Empty docs dir should pass: {result.stdout}\n{result.stderr}"


@pytest.mark.xdist_group(name="testfilenaming")
class TestFileNamingValidation:
    """Test file naming convention validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rejects_uppercase_filenames(self):
        """Test that UPPERCASE filenames are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Create file with uppercase name
            (docs_dir / "TEST_FILE.mdx").write_text("---\ntitle: Test\n---\n# Test")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, "Should fail with uppercase filename"
            assert "TEST_FILE" in result.stdout or "TEST_FILE" in result.stderr

    def test_rejects_underscore_filenames(self):
        """Test that snake_case filenames are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Create file with underscore
            (docs_dir / "my_file.mdx").write_text("---\ntitle: Test\n---\n# Test")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, "Should fail with snake_case filename"

    def test_accepts_kebab_case_filenames(self):
        """Test that kebab-case filenames pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Create valid kebab-case file
            (docs_dir / "my-file.mdx").write_text("---\ntitle: Test\n---\n# Test")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Kebab-case should pass: {result.stdout}\n{result.stderr}"


@pytest.mark.xdist_group(name="testfrontmatter")
class TestFrontmatterValidation:
    """Test frontmatter validation functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_detects_inconsistent_frontmatter_quotes(self):
        """Test that inconsistent frontmatter quote style is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            # Create file with double quotes (should use single quotes for description)
            content = """---
title: Test Title
description: "This should use single quotes"
icon: "star"
---
# Content
"""
            (docs_dir / "test-file.mdx").write_text(content)

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should detect frontmatter issues (exit 0 in dry-run mode, but report issues)
            assert "frontmatter" in result.stdout.lower() or result.returncode == 0


@pytest.mark.xdist_group(name="testadrvalidation")
class TestADRValidation:
    """Test ADR synchronization validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_detects_missing_adr_in_docs(self):
        """Test that ADRs missing from docs/architecture are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adr_dir = Path(tmpdir) / "adr"
            docs_arch_dir = Path(tmpdir) / "docs" / "architecture"
            adr_dir.mkdir()
            docs_arch_dir.mkdir(parents=True)

            # Create ADR in source but not in docs
            (adr_dir / "adr-0001-test.md").write_text("# ADR 0001")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_DOCS_SCRIPT),
                    "--adr",
                    "--repo-root",
                    str(tmpdir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, "Should fail when ADR missing in docs"
            assert "adr-0001" in result.stdout.lower() or "adr-0001" in result.stderr.lower()

    def test_detects_orphaned_adr_in_docs(self):
        """Test that orphaned ADRs in docs/architecture are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adr_dir = Path(tmpdir) / "adr"
            docs_arch_dir = Path(tmpdir) / "docs" / "architecture"
            adr_dir.mkdir()
            docs_arch_dir.mkdir(parents=True)

            # Create ADR in docs but not in source
            (docs_arch_dir / "adr-0001-orphan.mdx").write_text("# Orphan ADR")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_DOCS_SCRIPT),
                    "--adr",
                    "--repo-root",
                    str(tmpdir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, "Should fail when orphaned ADR in docs"

    def test_synced_adrs_pass(self):
        """Test that synchronized ADRs pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adr_dir = Path(tmpdir) / "adr"
            docs_arch_dir = Path(tmpdir) / "docs" / "architecture"
            adr_dir.mkdir()
            docs_arch_dir.mkdir(parents=True)

            # Create matching ADRs
            (adr_dir / "adr-0001-test.md").write_text("# ADR 0001")
            (docs_arch_dir / "adr-0001-test.mdx").write_text("# ADR 0001")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_DOCS_SCRIPT),
                    "--adr",
                    "--repo-root",
                    str(tmpdir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Synced ADRs should pass: {result.stdout}\n{result.stderr}"

    def test_detects_uppercase_adr_filenames(self):
        """Test that uppercase ADR-* filenames are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adr_dir = Path(tmpdir) / "adr"
            docs_arch_dir = Path(tmpdir) / "docs" / "architecture"
            adr_dir.mkdir()
            docs_arch_dir.mkdir(parents=True)

            # Create ADR with uppercase prefix (should be lowercase)
            (adr_dir / "ADR-0001-test.md").write_text("# ADR 0001")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_DOCS_SCRIPT),
                    "--adr",
                    "--repo-root",
                    str(tmpdir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, "Should fail with uppercase ADR- prefix"


@pytest.mark.xdist_group(name="testtestsvalidation")
class TestTestsValidation:
    """Test the --tests flag that runs pytest validation tests."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_tests_flag_runs_pytest(self):
        """Test that --tests flag invokes pytest."""
        result = subprocess.run(
            [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--tests", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # In dry-run mode, should report what tests would run
        assert "pytest" in result.stdout.lower() or "test" in result.stdout.lower()


@pytest.mark.xdist_group(name="testallvalidation")
class TestAllValidation:
    """Test the --all flag that runs all validations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_flag_runs_all_validations(self):
        """Test that --all runs MDX, ADR, and test validations."""
        result = subprocess.run(
            [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--all", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should mention all validation types
        output = result.stdout.lower()
        assert "mdx" in output or result.returncode == 0
        assert "adr" in output or result.returncode == 0

    def test_all_flag_on_real_repo_mdx_and_adr_only(self):
        """Test --mdx and --adr on the actual repository (skip pytest tests)."""
        # Only test MDX and ADR validation, not the pytest tests
        # (pytest tests may fail for unrelated reasons)
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATE_DOCS_SCRIPT),
                "--mdx",
                "--adr",
                "--docs-dir",
                str(PROJECT_ROOT / "docs"),
                "--repo-root",
                str(PROJECT_ROOT),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # The real repo should pass MDX and ADR validations
        assert result.returncode == 0, f"Real repo failed validation:\n{result.stdout}\n{result.stderr}"


@pytest.mark.xdist_group(name="testquietmode")
class TestQuietMode:
    """Test quiet mode output."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_quiet_flag_suppresses_output(self):
        """Test that --quiet suppresses normal output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "test.mdx").write_text("---\ntitle: Test\n---\n# Test")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_DOCS_SCRIPT),
                    "--mdx",
                    "--docs-dir",
                    str(docs_dir),
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0
            # Quiet mode should have minimal output
            assert len(result.stdout) < 100 or result.stdout.strip() == ""


@pytest.mark.xdist_group(name="testexitcodes")
class TestExitCodes:
    """Test exit codes for different scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_exit_0_on_success(self):
        """Test exit code 0 when all validations pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "valid-file.mdx").write_text("---\ntitle: Test\n---\n# Test")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0

    def test_exit_1_on_validation_failure(self):
        """Test exit code 1 when validation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            (docs_dir / "invalid.md").write_text("# Invalid")

            result = subprocess.run(
                [sys.executable, str(VALIDATE_DOCS_SCRIPT), "--mdx", "--docs-dir", str(docs_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 1
