"""Add langgraph_execution_traces table.

Revision ID: d1e2f3g4h5i6
Revises: c0d1e2f3g4h5
Create Date: 2026-02-01

Phase 4: Add table for persisting LangGraph node execution traces.

Purpose:
- Store LangGraph node execution events (router, planner, executor)
- Enable historical trace display in DevTools AgentTraceTab after page reload
- Support GDPR export/delete by user_id

Data Flow:
- Live: WebSocket `trace_step` messages to DevTools
- Persistence: Stored here for historical retrieval
- Query: `/api/v1/sessions/{id}/agent-execution-trace`

Fields:
- trace_id: Unique identifier (UUID)
- session_id, run_id, workflow_id: Context identifiers
- user_id, organization_id: GDPR compliance
- node_id, node_name, node_type: Node identification
- status: running, completed, failed, skipped
- start_time, end_time, duration_ms: Timing in epoch ms
- sequence_number: Order within session
- attributes: Additional metadata (JSONB)
- error_message: Error details if failed

Indexes:
- session_id: Primary query path for timeline
- user_id: GDPR export/delete
- created_at: Retention cleanup
- (session_id, sequence_number): Ordered timeline
"""

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3g4h5i6"
down_revision: str | None = "c0d1e2f3g4h5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create langgraph_execution_traces table."""
    op.create_table(
        "langgraph_execution_traces",
        # Primary key
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "trace_id",
            sa.String(36),
            nullable=False,
            comment="Unique trace identifier (UUID)",
        ),
        # Context identifiers
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=False,
            comment="Session identifier",
        ),
        sa.Column(
            "run_id",
            sa.String(36),
            nullable=False,
            comment="LangGraph run ID for correlation",
        ),
        sa.Column(
            "workflow_id",
            sa.String(255),
            nullable=True,
            comment="Optional workflow identifier",
        ),
        # GDPR compliance
        sa.Column(
            "user_id",
            sa.String(255),
            nullable=False,
            comment="User identifier for GDPR export/delete",
        ),
        sa.Column(
            "organization_id",
            sa.String(255),
            nullable=False,
            comment="Organization identifier for analytics",
        ),
        # Node execution data
        sa.Column(
            "node_id",
            sa.String(255),
            nullable=True,
            comment="Node identifier (may differ from name)",
        ),
        sa.Column(
            "node_name",
            sa.String(255),
            nullable=False,
            comment="Node name (router, planner, executor, etc.)",
        ),
        sa.Column(
            "node_type",
            sa.String(50),
            nullable=True,
            comment="Node type (default, conditional, etc.)",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            comment="Execution status: running, completed, failed, skipped",
        ),
        # Timing (epoch milliseconds)
        sa.Column(
            "start_time",
            sa.BigInteger(),
            nullable=False,
            comment="Start timestamp in epoch milliseconds",
        ),
        sa.Column(
            "end_time",
            sa.BigInteger(),
            nullable=True,
            comment="End timestamp in epoch milliseconds",
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Duration in milliseconds",
        ),
        # Ordering
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Sequential order within session",
        ),
        # Metadata
        sa.Column(
            "attributes",
            postgresql.JSON(),
            nullable=True,
            comment="Additional node attributes (JSON)",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message if status is 'failed'",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="When the record was created (UTC)",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trace_id"),
    )

    # Create indexes
    op.create_index(
        "ix_lget_session_id",
        "langgraph_execution_traces",
        ["session_id"],
    )
    op.create_index(
        "ix_lget_user_id",
        "langgraph_execution_traces",
        ["user_id"],
    )
    op.create_index(
        "ix_lget_org_id",
        "langgraph_execution_traces",
        ["organization_id"],
    )
    op.create_index(
        "ix_lget_created_at",
        "langgraph_execution_traces",
        ["created_at"],
    )
    op.create_index(
        "ix_lget_session_sequence",
        "langgraph_execution_traces",
        ["session_id", "sequence_number"],
    )


def downgrade() -> None:
    """Drop langgraph_execution_traces table."""
    # Drop indexes
    op.drop_index("ix_lget_session_sequence", table_name="langgraph_execution_traces")
    op.drop_index("ix_lget_created_at", table_name="langgraph_execution_traces")
    op.drop_index("ix_lget_org_id", table_name="langgraph_execution_traces")
    op.drop_index("ix_lget_user_id", table_name="langgraph_execution_traces")
    op.drop_index("ix_lget_session_id", table_name="langgraph_execution_traces")

    # Drop table
    op.drop_table("langgraph_execution_traces")
