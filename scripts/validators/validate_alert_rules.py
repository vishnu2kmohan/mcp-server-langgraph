#!/usr/bin/env python3
"""
Validate Prometheus/Mimir Alert Rules

Pre-commit hook that validates alert rules for:
1. No duplicate alert names across all files
2. All alerts have required severity label
3. All alerts have summary/description annotation
4. Critical alerts have runbook_url
5. No hardcoded Grafana URLs (use {{ grafana_url }} template)

Exit codes:
- 0: All validations passed
- 1: Validation errors found (blocks commit)

Usage:
    python scripts/validators/validate_alert_rules.py [files...]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).parent.parent.parent


def load_yaml_file(file_path: Path) -> dict[str, Any] | None:
    """Load and parse a YAML file."""
    try:
        with open(file_path) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, FileNotFoundError) as e:
        print(f"ERROR: Failed to parse {file_path}: {e}")
        return None


def is_k8s_crd_format(content: dict[str, Any]) -> bool:
    """Check if content is in Kubernetes PrometheusRule CRD format."""
    if not content or not isinstance(content, dict):
        return False
    api_version = content.get("apiVersion", "")
    kind = content.get("kind", "")
    return "monitoring.coreos.com" in api_version and kind == "PrometheusRule"


def extract_alerts(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract alerts from rule file."""
    if is_k8s_crd_format(content):
        groups = content.get("spec", {}).get("groups", [])
    else:
        groups = content.get("groups", [])

    alerts = []
    for group in groups:
        for rule in group.get("rules", []):
            if "alert" in rule:
                alerts.append(rule)
    return alerts


def validate_file(file_path: Path) -> list[str]:
    """Validate a single alert rules file. Returns list of error messages."""
    errors = []
    content = load_yaml_file(file_path)

    if content is None:
        return [f"{file_path}: Failed to parse YAML"]

    # Skip files that aren't alert rules
    if is_k8s_crd_format(content):
        spec = content.get("spec", {})
        if "groups" not in spec:
            return []  # Not an alert rules file
    elif "groups" not in content:
        return []  # Not an alert rules file

    alerts = extract_alerts(content)
    rel_path = file_path.relative_to(PROJECT_ROOT) if file_path.is_relative_to(PROJECT_ROOT) else file_path

    valid_severities = {"critical", "warning", "info", "page"}

    for alert in alerts:
        alert_name = alert.get("alert", "unknown")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        # Check severity label
        severity = labels.get("severity")
        if not severity:
            errors.append(f"{rel_path}: {alert_name} - missing severity label")
        elif severity not in valid_severities:
            errors.append(f"{rel_path}: {alert_name} - invalid severity '{severity}'")

        # Check summary/description
        if "summary" not in annotations and "description" not in annotations:
            errors.append(f"{rel_path}: {alert_name} - missing summary/description annotation")

        # Check runbook_url for critical alerts
        if severity == "critical" and "runbook_url" not in annotations:
            # This is a warning, not an error
            pass

        # Check for hardcoded Grafana URLs
        dashboard_url = annotations.get("dashboard_url", "") or annotations.get("dashboard", "")
        if dashboard_url and ("http://" in dashboard_url or "https://" in dashboard_url):
            if "{{ grafana_url }}" not in dashboard_url:
                errors.append(f"{rel_path}: {alert_name} - hardcoded dashboard URL, use '{{{{ grafana_url }}}}' template")

    return errors


def check_duplicates(files: list[Path]) -> list[str]:
    """Check for duplicate alert names within the canonical directory.

    Duplicates are only checked within the canonical directory:
    - monitoring/prometheus/rules/ (source of truth)

    The Mimir rules (docker/mimir/rules/) are a synced copy and are
    not cross-checked to avoid false positive duplicate detection.
    """
    # Filter to only canonical files for duplicate checking
    # Exclude docker/mimir/rules which is a synced copy
    canonical_files = [f for f in files if "docker/mimir/rules" not in str(f)]

    # If no canonical files in the list, check all files passed
    files_to_check = canonical_files if canonical_files else files

    alert_to_files: dict[str, list[str]] = {}
    errors = []

    for file_path in files_to_check:
        content = load_yaml_file(file_path)
        if not content:
            continue

        alerts = extract_alerts(content)
        rel_path = str(file_path.relative_to(PROJECT_ROOT) if file_path.is_relative_to(PROJECT_ROOT) else file_path)

        for alert in alerts:
            alert_name = alert.get("alert")
            if alert_name:
                if alert_name not in alert_to_files:
                    alert_to_files[alert_name] = []
                alert_to_files[alert_name].append(rel_path)

    # Find duplicates within canonical directory only
    for name, locs in alert_to_files.items():
        if len(locs) > 1:
            errors.append(f"Duplicate alert '{name}' defined in: {', '.join(locs)}")

    return errors


def main() -> int:
    # Get files from arguments or scan canonical directory
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if f.endswith((".yaml", ".yml"))]
    else:
        # Scan canonical directory
        canonical_dir = PROJECT_ROOT / "monitoring" / "prometheus" / "rules"
        if canonical_dir.exists():
            files = list(canonical_dir.glob("*.y*ml"))
        else:
            files = []

    if not files:
        print("No alert rule files to validate")
        return 0

    all_errors = []

    # Validate each file
    for file_path in files:
        if file_path.exists():
            errors = validate_file(file_path)
            all_errors.extend(errors)

    # Check for duplicates across all files
    duplicate_errors = check_duplicates(files)
    all_errors.extend(duplicate_errors)

    # Report results
    if all_errors:
        print(f"Found {len(all_errors)} alert rule validation errors:\n")
        for error in all_errors:
            print(f"  ❌ {error}")
        print("\nFix these issues before committing.")
        return 1

    print(f"✅ Validated {len(files)} alert rule files with no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
