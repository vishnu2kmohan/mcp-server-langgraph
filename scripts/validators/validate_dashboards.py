#!/usr/bin/env python3
"""
Validate Grafana dashboard JSON files.

Checks:
1. Valid JSON syntax
2. Required dashboard fields (panels, title, uid)
3. Panel structure validation
"""

import json
import sys
from pathlib import Path


def validate_dashboard(filepath: Path) -> list[str]:
    """Validate a single dashboard file."""
    errors = []

    try:
        with open(filepath) as f:
            dashboard = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return [f"File not found: {filepath}"]

    # Required fields
    if "panels" not in dashboard:
        errors.append("Missing 'panels' field")
    elif not isinstance(dashboard["panels"], list):
        errors.append("'panels' must be a list")

    if "title" not in dashboard:
        errors.append("Missing 'title' field")

    if "uid" not in dashboard:
        errors.append("Missing 'uid' field")

    # Validate panels structure
    if "panels" in dashboard and isinstance(dashboard["panels"], list):
        for i, panel in enumerate(dashboard["panels"]):
            if not isinstance(panel, dict):
                errors.append(f"Panel {i} is not a dict")
                continue

            # Row panels don't need these fields
            if panel.get("type") == "row":
                continue

            if "id" not in panel:
                errors.append(f"Panel {i} missing 'id'")
            if "type" not in panel:
                errors.append(f"Panel {i} missing 'type'")

    return errors


def main() -> int:
    """Validate all dashboard files."""
    monitoring_dir = Path("deployments/monitoring")

    if not monitoring_dir.exists():
        print(f"Warning: {monitoring_dir} does not exist")
        return 0

    dashboard_files = list(monitoring_dir.glob("*.json"))

    if not dashboard_files:
        print("No dashboard JSON files found")
        return 0

    all_valid = True

    for filepath in dashboard_files:
        errors = validate_dashboard(filepath)

        if errors:
            print(f"  ✗ {filepath}")
            for error in errors:
                print(f"    - {error}")
            all_valid = False
        else:
            print(f"  ✓ {filepath}")

    if all_valid:
        print("\nAll dashboards are valid!")
        return 0
    else:
        print("\nValidation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
