"""
Unit tests for database models.

Tests SQLAlchemy model definitions for cost tracking persistence.
"""

import gc
from datetime import datetime, UTC
from decimal import Decimal

import pytest

from mcp_server_langgraph.database import Base, TokenUsageRecord

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_database_models")
class TestTokenUsageRecord:
    """Test TokenUsageRecord model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_token_usage_record_table_name(self) -> None:
        """Test TokenUsageRecord has correct table name."""
        assert TokenUsageRecord.__tablename__ == "token_usage_records"

    def test_token_usage_record_inherits_from_base(self) -> None:
        """Test TokenUsageRecord inherits from declarative Base."""
        assert issubclass(TokenUsageRecord, Base)

    def test_token_usage_record_columns_exist(self) -> None:
        """Test TokenUsageRecord has expected columns."""
        # Get column names from the mapper
        column_names = [col.name for col in TokenUsageRecord.__table__.columns]

        expected_columns = [
            "id",
            "timestamp",
            "created_at",
            "user_id",
            "session_id",
            "model",
            "provider",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "feature",
            "metadata",  # Stored as "metadata" in DB, mapped as "metadata_"
        ]

        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_token_usage_record_repr(self) -> None:
        """Test TokenUsageRecord __repr__ method."""
        record = TokenUsageRecord(
            id=1,
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            created_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            user_id="user123",
            session_id="session456",
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.001500"),
        )

        repr_str = repr(record)
        assert "TokenUsageRecord" in repr_str
        assert "id=1" in repr_str
        assert "user_id=user123" in repr_str
        assert "model=claude-3-5-sonnet-20241022" in repr_str
        assert "tokens=150" in repr_str

    def test_token_usage_record_to_dict(self) -> None:
        """Test TokenUsageRecord to_dict method."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        record = TokenUsageRecord(
            id=1,
            timestamp=timestamp,
            created_at=timestamp,
            user_id="user123",
            session_id="session456",
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.001500"),
            feature="chat",
            metadata_={"request_id": "req123"},
        )

        result = record.to_dict()

        assert result["id"] == 1
        assert result["user_id"] == "user123"
        assert result["session_id"] == "session456"
        assert result["model"] == "claude-3-5-sonnet-20241022"
        assert result["provider"] == "anthropic"
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["estimated_cost_usd"] == "0.001500"
        assert result["feature"] == "chat"
        assert result["metadata"] == {"request_id": "req123"}
        # Verify timestamps are ISO format strings
        assert "2025-01-15" in result["timestamp"]
        assert "2025-01-15" in result["created_at"]

    def test_token_usage_record_indexes_exist(self) -> None:
        """Test TokenUsageRecord has expected indexes."""
        indexes = TokenUsageRecord.__table__.indexes
        index_names = {idx.name for idx in indexes}

        # Check composite indexes exist
        assert "ix_user_timestamp" in index_names
        assert "ix_provider_model" in index_names


@pytest.mark.xdist_group(name="test_database_models")
class TestDatabaseBase:
    """Test database Base configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_base_is_declarative_base(self) -> None:
        """Test Base is a proper SQLAlchemy declarative base."""
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

    def test_base_metadata_contains_token_usage_table(self) -> None:
        """Test Base metadata contains the token_usage_records table."""
        table_names = list(Base.metadata.tables.keys())
        assert "token_usage_records" in table_names
