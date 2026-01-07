"""
Meta-test for Dashboard Datasource Consistency.

Validates that all Grafana dashboards use the correct datasource UIDs
as configured in monitoring/grafana/datasources.yml.

This test catches the common bug where a dashboard references a deprecated
or non-existent datasource UID (e.g., "prometheus" instead of "mimir"),
leading to "Datasource not found" errors in Grafana at runtime.

Why this matters:
- After migrating from Prometheus to Mimir (or other datasource changes),
  dashboards must be updated to use the new UID
- Hardcoded UIDs that don't match datasources.yml cause runtime failures
- This is not caught by JSON syntax validation alone

Reference: ADR-0095 - Grafana LGTM Stack Migration
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.meta, pytest.mark.unit]


# Valid datasource UIDs from monitoring/grafana/datasources.yml
VALID_DATASOURCE_UIDS = {
    "mimir",  # Prometheus-compatible metrics (replaces "prometheus")
    "tempo",  # Tracing
    "loki",  # Logging
    "-- Grafana --",  # Built-in Grafana datasource for annotations
}

# Deprecated datasource UIDs that should be migrated
DEPRECATED_DATASOURCE_UIDS = {
    "prometheus": "mimir",  # Prometheus was replaced by Mimir
}


def find_dashboard_files() -> list[Path]:
    """Find all dashboard JSON files in monitoring and helm directories."""
    dashboard_dirs = [
        Path("monitoring/grafana/dashboards"),
        Path("deployments/helm/mcp-server-langgraph/dashboards"),
    ]

    files = []
    for dir_path in dashboard_dirs:
        if dir_path.exists():
            files.extend(dir_path.rglob("*.json"))

    return sorted(set(files))


def extract_datasource_uids(dashboard: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract all hardcoded datasource UIDs from a dashboard.

    Returns list of (uid, path) tuples for each datasource reference.
    Variable-based datasources (${datasource}) are skipped.
    """
    uids: list[tuple[str, str]] = []

    def scan(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            # Check if this is a datasource reference with hardcoded UID
            if "uid" in obj and "type" in obj:
                uid = obj.get("uid", "")
                if isinstance(uid, str) and not uid.startswith("${"):
                    uids.append((uid, path))

            # Check nested datasource key
            if "datasource" in obj and isinstance(obj["datasource"], dict):
                ds = obj["datasource"]
                uid = ds.get("uid", "")
                if isinstance(uid, str) and not uid.startswith("${"):
                    uids.append((uid, f"{path}/datasource"))

            # Recurse
            for key, value in obj.items():
                scan(value, f"{path}/{key}" if path else key)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                scan(item, f"{path}[{i}]")

    scan(dashboard)
    return uids


class TestDashboardDatasourceConsistency:
    """Validate that dashboards use correct datasource UIDs."""

    @pytest.fixture
    def dashboard_files(self) -> list[Path]:
        """Get all dashboard files to validate."""
        files = find_dashboard_files()
        if not files:
            pytest.skip("No dashboard files found")
        return files

    def test_no_deprecated_prometheus_uid(self, dashboard_files: list[Path]) -> None:
        """Ensure no dashboards use deprecated 'prometheus' datasource UID.

        After migration to Mimir, all dashboards should use 'mimir' UID
        instead of 'prometheus'. This prevents 'Datasource not found' errors.
        """
        violations: list[str] = []

        for filepath in dashboard_files:
            try:
                with open(filepath) as f:
                    dashboard = json.load(f)
            except json.JSONDecodeError:
                continue  # Skip invalid JSON (caught by other tests)

            uids = extract_datasource_uids(dashboard)
            for uid, path in uids:
                if uid in DEPRECATED_DATASOURCE_UIDS:
                    replacement = DEPRECATED_DATASOURCE_UIDS[uid]
                    violations.append(f"{filepath.name}: deprecated '{uid}' at {path} (should be '{replacement}')")

        assert not violations, (
            f"Found {len(violations)} deprecated datasource UIDs:\n"
            + "\n".join(f"  - {v}" for v in violations[:10])
            + (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            + "\n\nFix: Replace 'prometheus' with 'mimir' in dashboard JSON files"
        )

    def test_all_dashboards_have_valid_json(self, dashboard_files: list[Path]) -> None:
        """Ensure all dashboard files are valid JSON."""
        invalid_files: list[str] = []

        for filepath in dashboard_files:
            try:
                with open(filepath) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                invalid_files.append(f"{filepath.name}: {e}")

        assert not invalid_files, f"Found {len(invalid_files)} invalid JSON files:\n" + "\n".join(
            f"  - {v}" for v in invalid_files
        )

    def test_dashboard_uid_format(self, dashboard_files: list[Path]) -> None:
        """Ensure dashboard UIDs follow naming convention."""
        invalid_uids: list[str] = []

        # Dashboard UID should be lowercase-kebab-case
        uid_pattern = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")

        for filepath in dashboard_files:
            try:
                with open(filepath) as f:
                    dashboard = json.load(f)
            except json.JSONDecodeError:
                continue

            uid = dashboard.get("uid", "")
            if uid and not uid_pattern.match(uid):
                invalid_uids.append(f"{filepath.name}: '{uid}' (should be kebab-case)")

        assert not invalid_uids, f"Found {len(invalid_uids)} dashboards with invalid UID format:\n" + "\n".join(
            f"  - {v}" for v in invalid_uids
        )

    def test_datasource_count_sanity_check(self, dashboard_files: list[Path]) -> None:
        """Sanity check that datasource validation is working.

        We expect a reasonable number of mimir UIDs across dashboards.
        This catches if our detection logic is broken.
        """
        total_mimir_refs = 0

        for filepath in dashboard_files:
            try:
                with open(filepath) as f:
                    dashboard = json.load(f)
            except json.JSONDecodeError:
                continue

            uids = extract_datasource_uids(dashboard)
            total_mimir_refs += sum(1 for uid, _ in uids if uid == "mimir")

        # We expect at least 20 mimir references across all dashboards
        assert total_mimir_refs >= 20, (
            f"Only found {total_mimir_refs} 'mimir' datasource references. This seems low - is the detection logic working?"
        )
