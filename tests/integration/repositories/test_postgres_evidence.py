"""
Integration Tests for PostgresEvidenceRepository.

Tests the PostgreSQL implementation of the evidence repository
with real database connections.

Phase 4: PostgreSQL Repositories (SQLAlchemy AsyncSession)
"""

from __future__ import annotations

import gc
import socket
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from tests.constants import (
    TEST_POSTGRES_DB,
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.compliance.soc2.evidence import ComplianceReport

pytestmark = [pytest.mark.integration, pytest.mark.repository]


def create_test_report(
    report_type: str = "daily",
    compliance_score: float = 95.0,
) -> ComplianceReport:
    from mcp_server_langgraph.compliance.soc2.evidence import ComplianceReport

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return ComplianceReport(
        report_id=f"report-{uuid.uuid4().hex[:8]}",
        report_type=report_type,
        generated_at=now,
        period_start=now,
        period_end=now,
        evidence_items=[],
        summary={},
        compliance_score=compliance_score,
        passed_controls=10,
        failed_controls=0,
        partial_controls=1,
        total_controls=11,
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testpostgresevidencerepo")
@pytest.mark.skip_isolation_check
class TestPostgresEvidenceRepository:
    """Test PostgresEvidenceRepository with real PostgreSQL."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    async def async_engine(self):
        try:
            with socket.create_connection((TEST_POSTGRES_HOST, TEST_POSTGRES_PORT), timeout=2):
                pass
        except (ConnectionRefusedError, TimeoutError, OSError):
            pytest.skip(f"PostgreSQL not available at {TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}")

        import mcp_server_langgraph.repositories.postgres_models.agentic  # noqa: F401

        database_url = (
            f"postgresql+asyncpg://{TEST_POSTGRES_USER}:{TEST_POSTGRES_PASSWORD}"
            f"@{TEST_POSTGRES_HOST}:{TEST_POSTGRES_PORT}/{TEST_POSTGRES_DB}"
        )
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        yield engine
        await engine.dispose()

    @pytest.fixture
    async def repo(self, async_engine: AsyncEngine):
        from sqlalchemy import text

        from mcp_server_langgraph.repositories.postgres_evidence import PostgresEvidenceRepository

        async with async_engine.begin() as conn:
            await conn.execute(text("DELETE FROM compliance_reports"))

        session_factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
        return PostgresEvidenceRepository(session_factory)

    async def test_save_and_get_report(self, repo):
        report = create_test_report()
        await repo.save_report(report)

        retrieved = await repo.get_report(report.report_id)
        assert retrieved is not None
        assert retrieved.compliance_score == 95.0

    async def test_upsert_report(self, repo):
        report = create_test_report(compliance_score=90.0)
        await repo.save_report(report)

        report.compliance_score = 95.0
        await repo.save_report(report)

        retrieved = await repo.get_report(report.report_id)
        assert retrieved is not None
        assert retrieved.compliance_score == 95.0

    async def test_list_reports_by_type(self, repo):
        await repo.save_report(create_test_report(report_type="daily"))
        await repo.save_report(create_test_report(report_type="weekly"))

        daily = await repo.list_reports(report_type="daily")
        assert len(daily) >= 1
        assert all(r.report_type == "daily" for r in daily)

    async def test_list_reports_pagination(self, repo):
        for _ in range(5):
            await repo.save_report(create_test_report())

        page1 = await repo.list_reports(limit=2, offset=0)
        page2 = await repo.list_reports(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

    async def test_get_nonexistent_returns_none(self, repo):
        result = await repo.get_report("nonexistent-id")
        assert result is None
