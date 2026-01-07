#!/usr/bin/env python3
"""
Convert K8s PrometheusRule CRD format alerts to standard Prometheus rules format.

This script converts alerts from Kubernetes PrometheusRule CRD format
(monitoring.coreos.com/v1) to standard Prometheus rules format that can be
used directly by Prometheus or Mimir ruler.

Usage:
    # Convert a single file
    python scripts/convert-k8s-crd-alerts.py source.yaml --output dest.yaml

    # Convert all files in a directory
    python scripts/convert-k8s-crd-alerts.py --source-dir src/ --output-dir dest/

    # Dry run (show what would be done)
    python scripts/convert-k8s-crd-alerts.py source.yaml --output dest.yaml --dry-run

Options:
    --output        Output file path (for single file conversion)
    --source-dir    Source directory containing K8s CRD files
    --output-dir    Output directory for converted files
    --dry-run       Show what would be done without making changes
    --verbose       Show detailed output
    --help          Show this help message

Examples:
    # Convert langgraph-agent.yaml
    python scripts/convert-k8s-crd-alerts.py \\
        monitoring/prometheus/alerts/langgraph-agent.yaml \\
        --output monitoring/prometheus/rules/langgraph-agent-alerts.yaml

    # Convert all CRD alerts in deployments/monitoring/
    python scripts/convert-k8s-crd-alerts.py \\
        --source-dir deployments/monitoring/ \\
        --output-dir monitoring/prometheus/rules/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def is_k8s_crd_format(content: dict[str, Any]) -> bool:
    """Check if content is in Kubernetes PrometheusRule CRD format."""
    if not content or not isinstance(content, dict):
        return False
    api_version = content.get("apiVersion", "")
    kind = content.get("kind", "")
    return "monitoring.coreos.com" in api_version and kind == "PrometheusRule"


def convert_crd_to_standard(content: dict[str, Any], source_path: str) -> str:
    """Convert K8s CRD format to standard Prometheus rules format."""
    if not is_k8s_crd_format(content):
        raise ValueError("Input is not a valid K8s PrometheusRule CRD")

    spec = content.get("spec", {})
    groups = spec.get("groups", [])

    if not groups:
        raise ValueError("No groups found in CRD spec")

    # Build output with header comment
    header = f"""# Converted from K8s PrometheusRule CRD
# Source: {source_path}
# Original name: {content.get("metadata", {}).get("name", "unknown")}
# Original namespace: {content.get("metadata", {}).get("namespace", "unknown")}
#
# This file is in standard Prometheus rules format.
# It can be used directly by Prometheus or Mimir ruler.

"""

    # Convert to standard format
    standard_content = {"groups": groups}

    # Use yaml.dump with custom options for readability
    yaml_content = yaml.dump(
        standard_content,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )

    return header + yaml_content


def convert_file(
    source_path: Path,
    output_path: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Convert a single K8s CRD file to standard format.

    Returns True if conversion was successful, False if skipped.
    """
    try:
        with open(source_path) as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse {source_path}: {e}", file=sys.stderr)
        return False

    if not is_k8s_crd_format(content):
        if verbose:
            print(f"SKIP: {source_path} is not a K8s PrometheusRule CRD")
        return False

    try:
        converted = convert_crd_to_standard(content, str(source_path))
    except ValueError as e:
        print(f"ERROR: Failed to convert {source_path}: {e}", file=sys.stderr)
        return False

    if dry_run:
        print(f"DRY-RUN: Would convert {source_path} -> {output_path}")
        return True

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(converted)

    print(f"CONVERTED: {source_path} -> {output_path}")
    return True


def convert_directory(
    source_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[int, int]:
    """Convert all K8s CRD files in a directory.

    Returns (converted_count, skipped_count).
    """
    converted = 0
    skipped = 0

    for source_path in source_dir.glob("*.y*ml"):
        if not source_path.is_file():
            continue

        # Determine output filename
        output_filename = source_path.stem + ".yaml"
        output_path = output_dir / output_filename

        if convert_file(source_path, output_path, dry_run, verbose):
            converted += 1
        else:
            skipped += 1

    return converted, skipped


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert K8s PrometheusRule CRD to standard Prometheus rules format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "source_file",
        nargs="?",
        type=Path,
        help="Source K8s CRD file to convert",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (for single file conversion)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Source directory containing K8s CRD files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for converted files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.source_dir and args.output_dir:
        # Directory mode
        if not args.source_dir.exists():
            print(f"ERROR: Source directory not found: {args.source_dir}", file=sys.stderr)
            return 1

        converted, skipped = convert_directory(
            args.source_dir,
            args.output_dir,
            args.dry_run,
            args.verbose,
        )

        print(f"\nSummary: {converted} converted, {skipped} skipped")
        return 0

    elif args.source_file and args.output:
        # Single file mode
        if not args.source_file.exists():
            print(f"ERROR: Source file not found: {args.source_file}", file=sys.stderr)
            return 1

        success = convert_file(
            args.source_file,
            args.output,
            args.dry_run,
            args.verbose,
        )
        return 0 if success else 1

    else:
        parser.print_help()
        print("\nERROR: Must specify either:")
        print("  1. source_file and --output for single file conversion")
        print("  2. --source-dir and --output-dir for directory conversion")
        return 1


if __name__ == "__main__":
    sys.exit(main())
