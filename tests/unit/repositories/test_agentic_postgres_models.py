"""
Tests for Agentic Postgres Models

TDD: Verify model instantiation, column defaults, and table configuration.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.repository]


class TestNoteModel:
    """Tests for NoteModel ORM class."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_note_model_class_is_importable(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import NoteModel

        assert NoteModel is not None

    def test_note_model_tablename_is_notes(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import NoteModel

        assert NoteModel.__tablename__ == "notes"

    def test_has_required_columns(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import NoteModel

        columns = {c.name for c in NoteModel.__table__.columns}
        expected = {
            "id",
            "content",
            "category",
            "tags",
            "created_at",
            "metadata_json",
            "session_id",
            "user_id",
            "title",
            "slug",
            "search_vector",
        }
        assert expected.issubset(columns)

    def test_has_gin_indices(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import NoteModel

        index_names = {idx.name for idx in NoteModel.__table__.indexes}
        assert "ix_notes_tags" in index_names
        assert "ix_notes_search_vector" in index_names


class TestPhaseCheckpointModel:
    """Tests for PhaseCheckpointModel ORM class."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_checkpoint_model_class_is_importable(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import PhaseCheckpointModel

        assert PhaseCheckpointModel is not None

    def test_checkpoint_model_tablename_is_phase_checkpoints(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import PhaseCheckpointModel

        assert PhaseCheckpointModel.__tablename__ == "phase_checkpoints"

    def test_has_required_columns(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import PhaseCheckpointModel

        columns = {c.name for c in PhaseCheckpointModel.__table__.columns}
        expected = {"id", "phase", "summary", "created_at", "artifacts", "metadata_json", "session_id", "user_id"}
        assert expected.issubset(columns)


class TestComplianceReportModel:
    """Tests for ComplianceReportModel ORM class."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_report_model_class_is_importable(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import ComplianceReportModel

        assert ComplianceReportModel is not None

    def test_report_model_tablename_is_compliance_reports(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import ComplianceReportModel

        assert ComplianceReportModel.__tablename__ == "compliance_reports"

    def test_has_required_columns(self) -> None:
        from mcp_server_langgraph.repositories.postgres_models.agentic import ComplianceReportModel

        columns = {c.name for c in ComplianceReportModel.__table__.columns}
        expected = {
            "report_id",
            "report_type",
            "generated_at",
            "period_start",
            "period_end",
            "evidence_items",
            "summary",
            "compliance_score",
            "passed_controls",
            "failed_controls",
            "partial_controls",
            "total_controls",
            "user_id",
        }
        assert expected.issubset(columns)
