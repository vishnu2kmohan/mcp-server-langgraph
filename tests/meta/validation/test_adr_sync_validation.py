#!/usr/bin/env python3
"""
Tests for ADR synchronization validator.

Validates that the check_adr_sync.py script correctly:
1. Counts ADR files and validates README badge
2. Validates ADR numbering (no duplicates/gaps)
3. Validates source/MDX synchronization
4. Supports --fix flag for badge count
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta


def get_repo_root() -> Path:
    """Find repository root with marker validation."""
    current = Path(__file__).parent
    markers = [".git", "pyproject.toml"]
    while current != current.parent:
        if any((current / m).exists() for m in markers):
            return current
        current = current.parent
    raise RuntimeError("Cannot find repo root")


PROJECT_ROOT = get_repo_root()
VALIDATOR_SCRIPT = PROJECT_ROOT / "scripts" / "validators" / "check_adr_sync.py"


@pytest.mark.meta
@pytest.mark.unit
class TestADRSyncValidator:
    """Test ADR synchronization validator."""

    def test_validator_script_exists(self):
        """GIVEN the repository structure WHEN checking for validator THEN it should exist."""
        assert VALIDATOR_SCRIPT.exists(), f"Validator script not found: {VALIDATOR_SCRIPT}"
        assert VALIDATOR_SCRIPT.is_file(), f"Validator script is not a file: {VALIDATOR_SCRIPT}"

    def test_validator_is_executable(self):
        """GIVEN the validator script WHEN checking permissions THEN it should be executable."""
        # Check shebang line exists
        content = VALIDATOR_SCRIPT.read_text()
        assert content.startswith("#!/usr/bin/env python3"), "Validator should have python3 shebang"

    def test_validator_has_help(self):
        """GIVEN the validator script WHEN running with --help THEN it should display help."""
        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, "Validator --help should exit with 0"
        assert "ADR" in result.stdout.upper(), "Help should mention ADR"
        assert "--fix" in result.stdout, "Help should document --fix flag"

    def test_badge_count_matches_actual_adrs(self):
        """GIVEN ADR files in adr/ WHEN validating badge THEN count should match."""
        # Count actual ADRs (exclude README.md)
        adr_dir = PROJECT_ROOT / "adr"
        assert adr_dir.exists(), "adr/ directory should exist"

        adr_files = [f for f in adr_dir.glob("adr-*.md")]
        actual_count = len(adr_files)

        # Read badge from README
        readme = PROJECT_ROOT / "README.md"
        assert readme.exists(), "README.md should exist"

        readme_content = readme.read_text()
        badge_match = re.search(r"ADRs-(\d+)-informational", readme_content)
        assert badge_match, "README should have ADR badge"

        badge_count = int(badge_match.group(1))

        assert badge_count == actual_count, (
            f"Badge count ({badge_count}) should match actual ADRs ({actual_count}). Run: python {VALIDATOR_SCRIPT} --fix"
        )

    def test_validator_detects_badge_mismatch(self, tmp_path):
        """GIVEN mismatched badge count WHEN running validator THEN it should detect the issue."""
        # Create a temporary README with wrong badge count
        test_readme = tmp_path / "README.md"
        test_readme.write_text(
            """# Test Project
[![ADRs](https://img.shields.io/badge/ADRs-99-informational.svg)](adr/README.md)
"""
        )

        # Create test ADR directory with fewer ADRs
        test_adr_dir = tmp_path / "adr"
        test_adr_dir.mkdir()
        (test_adr_dir / "adr-0001-test.md").write_text("# Test ADR")

        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--repo-root", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1, "Validator should exit with 1 on mismatch"
        assert "badge" in result.stdout.lower() or "badge" in result.stderr.lower(), "Should mention badge issue"

    def test_validator_detects_duplicate_numbers(self, tmp_path):
        """GIVEN duplicate ADR numbers WHEN running validator THEN it should detect them."""
        test_adr_dir = tmp_path / "adr"
        test_adr_dir.mkdir()

        # Create duplicate ADR numbers
        (test_adr_dir / "adr-0001-first.md").write_text("# First")
        (test_adr_dir / "adr-0001-duplicate.md").write_text("# Duplicate")
        (test_adr_dir / "adr-0002-second.md").write_text("# Second")

        # Create README with correct count
        readme = tmp_path / "README.md"
        readme.write_text("[![ADRs](https://img.shields.io/badge/ADRs-3-informational.svg)](adr/README.md)")

        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--repo-root", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1, "Validator should exit with 1 on duplicate numbers"
        assert "duplicate" in result.stdout.lower() or "duplicate" in result.stderr.lower(), "Should mention duplicates"

    def test_validator_detects_missing_gaps(self, tmp_path):
        """GIVEN gaps in ADR numbering WHEN running validator THEN it should detect them."""
        test_adr_dir = tmp_path / "adr"
        test_adr_dir.mkdir()

        # Create ADRs with a gap (missing 0002)
        (test_adr_dir / "adr-0001-first.md").write_text("# First")
        (test_adr_dir / "adr-0003-third.md").write_text("# Third")

        # Create README with correct count
        readme = tmp_path / "README.md"
        readme.write_text("[![ADRs](https://img.shields.io/badge/ADRs-2-informational.svg)](adr/README.md)")

        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--repo-root", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Gaps are warnings, not errors (some ADRs may be deprecated/removed)
        # But should be reported
        output = result.stdout + result.stderr
        assert "gap" in output.lower() or "missing" in output.lower(), "Should mention gaps in numbering"

    def test_validator_detects_missing_mdx(self, tmp_path):
        """GIVEN ADR .md without .mdx WHEN running validator THEN it should detect missing sync."""
        test_adr_dir = tmp_path / "adr"
        test_adr_dir.mkdir()
        (test_adr_dir / "adr-0001-test.md").write_text("# Test ADR")

        test_docs_dir = tmp_path / "docs" / "architecture"
        test_docs_dir.mkdir(parents=True)
        # Missing adr-0001-test.mdx

        readme = tmp_path / "README.md"
        readme.write_text("[![ADRs](https://img.shields.io/badge/ADRs-1-informational.svg)](adr/README.md)")

        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--repo-root", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 1, "Validator should exit with 1 on missing MDX"
        assert "mdx" in result.stdout.lower() or "docs" in result.stdout.lower(), "Should mention missing MDX files"

    def test_validator_passes_on_valid_repo(self):
        """GIVEN a valid repository WHEN running validator THEN it should pass."""
        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--repo-root", str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Current repo should be valid
        assert result.returncode == 0, f"Validator should pass on current repo. Output:\n{result.stdout}\n{result.stderr}"

    def test_fix_flag_updates_badge(self, tmp_path):
        """GIVEN wrong badge count WHEN running with --fix THEN badge should be updated."""
        # Create test README with wrong count
        test_readme = tmp_path / "README.md"
        original_content = """# Test Project
[![ADRs](https://img.shields.io/badge/ADRs-99-informational.svg)](adr/README.md)
Some other content
"""
        test_readme.write_text(original_content)

        # Create test ADRs
        test_adr_dir = tmp_path / "adr"
        test_adr_dir.mkdir()
        (test_adr_dir / "adr-0001-test.md").write_text("# Test 1")
        (test_adr_dir / "adr-0002-test.md").write_text("# Test 2")

        # Create docs/architecture with matching MDX files
        test_docs_dir = tmp_path / "docs" / "architecture"
        test_docs_dir.mkdir(parents=True)
        (test_docs_dir / "adr-0001-test.mdx").write_text("# Test 1")
        (test_docs_dir / "adr-0002-test.mdx").write_text("# Test 2")

        # Run with --fix
        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--repo-root", str(tmp_path), "--fix"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"--fix should succeed. Output:\n{result.stdout}\n{result.stderr}"

        # Verify badge was updated
        updated_content = test_readme.read_text()
        assert "ADRs-2-informational" in updated_content, "Badge should be updated to 2"
        assert "ADRs-99-informational" not in updated_content, "Old badge count should be removed"
        assert "Some other content" in updated_content, "Other content should be preserved"

    def test_validator_output_format(self):
        """GIVEN validator execution WHEN checking output THEN it should have clear formatting."""
        result = subprocess.run(
            [sys.executable, str(VALIDATOR_SCRIPT), "--repo-root", str(PROJECT_ROOT)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Should have clear sections
        assert "ADR" in output.upper(), "Output should mention ADR"

        # Should use status indicators
        status_indicators = ["✅", "✓", "PASS", "❌", "✗", "FAIL", "⚠️", "WARNING"]
        has_status = any(indicator in output for indicator in status_indicators)
        assert has_status, "Output should include status indicators"


@pytest.mark.meta
@pytest.mark.integration
class TestADRSyncIntegration:
    """Integration tests for ADR sync validator."""

    def test_all_source_adrs_have_mdx(self):
        """GIVEN ADRs in adr/ WHEN checking docs/ THEN all should have .mdx equivalents."""
        adr_dir = PROJECT_ROOT / "adr"
        docs_dir = PROJECT_ROOT / "docs" / "architecture"

        assert adr_dir.exists(), "adr/ directory should exist"
        assert docs_dir.exists(), "docs/architecture/ directory should exist"

        source_adrs = {f.stem for f in adr_dir.glob("adr-*.md")}
        docs_adrs = {f.stem for f in docs_dir.glob("adr-*.mdx")}

        missing_in_docs = source_adrs - docs_adrs
        assert not missing_in_docs, f"ADRs missing in docs/architecture: {sorted(missing_in_docs)}"

    def test_no_orphaned_mdx_files(self):
        """GIVEN ADRs in docs/ WHEN checking adr/ THEN no orphaned .mdx files should exist."""
        adr_dir = PROJECT_ROOT / "adr"
        docs_dir = PROJECT_ROOT / "docs" / "architecture"

        source_adrs = {f.stem for f in adr_dir.glob("adr-*.md")}
        docs_adrs = {f.stem for f in docs_dir.glob("adr-*.mdx")}

        orphaned_in_docs = docs_adrs - source_adrs
        assert not orphaned_in_docs, f"Orphaned ADRs in docs/architecture: {sorted(orphaned_in_docs)}"

    def test_no_duplicate_adr_numbers(self):
        """GIVEN ADRs in adr/ WHEN checking numbers THEN no duplicates should exist."""
        adr_dir = PROJECT_ROOT / "adr"

        adr_numbers = []
        for adr_file in adr_dir.glob("adr-*.md"):
            match = re.match(r"adr-(\d+)-", adr_file.name)
            if match:
                adr_numbers.append(int(match.group(1)))

        duplicates = [num for num in adr_numbers if adr_numbers.count(num) > 1]
        assert not duplicates, f"Duplicate ADR numbers found: {sorted(set(duplicates))}"

    def test_adr_numbering_sequential(self):
        """GIVEN ADRs in adr/ WHEN checking sequence THEN report gaps (informational)."""
        adr_dir = PROJECT_ROOT / "adr"

        adr_numbers = []
        for adr_file in adr_dir.glob("adr-*.md"):
            match = re.match(r"adr-(\d+)-", adr_file.name)
            if match:
                adr_numbers.append(int(match.group(1)))

        if not adr_numbers:
            pytest.skip("No ADR files found")

        adr_numbers.sort()
        min_num = min(adr_numbers)
        max_num = max(adr_numbers)

        expected_range = set(range(min_num, max_num + 1))
        actual_set = set(adr_numbers)
        gaps = expected_range - actual_set

        # This is informational - gaps may be intentional (deprecated ADRs)
        if gaps:
            print(f"\nINFO: Gaps in ADR numbering (may be intentional): {sorted(gaps)}")
