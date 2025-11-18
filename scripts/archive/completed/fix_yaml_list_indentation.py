#!/usr/bin/env python3
"""
Fix YAML list indentation issues using regex-based approach.

This is a conservative approach that only fixes the specific indentation
pattern identified by yamllint: list items indented 2 spaces less than expected.
"""

import re
import sys
from pathlib import Path


def fix_list_indentation(content: str) -> str:
    """
    Fix list indentation in YAML content.

    The issue pattern from yamllint:
    - Lines with list items (-) are indented N spaces
    - They should be indented N+2 spaces
    - This happens after keys like 'initContainers:', 'args:', 'containers:', etc.

    Strategy:
    1. Identify list items that follow a key ending with ':'
    2. Add 2 spaces of indentation to those items
    """
    lines = content.split("\n")
    fixed_lines = []
    prev_line_is_list_parent = False
    list_parent_indent = 0

    for i, line in enumerate(lines):
        # Check if previous line was a list parent (key ending with :)
        if i > 0:
            prev_line = lines[i - 1].strip()
            if prev_line.endswith(":") and not prev_line.startswith("#"):
                prev_line_is_list_parent = True
                # Calculate the indent level of the parent
                list_parent_indent = len(lines[i - 1]) - len(lines[i - 1].lstrip())

        # Check if current line is a list item
        stripped = line.lstrip()
        if stripped.startswith("- "):
            current_indent = len(line) - len(stripped)

            # If this list item follows a list parent and is at the same indent level
            # then it needs to be indented 2 more spaces
            if prev_line_is_list_parent and current_indent == list_parent_indent:
                line = "  " + line
                prev_line_is_list_parent = False  # Only fix the first item

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_yaml_file(file_path: Path) -> bool:
    """
    Fix indentation in a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        True if file was modified, False otherwise
    """
    print(f"Processing: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        fixed_content = fix_list_indentation(original_content)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"  ✅ Fixed")
            return True
        print(f"  ℹ️  No changes needed")
        return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function to fix YAML indentation."""

    # Files to fix (from the investigation report)
    files_to_fix = [
        "deployments/base/deployment.yaml",
        "deployments/base/redis-session-deployment.yaml",
        "deployments/base/postgres-statefulset.yaml",
        "deployments/base/role.yaml",
        "deployments/base/keycloak-deployment.yaml",
        "deployments/base/openfga-deployment.yaml",
        "deployments/base/service.yaml",
        "deployments/base/hpa.yaml",
        "deployments/base/keycloak-service.yaml",
        "deployments/base/redis-session-service.yaml",
        "deployments/optimized/deployment.yaml",
        "deployments/optimized/postgres-statefulset.yaml",
        "deployments/optimized/hpa.yaml",
        "deployments/optimized/redis-session-deployment.yaml",
        "deployments/cloudrun/service.yaml",
        "deployments/kubernetes/skaffold.yaml",
        "deployments/kubernetes/kong/kong-ingress.yaml",
        "deployments/kubernetes/kong/kong-apikey-jwt-plugin.yaml",
        "deployments/kubernetes/kong/kong-jwks-updater-cronjob.yaml",
        "deployments/kubernetes/kong/redis-deployment.yaml",
        "deployments/components/gcp-cloud-sql-proxy/cloud-sql-proxy-sidecar.yaml",
    ]

    repo_root = Path(__file__).parent.parent
    fixed_count = 0
    error_count = 0

    print(f"Fixing YAML list indentation in {len(files_to_fix)} files...\n")

    for file_path_str in files_to_fix:
        file_path = repo_root / file_path_str

        if not file_path.exists():
            print(f"⚠️  Not found: {file_path}")
            error_count += 1
            continue

        if fix_yaml_file(file_path):
            fixed_count += 1

    print(f"\n📊 Summary:")
    print(f"  ✅ Fixed: {fixed_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  📁 Total: {len(files_to_fix)}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
