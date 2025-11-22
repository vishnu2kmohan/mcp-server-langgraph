#!/usr/bin/env python3
"""
Validate ServiceAccount naming consistency across base and overlays.

This script ensures that ServiceAccount names in overlays match the naming
convention from the base ServiceAccounts. All ServiceAccounts should follow
the pattern: <component>-sa

Usage:
    python scripts/validate_serviceaccount_names.py

Returns:
    0 if all ServiceAccount names are consistent
    1 if naming inconsistencies are found
"""

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
BASE_SA_PATH = REPO_ROOT / "deployments" / "base" / "serviceaccounts.yaml"
OVERLAYS_DIR = REPO_ROOT / "deployments" / "overlays"


def load_base_serviceaccount_names() -> set[str]:
    """Load ServiceAccount names from base deployment."""
    base_names = set()

    if not BASE_SA_PATH.exists():
        print(f"ERROR: Base ServiceAccounts file not found: {BASE_SA_PATH}", file=sys.stderr)
        return base_names

    with open(BASE_SA_PATH) as f:
        try:
            for doc in yaml.safe_load_all(f):
                if doc and doc.get("kind") == "ServiceAccount":
                    name = doc["metadata"]["name"]
                    base_names.add(name)

                    # Validate base name follows convention
                    if not name.endswith("-sa"):
                        print(f"WARNING: Base ServiceAccount '{name}' doesn't follow -sa naming convention", file=sys.stderr)
        except yaml.YAMLError as e:
            print(f"ERROR: Failed to parse {BASE_SA_PATH}: {e}", file=sys.stderr)

    return base_names


def validate_overlay_serviceaccounts(base_names: set[str]) -> list[tuple[Path, str, str]]:
    """
    Validate ServiceAccount names in overlays match base naming convention.

    Only validates ServiceAccounts that have corresponding base definitions.
    Overlay-only ServiceAccounts (e.g., mcp-server-langgraph, external-secrets-operator)
    are allowed and not validated.

    Returns:
        List of (file_path, sa_name, error_message) tuples for errors found
    """
    errors = []
    overlay_only_allowed = {
        "mcp-server-langgraph",  # Main application SA (GKE only)
        "external-secrets-operator",  # External Secrets Operator SA
        "otel-collector",  # OpenTelemetry Collector SA
    }

    if not OVERLAYS_DIR.exists():
        print(f"WARNING: Overlays directory not found: {OVERLAYS_DIR}", file=sys.stderr)
        return errors

    # Find all serviceaccount YAML files in overlays
    for sa_file in OVERLAYS_DIR.rglob("serviceaccount*.yaml"):
        try:
            with open(sa_file) as f:
                for doc in yaml.safe_load_all(f):
                    if not doc or doc.get("kind") != "ServiceAccount":
                        continue

                    sa_name = doc["metadata"]["name"]

                    # Remove environment prefixes to get clean name
                    clean_name = sa_name
                    for prefix in ["staging-", "production-", "dev-", "test-"]:
                        if clean_name.startswith(prefix):
                            clean_name = clean_name[len(prefix) :]
                            break

                    # Skip overlay-only ServiceAccounts (they don't need to match base)
                    if clean_name in overlay_only_allowed:
                        continue

                    # Check if clean name matches base convention
                    if clean_name not in base_names:
                        # Check if adding -sa suffix would match
                        if not clean_name.endswith("-sa"):
                            potential_name = f"{clean_name}-sa"
                            if potential_name in base_names:
                                errors.append(
                                    (
                                        sa_file,
                                        sa_name,
                                        f"ServiceAccount '{sa_name}' should be named with -sa suffix to match base. "
                                        f"Expected: {sa_name}-sa (which would match base: {potential_name})",
                                    )
                                )
                            # Else: Overlay-only SA not in allowed list - could be added later

        except yaml.YAMLError as e:
            print(f"WARNING: Failed to parse {sa_file}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: Error processing {sa_file}: {e}", file=sys.stderr)

    return errors


def main() -> int:
    """Main validation function."""
    print("🔍 Validating ServiceAccount naming consistency...")
    print(f"   Base: {BASE_SA_PATH}")
    print(f"   Overlays: {OVERLAYS_DIR}")
    print()

    # Load base ServiceAccount names
    base_names = load_base_serviceaccount_names()
    if not base_names:
        print("ERROR: No ServiceAccounts found in base deployment", file=sys.stderr)
        return 1

    print(f"✓ Found {len(base_names)} base ServiceAccounts:")
    for name in sorted(base_names):
        print(f"  - {name}")
    print()

    # Validate overlay ServiceAccounts
    errors = validate_overlay_serviceaccounts(base_names)

    if errors:
        print(f"❌ Found {len(errors)} naming inconsistenc{'y' if len(errors) == 1 else 'ies'}:")
        print()
        for file_path, sa_name, error_msg in errors:
            rel_path = file_path.relative_to(REPO_ROOT)
            print(f"  {rel_path}:")
            print(f"    {error_msg}")
            print()

        print("💡 Fix: Update ServiceAccount names in overlays to match base naming convention (<component>-sa)")
        return 1

    print("✅ All ServiceAccount names are consistent!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
