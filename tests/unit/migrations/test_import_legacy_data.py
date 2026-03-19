"""
Unit tests for legacy data migration utility.

Tests the import_legacy_data module which migrates file-based runtime state
(NOTES.json, checkpoints.json, sessions.json, evidence/*.json) into
repository backends.
"""

import gc
import json

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_import_legacy_data")
class TestLegacyDataImporter:
    """Tests for LegacyDataImporter class."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_importer_class_exists(self) -> None:
        """LegacyDataImporter should be importable."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter

        assert LegacyDataImporter is not None

    def test_importer_accepts_base_dir(self, tmp_path) -> None:
        """Importer should accept a base directory."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter

        importer = LegacyDataImporter(base_dir=tmp_path)
        assert importer.base_dir == tmp_path

    def test_importer_accepts_dry_run_flag(self, tmp_path) -> None:
        """Importer should accept a dry_run flag."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter

        importer = LegacyDataImporter(base_dir=tmp_path, dry_run=True)
        assert importer.dry_run is True

    def test_importer_defaults_dry_run_false(self, tmp_path) -> None:
        """Importer should default dry_run to False."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter

        importer = LegacyDataImporter(base_dir=tmp_path)
        assert importer.dry_run is False


@pytest.mark.xdist_group(name="test_import_legacy_data")
class TestImportNotes:
    """Tests for importing notes from NOTES.json."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_import_notes_from_json(self, tmp_path) -> None:
        """Should import notes from NOTES.json file."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

        # Create legacy NOTES.json
        notes_data = [
            {
                "id": "note-abc123",
                "content": "Test note content",
                "category": "research",
                "tags": ["ai", "safety"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "metadata": {},
            }
        ]
        notes_file = tmp_path / "NOTES.json"
        notes_file.write_text(json.dumps(notes_data))

        repo = InMemoryNotesRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_notes(repo)

        assert result.success == 1
        assert result.skipped == 0
        assert result.failed == 0

        # Verify note was imported
        note = await repo.get("note-abc123")
        assert note is not None
        assert note.content == "Test note content"
        assert note.category == "research"

    @pytest.mark.asyncio
    async def test_import_notes_skips_existing(self, tmp_path) -> None:
        """Should skip notes that already exist in the repository."""
        from mcp_server_langgraph.memory.notes import Note
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

        notes_data = [
            {
                "id": "note-existing",
                "content": "Already exists",
                "category": "general",
                "tags": [],
                "created_at": "2026-01-01T00:00:00+00:00",
                "metadata": {},
            }
        ]
        notes_file = tmp_path / "NOTES.json"
        notes_file.write_text(json.dumps(notes_data))

        repo = InMemoryNotesRepository()
        # Pre-insert the note
        await repo.create(Note(id="note-existing", content="Already exists", category="general"))

        importer = LegacyDataImporter(base_dir=tmp_path)
        result = await importer.import_notes(repo)

        assert result.success == 0
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_import_notes_handles_missing_file(self, tmp_path) -> None:
        """Should handle missing NOTES.json gracefully."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

        repo = InMemoryNotesRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_notes(repo)

        assert result.success == 0
        assert result.skipped == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_import_notes_handles_invalid_entry(self, tmp_path) -> None:
        """Should skip invalid note entries and continue."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

        notes_data = [
            {"invalid": "entry"},  # Missing required fields
            {
                "id": "note-valid",
                "content": "Valid note",
                "category": "general",
                "tags": [],
                "created_at": "2026-01-01T00:00:00+00:00",
                "metadata": {},
            },
        ]
        notes_file = tmp_path / "NOTES.json"
        notes_file.write_text(json.dumps(notes_data))

        repo = InMemoryNotesRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_notes(repo)

        assert result.success == 1
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_import_notes_dry_run(self, tmp_path) -> None:
        """Dry run should not actually import notes."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

        notes_data = [
            {
                "id": "note-dry",
                "content": "Dry run note",
                "category": "general",
                "tags": [],
                "created_at": "2026-01-01T00:00:00+00:00",
                "metadata": {},
            }
        ]
        notes_file = tmp_path / "NOTES.json"
        notes_file.write_text(json.dumps(notes_data))

        repo = InMemoryNotesRepository()
        importer = LegacyDataImporter(base_dir=tmp_path, dry_run=True)

        result = await importer.import_notes(repo)

        assert result.success == 1  # Counted as would-be-imported

        # But not actually in repo
        note = await repo.get("note-dry")
        assert note is None


@pytest.mark.xdist_group(name="test_import_legacy_data")
class TestImportCheckpoints:
    """Tests for importing checkpoints from checkpoints.json."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_import_checkpoints_from_json(self, tmp_path) -> None:
        """Should import checkpoints from checkpoints/checkpoints.json."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository

        cp_dir = tmp_path / "checkpoints"
        cp_dir.mkdir()
        cp_data = [
            {
                "id": "cp-001",
                "phase": "research",
                "summary": "Completed research phase",
                "created_at": "2026-01-01T00:00:00+00:00",
                "artifacts": [],
                "metadata": {},
            }
        ]
        (cp_dir / "checkpoints.json").write_text(json.dumps(cp_data))

        repo = InMemoryCheckpointRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_checkpoints(repo)

        assert result.success == 1
        checkpoint = await repo.get("cp-001")
        assert checkpoint is not None
        assert checkpoint.phase == "research"

    @pytest.mark.asyncio
    async def test_import_checkpoints_skips_existing(self, tmp_path) -> None:
        """Should skip checkpoints that already exist."""
        from mcp_server_langgraph.memory.checkpoints import Checkpoint
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository

        cp_dir = tmp_path / "checkpoints"
        cp_dir.mkdir()
        cp_data = [
            {
                "id": "cp-existing",
                "phase": "research",
                "summary": "Already exists",
                "created_at": "2026-01-01T00:00:00+00:00",
                "artifacts": [],
                "metadata": {},
            }
        ]
        (cp_dir / "checkpoints.json").write_text(json.dumps(cp_data))

        repo = InMemoryCheckpointRepository()
        await repo.create(Checkpoint(id="cp-existing", phase="research", summary="Already exists"))

        importer = LegacyDataImporter(base_dir=tmp_path)
        result = await importer.import_checkpoints(repo)

        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_import_checkpoints_handles_missing_file(self, tmp_path) -> None:
        """Should handle missing checkpoints.json gracefully."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository

        repo = InMemoryCheckpointRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_checkpoints(repo)

        assert result.success == 0


@pytest.mark.xdist_group(name="test_import_legacy_data")
class TestImportAgentState:
    """Tests for importing agent state from sessions.json."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_import_agent_state_from_json(self, tmp_path) -> None:
        """Should import agent state from agent_state/sessions.json."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.agent_state import InMemoryAgentStateRepository

        state_dir = tmp_path / "agent_state"
        state_dir.mkdir()
        state_data = {
            "session-1": {"last_query": "Hello", "progress": "50%"},
            "session-2": {"last_query": "Goodbye", "progress": "100%"},
        }
        (state_dir / "sessions.json").write_text(json.dumps(state_data))

        repo = InMemoryAgentStateRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_agent_state(repo)

        assert result.success == 2

        state = await repo.get("session-1")
        assert state is not None
        assert state["last_query"] == "Hello"

    @pytest.mark.asyncio
    async def test_import_agent_state_skips_existing(self, tmp_path) -> None:
        """Should skip sessions that already exist."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.agent_state import InMemoryAgentStateRepository

        state_dir = tmp_path / "agent_state"
        state_dir.mkdir()
        state_data = {"session-existing": {"last_query": "Test"}}
        (state_dir / "sessions.json").write_text(json.dumps(state_data))

        repo = InMemoryAgentStateRepository()
        await repo.save("session-existing", {"last_query": "Already here"})

        importer = LegacyDataImporter(base_dir=tmp_path)
        result = await importer.import_agent_state(repo)

        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_import_agent_state_handles_missing_file(self, tmp_path) -> None:
        """Should handle missing sessions.json gracefully."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.agent_state import InMemoryAgentStateRepository

        repo = InMemoryAgentStateRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_agent_state(repo)

        assert result.success == 0


@pytest.mark.xdist_group(name="test_import_legacy_data")
class TestImportEvidence:
    """Tests for importing evidence from evidence/*.json."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_import_evidence_from_json_files(self, tmp_path) -> None:
        """Should import evidence from evidence/*.json files."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.evidence import InMemoryEvidenceRepository

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()

        report_data = {
            "report_id": "daily_20260101",
            "report_type": "daily",
            "generated_at": "2026-01-01T00:00:00Z",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-01-01T23:59:59Z",
            "evidence_items": [],
            "summary": {},
            "compliance_score": 95.0,
            "passed_controls": 10,
            "failed_controls": 0,
            "partial_controls": 1,
            "total_controls": 11,
        }
        (evidence_dir / "daily_20260101.json").write_text(json.dumps(report_data))

        repo = InMemoryEvidenceRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_evidence(repo)

        assert result.success == 1

        report = await repo.get_report("daily_20260101")
        assert report is not None
        assert report.compliance_score == 95.0

    @pytest.mark.asyncio
    async def test_import_evidence_skips_existing(self, tmp_path) -> None:
        """Should skip reports that already exist."""
        from mcp_server_langgraph.compliance.soc2.evidence import ComplianceReport
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.evidence import InMemoryEvidenceRepository

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()

        report_data = {
            "report_id": "daily_existing",
            "report_type": "daily",
            "generated_at": "2026-01-01T00:00:00Z",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-01-01T23:59:59Z",
            "evidence_items": [],
            "summary": {},
            "compliance_score": 90.0,
            "passed_controls": 9,
            "failed_controls": 1,
            "partial_controls": 0,
            "total_controls": 10,
        }
        (evidence_dir / "daily_existing.json").write_text(json.dumps(report_data))

        repo = InMemoryEvidenceRepository()
        await repo.save_report(ComplianceReport(**report_data))

        importer = LegacyDataImporter(base_dir=tmp_path)
        result = await importer.import_evidence(repo)

        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_import_evidence_handles_missing_dir(self, tmp_path) -> None:
        """Should handle missing evidence directory gracefully."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.evidence import InMemoryEvidenceRepository

        repo = InMemoryEvidenceRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_evidence(repo)

        assert result.success == 0

    @pytest.mark.asyncio
    async def test_import_evidence_skips_non_json_files(self, tmp_path) -> None:
        """Should skip non-JSON files in evidence directory."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.evidence import InMemoryEvidenceRepository

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "readme.txt").write_text("Not a report")

        repo = InMemoryEvidenceRepository()
        importer = LegacyDataImporter(base_dir=tmp_path)

        result = await importer.import_evidence(repo)

        assert result.success == 0
        assert result.failed == 0


@pytest.mark.xdist_group(name="test_import_legacy_data")
class TestImportAll:
    """Tests for full migration run."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_import_all_runs_all_importers(self, tmp_path) -> None:
        """import_all should run notes, checkpoints, agent_state, and evidence importers."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.agent_state import InMemoryAgentStateRepository
        from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository
        from mcp_server_langgraph.repositories.evidence import InMemoryEvidenceRepository
        from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

        importer = LegacyDataImporter(base_dir=tmp_path)

        summary = await importer.import_all(
            notes_repo=InMemoryNotesRepository(),
            checkpoint_repo=InMemoryCheckpointRepository(),
            agent_state_repo=InMemoryAgentStateRepository(),
            evidence_repo=InMemoryEvidenceRepository(),
        )

        # All should report 0 (no files to import)
        assert "notes" in summary
        assert "checkpoints" in summary
        assert "agent_state" in summary
        assert "evidence" in summary

    @pytest.mark.asyncio
    async def test_import_all_with_data(self, tmp_path) -> None:
        """import_all should import data from all sources."""
        from mcp_server_langgraph.migrations.import_legacy_data import LegacyDataImporter
        from mcp_server_langgraph.repositories.agent_state import InMemoryAgentStateRepository
        from mcp_server_langgraph.repositories.checkpoint import InMemoryCheckpointRepository
        from mcp_server_langgraph.repositories.evidence import InMemoryEvidenceRepository
        from mcp_server_langgraph.repositories.notes import InMemoryNotesRepository

        # Create legacy files
        notes_data = [
            {
                "id": "note-1",
                "content": "Test",
                "category": "general",
                "tags": [],
                "created_at": "2026-01-01T00:00:00+00:00",
                "metadata": {},
            }
        ]
        (tmp_path / "NOTES.json").write_text(json.dumps(notes_data))

        cp_dir = tmp_path / "checkpoints"
        cp_dir.mkdir()
        cp_data = [
            {
                "id": "cp-1",
                "phase": "research",
                "summary": "Done",
                "created_at": "2026-01-01T00:00:00+00:00",
                "artifacts": [],
                "metadata": {},
            }
        ]
        (cp_dir / "checkpoints.json").write_text(json.dumps(cp_data))

        state_dir = tmp_path / "agent_state"
        state_dir.mkdir()
        state_data = {"session-1": {"progress": "50%"}}
        (state_dir / "sessions.json").write_text(json.dumps(state_data))

        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        report_data = {
            "report_id": "daily_1",
            "report_type": "daily",
            "generated_at": "2026-01-01T00:00:00Z",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-01-01T23:59:59Z",
            "evidence_items": [],
            "summary": {},
            "compliance_score": 95.0,
            "passed_controls": 10,
            "failed_controls": 0,
            "partial_controls": 1,
            "total_controls": 11,
        }
        (evidence_dir / "daily_1.json").write_text(json.dumps(report_data))

        notes_repo = InMemoryNotesRepository()
        cp_repo = InMemoryCheckpointRepository()
        state_repo = InMemoryAgentStateRepository()
        evidence_repo = InMemoryEvidenceRepository()

        importer = LegacyDataImporter(base_dir=tmp_path)
        summary = await importer.import_all(
            notes_repo=notes_repo,
            checkpoint_repo=cp_repo,
            agent_state_repo=state_repo,
            evidence_repo=evidence_repo,
        )

        assert summary["notes"].success == 1
        assert summary["checkpoints"].success == 1
        assert summary["agent_state"].success == 1
        assert summary["evidence"].success == 1


@pytest.mark.xdist_group(name="test_import_legacy_data")
class TestMigrationResult:
    """Tests for MigrationResult dataclass."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_migration_result_exists(self) -> None:
        """MigrationResult should be importable."""
        from mcp_server_langgraph.migrations.import_legacy_data import MigrationResult

        result = MigrationResult()
        assert result.success == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []

    def test_migration_result_total(self) -> None:
        """MigrationResult.total should sum success + skipped + failed."""
        from mcp_server_langgraph.migrations.import_legacy_data import MigrationResult

        result = MigrationResult(success=3, skipped=2, failed=1)
        assert result.total == 6
