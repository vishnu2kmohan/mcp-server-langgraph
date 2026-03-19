"""CLI entry point for legacy data migration.

Usage:
    uv run python -m mcp_server_langgraph.migrations --dry-run
    uv run python -m mcp_server_langgraph.migrations
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main(base_dir: Path, dry_run: bool) -> None:
    from mcp_server_langgraph.core.dependencies import (
        get_agent_state_repository,
        get_checkpoint_repository,
        get_evidence_repository,
        get_notes_repository,
    )
    from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter

    importer = LegacyDataImporter(base_dir=base_dir, dry_run=dry_run)

    if dry_run:
        logger.info("DRY RUN — no data will be written")

    summary = await importer.import_all(
        notes_repo=get_notes_repository(),
        checkpoint_repo=get_checkpoint_repository(),
        agent_state_repo=get_agent_state_repository(),
        evidence_repo=get_evidence_repository(),
    )

    print("\n=== Migration Summary ===")
    for artifact_type, result in summary.items():
        status = "DRY RUN" if dry_run else "LIVE"
        print(f"  {artifact_type}: {result.success} imported, {result.skipped} skipped, {result.failed} failed [{status}]")
        for error in result.errors:
            print(f"    ERROR: {error}")

    total_failed = sum(r.failed for r in summary.values())
    if total_failed > 0:
        print(f"\n{total_failed} entries failed. Check logs for details.")
    else:
        print("\nAll entries processed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import legacy file-based data into repository backends")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be imported without writing")
    parser.add_argument("--base-dir", type=Path, default=Path("."), help="Base directory for legacy files (default: CWD)")
    args = parser.parse_args()

    asyncio.run(main(base_dir=args.base_dir, dry_run=args.dry_run))
