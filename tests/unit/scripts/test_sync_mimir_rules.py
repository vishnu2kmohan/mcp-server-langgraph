"""
Tests for scripts/sync-mimir-rules.sh

TDD tests for the Mimir alert rules sync script.
These tests verify the script behavior in various modes:
- --help: Shows usage information
- --check: Exits with error if rules are out of sync
- --dry-run: Shows what would be synced without changes
- Normal mode: Actually syncs the rules

Also includes validation tests for:
- No duplicate alert names across all rule files
- All canonical rules are synced to docker/mimir/rules/
- Documentation references to valid rule files
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

# Mark all tests as unit tests
pytestmark = [pytest.mark.unit]

# Paths
PROJECT_ROOT = get_repo_root()
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "sync-mimir-rules.sh"
CANONICAL_RULES_DIR = PROJECT_ROOT / "monitoring" / "prometheus" / "rules"
MIMIR_RULES_DIR = PROJECT_ROOT / "docker" / "mimir" / "rules"


class TestAlertRuleUniqueness:
    """Tests to prevent duplicate alert names across rule files."""

    def test_no_duplicate_alert_names_in_canonical_rules(self) -> None:
        """All alerts in monitoring/prometheus/rules/ must have unique names.

        Duplicate alert names cause confusion and can lead to missed alerts
        when one rule shadows another.
        """
        if not CANONICAL_RULES_DIR.exists():
            pytest.skip("Canonical rules directory not found")

        # Collect all alert names with their file paths
        alert_to_files: dict[str, list[str]] = {}

        for rule_file in CANONICAL_RULES_DIR.glob("*.y*ml"):
            try:
                with open(rule_file) as f:
                    content = yaml.safe_load(f)

                if not content or "groups" not in content:
                    continue

                for group in content.get("groups", []):
                    for rule in group.get("rules", []):
                        alert_name = rule.get("alert")
                        if alert_name:
                            rel_path = str(rule_file.relative_to(CANONICAL_RULES_DIR))
                            if alert_name not in alert_to_files:
                                alert_to_files[alert_name] = []
                            alert_to_files[alert_name].append(rel_path)
            except (yaml.YAMLError, KeyError):
                continue

        # Find duplicates
        duplicates = {name: files for name, files in alert_to_files.items() if len(files) > 1}

        if duplicates:
            duplicate_msg = "\n".join(f"  Alert '{name}': {files}" for name, files in duplicates.items())
            pytest.fail(
                f"Found {len(duplicates)} duplicate alert names:\n{duplicate_msg}\n\n"
                "Each alert must have a unique name. Rename or consolidate duplicate alerts."
            )

    def test_no_duplicate_alert_names_in_mimir_rules(self) -> None:
        """All alerts in docker/mimir/rules/ must have unique names."""
        if not MIMIR_RULES_DIR.exists():
            pytest.skip("Mimir rules directory not found")

        alert_to_files: dict[str, list[str]] = {}

        for rule_file in MIMIR_RULES_DIR.glob("*.y*ml"):
            try:
                with open(rule_file) as f:
                    content = yaml.safe_load(f)

                if not content or "groups" not in content:
                    continue

                for group in content.get("groups", []):
                    for rule in group.get("rules", []):
                        alert_name = rule.get("alert")
                        if alert_name:
                            rel_path = str(rule_file.relative_to(MIMIR_RULES_DIR))
                            if alert_name not in alert_to_files:
                                alert_to_files[alert_name] = []
                            alert_to_files[alert_name].append(rel_path)
            except (yaml.YAMLError, KeyError):
                continue

        duplicates = {name: files for name, files in alert_to_files.items() if len(files) > 1}

        if duplicates:
            duplicate_msg = "\n".join(f"  Alert '{name}': {files}" for name, files in duplicates.items())
            pytest.fail(f"Found {len(duplicates)} duplicate alert names in Mimir rules:\n{duplicate_msg}")


class TestAlertRuleSync:
    """Tests to ensure canonical rules are synced to Mimir."""

    def test_all_canonical_rules_synced_to_mimir(self) -> None:
        """All rule files in monitoring/prometheus/rules/ must be synced to docker/mimir/rules/.

        This test ensures the test environment has all production alert rules.
        Files may have different extensions (.yml vs .yaml) but content should match.
        """
        if not CANONICAL_RULES_DIR.exists():
            pytest.skip("Canonical rules directory not found")
        if not MIMIR_RULES_DIR.exists():
            pytest.skip("Mimir rules directory not found")

        # Get canonical rule files (excluding K8s CRD files which need conversion)
        canonical_files: dict[str, Path] = {}
        for rule_file in CANONICAL_RULES_DIR.glob("*.y*ml"):
            # Check if it's a K8s CRD (has apiVersion field)
            with open(rule_file) as f:
                content = f.read()
            if "apiVersion:" in content and "kind: PrometheusRule" in content:
                # Skip K8s CRDs - they're tested separately
                continue
            # Use stem (filename without extension) as key
            canonical_files[rule_file.stem] = rule_file

        # Get Mimir rule files
        mimir_files: dict[str, Path] = {}
        for rule_file in MIMIR_RULES_DIR.glob("*.y*ml"):
            mimir_files[rule_file.stem] = rule_file

        # Check for missing files
        missing_files = set(canonical_files.keys()) - set(mimir_files.keys())

        if missing_files:
            missing_msg = "\n".join(f"  {name}: {canonical_files[name]}" for name in sorted(missing_files))
            pytest.fail(
                f"Found {len(missing_files)} canonical rules not synced to docker/mimir/rules/:\n"
                f"{missing_msg}\n\n"
                "Run: ./scripts/sync-mimir-rules.sh"
            )

    def test_synced_rules_content_matches(self) -> None:
        """Synced rule files should have matching content (ignoring format differences).

        Compares alert names between canonical and Mimir versions.
        """
        if not CANONICAL_RULES_DIR.exists():
            pytest.skip("Canonical rules directory not found")
        if not MIMIR_RULES_DIR.exists():
            pytest.skip("Mimir rules directory not found")

        mismatches: list[str] = []

        for canonical_file in CANONICAL_RULES_DIR.glob("*.y*ml"):
            # Skip K8s CRDs
            with open(canonical_file) as f:
                content = f.read()
            if "apiVersion:" in content and "kind: PrometheusRule" in content:
                continue

            # Find matching Mimir file
            mimir_file = None
            for ext in [".yaml", ".yml"]:
                candidate = MIMIR_RULES_DIR / f"{canonical_file.stem}{ext}"
                if candidate.exists():
                    mimir_file = candidate
                    break

            if not mimir_file:
                continue  # Missing files are caught by other test

            # Compare alert names
            try:
                with open(canonical_file) as f:
                    canonical_content = yaml.safe_load(f)
                with open(mimir_file) as f:
                    mimir_content = yaml.safe_load(f)

                canonical_alerts = set()
                for group in canonical_content.get("groups", []):
                    for rule in group.get("rules", []):
                        if "alert" in rule:
                            canonical_alerts.add(rule["alert"])

                mimir_alerts = set()
                for group in mimir_content.get("groups", []):
                    for rule in group.get("rules", []):
                        if "alert" in rule:
                            mimir_alerts.add(rule["alert"])

                if canonical_alerts != mimir_alerts:
                    missing_in_mimir = canonical_alerts - mimir_alerts
                    extra_in_mimir = mimir_alerts - canonical_alerts
                    mismatch_details = []
                    if missing_in_mimir:
                        mismatch_details.append(f"missing: {missing_in_mimir}")
                    if extra_in_mimir:
                        mismatch_details.append(f"extra: {extra_in_mimir}")
                    mismatches.append(f"  {canonical_file.name}: {', '.join(mismatch_details)}")
            except yaml.YAMLError:
                continue

        if mismatches:
            pytest.fail(
                f"Found {len(mismatches)} rule files with alert mismatches:\n"
                + "\n".join(mismatches)
                + "\n\nRun: ./scripts/sync-mimir-rules.sh"
            )


class TestAlertRuleFormat:
    """Tests to validate alert rule format and content."""

    def test_no_hardcoded_grafana_urls_in_canonical(self) -> None:
        """Alert rules should use {{ grafana_url }} template, not hardcoded URLs.

        Hardcoded URLs break across environments.
        """
        if not CANONICAL_RULES_DIR.exists():
            pytest.skip("Canonical rules directory not found")

        hardcoded_files: list[tuple[str, int]] = []

        for rule_file in CANONICAL_RULES_DIR.glob("*.y*ml"):
            with open(rule_file) as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Check for hardcoded Grafana URLs
                if "dashboard_url:" in line or "grafana" in line.lower():
                    if "https://grafana" in line or "http://grafana" in line:
                        if "{{ grafana_url }}" not in line:
                            rel_path = str(rule_file.relative_to(CANONICAL_RULES_DIR))
                            hardcoded_files.append((rel_path, i))

        if hardcoded_files:
            msg = "\n".join(f"  {path}:{line}" for path, line in hardcoded_files)
            pytest.fail(
                f"Found {len(hardcoded_files)} hardcoded Grafana URLs:\n{msg}\n\n"
                "Use '{{ grafana_url }}' template variable instead."
            )

    def test_all_alerts_have_required_labels(self) -> None:
        """All alerts should have severity label.

        Required labels:
        - severity: critical, warning, or info
        """
        if not CANONICAL_RULES_DIR.exists():
            pytest.skip("Canonical rules directory not found")

        missing_labels: list[str] = []

        for rule_file in CANONICAL_RULES_DIR.glob("*.y*ml"):
            try:
                with open(rule_file) as f:
                    content = yaml.safe_load(f)

                if not content or "groups" not in content:
                    continue

                for group in content.get("groups", []):
                    for rule in group.get("rules", []):
                        alert_name = rule.get("alert")
                        if not alert_name:
                            continue  # Recording rule, not alert

                        labels = rule.get("labels", {})
                        if "severity" not in labels:
                            rel_path = str(rule_file.relative_to(CANONICAL_RULES_DIR))
                            missing_labels.append(f"  {rel_path}: {alert_name}")
            except yaml.YAMLError:
                continue

        if missing_labels:
            pytest.fail(
                f"Found {len(missing_labels)} alerts missing 'severity' label:\n"
                + "\n".join(missing_labels[:20])  # Limit output
                + ("\n  ..." if len(missing_labels) > 20 else "")
            )


class TestSyncMimirRulesScript:
    """Tests for the sync-mimir-rules.sh script."""

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Sync script not yet created (TDD - RED phase)",
    )
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
        assert "--check" in result.stdout

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Sync script not yet created (TDD - RED phase)",
    )
    def test_check_mode_on_actual_project(self) -> None:
        """Run --check mode on actual project to verify rules are in sync."""
        result = subprocess.run(
            [str(SCRIPT_PATH), "--check"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=PROJECT_ROOT,
        )

        assert result.returncode == 0, (
            f"Mimir rules are out of sync!\n"
            f"Run: ./scripts/sync-mimir-rules.sh\n"
            f"Output: {result.stdout}\n"
            f"Stderr: {result.stderr}"
        )


class TestSyncMimirRulesWithTempDirs:
    """Test sync functionality with temporary directories."""

    @pytest.fixture
    def temp_project(self, tmp_path: Path) -> dict[str, Path]:
        """Create a temporary project structure for testing."""
        source_dir = tmp_path / "monitoring" / "prometheus" / "rules"
        dest_dir = tmp_path / "docker" / "mimir" / "rules"
        scripts_dir = tmp_path / "scripts"

        source_dir.mkdir(parents=True)
        dest_dir.mkdir(parents=True)
        scripts_dir.mkdir(parents=True)

        return {
            "root": tmp_path,
            "source": source_dir,
            "dest": dest_dir,
            "scripts": scripts_dir,
        }

    def _create_rule_file(self, folder: Path, name: str, alerts: list[str], namespace: str | None = None) -> Path:
        """Create a test rule file."""
        folder.mkdir(parents=True, exist_ok=True)

        rules = [
            {
                "alert": alert,
                "expr": f'up{{job="{alert}"}} == 0',
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": f"Test alert {alert}"},
            }
            for alert in alerts
        ]

        content: dict = {"groups": [{"name": f"{name}_group", "rules": rules}]}

        if namespace:
            content["namespace"] = namespace

        filepath = folder / f"{name}.yaml"
        with open(filepath, "w") as f:
            yaml.dump(content, f, default_flow_style=False)
        return filepath

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Sync script not yet created (TDD - RED phase)",
    )
    def test_sync_copies_missing_files(self, temp_project: dict[str, Path]) -> None:
        """Sync should copy missing rule files to destination."""
        # Create rule file only in source
        self._create_rule_file(temp_project["source"], "test-alerts", ["TestAlert1", "TestAlert2"])

        dest_file = temp_project["dest"] / "test-alerts.yaml"
        assert not dest_file.exists()

        # Copy and modify script for temp paths
        sync_script = temp_project["scripts"] / "sync-mimir-rules.sh"
        with open(SCRIPT_PATH) as f:
            script_content = f.read()

        modified_script = script_content.replace(
            'PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"',
            f'PROJECT_ROOT="{temp_project["root"]}"',
        )
        sync_script.write_text(modified_script)
        sync_script.chmod(0o755)

        result = subprocess.run(
            [str(sync_script)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert dest_file.exists()
        assert result.returncode == 0

    @pytest.mark.skipif(
        not SCRIPT_PATH.exists(),
        reason="Sync script not yet created (TDD - RED phase)",
    )
    def test_check_mode_fails_when_out_of_sync(self, temp_project: dict[str, Path]) -> None:
        """--check mode should fail when rules differ."""
        # Create different rules in source and dest
        self._create_rule_file(temp_project["source"], "test-alerts", ["SourceAlert"])
        self._create_rule_file(temp_project["dest"], "test-alerts", ["DifferentAlert"])

        sync_script = temp_project["scripts"] / "sync-mimir-rules.sh"
        with open(SCRIPT_PATH) as f:
            script_content = f.read()

        modified_script = script_content.replace(
            'PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"',
            f'PROJECT_ROOT="{temp_project["root"]}"',
        )
        sync_script.write_text(modified_script)
        sync_script.chmod(0o755)

        result = subprocess.run(
            [str(sync_script), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 1
        assert "out of sync" in result.stdout.lower()
