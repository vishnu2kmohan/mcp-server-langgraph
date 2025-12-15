#!/usr/bin/env python3
"""
Migrate audit logs from unpartitioned table to partitioned table.

This script migrates data from the legacy audit_logs table to the new
audit_logs_partitioned table with monthly partitions.

Features:
- Batched migration to minimize lock time
- Resumable migration (tracks progress via marker table)
- Progress reporting with ETA
- Dry-run mode for testing
- Configurable batch size and delay

Usage:
    # Dry run (no changes)
    uv run python scripts/migrate_audit_to_partitioned.py --dry-run

    # Run migration with default settings
    uv run python scripts/migrate_audit_to_partitioned.py

    # Run with custom batch size
    uv run python scripts/migrate_audit_to_partitioned.py --batch-size 5000

    # Resume from last checkpoint
    uv run python scripts/migrate_audit_to_partitioned.py --resume

Safety:
- Does NOT delete original data
- Creates checkpoint table for resume support
- Reports progress every batch
- Graceful shutdown on SIGINT/SIGTERM

Regulatory Context:
This migration supports O(1) retention cleanup via DROP PARTITION for:
- FedRAMP AU-11: 7-year retention
- HIPAA: 6-year retention
- GDPR: Right to erasure support
- SOC 2: Audit data lifecycle management
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info("Shutdown requested, completing current batch...")
    shutdown_requested = True


async def get_connection():
    """Get database connection from environment."""
    import os

    try:
        import asyncpg
    except ImportError:
        logger.exception("asyncpg not installed. Run: uv add asyncpg")
        sys.exit(1)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    # Convert SQLAlchemy URL to asyncpg URL
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    return await asyncpg.connect(database_url)


async def check_tables_exist(conn: Any) -> tuple[bool, bool]:
    """Check if source and target tables exist."""
    source_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'audit_logs'
            AND n.nspname = current_schema()
        )
    """)

    target_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'audit_logs_partitioned'
            AND n.nspname = current_schema()
        )
    """)

    return source_exists, target_exists


async def create_checkpoint_table(conn: Any) -> None:
    """Create checkpoint table for resumable migration."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS _audit_migration_checkpoint (
            id SERIAL PRIMARY KEY,
            last_migrated_id VARCHAR(255),
            last_migrated_timestamp TIMESTAMP WITH TIME ZONE,
            rows_migrated BIGINT DEFAULT 0,
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)


async def get_checkpoint(conn: Any) -> tuple[str | None, datetime | None, int]:
    """Get last checkpoint for resume."""
    row = await conn.fetchrow("""
        SELECT last_migrated_id, last_migrated_timestamp, rows_migrated
        FROM _audit_migration_checkpoint
        ORDER BY id DESC
        LIMIT 1
    """)

    if row:
        return row["last_migrated_id"], row["last_migrated_timestamp"], row["rows_migrated"]
    return None, None, 0


async def update_checkpoint(conn: Any, last_id: str, last_timestamp: datetime, total_migrated: int) -> None:
    """Update migration checkpoint."""
    await conn.execute(
        """
        INSERT INTO _audit_migration_checkpoint
            (last_migrated_id, last_migrated_timestamp, rows_migrated)
        VALUES ($1, $2, $3)
    """,
        last_id,
        last_timestamp,
        total_migrated,
    )


async def get_total_count(conn: Any, resume_from: tuple[str | None, datetime | None]) -> int:
    """Get total count of rows to migrate."""
    if resume_from[0]:
        return await conn.fetchval(
            """
            SELECT COUNT(*) FROM audit_logs
            WHERE (timestamp, id) > ($1, $2)
        """,
            resume_from[1],
            resume_from[0],
        )
    return await conn.fetchval("SELECT COUNT(*) FROM audit_logs")


async def migrate_batch(
    conn: Any,
    batch_size: int,
    resume_from: tuple[str | None, datetime | None],
    dry_run: bool,
) -> tuple[list[Any], str | None, datetime | None]:
    """Migrate a batch of rows."""
    if resume_from[0]:
        rows = await conn.fetch(
            """
            SELECT
                id,
                timestamp,
                event_type,
                actor_id,
                resource_type,
                resource_id,
                action,
                ip_address,
                user_agent,
                COALESCE(details, metadata) as metadata,
                category,
                outcome,
                actor_type,
                organization_id,
                trace_id,
                span_id,
                session_id,
                ai_operation,
                sequence_number,
                previous_hash,
                event_hash,
                regulation_tags,
                COALESCE(retention_days, 2555) as retention_days
            FROM audit_logs
            WHERE (timestamp, id) > ($1, $2)
            ORDER BY timestamp, id
            LIMIT $3
        """,
            resume_from[1],
            resume_from[0],
            batch_size,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT
                id,
                timestamp,
                event_type,
                actor_id,
                resource_type,
                resource_id,
                action,
                ip_address,
                user_agent,
                COALESCE(details, metadata) as metadata,
                category,
                outcome,
                actor_type,
                organization_id,
                trace_id,
                span_id,
                session_id,
                ai_operation,
                sequence_number,
                previous_hash,
                event_hash,
                regulation_tags,
                COALESCE(retention_days, 2555) as retention_days
            FROM audit_logs
            ORDER BY timestamp, id
            LIMIT $1
        """,
            batch_size,
        )

    if not rows:
        return [], None, None

    if not dry_run:
        # Ensure partition exists for each row's timestamp
        for row in rows:
            await conn.execute(
                """
                SELECT create_audit_partition_if_needed($1)
            """,
                row["timestamp"],
            )

        # Insert into partitioned table
        await conn.executemany(
            """
            INSERT INTO audit_logs_partitioned (
                id, timestamp, event_type, actor_id, resource_type, resource_id,
                action, ip_address, user_agent, metadata, category, outcome,
                actor_type, organization_id, trace_id, span_id, session_id,
                ai_operation, sequence_number, previous_hash, event_hash,
                regulation_tags, retention_days
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18, $19, $20, $21, $22, $23
            )
            ON CONFLICT (id, timestamp) DO NOTHING
        """,
            [
                (
                    row["id"],
                    row["timestamp"],
                    row["event_type"],
                    row["actor_id"],
                    row["resource_type"],
                    row["resource_id"],
                    row["action"],
                    row["ip_address"],
                    row["user_agent"],
                    row["metadata"],
                    row["category"],
                    row["outcome"],
                    row["actor_type"],
                    row["organization_id"],
                    row["trace_id"],
                    row["span_id"],
                    row["session_id"],
                    row["ai_operation"],
                    row["sequence_number"],
                    row["previous_hash"],
                    row["event_hash"],
                    row["regulation_tags"],
                    row["retention_days"],
                )
                for row in rows
            ],
        )

    last_row = rows[-1]
    return rows, last_row["id"], last_row["timestamp"]


async def run_migration(
    batch_size: int,
    batch_delay: float,
    dry_run: bool,
    resume: bool,
) -> None:
    """Run the migration."""
    conn = await get_connection()

    try:
        # Check tables exist
        source_exists, target_exists = await check_tables_exist(conn)

        if not source_exists:
            logger.error("Source table 'audit_logs' does not exist")
            return

        if not target_exists:
            logger.error(
                "Target table 'audit_logs_partitioned' does not exist. Run Alembic migration first: alembic upgrade head"
            )
            return

        # Create checkpoint table
        await create_checkpoint_table(conn)

        # Get checkpoint if resuming
        last_id: str | None = None
        last_timestamp: datetime | None = None
        total_migrated = 0

        if resume:
            last_id, last_timestamp, total_migrated = await get_checkpoint(conn)
            if last_id:
                logger.info(f"Resuming from checkpoint: {total_migrated} rows already migrated")
            else:
                logger.info("No checkpoint found, starting fresh")

        # Get total count
        total_count = await get_total_count(conn, (last_id, last_timestamp))
        remaining = total_count

        if remaining == 0:
            logger.info("No rows to migrate")
            return

        logger.info(f"Migration starting: {remaining} rows to migrate")
        if dry_run:
            logger.info("DRY RUN MODE - No data will be modified")

        start_time = time.time()
        batch_num = 0

        while remaining > 0 and not shutdown_requested:
            batch_start = time.time()

            rows, last_id, last_timestamp = await migrate_batch(conn, batch_size, (last_id, last_timestamp), dry_run)

            if not rows:
                break

            batch_count = len(rows)
            total_migrated += batch_count
            remaining -= batch_count
            batch_num += 1

            # Update checkpoint
            if not dry_run and last_id:
                await update_checkpoint(conn, last_id, last_timestamp, total_migrated)

            # Calculate ETA
            elapsed = time.time() - start_time
            if total_migrated > 0:
                rate = total_migrated / elapsed
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            else:
                eta_str = "calculating..."

            batch_time = time.time() - batch_start

            logger.info(
                f"Batch {batch_num}: {batch_count} rows ({batch_time:.2f}s) | "
                f"Progress: {total_migrated}/{total_count + total_migrated} | "
                f"Remaining: {remaining} | ETA: {eta_str}"
            )

            # Delay between batches to reduce load
            if batch_delay > 0 and remaining > 0:
                await asyncio.sleep(batch_delay)

        if shutdown_requested:
            logger.info("Migration paused. Run with --resume to continue.")
        else:
            elapsed = time.time() - start_time
            logger.info(f"Migration complete: {total_migrated} rows in {elapsed:.1f}s ({total_migrated / elapsed:.1f} rows/s)")

            if not dry_run:
                logger.info(
                    "\nNext steps:\n"
                    "1. Verify data: SELECT COUNT(*) FROM audit_logs_partitioned;\n"
                    "2. Update application to use audit_logs_partitioned\n"
                    "3. When ready, rename tables:\n"
                    "   ALTER TABLE audit_logs RENAME TO audit_logs_legacy;\n"
                    "   ALTER TABLE audit_logs_partitioned RENAME TO audit_logs;\n"
                    "4. After verification period, drop legacy table:\n"
                    "   DROP TABLE audit_logs_legacy;"
                )

    finally:
        await conn.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate audit logs to partitioned table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of rows per batch (default: 1000)",
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=0.1,
        help="Delay between batches in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without making changes",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )

    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run migration
    asyncio.run(
        run_migration(
            batch_size=args.batch_size,
            batch_delay=args.batch_delay,
            dry_run=args.dry_run,
            resume=args.resume,
        )
    )


if __name__ == "__main__":
    main()
