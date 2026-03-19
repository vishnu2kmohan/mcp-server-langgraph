"""
PostgreSQL Implementation of Evidence Repository.

Uses SQLAlchemy AsyncSession for async database operations.
Supports upsert by report_id (reports can be regenerated).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from mcp_server_langgraph.compliance.soc2.evidence import ComplianceReport, Evidence
from mcp_server_langgraph.repositories.evidence import EvidenceRepository
from mcp_server_langgraph.repositories.postgres_models.agentic import ComplianceReportModel

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Any]


class PostgresEvidenceRepository(EvidenceRepository):
    """PostgreSQL implementation of evidence repository."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def _model_to_pydantic(self, model: ComplianceReportModel) -> ComplianceReport:
        # Reconstruct Evidence items from JSONB
        evidence_items = []
        if isinstance(model.evidence_items, list):
            for item in model.evidence_items:
                try:
                    evidence_items.append(Evidence(**item))
                except Exception as e:
                    logger.warning("Skipping malformed evidence item in report %s: %s", model.report_id, e)

        return ComplianceReport(
            report_id=model.report_id,
            report_type=model.report_type,
            generated_at=model.generated_at,
            period_start=model.period_start,
            period_end=model.period_end,
            evidence_items=evidence_items,
            summary=model.summary if isinstance(model.summary, dict) else {},
            compliance_score=model.compliance_score,
            passed_controls=model.passed_controls,
            failed_controls=model.failed_controls,
            partial_controls=model.partial_controls,
            total_controls=model.total_controls,
        )

    async def save_report(self, report: ComplianceReport) -> None:
        async with self._session_factory() as session:
            # Upsert: insert or update on conflict
            values = {
                "report_id": report.report_id,
                "report_type": report.report_type,
                "generated_at": report.generated_at,
                "period_start": report.period_start,
                "period_end": report.period_end,
                "evidence_items": [e.model_dump(mode="json") for e in report.evidence_items],
                "summary": report.summary,
                "compliance_score": report.compliance_score,
                "passed_controls": report.passed_controls,
                "failed_controls": report.failed_controls,
                "partial_controls": report.partial_controls,
                "total_controls": report.total_controls,
            }

            stmt = insert(ComplianceReportModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["report_id"],
                set_={k: v for k, v in values.items() if k != "report_id"},
            )
            await session.execute(stmt)
            await session.commit()

    async def get_report(self, report_id: str) -> ComplianceReport | None:
        async with self._session_factory() as session:
            result = await session.execute(select(ComplianceReportModel).where(ComplianceReportModel.report_id == report_id))
            model = result.scalar_one_or_none()
            return self._model_to_pydantic(model) if model else None

    async def list_reports(
        self,
        *,
        report_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ComplianceReport]:
        async with self._session_factory() as session:
            query = select(ComplianceReportModel)
            if report_type:
                query = query.where(ComplianceReportModel.report_type == report_type)
            query = query.order_by(ComplianceReportModel.generated_at.desc()).limit(limit).offset(offset)

            result = await session.execute(query)
            return [self._model_to_pydantic(m) for m in result.scalars().all()]

    async def delete_reports_by_user(self, user_id: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(delete(ComplianceReportModel).where(ComplianceReportModel.user_id == user_id))
            await session.commit()
            return result.rowcount
