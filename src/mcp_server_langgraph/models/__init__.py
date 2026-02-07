"""
SQLAlchemy Models

Provides SQLAlchemy ORM models for:
- Projects (Unified Workspace Paradigm)
- MCP Connections (OAuth2 and API Key authentication)
- Audit Logs (Regulatory compliance: GDPR, HIPAA, SOC2, FedRAMP, EU AI Act)
- Session Goals (user goal tracking)
- Database Connections (SQL execution)
- Unified Audit (partitioned audit logging)

Importing this module registers all model tables on Base.metadata,
enabling Alembic autogenerate to discover all tables.
"""

from mcp_server_langgraph.models.base import Base
from mcp_server_langgraph.models.audit_log import (
    AuditLogModel,
    UnifiedAuditLog,
)
from mcp_server_langgraph.models.connection import (
    MCPConnectionModel,
    OAuth2StateModel,
)
from mcp_server_langgraph.models.database_connection import DatabaseConnection
from mcp_server_langgraph.models.project import (
    ProjectConnectionModel,
    ProjectMemberModel,
    ProjectModel,
    ProjectSessionModel,
    ProjectWorkflowModel,
)
from mcp_server_langgraph.models.session_goal import SessionGoal
from mcp_server_langgraph.models.unified_audit import UnifiedAuditModel

__all__ = [
    "Base",
    # Audit models
    "AuditLogModel",
    "UnifiedAuditLog",
    # Connection models
    "MCPConnectionModel",
    "OAuth2StateModel",
    # Database connection models
    "DatabaseConnection",
    # Project models
    "ProjectConnectionModel",
    "ProjectMemberModel",
    "ProjectModel",
    "ProjectSessionModel",
    "ProjectWorkflowModel",
    # Session goal models
    "SessionGoal",
    # Unified audit models (partitioned table: audit_logs_partitioned)
    "UnifiedAuditModel",
]
