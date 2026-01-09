"""Add decision_traces and decision_edges tables for context graphs.

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-01-08

This migration adds the context graph tables for capturing decision traces:
- decision_traces: Append-only log of agent decisions (the WHY)
- decision_edges: Graph edges connecting decisions to entities

Reference: ADR-0101 Context Graphs, Foundation Capital's Context Graph article
Features:
- Captures decision rationale for searchable precedent
- Enables feedback loops via outcome tracking
- OTEL correlation for distributed tracing
- Indexes optimized for common query patterns
- CASCADE delete on edges when trace is deleted
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "y5z6a7b8c9d0"
down_revision = "x4y5z6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create decision_traces and decision_edges tables for context graphs."""
    # Create decision_traces table (append-only decision log)
    op.create_table(
        "decision_traces",
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
            "run_id",
            sa.String(36),
            nullable=False,
            comment="LangGraph run ID for correlation",
        ),
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=False,
            comment="Session identifier",
        ),
        sa.Column(
            "workflow_id",
            sa.String(255),
            nullable=True,
            comment="Workflow identifier (if applicable)",
        ),
        sa.Column(
            "project_id",
            sa.String(255),
            nullable=True,
            comment="Project identifier (e.g., 'project:backend')",
        ),
        sa.Column(
            "organization_id",
            sa.String(255),
            nullable=False,
            comment="Organization identifier (e.g., 'organization:acme')",
        ),
        sa.Column(
            "user_id",
            sa.String(255),
            nullable=False,
            comment="User identifier (e.g., 'user:alice')",
        ),
        # Temporal
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the decision was made (UTC)",
        ),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Sequential order within session",
        ),
        # Decision classification
        sa.Column(
            "decision_type",
            sa.String(50),
            nullable=False,
            comment="Decision type: routing, tool_selection, skill_selection, model_selection, response, approval, exception",
        ),
        sa.Column(
            "decision_stage",
            sa.String(50),
            nullable=False,
            comment="Pipeline stage: context_gathering, policy_check, action, write",
        ),
        # Input context (truncated)
        sa.Column(
            "query_text",
            sa.Text(),
            nullable=False,
            comment="User query or input that triggered the decision (truncated to 500 chars)",
        ),
        sa.Column(
            "input_artifacts",
            postgresql.JSON(),
            nullable=True,
            comment="Input artifact references (e.g., file IDs, document IDs)",
        ),
        sa.Column(
            "available_options",
            postgresql.JSON(),
            nullable=True,
            comment="Options considered (e.g., tool names, skill names) - max 20",
        ),
        sa.Column(
            "constraints",
            postgresql.JSON(),
            nullable=True,
            comment="Active constraints/policies affecting the decision",
        ),
        # Decision output
        sa.Column(
            "chosen_action",
            sa.String(255),
            nullable=False,
            comment="The action/tool/skill that was chosen",
        ),
        sa.Column(
            "selected_items",
            postgresql.JSON(),
            nullable=True,
            comment="List of selected items if multiple (e.g., tools, skills) - max 20",
        ),
        sa.Column(
            "confidence",
            sa.Numeric(4, 3),
            nullable=False,
            comment="Confidence score for the decision (0.000-1.000)",
        ),
        # Reasoning (WHY - core value of context graphs)
        sa.Column(
            "rationale",
            sa.Text(),
            nullable=False,
            comment="Explanation for why this decision was made (truncated to 1000 chars)",
        ),
        sa.Column(
            "reasoning_chain",
            postgresql.JSON(),
            nullable=True,
            comment="Chain of thought steps (if available)",
        ),
        sa.Column(
            "policy_version",
            sa.String(100),
            nullable=True,
            comment="Version of policy/rules applied (for reproducibility)",
        ),
        sa.Column(
            "feature_flags_snapshot",
            postgresql.JSON(),
            nullable=True,
            comment="Relevant feature flags at decision time",
        ),
        # Approval (HITL)
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            server_default="false",
            comment="Whether this decision requires human approval",
        ),
        sa.Column(
            "approver_id",
            sa.String(255),
            nullable=True,
            comment="User who approved/rejected (e.g., 'user:manager')",
        ),
        sa.Column(
            "approval_status",
            sa.String(20),
            nullable=True,
            comment="Approval status: approved, rejected, pending, expired",
        ),
        sa.Column(
            "approval_rationale",
            sa.Text(),
            nullable=True,
            comment="Reason provided for approval/rejection",
        ),
        # Outcome (feedback loop)
        sa.Column(
            "outcome",
            sa.String(20),
            nullable=True,
            comment="Outcome: success, failure, partial, pending",
        ),
        sa.Column(
            "outcome_details",
            postgresql.JSON(),
            nullable=True,
            comment="Detailed outcome information (errors, metrics)",
        ),
        sa.Column(
            "user_feedback",
            sa.Text(),
            nullable=True,
            comment="User's explicit feedback on the decision",
        ),
        # Embedding text for semantic search
        sa.Column(
            "embedding_text",
            sa.Text(),
            nullable=True,
            comment="Generated text for embedding (query + rationale)",
        ),
        # OTEL correlation
        sa.Column(
            "otel_trace_id",
            sa.String(64),
            nullable=True,
            comment="OpenTelemetry trace ID for correlation",
        ),
        sa.Column(
            "otel_span_id",
            sa.String(32),
            nullable=True,
            comment="OpenTelemetry span ID for correlation",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trace_id"),
    )

    # Create indexes for decision_traces
    op.create_index("ix_decision_trace_id", "decision_traces", ["trace_id"])
    op.create_index("ix_decision_session", "decision_traces", ["session_id"])
    op.create_index("ix_decision_user", "decision_traces", ["user_id"])
    op.create_index("ix_decision_org", "decision_traces", ["organization_id"])
    op.create_index("ix_decision_type", "decision_traces", ["decision_type"])
    op.create_index("ix_decision_timestamp", "decision_traces", ["timestamp"])
    op.create_index(
        "ix_decision_session_seq",
        "decision_traces",
        ["session_id", "sequence_number"],
    )
    op.create_index(
        "ix_decision_org_time",
        "decision_traces",
        ["organization_id", "timestamp"],
    )
    op.create_index("ix_decision_outcome", "decision_traces", ["outcome"])

    # Create decision_edges table (graph edges)
    op.create_table(
        "decision_edges",
        # Primary key
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "edge_id",
            sa.String(36),
            nullable=False,
            comment="Unique edge identifier (UUID)",
        ),
        # FK to decision trace
        sa.Column(
            "trace_id",
            sa.String(36),
            nullable=False,
            comment="Reference to parent decision trace",
        ),
        # Source entity
        sa.Column(
            "source_type",
            sa.String(50),
            nullable=False,
            comment="Source entity type: session, workflow, project, user, decision",
        ),
        sa.Column(
            "source_id",
            sa.String(255),
            nullable=False,
            comment="Source entity identifier",
        ),
        # Target entity
        sa.Column(
            "target_type",
            sa.String(50),
            nullable=False,
            comment="Target entity type: tool, skill, model, artifact, decision",
        ),
        sa.Column(
            "target_id",
            sa.String(255),
            nullable=False,
            comment="Target entity identifier",
        ),
        # Relation
        sa.Column(
            "relation",
            sa.String(50),
            nullable=False,
            comment="Relation type: invoked, selected, produced, caused_by, approved_by",
        ),
        sa.Column(
            "weight",
            sa.Numeric(4, 3),
            server_default="1.0",
            comment="Edge weight for weighted graph operations (0.000-1.000)",
        ),
        sa.Column(
            "edge_metadata",
            postgresql.JSON(),
            nullable=True,
            comment="Additional edge metadata",
        ),
        # Timestamp
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the edge was created (UTC)",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edge_id"),
        sa.ForeignKeyConstraint(
            ["trace_id"],
            ["decision_traces.trace_id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes for decision_edges
    op.create_index("ix_edge_trace_id", "decision_edges", ["trace_id"])
    op.create_index(
        "ix_edge_source",
        "decision_edges",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_edge_target",
        "decision_edges",
        ["target_type", "target_id"],
    )
    op.create_index("ix_edge_relation", "decision_edges", ["relation"])


def downgrade() -> None:
    """Drop decision_traces and decision_edges tables."""
    # Drop decision_edges indexes
    op.drop_index("ix_edge_relation", table_name="decision_edges")
    op.drop_index("ix_edge_target", table_name="decision_edges")
    op.drop_index("ix_edge_source", table_name="decision_edges")
    op.drop_index("ix_edge_trace_id", table_name="decision_edges")

    # Drop decision_edges table
    op.drop_table("decision_edges")

    # Drop decision_traces indexes
    op.drop_index("ix_decision_outcome", table_name="decision_traces")
    op.drop_index("ix_decision_org_time", table_name="decision_traces")
    op.drop_index("ix_decision_session_seq", table_name="decision_traces")
    op.drop_index("ix_decision_timestamp", table_name="decision_traces")
    op.drop_index("ix_decision_type", table_name="decision_traces")
    op.drop_index("ix_decision_org", table_name="decision_traces")
    op.drop_index("ix_decision_user", table_name="decision_traces")
    op.drop_index("ix_decision_session", table_name="decision_traces")
    op.drop_index("ix_decision_trace_id", table_name="decision_traces")

    # Drop decision_traces table
    op.drop_table("decision_traces")
