"""Add execution_plans table.

Revision ID: d0e1f2g3h4i5
Revises: c9d0e1f2g3h4
Create Date: 2026-01-28

This migration creates the execution_plans table for storing execution plans
that may require user approval before execution.

Features:
- Full plan lifecycle tracking (awaiting_approval → approved/rejected → executed/expired)
- Risk-based approval requirements
- Cost estimation and tracking
- Orchestrator configuration
- Thinking budget and critique rounds
- Timestamps for auditing

Related Models:
- ExecutionPlan (core/models/execution_plan.py)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "d0e1f2g3h4i5"
down_revision = "c9d0e1f2g3h4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create execution_plans table."""

    # Create status enum type
    status_enum = postgresql.ENUM(
        "awaiting_approval",
        "approved",
        "rejected",
        "executed",
        "expired",
        name="execution_plan_status",
        create_type=False,  # We create manually below
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    # Create complexity enum type
    complexity_enum = postgresql.ENUM(
        "simple",
        "complicated",
        "complex",
        name="execution_plan_complexity",
        create_type=False,  # We create manually below
    )
    complexity_enum.create(op.get_bind(), checkfirst=True)

    # Create risk_level enum type
    risk_enum = postgresql.ENUM(
        "low",
        "medium",
        "high",
        name="execution_plan_risk_level",
        create_type=False,  # We create manually below
    )
    risk_enum.create(op.get_bind(), checkfirst=True)

    # Create task_type enum type
    task_type_enum = postgresql.ENUM(
        "chat",
        "code",
        "analysis",
        "data",
        "ops",
        "other",
        name="execution_plan_task_type",
        create_type=False,  # We create manually below
    )
    task_type_enum.create(op.get_bind(), checkfirst=True)

    # Create orchestrator enum type
    orchestrator_enum = postgresql.ENUM(
        "standard",
        "swarm",
        "studio",
        "ux",
        "alert",
        name="execution_plan_orchestrator",
        create_type=False,  # We create manually below
    )
    orchestrator_enum.create(op.get_bind(), checkfirst=True)

    # Create thinking_budget enum type
    thinking_budget_enum = postgresql.ENUM(
        "none",
        "light",
        "medium",
        "deep",
        name="execution_plan_thinking_budget",
        create_type=False,  # We create manually below
    )
    thinking_budget_enum.create(op.get_bind(), checkfirst=True)

    # Create execution_plans table
    op.create_table(
        "execution_plans",
        # Primary key
        sa.Column("plan_id", sa.String(36), primary_key=True),
        # Foreign key to sessions
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Status and classification
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default="awaiting_approval",
            index=True,
        ),
        sa.Column("complexity", complexity_enum, nullable=False),
        sa.Column("risk_level", risk_enum, nullable=False, index=True),
        sa.Column("task_type", task_type_enum, nullable=False),
        # Model configuration
        sa.Column("executor_model", sa.String(255), nullable=False),
        sa.Column("critic_model", sa.String(255), nullable=True),
        # Cost tracking
        sa.Column("estimated_cost", sa.Numeric(10, 4), nullable=False),
        sa.Column("actual_cost", sa.Numeric(10, 4), nullable=True),
        # Content
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("tools_needed", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        # Approval configuration
        sa.Column("force_approval", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        # Orchestrator configuration
        sa.Column(
            "suggested_orchestrator",
            orchestrator_enum,
            nullable=False,
            server_default="standard",
        ),
        sa.Column("critique_rounds", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "thinking_budget",
            thinking_budget_enum,
            nullable=False,
            server_default="none",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Approval/rejection tracking
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(255), nullable=True),
        sa.Column("rejected_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
    )

    # Create composite index for common queries (session + status)
    op.create_index(
        "ix_execution_plans_session_status",
        "execution_plans",
        ["session_id", "status"],
    )

    # Create index for expiry checks
    op.create_index(
        "ix_execution_plans_expires_at",
        "execution_plans",
        ["expires_at"],
        postgresql_where=sa.text("status = 'awaiting_approval'"),
    )


def downgrade() -> None:
    """Drop execution_plans table and enum types."""
    op.drop_table("execution_plans")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS execution_plan_status")
    op.execute("DROP TYPE IF EXISTS execution_plan_complexity")
    op.execute("DROP TYPE IF EXISTS execution_plan_risk_level")
    op.execute("DROP TYPE IF EXISTS execution_plan_task_type")
    op.execute("DROP TYPE IF EXISTS execution_plan_orchestrator")
    op.execute("DROP TYPE IF EXISTS execution_plan_thinking_budget")
