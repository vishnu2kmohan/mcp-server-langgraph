#!/usr/bin/env python3
"""
Migrate workflows to use setup-python-deps composite action.

This script automatically replaces manual Python + UV setup sequences
with the ./.github/actions/setup-python-deps composite action.

Target: Phase 5.5.1 - Automated workflow migration
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


class WorkflowMigrator:
    """Migrate workflows to use composite actions."""

    def __init__(self, workflows_dir: Path, dry_run: bool = False):
        """Initialize migrator."""
        self.workflows_dir = Path(workflows_dir)
        self.dry_run = dry_run
        self.migrations: dict[str, int] = {}

    def migrate_all(self, workflow_files: list[str]) -> None:
        """Migrate specified workflow files."""
        for workflow_file in workflow_files:
            workflow_path = self.workflows_dir / workflow_file
            if not workflow_path.exists():
                print(f"⚠️  Workflow not found: {workflow_file}")
                continue

            print(f"\n📝 Processing {workflow_file}...")
            migrated = self.migrate_workflow(workflow_path)
            self.migrations[workflow_file] = migrated

            if migrated > 0:
                print(f"   ✓ Migrated {migrated} job(s)")
            else:
                print("   • No migrations needed")

    def migrate_workflow(self, workflow_path: Path) -> int:
        """Migrate a single workflow file."""
        # Read the workflow file as text (preserve formatting)
        content = workflow_path.read_text()
        original_content = content
        migrations_count = 0

        # Pattern: Manual Python + UV setup
        # This matches the 3-step sequence:
        # 1. actions/setup-python
        # 2. astral-sh/setup-uv
        # 3. uv sync or uv pip install

        # Step 1: Find and replace setup-python + setup-uv sequences
        # We need to be careful to preserve indentation and structure

        # Pattern 1: setup-python@v6 + setup-uv@v5/v7 + uv sync/install
        pattern_1 = re.compile(
            r"(      - name: Set up Python.*?\n"
            r"        uses: actions/setup-python@v\d+.*?\n"
            r"        with:.*?\n"
            r"          python-version: '(\d+\.\d+)'.*?\n)"
            r"(      - name: (?:Install uv|Set up uv).*?\n"
            r"        uses: astral-sh/setup-uv@v\d+.*?\n"
            r"(?:        with:.*?\n)?(?:          version:.*?\n)?(?:          enable-cache:.*?\n)?)"
            r"(      - name: Install (?:package and test )?dependencies.*?\n"
            r"        run: \|.*?\n"
            r"(?:          # .*?\n)*"
            r"          (?:uv sync --frozen|uv pip install).*?\n)",
            re.MULTILINE | re.DOTALL,
        )

        def replacement_1(match):
            """Generate replacement for pattern 1."""
            nonlocal migrations_count
            migrations_count += 1

            python_version = match.group(2)
            indent = "      "  # Standard job step indentation

            # Determine cache key prefix from job context if possible
            # For now, use generic prefix
            cache_prefix = "deps"

            # Check if dev extras needed (look for uv pip install -e .[dev])
            if "[dev]" in match.group(0):
                extras = "dev"
            else:
                extras = ""

            replacement = (
                f"{indent}- name: Set up Python and dependencies\n"
                f"{indent}  uses: ./.github/actions/setup-python-deps\n"
                f"{indent}  with:\n"
                f"{indent}    python-version: '{python_version}'\n"
            )

            if extras:
                replacement += f"{indent}    extras: '{extras}'\n"

            replacement += f"{indent}    cache-key-prefix: '{cache_prefix}'\n"

            return replacement

        # Apply pattern replacement
        content = pattern_1.sub(replacement_1, content)

        # Only write if changes were made and not in dry-run mode
        if content != original_content:
            if not self.dry_run:
                workflow_path.write_text(content)
            return migrations_count

        return 0

    def generate_summary(self) -> str:
        """Generate migration summary."""
        total_workflows = len(self.migrations)
        total_jobs = sum(self.migrations.values())

        summary = []
        summary.append("\n" + "=" * 80)
        summary.append("Migration Summary")
        summary.append("=" * 80)
        summary.append(f"  Workflows processed: {total_workflows}")
        summary.append(f"  Jobs migrated: {total_jobs}")
        summary.append("")

        if self.dry_run:
            summary.append("⚠️  DRY RUN - No files were modified")
        else:
            summary.append("✅ Migration complete!")

        summary.append("")
        summary.append("Migrated workflows:")
        for workflow, count in sorted(self.migrations.items()):
            if count > 0:
                summary.append(f"  • {workflow}: {count} job(s)")

        summary.append("=" * 80)

        return "\n".join(summary)


def main():
    """Run workflow migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate workflows to use composite actions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--workflows-dir", default=".github/workflows", help="Workflows directory")
    args = parser.parse_args()

    workflows_dir = Path(args.workflows_dir)

    if not workflows_dir.exists():
        print(f"❌ Workflows directory not found: {workflows_dir}")
        return 1

    # List of workflows to migrate (from find_manual_python_uv_setup.py output)
    workflows_to_migrate = [
        "ci.yaml",
        "docs-validation.yaml",
        "dora-metrics.yaml",
        "e2e-tests.yaml",
        "integration-tests.yaml",
        "local-preflight-check.yaml",
        "performance-regression.yaml",
        "release.yaml",
        # "security-validation.yml",  # Already migrated manually
        "weekly-reports.yaml",
    ]

    print("🔄 Migrating workflows to use setup-python-deps composite action...")
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No files will be modified\n")

    migrator = WorkflowMigrator(workflows_dir, dry_run=args.dry_run)
    migrator.migrate_all(workflows_to_migrate)

    print(migrator.generate_summary())

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
