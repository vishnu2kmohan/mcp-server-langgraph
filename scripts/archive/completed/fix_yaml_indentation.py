#!/usr/bin/env python3
"""
Fix YAML indentation issues in deployment files.

This script reads YAML files, parses them, and rewrites them with correct
2-space indentation following yamllint standards.

Uses ruamel.yaml to preserve comments and formatting.
"""

import sys
from pathlib import Path

from ruamel.yaml import YAML


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
        # Configure ruamel.yaml to preserve comments and use 2-space indentation
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        yaml.indent(mapping=2, sequence=2, offset=2)
        yaml.width = 120

        # Load all documents (handles multi-document YAML files)
        with open(file_path, "r", encoding="utf-8") as f:
            documents = list(yaml.load_all(f))

        # Skip empty files
        if not documents or all(doc is None for doc in documents):
            print(f"  ⚠️  Skipped (empty file)")
            return False

        # Rewrite with proper indentation
        with open(file_path, "w", encoding="utf-8") as f:
            # Write all documents with proper formatting
            for i, doc in enumerate(documents):
                if doc is not None:
                    if i > 0:
                        f.write("---\n")
                    yaml.dump(doc, f)

        print(f"  ✅ Fixed")
        return True

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

    print(f"Fixing YAML indentation in {len(files_to_fix)} files...\n")

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
