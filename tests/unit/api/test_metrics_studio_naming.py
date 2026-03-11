"""
Tests for HEART Metrics API studio naming migration.

TDD Phase: RED - These tests define the expected behavior after migrating
from builder/playground to studio app_name.

Migration: Literal["builder", "playground"] -> Literal["studio"]
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mcp_server_langgraph.api.metrics import (
    EventBatch,
    FeatureEvent,
    HeartMetricsBatch,
    TaskMetrics,
)

pytestmark = pytest.mark.unit


class TestStudioAppName:
    """Verify app_name only accepts 'studio'."""

    def test_accepts_studio_app_name(self) -> None:
        """Should accept 'studio' as valid app_name."""
        batch = HeartMetricsBatch(
            session_id="test-123",
            app_name="studio",
        )
        assert batch.app_name == "studio"

    def test_rejects_playground_app_name(self) -> None:
        """Should reject deprecated 'playground' app_name."""
        with pytest.raises(ValidationError) as exc_info:
            HeartMetricsBatch(
                session_id="test-123",
                app_name="playground",
            )
        assert "app_name" in str(exc_info.value)

    def test_rejects_builder_app_name(self) -> None:
        """Should reject deprecated 'builder' app_name."""
        with pytest.raises(ValidationError) as exc_info:
            HeartMetricsBatch(
                session_id="test-123",
                app_name="builder",
            )
        assert "app_name" in str(exc_info.value)

    def test_heart_metrics_batch_with_full_data(self) -> None:
        """Should accept full metrics batch with studio app_name."""
        batch = HeartMetricsBatch(
            session_id="test-456",
            app_name="studio",
            task_success=TaskMetrics(
                tasks_started=10,
                tasks_completed=8,
                tasks_errored=2,
            ),
            timestamp=datetime.now(UTC),
        )
        assert batch.app_name == "studio"
        assert batch.task_success.tasks_started == 10

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestEventBatchStudioAppName:
    """Verify EventBatch also uses studio app_name."""

    def test_event_batch_accepts_studio(self) -> None:
        """EventBatch should accept 'studio' as valid app_name."""
        batch = EventBatch(
            session_id="test-789",
            app_name="studio",
            events=[
                FeatureEvent(
                    feature_name="dark_mode",
                    event_type="clicked",
                ),
            ],
        )
        assert batch.app_name == "studio"

    def test_event_batch_rejects_playground(self) -> None:
        """EventBatch should reject deprecated 'playground' app_name."""
        with pytest.raises(ValidationError) as exc_info:
            EventBatch(
                session_id="test-789",
                app_name="playground",
                events=[],
            )
        assert "app_name" in str(exc_info.value)

    def test_event_batch_rejects_builder(self) -> None:
        """EventBatch should reject deprecated 'builder' app_name."""
        with pytest.raises(ValidationError) as exc_info:
            EventBatch(
                session_id="test-789",
                app_name="builder",
                events=[],
            )
        assert "app_name" in str(exc_info.value)

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
