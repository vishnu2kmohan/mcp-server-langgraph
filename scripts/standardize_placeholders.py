#!/usr/bin/env python3
"""
Standardize placeholder syntax in documentation.

Converts informal placeholders like 'xxx', 'your-*', etc. to ${PLACEHOLDER} format.
"""

import re
import sys
from pathlib import Path


# Placeholder patterns to standardize
PLACEHOLDER_PATTERNS = [
    # Pod/container identifiers
    (r"mcp-server-langgraph-xxx", r"mcp-server-langgraph-${POD_ID}"),
    (r"mcp-server-langgraph-\w+-xxx", r"mcp-server-langgraph-${DEPLOYMENT_ID}-${POD_ID}"),
    # Azure subscription IDs
    (r"/subscriptions/xxx/", r"/subscriptions/${SUBSCRIPTION_ID}/"),
    (r"resourceGroups/xxx", r"resourceGroups/${RESOURCE_GROUP}"),
    # GCP project IDs
    (r"projects/xxx/", r"projects/${PROJECT_ID}/"),
    (r"--project=xxx", r"--project=${PROJECT_ID}"),
    # AWS account IDs and ARNs
    (r"arn:aws:iam::xxx:", r"arn:aws:iam::${ACCOUNT_ID}:"),
    (r":ACCOUNT_ID:certificate/xxx", r":ACCOUNT_ID:certificate/${CERT_ID}"),
    (r":ACCOUNT_ID:key/xxx", r":ACCOUNT_ID:key/${KMS_KEY_ID}"),
    # AWS resource IDs
    (r"subnet-xxx", r"subnet-${SUBNET_ID}"),
    (r"subnet-yyy", r"subnet-${SUBNET_ID_2}"),
    (r"sg-xxx", r"sg-${SECURITY_GROUP_ID}"),
    (r"vpc-xxx", r"vpc-${VPC_ID}"),
    # AWS RDS/ElastiCache endpoints
    (r"\.xxx\.cache\.amazonaws\.com", r".${CLUSTER_ID}.cache.amazonaws.com"),
    (r"\.xxx\.us-east-1\.rds\.amazonaws\.com", r".${DB_INSTANCE}.us-east-1.rds.amazonaws.com"),
    (r"\.xxx\.\w{2}-\w+-\d\.rds\.amazonaws\.com", r".${DB_INSTANCE}.${REGION}.rds.amazonaws.com"),
    # Application Insights instrumentation keys
    (r"InstrumentationKey=xxx;", r"InstrumentationKey=${INSTRUMENTATION_KEY};"),
    # Generic xxx in commands (be conservative)
    (r"kubectl exec -it (\S+)-xxx", r"kubectl exec -it \1-${POD_ID}"),
    (r"kubectl describe pod (\S+)-xxx", r"kubectl describe pod \1-${POD_ID}"),
]


def standardize_file(filepath: Path, dry_run: bool = False) -> int:
    """Standardize placeholders in a file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        original_content = content
        replacements = 0

        for pattern, replacement in PLACEHOLDER_PATTERNS:
            matches_before = len(re.findall(pattern, content))
            content = re.sub(pattern, replacement, content)
            matches_after = len(re.findall(pattern, content))
            replacements += matches_before - matches_after

        if content != original_content:
            if not dry_run:
                filepath.write_text(content, encoding="utf-8")
                print(f"✅ Standardized {replacements} placeholders in {filepath}")
            else:
                print(f"🔍 Would standardize {replacements} placeholders in {filepath}")
            return replacements

        return 0

    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}", file=sys.stderr)
        return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Standardize placeholder syntax in documentation")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be changed")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all markdown files with xxx placeholders
    md_files = []
    for ext in ["*.md", "*.mdx"]:
        for f in docs_path.rglob(ext):
            if ".mintlify/templates" in str(f):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                if "xxx" in content:
                    md_files.append(f)
            except Exception:
                pass

    if not md_files:
        print("No files with 'xxx' placeholders found")
        return

    print(f"Processing {len(md_files)} files with 'xxx' placeholders...")
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made\n")

    total_replacements = 0
    files_modified = 0

    for filepath in sorted(md_files):
        replacements = standardize_file(filepath, args.dry_run)
        if replacements > 0:
            total_replacements += replacements
            files_modified += 1

    print(f"\n{'=' * 80}")
    verb = "Would standardize" if args.dry_run else "Standardized"
    print(f"{verb} {total_replacements} placeholders in {files_modified} files")
    print(f"{'=' * 80}")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
