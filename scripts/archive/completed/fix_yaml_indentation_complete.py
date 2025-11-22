#!/usr/bin/env python3
"""
Fix YAML indentation comprehensively.

This script fixes indentation issues in YAML files by:
1. Ensuring list items (-) are indented 2 spaces more than their parent
2. Ensuring properties of list items are aligned with the first property

Pattern detected by yamllint:
- List items and their properties are consistently 2 spaces less than expected
"""

import sys
from pathlib import Path


def calculate_expected_indent(lines, line_idx):
    """
    Calculate the expected indentation for a line based on context.

    Returns: (expected_indent, is_list_item, parent_indent)
    """
    line = lines[line_idx]
    stripped = line.lstrip()

    # Skip empty lines and comments
    if not stripped or stripped.startswith("#"):
        return None, False, None

    current_indent = len(line) - len(stripped)
    is_list_item = stripped.startswith("- ")

    # Look backwards to find the parent context
    for i in range(line_idx - 1, -1, -1):
        prev_line = lines[i].strip()

        # Skip empty lines and comments
        if not prev_line or prev_line.startswith("#"):
            continue

        prev_indent = len(lines[i]) - len(lines[i].lstrip())

        # If previous line ends with ':', it's a parent
        if prev_line.endswith(":"):
            if is_list_item:
                # List items should be indented 2 more than parent
                return prev_indent + 2, True, prev_indent
            else:
                # Regular keys should also be indented 2 more than parent
                return prev_indent + 2, False, prev_indent

        # If previous line is a list item at the same or less indent
        if prev_line.startswith("- "):
            prev_list_indent = prev_indent
            if not is_list_item and current_indent <= prev_list_indent:
                # Properties of list items should align with the first property
                # which is at list_indent + 2 (for "- ") = prev_indent + 2
                return prev_indent + 2, False, prev_indent
            break

    return None, False, None


def fix_yaml_indentation(content: str) -> str:
    """
    Fix all indentation issues in YAML content.
    """
    lines = content.split("\n")
    in_literal_block = False
    literal_block_indent = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        # Track literal blocks (| or >)
        if stripped in ["|", ">"] or stripped.startswith("| ") or stripped.startswith("> "):
            in_literal_block = True
            literal_block_indent = len(line) - len(stripped)
            continue

        # Skip lines in literal blocks
        if in_literal_block:
            current_indent = len(line) - len(stripped) if stripped else 0
            if stripped and current_indent <= literal_block_indent:
                in_literal_block = False
            else:
                continue

        # Skip empty lines, comments, and YAML document markers
        if not stripped or stripped.startswith("#") or stripped in ["---", "..."]:
            continue

        expected_indent, is_list_item, parent_indent = calculate_expected_indent(lines, i)

        if expected_indent is not None:
            current_indent = len(line) - len(stripped)

            # Fix indentation if needed
            if current_indent != expected_indent:
                # Add or remove spaces
                indent_diff = expected_indent - current_indent
                if indent_diff > 0:
                    lines[i] = (" " * indent_diff) + line
                elif indent_diff < 0:
                    lines[i] = line[-indent_diff:]

    return "\n".join(lines)


def fix_yaml_file(file_path: Path) -> bool:
    """Fix indentation in a YAML file."""
    print(f"Processing: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        fixed_content = fix_yaml_indentation(original_content)

        if fixed_content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print("  ✅ Fixed")
            return True
        else:
            print("  ℹ️  No changes needed")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function to fix YAML indentation."""

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

    print(f"Fixing YAML indentation in {len(files_to_fix)} files...\n")

    for file_path_str in files_to_fix:
        file_path = repo_root / file_path_str

        if not file_path.exists():
            print(f"⚠️  Not found: {file_path}")
            error_count += 1
            continue

        if fix_yaml_file(file_path):
            fixed_count += 1

    print("\n📊 Summary:")
    print(f"  ✅ Fixed: {fixed_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  📁 Total: {len(files_to_fix)}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
