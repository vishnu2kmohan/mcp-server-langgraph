"""
Tests for Evidence Repository

TDD: These tests define the contract for storing and retrieving SOC 2 compliance reports.
Supports both InMemory (testing) and Postgres (production) implementations.
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime, timedelta

import pytest

from mcp_server_langgraph.compliance.soc2.evidence import ComplianceReport

pytestmark = [pytest.mark.unit, pytest.mark.repository]


def _make_report(
    report_id: str = "soc2_daily_20250101",
    report_type: str = "daily",
    compliance_score: float = 95.0,
    user_id: str | None = None,
    generated_at: str | None = None,
) -> ComplianceReport:
    """Create a test compliance report with sensible defaults."""
    now = generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return ComplianceReport(
        report_id=report_id,
        report_type=report_type,
        generated_at=now,
        period_start=(datetime.now(UTC) - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        period_end=now,
        evidence_items=[],
        summary={"compliance_percentage": f"{compliance_score:.1f}%"},
        compliance_score=compliance_score,
        passed_controls=9,
        failed_controls=0,
        partial_controls=1,
        total_controls=10,
    )


@pytest.fixture
def in_memory_repo():
    """Create an in-memory evidence repository for testing."""
    from mcp_server_langgraph.repositories.evidence import InMemoryEvidenceRepository

    return InMemoryEvidenceRepository()


class TestEvidenceRepositoryInterface:
    """Tests for EvidenceRepository abstract interface."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_repository_base_class_exists(self) -> None:
        from mcp_server_langgraph.repositories.evidence import EvidenceRepository

        assert EvidenceRepository is not None

    def test_abstract_methods_defined(self) -> None:
        from mcp_server_langgraph.repositories.evidence import EvidenceRepository

        expected = {"save_report", "get_report", "list_reports", "delete_reports_by_user"}
        assert expected.issubset(EvidenceRepository.__abstractmethods__)


class TestInMemoryEvidenceRepository:
    """Tests for InMemoryEvidenceRepository."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_save_and_get_report(self, in_memory_repo) -> None:
        report = _make_report()
        await in_memory_repo.save_report(report)

        result = await in_memory_repo.get_report(report.report_id)
        assert result is not None
        assert result.report_id == report.report_id
        assert result.compliance_score == 95.0

    @pytest.mark.asyncio
    async def test_get_report_returns_none_for_missing(self, in_memory_repo) -> None:
        result = await in_memory_repo.get_report("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_report_upserts(self, in_memory_repo) -> None:
        """Reports can be regenerated — save should upsert by report_id."""
        report1 = _make_report(report_id="r1", compliance_score=90.0)
        await in_memory_repo.save_report(report1)

        report2 = _make_report(report_id="r1", compliance_score=95.0)
        await in_memory_repo.save_report(report2)

        result = await in_memory_repo.get_report("r1")
        assert result is not None
        assert result.compliance_score == 95.0

    @pytest.mark.asyncio
    async def test_list_reports_returns_all(self, in_memory_repo) -> None:
        for i in range(3):
            await in_memory_repo.save_report(_make_report(report_id=f"r-{i}"))

        reports = await in_memory_repo.list_reports()
        assert len(reports) == 3

    @pytest.mark.asyncio
    async def test_list_reports_filters_by_type(self, in_memory_repo) -> None:
        await in_memory_repo.save_report(_make_report(report_id="r1", report_type="daily"))
        await in_memory_repo.save_report(_make_report(report_id="r2", report_type="daily"))
        await in_memory_repo.save_report(_make_report(report_id="r3", report_type="weekly"))

        reports = await in_memory_repo.list_reports(report_type="daily")
        assert len(reports) == 2
        assert all(r.report_type == "daily" for r in reports)

    @pytest.mark.asyncio
    async def test_list_reports_with_limit(self, in_memory_repo) -> None:
        for i in range(5):
            await in_memory_repo.save_report(_make_report(report_id=f"r-{i}"))

        reports = await in_memory_repo.list_reports(limit=3)
        assert len(reports) == 3

    @pytest.mark.asyncio
    async def test_list_reports_with_offset(self, in_memory_repo) -> None:
        for i in range(5):
            await in_memory_repo.save_report(_make_report(report_id=f"r-{i}"))

        reports = await in_memory_repo.list_reports(offset=3)
        assert len(reports) == 2

    @pytest.mark.asyncio
    async def test_list_reports_sorted_by_generated_at_desc(self, in_memory_repo) -> None:
        base = datetime(2025, 1, 1, tzinfo=UTC)
        await in_memory_repo.save_report(
            _make_report(
                report_id="oldest",
                generated_at=base.isoformat().replace("+00:00", "Z"),
            )
        )
        await in_memory_repo.save_report(
            _make_report(
                report_id="newest",
                generated_at=(base + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            )
        )

        reports = await in_memory_repo.list_reports()
        assert reports[0].report_id == "newest"

    @pytest.mark.asyncio
    async def test_delete_reports_by_user_not_implemented_returns_zero(self, in_memory_repo) -> None:
        """InMemory reports don't track user_id — delete_by_user returns 0."""
        count = await in_memory_repo.delete_reports_by_user("user-A")
        assert count == 0
