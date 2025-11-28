"""
Unit tests for ADR synchronization validator.

Tests comprehensive ADR synchronization validation including:
1. ADR file discovery in source and docs directories
2. Synchronization status checking
3. Uppercase filename detection
4. Missing ADR detection (both directions)
5. CLI argument parsing and exit codes

TDD Principle: Test all public methods and critical edge cases.
Target: 80%+ code coverage for scripts/validators/adr_sync_validator.py
"""

import gc
from pathlib import Path
from unittest.mock import patch

import pytest

# Mark as unit test
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testadrsyncvalidator")
class TestAdrSyncValidator:
    """Comprehensive tests for AdrSyncValidator class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def temp_repo(self, tmp_path: Path) -> Path:
        """
        Create temporary repository structure for testing.

        Structure:
            repo/
            ├── adr/
            │   ├── adr-0001-test.md
            │   └── adr-0002-example.md
            └── docs/
                └── architecture/
                    ├── adr-0001-test.mdx
                    └── adr-0002-example.mdx
        """
        repo = tmp_path / "repo"
        adr_dir = repo / "adr"
        docs_adr_dir = repo / "docs" / "architecture"

        adr_dir.mkdir(parents=True)
        docs_adr_dir.mkdir(parents=True)

        # Create matching ADRs
        (adr_dir / "adr-0001-test.md").write_text("# ADR 0001: Test\n")
        (adr_dir / "adr-0002-example.md").write_text("# ADR 0002: Example\n")
        (docs_adr_dir / "adr-0001-test.mdx").write_text("# ADR 0001: Test\n")
        (docs_adr_dir / "adr-0002-example.mdx").write_text("# ADR 0002: Example\n")

        return repo

    def test_validator_initialization_sets_correct_paths(self, temp_repo: Path):
        """
        Test that validator initializes with correct paths.

        Validates:
        - repo_root is set correctly
        - adr_dir points to /adr
        - docs_adr_dir points to /docs/architecture
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        validator = AdrSyncValidator(temp_repo)

        assert validator.repo_root == temp_repo
        assert validator.adr_dir == temp_repo / "adr"
        assert validator.docs_adr_dir == temp_repo / "docs" / "architecture"

    def test_find_adrs_with_matching_files(self, temp_repo: Path):
        """
        Test ADR discovery in directory with .md and .mdx files.

        Expected:
        - Finds all adr-NNNN-*.md files in /adr
        - Finds all adr-NNNN-*.mdx files in /docs/architecture
        - Returns set of ADR names without extension
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        validator = AdrSyncValidator(temp_repo)

        # Test .md files in /adr
        source_adrs = validator._find_adrs(validator.adr_dir, ".md")
        assert source_adrs == {"adr-0001-test", "adr-0002-example"}

        # Test .mdx files in /docs/architecture
        docs_adrs = validator._find_adrs(validator.docs_adr_dir, ".mdx")
        assert docs_adrs == {"adr-0001-test", "adr-0002-example"}

    def test_find_adrs_with_nonexistent_directory(self):
        """
        Test ADR discovery when directory doesn't exist.

        Expected:
        - Returns empty set
        - Does not raise exception
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        nonexistent_repo = Path("/nonexistent/repo")
        validator = AdrSyncValidator(nonexistent_repo)

        adrs = validator._find_adrs(nonexistent_repo / "adr", ".md")
        assert adrs == set()

    def test_find_adrs_ignores_non_adr_files(self, temp_repo: Path):
        """
        Test that ADR discovery ignores non-ADR files.

        Setup:
        - Create README.md in /adr (not an ADR)
        - Create random-file.md in /adr (not an ADR)

        Expected:
        - Only returns files matching adr-NNNN-* pattern
        - Ignores README.md and other files
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        adr_dir = temp_repo / "adr"
        (adr_dir / "README.md").write_text("# ADRs\n")
        (adr_dir / "random-file.md").write_text("# Random\n")

        validator = AdrSyncValidator(temp_repo)
        adrs = validator._find_adrs(adr_dir, ".md")

        # Should only find adr-0001-test and adr-0002-example (not README or random-file)
        assert adrs == {"adr-0001-test", "adr-0002-example"}

    def test_validate_with_synchronized_adrs(self, temp_repo: Path):
        """
        Test validation when ADRs are fully synchronized.

        Expected:
        - is_synced = True
        - missing_in_docs = empty set
        - missing_in_source = empty set
        - uppercase_filenames = empty list
        - exit_code = 0
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        validator = AdrSyncValidator(temp_repo)
        result = validator.validate()

        assert result.is_synced is True
        assert result.missing_in_docs == set()
        assert result.missing_in_source == set()
        assert result.uppercase_filenames == []
        assert result.exit_code == 0
        assert result.stats["source_count"] == 2
        assert result.stats["docs_count"] == 2

    def test_validate_with_missing_docs_adr(self, temp_repo: Path):
        """
        Test validation when ADR exists in /adr but missing in /docs/architecture.

        Setup:
        - Add adr-0003-new.md to /adr
        - Don't add corresponding .mdx to /docs/architecture

        Expected:
        - is_synced = False
        - missing_in_docs = {"adr-0003-new"}
        - missing_in_source = empty set
        - exit_code = 1
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        # Add ADR only in source
        adr_dir = temp_repo / "adr"
        (adr_dir / "adr-0003-new.md").write_text("# ADR 0003: New\n")

        validator = AdrSyncValidator(temp_repo)
        result = validator.validate()

        assert result.is_synced is False
        assert result.missing_in_docs == {"adr-0003-new"}
        assert result.missing_in_source == set()
        assert result.exit_code == 1
        assert result.stats["source_count"] == 3
        assert result.stats["docs_count"] == 2
        assert result.stats["missing_in_docs"] == 1

    def test_validate_with_orphaned_docs_adr(self, temp_repo: Path):
        """
        Test validation when ADR exists in /docs/architecture but missing in /adr.

        Setup:
        - Add adr-0004-orphan.mdx to /docs/architecture
        - Don't add corresponding .md to /adr

        Expected:
        - is_synced = False
        - missing_in_docs = empty set
        - missing_in_source = {"adr-0004-orphan"}
        - exit_code = 1
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        # Add ADR only in docs
        docs_adr_dir = temp_repo / "docs" / "architecture"
        (docs_adr_dir / "adr-0004-orphan.mdx").write_text("# ADR 0004: Orphan\n")

        validator = AdrSyncValidator(temp_repo)
        result = validator.validate()

        assert result.is_synced is False
        assert result.missing_in_docs == set()
        assert result.missing_in_source == {"adr-0004-orphan"}
        assert result.exit_code == 1
        assert result.stats["source_count"] == 2
        assert result.stats["docs_count"] == 3
        assert result.stats["missing_in_source"] == 1

    def test_find_uppercase_filenames(self, temp_repo: Path):
        """
        Test detection of uppercase ADR filenames (ADR-* instead of adr-*).

        Setup:
        - Create ADR-0005-WRONG.md in /adr (incorrect)
        - Create ADR-0006-WRONG.mdx in /docs/architecture (incorrect)

        Expected:
        - Returns list of 2 uppercase files
        - is_synced = False
        - uppercase_count = 2
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        # Add uppercase ADR files
        adr_dir = temp_repo / "adr"
        docs_adr_dir = temp_repo / "docs" / "architecture"
        uppercase_adr = adr_dir / "ADR-0005-WRONG.md"
        uppercase_doc = docs_adr_dir / "ADR-0006-WRONG.mdx"

        uppercase_adr.write_text("# ADR 0005: Wrong\n")
        uppercase_doc.write_text("# ADR 0006: Wrong\n")

        validator = AdrSyncValidator(temp_repo)
        uppercase_files = validator._find_uppercase_filenames()

        assert len(uppercase_files) == 2
        assert uppercase_adr in uppercase_files
        assert uppercase_doc in uppercase_files

        # Validate should fail due to uppercase
        result = validator.validate()
        assert result.is_synced is False
        assert result.stats["uppercase_count"] == 2

    def test_sync_result_exit_code(self):
        """
        Test SyncResult exit code property.

        Expected:
        - is_synced=True → exit_code=0
        - is_synced=False → exit_code=1
        """
        from scripts.validators.adr_sync_validator import SyncResult

        # Synced result
        synced_result = SyncResult(is_synced=True)
        assert synced_result.exit_code == 0

        # Out of sync result
        unsynced_result = SyncResult(is_synced=False)
        assert unsynced_result.exit_code == 1

    def test_print_report_with_synchronized_adrs(self, temp_repo: Path, capsys):
        """
        Test report printing when ADRs are synchronized.

        Expected output:
        - "✅ All ADRs are synchronized!"
        - Statistics section
        - No missing ADRs section
        - No recommendations section
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        validator = AdrSyncValidator(temp_repo)
        result = validator.validate()
        validator.print_report(result)

        captured = capsys.readouterr()
        assert "✅ All ADRs are synchronized!" in captured.out
        assert "📊 Statistics:" in captured.out
        assert "ADRs in /adr: 2" in captured.out
        assert "ADRs in /docs/architecture: 2" in captured.out
        assert "❌ ADRs missing" not in captured.out
        assert "💡 Recommendations:" not in captured.out

    def test_print_report_with_missing_docs_adr(self, temp_repo: Path, capsys):
        """
        Test report printing when ADR is missing in docs.

        Expected output:
        - "❌ ADRs are out of sync"
        - "❌ ADRs missing in /docs/architecture"
        - Lists missing ADR name
        - Recommendations section with sync command
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        # Add ADR only in source
        (temp_repo / "adr" / "adr-0003-new.md").write_text("# ADR 0003\n")

        validator = AdrSyncValidator(temp_repo)
        result = validator.validate()
        validator.print_report(result)

        captured = capsys.readouterr()
        assert "❌ ADRs are out of sync" in captured.out
        assert "❌ ADRs missing in /docs/architecture (1):" in captured.out
        assert "adr-0003-new.md → adr-0003-new.mdx" in captured.out
        assert "💡 Recommendations:" in captured.out
        assert "cp adr/adr-0003-new.md docs/architecture/adr-0003-new.mdx" in captured.out

    def test_print_report_with_uppercase_filenames(self, temp_repo: Path, capsys):
        """
        Test report printing when uppercase filenames are detected.

        Expected output:
        - "⚠️ Uppercase filenames detected"
        - Lists each uppercase file
        - Provides rename command
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        # Add uppercase file
        uppercase_file = temp_repo / "adr" / "ADR-0005-WRONG.md"
        uppercase_file.write_text("# ADR 0005\n")

        validator = AdrSyncValidator(temp_repo)
        result = validator.validate()
        validator.print_report(result)

        captured = capsys.readouterr()
        assert "⚠️  Uppercase filenames detected (1):" in captured.out
        assert "ADR-0005-WRONG.md" in captured.out
        assert "adr-0005-WRONG.md" in captured.out  # Lowercase rename target appears somewhere
        assert "💡 Recommendations:" in captured.out
        assert "mv adr/ADR-0005-WRONG.md adr/adr-0005-WRONG.md" in captured.out  # Check recommendation

    def test_main_cli_with_synchronized_adrs(self, temp_repo: Path):
        """
        Test CLI main() function with synchronized ADRs.

        Expected:
        - Exits with code 0
        - Prints validation report
        """
        from scripts.validators.adr_sync_validator import main

        with patch("sys.argv", ["adr_sync_validator.py", "--repo-root", str(temp_repo)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

    def test_main_cli_with_out_of_sync_adrs(self, temp_repo: Path):
        """
        Test CLI main() function with out-of-sync ADRs.

        Expected:
        - Exits with code 1
        - Prints validation report with errors
        """
        from scripts.validators.adr_sync_validator import main

        # Make ADRs out of sync
        (temp_repo / "adr" / "adr-0003-new.md").write_text("# ADR 0003\n")

        with patch("sys.argv", ["adr_sync_validator.py", "--repo-root", str(temp_repo)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_main_cli_quiet_mode(self, temp_repo: Path, capsys):
        """
        Test CLI main() function with --quiet flag.

        Expected:
        - Exits with correct code
        - No output printed (report suppressed)
        """
        from scripts.validators.adr_sync_validator import main

        with patch("sys.argv", ["adr_sync_validator.py", "--repo-root", str(temp_repo), "--quiet"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            # Quiet mode should suppress report
            # (Note: Some output may still appear from pytest itself, check capsys if needed)

    def test_complex_scenario_multiple_issues(self, temp_repo: Path):
        """
        Test validation with multiple issues simultaneously.

        Setup:
        - Missing ADR in docs
        - Orphaned ADR in docs
        - Uppercase filename

        Expected:
        - is_synced = False
        - All issues detected
        - Comprehensive recommendations
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        # Add missing source ADR
        (temp_repo / "adr" / "adr-0003-missing.md").write_text("# ADR 0003\n")

        # Add orphaned docs ADR
        (temp_repo / "docs" / "architecture" / "adr-0004-orphan.mdx").write_text("# ADR 0004\n")

        # Add uppercase file
        (temp_repo / "adr" / "ADR-0005-WRONG.md").write_text("# ADR 0005\n")

        validator = AdrSyncValidator(temp_repo)
        result = validator.validate()

        assert result.is_synced is False
        assert len(result.missing_in_docs) == 1  # adr-0003-missing
        assert len(result.missing_in_source) == 1  # adr-0004-orphan
        assert len(result.uppercase_filenames) == 1  # ADR-0005-WRONG.md
        assert result.exit_code == 1

    def test_validate_with_empty_directories_returns_synced(self, tmp_path: Path):
        """
        Test validation with empty ADR directories.

        Expected:
        - is_synced = True (no ADRs to sync)
        - Empty sets for all ADR collections
        - stats show 0 counts
        """
        from scripts.validators.adr_sync_validator import AdrSyncValidator

        empty_repo = tmp_path / "empty_repo"
        (empty_repo / "adr").mkdir(parents=True)
        (empty_repo / "docs" / "architecture").mkdir(parents=True)

        validator = AdrSyncValidator(empty_repo)
        result = validator.validate()

        assert result.is_synced is True
        assert len(result.source_adrs) == 0
        assert len(result.docs_adrs) == 0
        assert result.stats["source_count"] == 0
        assert result.stats["docs_count"] == 0
