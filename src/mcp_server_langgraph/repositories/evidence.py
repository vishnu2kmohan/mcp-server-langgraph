"""
Evidence Repository

Abstract interface and in-memory implementation for SOC 2 compliance report storage.
Supports Postgres backend via PostgresEvidenceRepository (separate module).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.compliance.soc2.evidence import ComplianceReport


class EvidenceRepository(ABC):
    """Abstract base class for evidence repository."""

    @abstractmethod
    async def save_report(self, report: ComplianceReport) -> None:
        """Save or upsert a compliance report.

        Args:
            report: The compliance report to store (upserts by report_id)
        """
        pass

    @abstractmethod
    async def get_report(self, report_id: str) -> ComplianceReport | None:
        """Get a compliance report by ID.

        Args:
            report_id: The report ID to retrieve

        Returns:
            The report if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_reports(
        self,
        *,
        report_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ComplianceReport]:
        """List compliance reports with optional filtering and pagination.

        Args:
            report_type: Optional report type filter (daily, weekly, monthly)
            limit: Maximum number of reports to return
            offset: Number of reports to skip

        Returns:
            List of reports sorted by generated_at DESC
        """
        pass

    @abstractmethod
    async def delete_reports_by_user(self, user_id: str) -> int:
        """Delete all reports referencing a user (GDPR deletion).

        Args:
            user_id: The user ID whose reports should be deleted

        Returns:
            Count of deleted reports
        """
        pass


class InMemoryEvidenceRepository(EvidenceRepository):
    """In-memory implementation for testing."""

    def __init__(self) -> None:
        self._reports: dict[str, ComplianceReport] = {}

    async def save_report(self, report: ComplianceReport) -> None:
        self._reports[report.report_id] = report

    async def get_report(self, report_id: str) -> ComplianceReport | None:
        return self._reports.get(report_id)

    async def list_reports(
        self,
        *,
        report_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ComplianceReport]:
        reports = list(self._reports.values())
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        # Sort by generated_at DESC
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        return reports[offset : offset + limit]

    async def delete_reports_by_user(self, user_id: str) -> int:
        # InMemory reports don't track user_id at this level
        return 0
