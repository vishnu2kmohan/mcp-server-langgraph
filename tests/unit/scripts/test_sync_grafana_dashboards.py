"""
Tests for scripts/sync-grafana-dashboards.sh

TDD tests for the Grafana dashboard sync script.
These tests verify the script behavior in various modes:
- --help: Shows usage information
- --check: Exits with error if dashboards are out of sync
- --dry-run: Shows what would be synced without changes
- Normal mode: Actually syncs the dashboards
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

# Mark all tests as unit tests
pytestmark = [pytest.mark.unit]

# Path to the sync script
SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "scripts" / "sync-grafana-dashboards.sh"


class TestSyncGrafanaDashboardsHelp:
    """Test help functionality."""

    def test_help_flag_shows_usage(self) -> None:
        """--help flag should show usage information."""
        result = subprocess.run(
            [str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--verbose" in result.stdout
        assert "--check" in result.stdout

    def test_unknown_option_fails(self) -> None:
        """Unknown option should fail with error."""
        result = subprocess.run(
            [str(SCRIPT_PATH), "--invalid-option"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 1
        assert "Unknown option" in result.stderr or "Unknown option" in result.stdout


class TestSyncGrafanaDashboardsWithTempDirs:
    """Test sync functionality with temporary directories."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> dict[str, Path]:
        """Create a temporary project structure for testing.

        Returns:
            Dict with paths to source and dest directories
        """
        # Create project structure
        source_dir = tmp_path / "monitoring" / "grafana" / "dashboards"
        dest_dir = tmp_path / "deployments" / "helm" / "mcp-server-langgraph" / "dashboards"
        scripts_dir = tmp_path / "scripts"

        # Create directories
        source_dir.mkdir(parents=True)
        dest_dir.mkdir(parents=True)
        scripts_dir.mkdir(parents=True)

        # Copy the sync script to temp location with modified paths
        sync_script = scripts_dir / "sync-grafana-dashboards.sh"
        with open(SCRIPT_PATH) as f:
            script_content = f.read()

        # Modify the script to use temp paths
        # Replace PROJECT_ROOT detection
        modified_script = script_content.replace(
            'PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"',
            f'PROJECT_ROOT="{tmp_path}"',
        )
        sync_script.write_text(modified_script)
        sync_script.chmod(0o755)

        return {
            "root": tmp_path,
            "source": source_dir,
            "dest": dest_dir,
            "script": sync_script,
        }

    def _create_dashboard(self, folder: Path, name: str, uid: str) -> Path:
        """Create a test dashboard JSON file."""
        folder.mkdir(parents=True, exist_ok=True)
        dashboard = {
            "uid": uid,
            "title": f"Test Dashboard {name}",
            "panels": [],
        }
        filepath = folder / f"{name}.json"
        with open(filepath, "w") as f:
            json.dump(dashboard, f, indent=2)
        return filepath

    def test_check_mode_passes_when_in_sync(self, temp_project: dict[str, Path]) -> None:
        """--check mode should pass when dashboards are in sync."""
        # Create matching dashboards in both locations
        self._create_dashboard(temp_project["source"] / "AI", "test", "test-uid")
        self._create_dashboard(temp_project["dest"] / "AI", "test", "test-uid")

        result = subprocess.run(
            [str(temp_project["script"]), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "in sync" in result.stdout.lower()

    def test_check_mode_fails_when_out_of_sync(self, temp_project: dict[str, Path]) -> None:
        """--check mode should fail when dashboards differ."""
        # Create different dashboards
        self._create_dashboard(temp_project["source"] / "AI", "test", "source-uid")
        self._create_dashboard(temp_project["dest"] / "AI", "test", "dest-uid")

        result = subprocess.run(
            [str(temp_project["script"]), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 1
        assert "out of sync" in result.stdout.lower()

    def test_check_mode_fails_when_missing_in_dest(self, temp_project: dict[str, Path]) -> None:
        """--check mode should fail when dashboards are missing in destination."""
        # Create dashboard only in source
        self._create_dashboard(temp_project["source"] / "AI", "test", "test-uid")
        (temp_project["dest"] / "AI").mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [str(temp_project["script"]), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 1
        assert "missing" in result.stdout.lower() or "MISSING" in result.stdout

    def test_dry_run_does_not_modify_files(self, temp_project: dict[str, Path]) -> None:
        """--dry-run should not modify any files."""
        # Create dashboard only in source (result unused - just need file to exist)
        self._create_dashboard(temp_project["source"] / "AI", "test", "test-uid")
        dest_folder = temp_project["dest"] / "AI"
        dest_folder.mkdir(parents=True, exist_ok=True)

        # Get initial state
        dest_file = dest_folder / "test.json"
        assert not dest_file.exists()

        result = subprocess.run(
            [str(temp_project["script"]), "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # File should still not exist
        assert not dest_file.exists()
        assert result.returncode == 0
        assert "DRY-RUN" in result.stdout or "dry-run" in result.stdout.lower()

    def test_normal_sync_copies_missing_files(self, temp_project: dict[str, Path]) -> None:
        """Normal sync should copy missing files to destination."""
        # Create dashboard only in source
        src_file = self._create_dashboard(temp_project["source"] / "AI", "test", "test-uid")
        dest_folder = temp_project["dest"] / "AI"
        dest_folder.mkdir(parents=True, exist_ok=True)

        dest_file = dest_folder / "test.json"
        assert not dest_file.exists()

        result = subprocess.run(
            [str(temp_project["script"])],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # File should now exist
        assert dest_file.exists()
        assert result.returncode == 0

        # Verify content matches
        with open(src_file) as f:
            src_content = f.read()
        with open(dest_file) as f:
            dest_content = f.read()
        assert src_content == dest_content

    def test_normal_sync_updates_out_of_sync_files(self, temp_project: dict[str, Path]) -> None:
        """Normal sync should update files that differ."""
        # Create different dashboards
        src_file = self._create_dashboard(temp_project["source"] / "AI", "test", "new-uid")
        dest_file = self._create_dashboard(temp_project["dest"] / "AI", "test", "old-uid")

        # Verify they're different
        with open(src_file) as f:
            src_content = f.read()
        with open(dest_file) as f:
            old_dest_content = f.read()
        assert src_content != old_dest_content

        result = subprocess.run(
            [str(temp_project["script"])],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Verify content now matches
        with open(dest_file) as f:
            new_dest_content = f.read()
        assert src_content == new_dest_content
        assert result.returncode == 0

    def test_sync_skips_files_already_in_sync(self, temp_project: dict[str, Path]) -> None:
        """Sync should skip files that are already identical."""
        # Create identical dashboards
        self._create_dashboard(temp_project["source"] / "AI", "test", "same-uid")
        self._create_dashboard(temp_project["dest"] / "AI", "test", "same-uid")

        result = subprocess.run(
            [str(temp_project["script"]), "--verbose"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # Should mention in sync, not copied/updated
        assert "In sync:" in result.stdout or "in sync" in result.stdout.lower()

    def test_sync_handles_multiple_folders(self, temp_project: dict[str, Path]) -> None:
        """Sync should handle multiple dashboard folders."""
        folders = ["AI", "Application", "Auth"]

        for folder in folders:
            self._create_dashboard(temp_project["source"] / folder, "test", f"{folder}-uid")
            (temp_project["dest"] / folder).mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [str(temp_project["script"])],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        # All files should be synced
        for folder in folders:
            dest_file = temp_project["dest"] / folder / "test.json"
            assert dest_file.exists(), f"Missing: {folder}/test.json"

    def test_sync_creates_missing_dest_folders(self, temp_project: dict[str, Path]) -> None:
        """Sync should create missing destination folders."""
        # Create dashboard in source, no dest folder
        self._create_dashboard(temp_project["source"] / "AI", "test", "test-uid")
        dest_folder = temp_project["dest"] / "AI"

        # Remove if exists
        if dest_folder.exists():
            shutil.rmtree(dest_folder)

        result = subprocess.run(
            [str(temp_project["script"])],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert dest_folder.exists()
        assert (dest_folder / "test.json").exists()


class TestDashboardUIDUniqueness:
    """Tests to prevent duplicate dashboard UIDs."""

    def test_no_duplicate_uids_in_canonical_dashboards(self) -> None:
        """All dashboards in monitoring/grafana/dashboards/ must have unique UIDs.

        Duplicate UIDs cause Grafana provisioning warnings:
        "Not saving new dashboard due to restricted database access"

        Root cause: Grafana can only store one dashboard per UID, so when
        multiple files have the same UID, only one is saved and others are skipped.
        """
        dashboards_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "dashboards"

        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        # Collect all UIDs with their file paths
        uid_to_files: dict[str, list[str]] = {}

        for dashboard_file in dashboards_dir.rglob("*.json"):
            try:
                with open(dashboard_file) as f:
                    dashboard = json.load(f)
                    uid = dashboard.get("uid")
                    if uid:
                        if uid not in uid_to_files:
                            uid_to_files[uid] = []
                        uid_to_files[uid].append(str(dashboard_file.relative_to(dashboards_dir)))
            except (json.JSONDecodeError, KeyError):
                continue

        # Find duplicates
        duplicates = {uid: files for uid, files in uid_to_files.items() if len(files) > 1}

        if duplicates:
            duplicate_msg = "\n".join(f"  UID '{uid}': {files}" for uid, files in duplicates.items())
            pytest.fail(
                f"Found {len(duplicates)} duplicate dashboard UIDs:\n{duplicate_msg}\n\n"
                "Each dashboard must have a unique UID. Remove duplicate files or "
                "change UIDs to be unique."
            )


class TestDocumentationDashboardPaths:
    """Tests to ensure documentation references valid dashboard paths."""

    def test_adr_dashboard_references_exist(self) -> None:
        """All dashboard paths referenced in ADRs must exist.

        This test validates that documentation doesn't reference dashboards
        that have been moved or renamed.
        """
        import re

        adr_dir = Path(__file__).parent.parent.parent.parent / "adr"
        dashboards_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "dashboards"

        if not adr_dir.exists():
            pytest.skip("ADR directory not found")
        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        # Pattern to match dashboard paths in docs
        pattern = re.compile(r"monitoring/grafana/dashboards/([^\s`\"']+\.json)")

        missing_refs: list[tuple[str, str]] = []

        for adr_file in adr_dir.glob("*.md"):
            content = adr_file.read_text()
            for match in pattern.finditer(content):
                rel_path = match.group(1)
                full_path = dashboards_dir / rel_path
                if not full_path.exists():
                    missing_refs.append((str(adr_file.name), f"monitoring/grafana/dashboards/{rel_path}"))

        if missing_refs:
            msg = "\n".join(f"  {adr}: {path}" for adr, path in missing_refs)
            pytest.fail(
                f"Found {len(missing_refs)} documentation references to non-existent dashboards:\n{msg}\n\n"
                "Update the documentation to reference the correct dashboard paths."
            )

    def test_compliance_docs_dashboard_references_exist(self) -> None:
        """All dashboard paths in COMPLIANCE.md must exist.

        Internal documentation must reference valid dashboard paths.
        """
        import re

        compliance_file = Path(__file__).parent.parent.parent.parent / "docs-internal" / "COMPLIANCE.md"
        dashboards_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "dashboards"

        if not compliance_file.exists():
            pytest.skip("COMPLIANCE.md not found")
        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        pattern = re.compile(r"monitoring/grafana/dashboards/([^\s`\"'\)]+\.json)")

        content = compliance_file.read_text()
        missing_refs: list[str] = []

        for match in pattern.finditer(content):
            rel_path = match.group(1)
            full_path = dashboards_dir / rel_path
            if not full_path.exists():
                missing_refs.append(f"monitoring/grafana/dashboards/{rel_path}")

        # Deduplicate
        missing_refs = list(set(missing_refs))

        if missing_refs:
            msg = "\n".join(f"  {path}" for path in sorted(missing_refs))
            pytest.fail(
                f"Found {len(missing_refs)} references to non-existent dashboards in COMPLIANCE.md:\n{msg}\n\n"
                "Update docs-internal/COMPLIANCE.md to reference correct dashboard paths with folder structure."
            )

    def test_docs_internal_dashboard_references_exist(self) -> None:
        """All dashboard paths in docs-internal/ must exist.

        Scans all markdown files in docs-internal/ for dashboard path references
        and validates they exist in the dashboards directory.

        Excludes:
        - grafana-dashboard-audit-report.md (historical audit, documents past state)
        """
        import re

        docs_internal_dir = Path(__file__).parent.parent.parent.parent / "docs-internal"
        dashboards_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "dashboards"

        if not docs_internal_dir.exists():
            pytest.skip("docs-internal directory not found")
        if not dashboards_dir.exists():
            pytest.skip("Dashboards directory not found")

        # Files to exclude (historical reports that document past state)
        excluded_files = {
            "grafana-dashboard-audit-report.md",
        }

        pattern = re.compile(r"monitoring/grafana/dashboards/([^\s`\"'\)\]]+\.json)")

        missing_refs: list[tuple[str, str]] = []

        for md_file in docs_internal_dir.rglob("*.md"):
            if md_file.name in excluded_files:
                continue

            content = md_file.read_text()
            for match in pattern.finditer(content):
                rel_path = match.group(1)
                full_path = dashboards_dir / rel_path
                if not full_path.exists():
                    relative_doc = md_file.relative_to(docs_internal_dir)
                    missing_refs.append((str(relative_doc), f"monitoring/grafana/dashboards/{rel_path}"))

        # Deduplicate while preserving file info
        seen = set()
        unique_refs = []
        for doc, path in missing_refs:
            key = (doc, path)
            if key not in seen:
                seen.add(key)
                unique_refs.append((doc, path))

        if unique_refs:
            msg = "\n".join(f"  {doc}: {path}" for doc, path in sorted(unique_refs))
            pytest.fail(
                f"Found {len(unique_refs)} references to non-existent dashboards in docs-internal/:\n{msg}\n\n"
                "Update the documentation to reference correct dashboard paths with folder structure."
            )


class TestAlertDashboardURLConsistency:
    """Tests to ensure alert dashboard URLs use consistent patterns."""

    def test_alert_dashboard_urls_use_template_pattern(self) -> None:
        """All alert dashboard_url annotations should use consistent pattern.

        Dashboard URLs in Prometheus alerts should use a template-friendly pattern:
        - Pattern: {{ grafana_url }}/d/<dashboard-uid>
        - This allows environment-specific URL configuration

        Note: We check for consistency and document which files need updating.
        """
        import re

        prometheus_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus"

        if not prometheus_dir.exists():
            pytest.skip("Prometheus directory not found")

        # Pattern to find hardcoded Grafana URLs
        hardcoded_pattern = re.compile(r'dashboard_url:\s*["\']https?://[^"\']+["\']')
        template_pattern = re.compile(r'dashboard_url:\s*["\']?\{\{\s*grafana_url\s*\}\}')

        hardcoded_files: dict[str, list[int]] = {}

        for alert_file in prometheus_dir.rglob("*.yaml"):
            content = alert_file.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                if hardcoded_pattern.search(line) and not template_pattern.search(line):
                    rel_path = str(alert_file.relative_to(prometheus_dir.parent.parent))
                    if rel_path not in hardcoded_files:
                        hardcoded_files[rel_path] = []
                    hardcoded_files[rel_path].append(i)

        for alert_file in prometheus_dir.rglob("*.yml"):
            content = alert_file.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                if hardcoded_pattern.search(line) and not template_pattern.search(line):
                    rel_path = str(alert_file.relative_to(prometheus_dir.parent.parent))
                    if rel_path not in hardcoded_files:
                        hardcoded_files[rel_path] = []
                    hardcoded_files[rel_path].append(i)

        if hardcoded_files:
            msg = "\n".join(f"  {path}: lines {lines}" for path, lines in sorted(hardcoded_files.items()))
            pytest.fail(
                f"Found {len(hardcoded_files)} alert files with hardcoded Grafana URLs:\n{msg}\n\n"
                "Alert dashboard_url annotations should use the pattern:\n"
                '  dashboard_url: "{{ grafana_url }}/d/<dashboard-uid>"\n\n'
                "This allows environment-specific configuration via Alertmanager templates."
            )


class TestSyncGrafanaDashboardsIntegration:
    """Integration tests using actual project directories."""

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Sync script not found",
    )
    def test_check_mode_on_actual_project(self) -> None:
        """Run --check mode on actual project to verify dashboards are in sync.

        This test will fail if dashboards are out of sync, which is intentional
        to catch drift before pre-commit hooks run.
        """
        result = subprocess.run(
            [str(SCRIPT_PATH), "--check"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=SCRIPT_PATH.parent.parent,  # Project root
        )

        # If this fails, run: ./scripts/sync-grafana-dashboards.sh
        assert result.returncode == 0, (
            f"Dashboards are out of sync!\n"
            f"Run: ./scripts/sync-grafana-dashboards.sh\n"
            f"Output: {result.stdout}\n"
            f"Stderr: {result.stderr}"
        )
