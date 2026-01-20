"""Add ai_predictions table for ML-powered HEART metrics predictions.

Revision ID: a7b8c9d0e1f2
Revises: z6a7b8c9d0e1
Create Date: 2026-01-13

This migration adds the ai_predictions table for storing ML pipeline predictions:
- Churn risk predictions
- Adoption forecasts
- Engagement decline predictions
- Factor analysis with impact weights

Reference: docs-internal/frontend/PENDING-BACKEND-APIS.md, ADR-0091 Phase 7
Frontend Integration: useGetPredictionsQuery
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "a7b8c9d0e1f2"
down_revision = "z6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_predictions table for ML-powered predictions."""
    op.create_table(
        "ai_predictions",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Unique prediction identifier (UUID)",
        ),
        # Optional session reference (predictions can be global or session-specific)
        sa.Column(
            "session_id",
            sa.String(255),
            nullable=True,
            comment="Session identifier (optional, for session-specific predictions)",
        ),
        # User/organization context
        sa.Column(
            "user_id",
            sa.String(255),
            nullable=True,
            comment="User identifier (for user-specific predictions)",
        ),
        sa.Column(
            "organization_id",
            sa.String(255),
            nullable=True,
            comment="Organization identifier (for org-level predictions)",
        ),
        # Prediction type
        sa.Column(
            "type",
            sa.String(50),
            nullable=False,
            comment="Prediction type: churn_risk, adoption_forecast, engagement_decline",
        ),
        # Metric being predicted
        sa.Column(
            "metric",
            sa.String(100),
            nullable=False,
            comment="The metric being predicted (e.g., user_engagement, feature_adoption)",
        ),
        # Predicted value (0-1 for probabilities/scores)
        sa.Column(
            "predicted_value",
            sa.Numeric(5, 4),
            nullable=False,
            comment="Predicted value (0.0000-1.0000 for probabilities)",
        ),
        # Confidence score
        sa.Column(
            "confidence",
            sa.Numeric(5, 4),
            nullable=False,
            comment="Confidence score for the prediction (0.0000-1.0000)",
        ),
        # Prediction timeframe
        sa.Column(
            "timeframe",
            sa.String(10),
            nullable=False,
            comment="Prediction timeframe: 7d, 30d, 90d",
        ),
        # Contributing factors
        sa.Column(
            "factors",
            postgresql.JSONB(),
            server_default="[]",
            nullable=False,
            comment="Contributing factors with impact weights [{name, impact}]",
        ),
        # Model metadata
        sa.Column(
            "model_version",
            sa.String(50),
            nullable=True,
            comment="ML model version used for this prediction",
        ),
        sa.Column(
            "model_name",
            sa.String(100),
            nullable=True,
            comment="ML model name (e.g., churn_predictor_v2)",
        ),
        # Timestamps (Unix milliseconds for frontend compatibility)
        sa.Column(
            "created_at",
            sa.BigInteger(),
            nullable=False,
            comment="When the prediction was generated (Unix timestamp ms)",
        ),
        sa.Column(
            "expires_at",
            sa.BigInteger(),
            nullable=True,
            comment="When the prediction expires (Unix timestamp ms)",
        ),
        # Database timestamp
        sa.Column(
            "db_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
            comment="Database record creation time",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "type IN ('churn_risk', 'adoption_forecast', 'engagement_decline')",
            name="ck_ai_predictions_type_values",
        ),
        sa.CheckConstraint(
            "timeframe IN ('7d', '30d', '90d')",
            name="ck_ai_predictions_timeframe_values",
        ),
        sa.CheckConstraint(
            "predicted_value >= 0 AND predicted_value <= 1",
            name="ck_ai_predictions_value_range",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_ai_predictions_confidence_range",
        ),
    )

    # Create indexes for efficient queries
    # Index for session-specific predictions
    op.create_index(
        "ix_ai_predictions_session_id",
        "ai_predictions",
        ["session_id"],
    )
    # Index for user-specific predictions
    op.create_index(
        "ix_ai_predictions_user_id",
        "ai_predictions",
        ["user_id"],
    )
    # Index for organization-level predictions
    op.create_index(
        "ix_ai_predictions_org_id",
        "ai_predictions",
        ["organization_id"],
    )
    # Index for filtering by prediction type
    op.create_index(
        "ix_ai_predictions_type",
        "ai_predictions",
        ["type"],
    )
    # Index for filtering by confidence threshold
    op.create_index(
        "ix_ai_predictions_confidence",
        "ai_predictions",
        ["confidence"],
    )
    # Index for chronological ordering
    op.create_index(
        "ix_ai_predictions_created_at",
        "ai_predictions",
        ["created_at"],
    )
    # Index for cleaning up expired predictions
    op.create_index(
        "ix_ai_predictions_expires_at",
        "ai_predictions",
        ["expires_at"],
    )
    # Composite index for common query pattern (type + confidence filtering)
    op.create_index(
        "ix_ai_predictions_type_confidence",
        "ai_predictions",
        ["type", "confidence"],
    )
    # GIN index for JSONB factors column (for factor-based queries)
    op.create_index(
        "ix_ai_predictions_factors",
        "ai_predictions",
        ["factors"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop ai_predictions table."""
    # Drop indexes
    op.drop_index("ix_ai_predictions_factors", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_type_confidence", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_expires_at", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_created_at", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_confidence", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_type", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_org_id", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_user_id", table_name="ai_predictions")
    op.drop_index("ix_ai_predictions_session_id", table_name="ai_predictions")

    # Drop table
    op.drop_table("ai_predictions")
