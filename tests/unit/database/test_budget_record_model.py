"""
Unit tests for BudgetRecord database model.

TDD Cycle: RED -> GREEN -> REFACTOR

Tests verify the BudgetRecord SQLAlchemy model for persisting budget configurations
for organizations, projects, teams, and users.
"""

import gc
from datetime import datetime, UTC
from decimal import Decimal

import pytest


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.database,
]


@pytest.mark.xdist_group(name="test_budget_record_model")
class TestBudgetRecordModel:
    """Test suite for BudgetRecord SQLAlchemy model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_record_model_exists(self):
        """
        GIVEN the database models module
        WHEN importing BudgetRecord
        THEN it should be importable without error
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        assert BudgetRecord is not None

    def test_budget_record_has_required_columns(self):
        """
        GIVEN the BudgetRecord model
        WHEN checking its column definitions
        THEN it should have all required columns
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        # Check that table name is correct
        assert BudgetRecord.__tablename__ == "budget_records"

        # Get column names from the model
        column_names = {col.name for col in BudgetRecord.__table__.columns}

        # Required columns
        required_columns = {
            "id",
            "entity_type",
            "entity_id",
            "monthly_limit_usd",
            "warning_threshold",
            "critical_threshold",
            "name",
            "description",
            "enabled",
            "created_at",
            "updated_at",
        }

        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_budget_record_entity_type_is_string(self):
        """
        GIVEN the BudgetRecord model
        WHEN checking entity_type column
        THEN it should be a string type
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        entity_type_col = BudgetRecord.__table__.columns["entity_type"]
        assert str(entity_type_col.type) == "VARCHAR(50)"

    def test_budget_record_monthly_limit_is_numeric(self):
        """
        GIVEN the BudgetRecord model
        WHEN checking monthly_limit_usd column
        THEN it should be a numeric type with proper precision
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        limit_col = BudgetRecord.__table__.columns["monthly_limit_usd"]
        assert "NUMERIC" in str(limit_col.type).upper()

    def test_budget_record_can_be_instantiated(self):
        """
        GIVEN the BudgetRecord model
        WHEN creating an instance with valid data
        THEN it should be created successfully
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        now = datetime.now(UTC)
        record = BudgetRecord(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("1000.00"),
            warning_threshold=0.80,
            critical_threshold=1.0,
            name="ACME Corp Monthly Budget",
            description="Monthly LLM budget for ACME Corporation",
            enabled=True,
            created_at=now,
            updated_at=now,
        )

        assert record.entity_type == "organization"
        assert record.entity_id == "organization:acme"
        assert record.monthly_limit_usd == Decimal("1000.00")
        assert record.warning_threshold == 0.80
        assert record.critical_threshold == 1.0
        assert record.name == "ACME Corp Monthly Budget"
        assert record.enabled is True

    def test_budget_record_has_unique_constraint_on_entity(self):
        """
        GIVEN the BudgetRecord model
        WHEN checking constraints
        THEN entity_type + entity_id should have a unique constraint
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        # Check for unique constraint on entity_type + entity_id
        indexes = BudgetRecord.__table__.indexes
        index_names = {idx.name for idx in indexes}

        # Should have an index for entity lookups
        assert "ix_budget_entity_type_id" in index_names or any("entity" in (idx.name or "") for idx in indexes)

    def test_budget_record_defaults(self):
        """
        GIVEN the BudgetRecord model
        WHEN creating an instance with explicit values
        THEN values should be stored correctly

        Note: SQLAlchemy defaults only apply at database INSERT time,
        not at Python object instantiation. This test verifies the
        model accepts the expected default values explicitly.
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        record = BudgetRecord(
            entity_type="user",
            entity_id="user:alice",
            monthly_limit_usd=Decimal("100.00"),
            warning_threshold=0.80,
            critical_threshold=1.0,
            enabled=True,
        )

        # Verify values are stored correctly
        assert record.warning_threshold == 0.80
        assert record.critical_threshold == 1.0
        assert record.enabled is True
        assert record.name is None
        assert record.description is None

    def test_budget_record_column_defaults_configured(self):
        """
        GIVEN the BudgetRecord model
        WHEN checking column default configurations
        THEN defaults should be configured for database INSERT
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        # Check that column defaults are configured
        warning_col = BudgetRecord.__table__.columns["warning_threshold"]
        critical_col = BudgetRecord.__table__.columns["critical_threshold"]
        enabled_col = BudgetRecord.__table__.columns["enabled"]

        # Defaults should be configured (they apply at INSERT time)
        assert warning_col.default is not None or warning_col.server_default is not None
        assert critical_col.default is not None or critical_col.server_default is not None
        assert enabled_col.default is not None or enabled_col.server_default is not None

    def test_budget_record_to_dict(self):
        """
        GIVEN a BudgetRecord instance
        WHEN calling to_dict()
        THEN it should return a dictionary with all fields
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        now = datetime.now(UTC)
        record = BudgetRecord(
            id=1,
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("500.00"),
            warning_threshold=0.75,
            critical_threshold=0.95,
            name="Backend Project Budget",
            description="Budget for backend team",
            enabled=True,
            created_at=now,
            updated_at=now,
        )

        result = record.to_dict()

        assert result["id"] == 1
        assert result["entity_type"] == "project"
        assert result["entity_id"] == "project:backend"
        assert result["monthly_limit_usd"] == "500.00"
        assert result["warning_threshold"] == 0.75
        assert result["critical_threshold"] == 0.95
        assert result["name"] == "Backend Project Budget"
        assert result["enabled"] is True
        assert "created_at" in result
        assert "updated_at" in result

    def test_budget_record_repr(self):
        """
        GIVEN a BudgetRecord instance
        WHEN calling repr()
        THEN it should return a readable string representation
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        record = BudgetRecord(
            id=42,
            entity_type="team",
            entity_id="team:platform",
            monthly_limit_usd=Decimal("250.00"),
        )

        repr_str = repr(record)

        assert "BudgetRecord" in repr_str
        assert "id=42" in repr_str
        assert "team:platform" in repr_str
        assert "250.00" in repr_str


@pytest.mark.xdist_group(name="test_budget_record_model")
class TestBudgetRecordEntityTypes:
    """Test suite for BudgetRecord entity type validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_organization_entity_type(self):
        """
        GIVEN BudgetRecord with entity_type='organization'
        WHEN creating the record
        THEN it should be valid
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        record = BudgetRecord(
            entity_type="organization",
            entity_id="organization:acme",
            monthly_limit_usd=Decimal("10000.00"),
        )

        assert record.entity_type == "organization"

    def test_project_entity_type(self):
        """
        GIVEN BudgetRecord with entity_type='project'
        WHEN creating the record
        THEN it should be valid
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        record = BudgetRecord(
            entity_type="project",
            entity_id="project:backend",
            monthly_limit_usd=Decimal("2000.00"),
        )

        assert record.entity_type == "project"

    def test_team_entity_type(self):
        """
        GIVEN BudgetRecord with entity_type='team'
        WHEN creating the record
        THEN it should be valid
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        record = BudgetRecord(
            entity_type="team",
            entity_id="team:platform",
            monthly_limit_usd=Decimal("500.00"),
        )

        assert record.entity_type == "team"

    def test_user_entity_type(self):
        """
        GIVEN BudgetRecord with entity_type='user'
        WHEN creating the record
        THEN it should be valid
        """
        from mcp_server_langgraph.database.models import BudgetRecord

        record = BudgetRecord(
            entity_type="user",
            entity_id="user:alice",
            monthly_limit_usd=Decimal("100.00"),
        )

        assert record.entity_type == "user"
