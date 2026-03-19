"""
Legacy Data Migration Utility

Migrates file-based runtime state to repository backends:
- ./NOTES.json → NotesRepository
- ./checkpoints/checkpoints.json → CheckpointRepository
- ./agent_state/sessions.json → AgentStateRepository
- ./evidence/*.json → EvidenceRepository

Usage:
    uv run python -m mcp_server_langgraph.migrations.import_legacy_data
    uv run python -m mcp_server_langgraph.migrations.import_legacy_data --dry-run
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.success + self.skipped + self.failed


class LegacyDataImporter:
    """Imports legacy file-based data into repository backends.

    Reads from CWD-relative locations and inserts into target repositories.
    Idempotent: skips existing entries by ID.
    """

    def __init__(self, base_dir: Path, dry_run: bool = False) -> None:
        self.base_dir = base_dir
        self.dry_run = dry_run

    async def import_notes(self, repo: Any) -> MigrationResult:
        """Import notes from NOTES.json.

        Args:
            repo: NotesRepository instance

        Returns:
            MigrationResult with counts
        """
        from mcp_server_langgraph.memory.notes import Note

        result = MigrationResult()
        notes_file = self.base_dir / "NOTES.json"

        if not notes_file.exists():
            logger.info("No NOTES.json found at %s, skipping", notes_file)
            return result

        try:
            raw_data = json.loads(notes_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            result.failed += 1
            result.errors.append(f"Failed to read NOTES.json: {e}")
            return result

        for entry in raw_data:
            try:
                note = Note(**entry)
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Invalid note entry: {e}")
                logger.warning("Skipping invalid note entry: %s", e)
                continue

            # Check if already exists
            existing = await repo.get(note.id)
            if existing is not None:
                result.skipped += 1
                logger.debug("Skipping existing note: %s", note.id)
                continue

            if not self.dry_run:
                await repo.create(note)

            result.success += 1
            logger.info("Imported note: %s", note.id)

        return result

    async def import_checkpoints(self, repo: Any) -> MigrationResult:
        """Import checkpoints from checkpoints/checkpoints.json.

        Args:
            repo: CheckpointRepository instance

        Returns:
            MigrationResult with counts
        """
        from mcp_server_langgraph.memory.checkpoints import Checkpoint

        result = MigrationResult()
        cp_file = self.base_dir / "checkpoints" / "checkpoints.json"

        if not cp_file.exists():
            logger.info("No checkpoints.json found at %s, skipping", cp_file)
            return result

        try:
            raw_data = json.loads(cp_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            result.failed += 1
            result.errors.append(f"Failed to read checkpoints.json: {e}")
            return result

        for entry in raw_data:
            try:
                checkpoint = Checkpoint(**entry)
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Invalid checkpoint entry: {e}")
                logger.warning("Skipping invalid checkpoint entry: %s", e)
                continue

            existing = await repo.get(checkpoint.id)
            if existing is not None:
                result.skipped += 1
                logger.debug("Skipping existing checkpoint: %s", checkpoint.id)
                continue

            if not self.dry_run:
                await repo.create(checkpoint)

            result.success += 1
            logger.info("Imported checkpoint: %s", checkpoint.id)

        return result

    async def import_agent_state(self, repo: Any) -> MigrationResult:
        """Import agent state from agent_state/sessions.json.

        Args:
            repo: AgentStateRepository instance

        Returns:
            MigrationResult with counts
        """
        result = MigrationResult()
        state_file = self.base_dir / "agent_state" / "sessions.json"

        if not state_file.exists():
            logger.info("No sessions.json found at %s, skipping", state_file)
            return result

        try:
            raw_data = json.loads(state_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            result.failed += 1
            result.errors.append(f"Failed to read sessions.json: {e}")
            return result

        if not isinstance(raw_data, dict):
            result.failed += 1
            result.errors.append("sessions.json should be a dict of session_id -> state")
            return result

        for session_id, state in raw_data.items():
            existing = await repo.get(session_id)
            if existing is not None:
                result.skipped += 1
                logger.debug("Skipping existing session: %s", session_id)
                continue

            if not self.dry_run:
                await repo.save(session_id, state)

            result.success += 1
            logger.info("Imported agent state: %s", session_id)

        return result

    async def import_evidence(self, repo: Any) -> MigrationResult:
        """Import evidence reports from evidence/*.json.

        Args:
            repo: EvidenceRepository instance

        Returns:
            MigrationResult with counts
        """
        from mcp_server_langgraph.compliance.soc2.evidence import ComplianceReport

        result = MigrationResult()
        evidence_dir = self.base_dir / "evidence"

        if not evidence_dir.exists():
            logger.info("No evidence directory found at %s, skipping", evidence_dir)
            return result

        for json_file in sorted(evidence_dir.glob("*.json")):
            try:
                raw_data = json.loads(json_file.read_text())
            except (json.JSONDecodeError, OSError) as e:
                result.failed += 1
                result.errors.append(f"Failed to read {json_file.name}: {e}")
                logger.warning("Skipping unreadable evidence file: %s", json_file.name)
                continue

            try:
                report = ComplianceReport(**raw_data)
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Invalid evidence entry in {json_file.name}: {e}")
                logger.warning("Skipping invalid evidence file: %s (%s)", json_file.name, e)
                continue

            existing = await repo.get_report(report.report_id)
            if existing is not None:
                result.skipped += 1
                logger.debug("Skipping existing report: %s", report.report_id)
                continue

            if not self.dry_run:
                await repo.save_report(report)

            result.success += 1
            logger.info("Imported evidence report: %s", report.report_id)

        return result

    async def import_all(
        self,
        notes_repo: Any,
        checkpoint_repo: Any,
        agent_state_repo: Any,
        evidence_repo: Any,
    ) -> dict[str, MigrationResult]:
        """Run all importers.

        Args:
            notes_repo: NotesRepository instance
            checkpoint_repo: CheckpointRepository instance
            agent_state_repo: AgentStateRepository instance
            evidence_repo: EvidenceRepository instance

        Returns:
            Dict mapping artifact type to MigrationResult
        """
        summary: dict[str, MigrationResult] = {}

        summary["notes"] = await self.import_notes(notes_repo)
        summary["checkpoints"] = await self.import_checkpoints(checkpoint_repo)
        summary["agent_state"] = await self.import_agent_state(agent_state_repo)
        summary["evidence"] = await self.import_evidence(evidence_repo)

        for artifact_type, result in summary.items():
            logger.info(
                "Migration summary [%s]: success=%d, skipped=%d, failed=%d",
                artifact_type,
                result.success,
                result.skipped,
                result.failed,
            )

        return summary
