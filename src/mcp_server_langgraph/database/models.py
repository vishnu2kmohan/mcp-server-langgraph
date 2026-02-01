"""
SQLAlchemy models for cost tracking and context graph persistence.

This module defines database models for storing:
- LLM token usage and cost metrics (TokenUsageRecord, BudgetRecord)
- Context graph decision traces (DecisionTrace, DecisionEdge)
- LangGraph execution traces (LangGraphExecutionTrace)

All models use PostgreSQL persistence with automatic retention policies.
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class TokenUsageRecord(Base):  # type: ignore[misc,valid-type]
    """
    Persistent storage for LLM token usage and cost data.

    This model stores detailed token usage metrics for cost tracking,
    budgeting, and analytics with automatic retention policies.

    Indexes:
        - timestamp: For time-range queries and retention cleanup
        - user_id: For per-user cost analysis
        - session_id: For per-session cost tracking
        - model: For per-model cost analysis
        - composite (user_id, timestamp): For efficient user cost queries

    Retention:
        Records are automatically purged after CONTEXT_RETENTION_DAYS (default: 90)
        via background cleanup job.
    """

    __tablename__ = "token_usage_records"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="When the LLM call was made (UTC)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When the record was created (UTC)",
    )

    # Identifiers
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="User identifier",
    )
    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Session identifier",
    )

    # Model information
    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Model name (e.g., claude-sonnet-4-5-20250929)",
    )
    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Provider name (e.g., anthropic, openai, google)",
    )

    # Token counts
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of input tokens",
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of output tokens",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Total tokens (prompt + completion)",
    )

    # Cost (stored as Decimal for precision)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        nullable=False,
        doc="Estimated cost in USD (6 decimal places for sub-cent precision)",
    )

    # Optional categorization
    feature: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Feature name (e.g., 'chat', 'summarization', 'context_compaction')",
    )

    # Metadata (stored as JSON)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # Column name in DB
        JSON,
        nullable=True,
        doc="Additional metadata (JSON)",
    )

    # Organizational hierarchy for multi-tenant cost attribution
    organization_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Organization ID for multi-tenant cost attribution (e.g., 'organization:acme')",
    )
    project_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Project ID for project-level cost breakdown (e.g., 'project:backend')",
    )
    team_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Team/group ID for team-level cost attribution (e.g., 'team:platform')",
    )

    # Custom cost allocation tags for flexible cost attribution
    allocation_tags: Mapped[dict[str, str] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Custom key-value tags for cost allocation (e.g., {'environment': 'production', 'campaign': 'launch-2025'})",
    )

    # Composite indexes for common queries
    __table_args__ = (
        # Existing indexes
        Index("ix_user_timestamp", "user_id", "timestamp"),
        Index("ix_provider_model", "provider", "model"),
        Index("ix_timestamp_desc", "timestamp", postgresql_ops={"timestamp": "DESC"}),
        # Organizational cost query indexes
        Index("ix_org_timestamp", "organization_id", "timestamp"),
        Index("ix_project_timestamp", "project_id", "timestamp"),
        Index("ix_team_user_timestamp", "team_id", "user_id", "timestamp"),
        Index("ix_org_project_team", "organization_id", "project_id", "team_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<TokenUsageRecord(id={self.id}, "
            f"user_id={self.user_id}, "
            f"model={self.model}, "
            f"tokens={self.total_tokens}, "
            f"cost=${self.estimated_cost_usd})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "created_at": self.created_at.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": str(self.estimated_cost_usd),
            "feature": self.feature,
            "metadata": self.metadata_,
            # Organizational hierarchy
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "team_id": self.team_id,
            # Custom allocation tags
            "allocation_tags": self.allocation_tags,
        }


class BudgetRecord(Base):  # type: ignore[misc,valid-type]
    """
    Persistent storage for budget configurations.

    Stores budget limits for organizations, projects, teams, and users
    to enable cost control and alerting.

    Entity Types:
        - organization: Company-wide budget limits
        - project: Per-project budget limits
        - team: Team-level budget limits
        - user: Individual user budget limits

    The entity_type + entity_id combination is unique (one budget per entity).
    """

    __tablename__ = "budget_records"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Entity identification (unique constraint on type + id)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Entity type: organization, project, team, user",
    )
    entity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Entity identifier (e.g., 'organization:acme', 'user:alice')",
    )

    # Budget configuration
    monthly_limit_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        doc="Monthly budget limit in USD",
    )
    warning_threshold: Mapped[float] = mapped_column(
        Numeric(precision=3, scale=2),
        nullable=False,
        insert_default=0.80,
        default=0.80,
        doc="Warning threshold as percentage (0.80 = 80%)",
    )
    critical_threshold: Mapped[float] = mapped_column(
        Numeric(precision=3, scale=2),
        nullable=False,
        insert_default=1.0,
        default=1.0,
        doc="Critical threshold as percentage (1.0 = 100%)",
    )

    # Metadata
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable budget name",
    )
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        doc="Budget description",
    )
    enabled: Mapped[bool] = mapped_column(
        default=True,
        doc="Whether budget monitoring is enabled",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When the budget was created (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        doc="When the budget was last updated (UTC)",
    )

    # Indexes
    __table_args__ = (
        # Unique constraint: one budget per entity
        Index("ix_budget_entity_type_id", "entity_type", "entity_id", unique=True),
        # For filtering by entity type
        Index("ix_budget_entity_type", "entity_type"),
        # For filtering enabled budgets
        Index("ix_budget_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        return f"<BudgetRecord(id={self.id}, entity={self.entity_id}, limit=${self.monthly_limit_usd})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "monthly_limit_usd": str(self.monthly_limit_usd),
            "warning_threshold": float(self.warning_threshold),
            "critical_threshold": float(self.critical_threshold),
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# Context Graph Decision Trace Models (ADR-0101)
# =============================================================================


class DecisionTrace(Base):  # type: ignore[misc,valid-type]
    """
    Append-only decision trace for context graphs.

    Captures the WHY behind every agent decision to enable:
    - Searchable precedent for similar situations
    - Audit trail for compliance (GDPR, SOC2, FedRAMP)
    - Feedback loops for continuous improvement
    - Cross-system synthesis of decision patterns

    Reference: ADR-0101 Context Graphs, Foundation Capital's Context Graph article

    Indexes:
        - trace_id: Unique identifier lookup
        - session_id: Per-session decision timeline
        - user_id: User's decision history (GDPR export/delete)
        - organization_id: Org-wide decision analytics
        - decision_type: Filter by decision category
        - timestamp: Time-range queries and retention
        - (session_id, sequence_number): Ordered session timeline
        - (organization_id, timestamp): Org analytics with time filter
        - outcome: Filter by decision success/failure

    Retention:
        Records are purged after FF_CONTEXT_GRAPH_RETENTION_DAYS (default: 2555 days)
        via schedulers/decision_retention.py background job.
    """

    __tablename__ = "decision_traces"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        doc="Unique trace identifier (UUID)",
    )

    # Context identifiers
    run_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        doc="LangGraph run ID for correlation",
    )
    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Session identifier",
    )
    workflow_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Workflow identifier (if applicable)",
    )
    project_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Project identifier (e.g., 'project:backend')",
    )
    organization_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Organization identifier (e.g., 'organization:acme')",
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User identifier (e.g., 'user:alice')",
    )

    # Temporal
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the decision was made (UTC)",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Sequential order within session",
    )

    # Decision classification
    decision_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Decision type: routing, tool_selection, skill_selection, model_selection, response, approval, exception",
    )
    decision_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Pipeline stage: context_gathering, policy_check, action, write",
    )

    # Input context (truncated to prevent bloat)
    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="User query or input that triggered the decision (truncated to 500 chars)",
    )
    input_artifacts: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Input artifact references (e.g., file IDs, document IDs)",
    )
    available_options: Mapped[list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Options considered (e.g., tool names, skill names) - max 20",
    )
    constraints: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Active constraints/policies affecting the decision",
    )

    # Decision output
    chosen_action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="The action/tool/skill that was chosen",
    )
    selected_items: Mapped[list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="List of selected items if multiple (e.g., tools, skills) - max 20",
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        nullable=False,
        doc="Confidence score for the decision (0.000-1.000)",
    )

    # Reasoning (WHY - the core value of context graphs)
    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Explanation for why this decision was made (truncated to 1000 chars)",
    )
    reasoning_chain: Mapped[list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Chain of thought steps (if available)",
    )
    policy_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Version of policy/rules applied (for reproducibility)",
    )
    feature_flags_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Relevant feature flags at decision time",
    )

    # Approval (HITL - Human-in-the-Loop)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="Whether this decision requires human approval",
    )
    approver_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="User who approved/rejected (e.g., 'user:manager')",
    )
    approval_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Approval status: approved, rejected, pending, expired",
    )
    approval_rationale: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Reason provided for approval/rejection",
    )

    # Outcome (feedback loop - was the decision good?)
    outcome: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        doc="Outcome: success, failure, partial, pending",
    )
    outcome_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Detailed outcome information (errors, metrics)",
    )
    user_feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="User's explicit feedback on the decision",
    )

    # Embedding text for semantic search (stored in Qdrant, not Postgres)
    embedding_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Generated text for embedding (query + rationale)",
    )

    # OTEL correlation for distributed tracing
    otel_trace_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="OpenTelemetry trace ID for correlation",
    )
    otel_span_id: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="OpenTelemetry span ID for correlation",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_decision_trace_id", "trace_id"),
        Index("ix_decision_session", "session_id"),
        Index("ix_decision_user", "user_id"),
        Index("ix_decision_org", "organization_id"),
        Index("ix_decision_type", "decision_type"),
        Index("ix_decision_timestamp", "timestamp"),
        Index("ix_decision_session_seq", "session_id", "sequence_number"),
        Index("ix_decision_org_time", "organization_id", "timestamp"),
        Index("ix_decision_outcome", "outcome"),
    )

    def __repr__(self) -> str:
        return (
            f"<DecisionTrace(trace_id={self.trace_id}, "
            f"decision_type={self.decision_type}, "
            f"chosen_action={self.chosen_action})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API/GDPR export."""
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "project_id": self.project_id,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "decision_type": self.decision_type,
            "decision_stage": self.decision_stage,
            "query_text": self.query_text,
            "chosen_action": self.chosen_action,
            "confidence": float(self.confidence) if self.confidence else None,
            "rationale": self.rationale,
            "outcome": self.outcome,
        }


class DecisionEdge(Base):  # type: ignore[misc,valid-type]
    """
    Graph edges connecting decisions to entities.

    Creates the graph structure in context graphs by linking decisions to:
    - Sessions, workflows, projects (context)
    - Tools, skills, models (capabilities)
    - Other decisions (causality)
    - Users, organizations (actors)

    The edge model enables graph traversal for:
    - Finding similar past decisions
    - Understanding decision dependencies
    - Tracing decision causality chains

    Reference: ADR-0101 Context Graphs

    Indexes:
        - trace_id: FK to parent decision
        - (source_type, source_id): Source entity lookup
        - (target_type, target_id): Target entity lookup
        - relation: Filter by edge type
    """

    __tablename__ = "decision_edges"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        doc="Unique edge identifier (UUID)",
    )

    # FK to decision trace (CASCADE delete when trace is deleted)
    trace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("decision_traces.trace_id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to parent decision trace",
    )

    # Source entity (where the edge comes from)
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Source entity type: session, workflow, project, user, decision",
    )
    source_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Source entity identifier",
    )

    # Target entity (where the edge points to)
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Target entity type: tool, skill, model, artifact, decision",
    )
    target_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Target entity identifier",
    )

    # Relation type (describes the edge)
    relation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Relation type: invoked, selected, produced, caused_by, approved_by",
    )
    weight: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        default=Decimal("1.0"),
        doc="Edge weight for weighted graph operations (0.000-1.000)",
    )
    edge_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional edge metadata",
    )

    # Timestamp for edge creation
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the edge was created (UTC)",
    )

    # Indexes
    __table_args__ = (
        Index("ix_edge_trace_id", "trace_id"),
        Index("ix_edge_source", "source_type", "source_id"),
        Index("ix_edge_target", "target_type", "target_id"),
        Index("ix_edge_relation", "relation"),
    )

    def __repr__(self) -> str:
        return (
            f"<DecisionEdge(edge_id={self.edge_id}, "
            f"relation={self.relation}, "
            f"{self.source_type}:{self.source_id} -> {self.target_type}:{self.target_id})>"
        )


# =============================================================================
# LangGraph Execution Trace Model (Phase 4)
# =============================================================================


class LangGraphExecutionTrace(Base):  # type: ignore[misc,valid-type]
    """
    Persistent storage for LangGraph node execution traces.

    Captures WHAT nodes ran and when (as opposed to DecisionTrace which
    captures WHY decisions were made). Used by DevTools AgentTraceTab
    to show historical execution traces after page reload.

    Data Flow:
    - Live: WebSocket `trace_step` messages to DevTools
    - Persistence: Stored here for historical retrieval
    - Query: `/api/v1/sessions/{id}/agent-execution-trace`

    Fields mirror the trace_step WebSocket payload:
    - node_name: Name of the LangGraph node (router, planner, executor)
    - status: Execution state (running, completed, failed, skipped)
    - start_time/end_time: Timing in epoch milliseconds
    - duration_ms: Calculated duration

    GDPR Compliance:
    - user_id: For GDPR export/delete
    - organization_id: For org-level analytics

    Indexes:
    - session_id: Primary query path
    - user_id: GDPR export/delete
    - created_at: Retention cleanup
    - (session_id, sequence_number): Ordered timeline
    """

    __tablename__ = "langgraph_execution_traces"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        doc="Unique trace identifier (UUID)",
    )

    # Context identifiers
    session_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Session identifier",
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        doc="LangGraph run ID for correlation",
    )
    workflow_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Optional workflow identifier",
    )

    # GDPR compliance
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User identifier for GDPR export/delete",
    )
    organization_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Organization identifier for analytics",
    )

    # Node execution data
    node_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Node identifier (may differ from name)",
    )
    node_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Node name (router, planner, executor, etc.)",
    )
    node_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Node type (default, conditional, etc.)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Execution status: running, completed, failed, skipped",
    )

    # Timing (epoch milliseconds)
    start_time: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        doc="Start timestamp in epoch milliseconds",
    )
    end_time: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        doc="End timestamp in epoch milliseconds",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Duration in milliseconds",
    )

    # Ordering
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Sequential order within session",
    )

    # Metadata
    attributes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional node attributes (JSON)",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if status is 'failed'",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When the record was created (UTC)",
    )

    # Indexes
    __table_args__ = (
        Index("ix_lget_session_id", "session_id"),
        Index("ix_lget_user_id", "user_id"),
        Index("ix_lget_org_id", "organization_id"),
        Index("ix_lget_created_at", "created_at"),
        Index("ix_lget_session_sequence", "session_id", "sequence_number"),
    )

    def __repr__(self) -> str:
        return f"<LangGraphExecutionTrace(trace_id={self.trace_id}, node_name={self.node_name}, status={self.status})>"

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API/GDPR export."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "sequence_number": self.sequence_number,
            "attributes": self.attributes,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
