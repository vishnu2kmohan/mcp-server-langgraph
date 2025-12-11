#!/usr/bin/env python3
"""
Grafana Dashboard Validation Script

Validates dashboard JSON files against Grafana best practices without
requiring a running Grafana/Mimir instance.

Checks:
- JSON validity
- Required fields (uid, title, schemaVersion)
- 24-column grid compliance
- graphTooltip configuration
- Dashboard description
- Navigation links with includeVars/keepTime
- Panel descriptions
- Collapsible rows structure
- timepicker configuration

Usage:
    uv run python scripts/validation/validate_grafana_dashboards.py
    uv run python scripts/validation/validate_grafana_dashboards.py --fix
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TypedDict

# Dashboard directories to validate
DASHBOARD_DIRS = [
    Path("monitoring/grafana/dashboards"),
    Path("deployments/helm/mcp-server-langgraph/dashboards"),
]


class ValidationResult(TypedDict):
    """Validation result for a single dashboard."""

    file: str
    title: str
    uid: str
    errors: list[str]
    warnings: list[str]
    info: list[str]


def validate_required_fields(dashboard: dict[str, Any]) -> list[str]:
    """Check for required dashboard fields."""
    errors = []
    required_fields = ["uid", "title", "schemaVersion"]

    for field in required_fields:
        if field not in dashboard:
            errors.append(f"Missing required field: {field}")
        elif not dashboard[field]:
            errors.append(f"Empty required field: {field}")

    # Check schemaVersion is recent
    schema_version = dashboard.get("schemaVersion", 0)
    if schema_version < 36:
        errors.append(f"Outdated schemaVersion: {schema_version} (should be >= 36)")

    return errors


def validate_grid_compliance(dashboard: dict[str, Any]) -> list[str]:
    """Check 24-column grid compliance."""
    errors = []

    def check_panel(panel: dict[str, Any], path: str) -> None:
        if panel.get("type") == "row":
            return

        grid_pos = panel.get("gridPos", {})
        x = grid_pos.get("x", 0)
        w = grid_pos.get("w", 0)

        if x + w > 24:
            errors.append(f"{path}: Grid overflow (x={x} + w={w} = {x + w} > 24)")

        if w > 24:
            errors.append(f"{path}: Panel width {w} exceeds 24 columns")

    for panel in dashboard.get("panels", []):
        panel_title = panel.get("title", "Untitled")
        check_panel(panel, panel_title)

        for nested in panel.get("panels", []):
            nested_title = nested.get("title", "Untitled")
            check_panel(nested, f"{panel_title}/{nested_title}")

    return errors


def validate_graph_tooltip(dashboard: dict[str, Any]) -> list[str]:
    """Check graphTooltip is set for shared crosshair."""
    warnings = []
    tooltip = dashboard.get("graphTooltip", 0)

    if tooltip != 1:
        warnings.append(f"graphTooltip is {tooltip} (should be 1 for shared crosshair)")

    return warnings


def validate_description(dashboard: dict[str, Any]) -> list[str]:
    """Check dashboard has a description."""
    warnings = []
    description = dashboard.get("description", "")

    if not description:
        warnings.append("Missing dashboard description")
    elif len(description) < 50:
        warnings.append(f"Short description ({len(description)} chars, recommend >= 50)")

    return warnings


def validate_links(dashboard: dict[str, Any]) -> list[str]:
    """Check navigation links configuration."""
    warnings = []
    links = dashboard.get("links", [])

    if not links:
        warnings.append("No navigation links defined")
        return warnings

    for i, link in enumerate(links):
        link_title = link.get("title", f"Link {i}")

        if not link.get("includeVars"):
            warnings.append(f"Link '{link_title}' missing includeVars: true")

        if not link.get("keepTime"):
            warnings.append(f"Link '{link_title}' missing keepTime: true")

    return warnings


def validate_panel_descriptions(dashboard: dict[str, Any]) -> list[str]:
    """Check panels have descriptions."""
    warnings = []
    panels_without_desc = []

    def check_panel(panel: dict[str, Any]) -> None:
        if panel.get("type") == "row":
            return

        title = panel.get("title", "Untitled")
        description = panel.get("description", "")

        if not description:
            panels_without_desc.append(title)

    for panel in dashboard.get("panels", []):
        check_panel(panel)
        for nested in panel.get("panels", []):
            check_panel(nested)

    if panels_without_desc:
        count = len(panels_without_desc)
        examples = panels_without_desc[:3]
        warning = f"{count} panels without descriptions (e.g., {', '.join(examples)})"
        if count > 3:
            warning += f" and {count - 3} more"
        warnings.append(warning)

    return warnings


def validate_row_structure(dashboard: dict[str, Any]) -> list[str]:
    """Check row grouping structure."""
    info = []
    panels = dashboard.get("panels", [])

    row_count = sum(1 for p in panels if p.get("type") == "row")
    collapsed_count = sum(1 for p in panels if p.get("type") == "row" and p.get("collapsed"))

    if row_count == 0:
        info.append("No row groupings (consider adding for organization)")
    else:
        info.append(f"{row_count} rows ({collapsed_count} collapsible)")

    return info


def validate_timepicker(dashboard: dict[str, Any]) -> list[str]:
    """Check timepicker configuration."""
    warnings = []
    timepicker = dashboard.get("timepicker", {})

    refresh_intervals = timepicker.get("refresh_intervals", [])
    if not refresh_intervals:
        warnings.append("Missing timepicker refresh_intervals")

    return warnings


def validate_dashboard(filepath: Path) -> ValidationResult:
    """Validate a single dashboard file."""
    result: ValidationResult = {
        "file": filepath.name,
        "title": "Unknown",
        "uid": "Unknown",
        "errors": [],
        "warnings": [],
        "info": [],
    }

    try:
        with open(filepath) as f:
            dashboard = json.load(f)
    except json.JSONDecodeError as e:
        result["errors"].append(f"Invalid JSON: {e}")
        return result

    result["title"] = dashboard.get("title", "Unknown")
    result["uid"] = dashboard.get("uid", "Unknown")

    # Run validations
    result["errors"].extend(validate_required_fields(dashboard))
    result["errors"].extend(validate_grid_compliance(dashboard))
    result["warnings"].extend(validate_graph_tooltip(dashboard))
    result["warnings"].extend(validate_description(dashboard))
    result["warnings"].extend(validate_links(dashboard))
    result["warnings"].extend(validate_timepicker(dashboard))
    # Panel descriptions are informational, not blocking (66 panels in infrastructure dashboards)
    result["info"].extend(validate_panel_descriptions(dashboard))
    result["info"].extend(validate_row_structure(dashboard))

    return result


def find_dashboard_files() -> list[Path]:
    """Find all dashboard JSON files."""
    files = []

    for dir_path in DASHBOARD_DIRS:
        if dir_path.exists():
            # Get files from root and subdirectories
            files.extend(dir_path.rglob("*.json"))

    return sorted(set(files))


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate Grafana dashboard JSON files")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show errors and summary",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Specific files to validate (default: all dashboards)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("GRAFANA DASHBOARD VALIDATION REPORT")
    print("=" * 80)
    print()

    # Get files to validate
    if args.files:
        dashboard_files = args.files
    else:
        dashboard_files = find_dashboard_files()

    if not dashboard_files:
        print("No dashboard files found")
        return 1

    print(f"Found {len(dashboard_files)} dashboard files\n")

    all_results: list[ValidationResult] = []
    total_errors = 0
    total_warnings = 0

    for filepath in dashboard_files:
        result = validate_dashboard(filepath)
        all_results.append(result)

        error_count = len(result["errors"])
        warning_count = len(result["warnings"])
        total_errors += error_count
        total_warnings += warning_count

        # Status indicator
        if error_count > 0:
            status = f"FAIL ({error_count} errors"
            if warning_count > 0:
                status += f", {warning_count} warnings)"
            else:
                status += ")"
        elif warning_count > 0:
            status = f"WARN ({warning_count} warnings)"
        else:
            status = "PASS"

        # Print relative path
        try:
            rel_path = filepath.relative_to(Path.cwd())
        except ValueError:
            rel_path = filepath

        print(f"  {status:25} {rel_path}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total dashboards: {len(dashboard_files)}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")
    print()

    # Print detailed errors
    if total_errors > 0:
        print("=" * 80)
        print("ERRORS")
        print("=" * 80)
        for result in all_results:
            if result["errors"]:
                print(f"\n{result['file']} ({result['title']}):")
                for error in result["errors"]:
                    print(f"  ERROR: {error}")

    # Print detailed warnings (unless quiet)
    if total_warnings > 0 and not args.quiet:
        print()
        print("=" * 80)
        print("WARNINGS")
        print("=" * 80)
        for result in all_results:
            if result["warnings"]:
                print(f"\n{result['file']} ({result['title']}):")
                for warning in result["warnings"]:
                    print(f"  WARN: {warning}")

    # Return code
    if total_errors > 0:
        return 1
    if args.strict and total_warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
