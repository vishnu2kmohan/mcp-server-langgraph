"""
Rotating Thresholds Tests

TDD tests for auto-adjusting confidence thresholds based on user approval patterns.

Features:
- Track approval/rejection history per user
- Calculate optimal threshold based on patterns
- Apply threshold adjustments within bounds
- Provide threshold recommendations

Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
"""

import gc
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.xdist_group(name="test_rotating_thresholds")
class TestRotatingThresholdModels:
    """Tests for rotating threshold model definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_history_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing ApprovalHistory
        THEN the model should exist with required fields.
        """
        from mcp_server_langgraph.api.v1.agent_requests import ApprovalHistory

        assert ApprovalHistory is not None

        # Test required fields
        history = ApprovalHistory(
            user_id="user-001",
            decision="approved",
            confidence=0.65,
            threshold=0.7,
            decided_at=datetime.now(UTC).isoformat(),
        )
        assert history.user_id == "user-001"
        assert history.decision == "approved"
        assert history.confidence == 0.65

    def test_threshold_recommendation_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing ThresholdRecommendation
        THEN the model should exist with required fields.
        """
        from mcp_server_langgraph.api.v1.agent_requests import ThresholdRecommendation

        assert ThresholdRecommendation is not None

        rec = ThresholdRecommendation(
            current_threshold=0.7,
            recommended_threshold=0.65,
            reason="High approval rate for low-confidence requests",
            confidence_level=0.85,
            sample_size=50,
        )
        assert rec.current_threshold == 0.7
        assert rec.recommended_threshold == 0.65

    def test_user_threshold_settings_model_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing UserThresholdSettings
        THEN the model should exist with required fields.
        """
        from mcp_server_langgraph.api.v1.agent_requests import UserThresholdSettings

        assert UserThresholdSettings is not None

        settings = UserThresholdSettings(
            user_id="user-001",
            base_threshold=0.7,
            adjusted_threshold=0.65,
            auto_adjust_enabled=True,
            min_threshold=0.5,
            max_threshold=0.9,
        )
        assert settings.user_id == "user-001"
        assert settings.adjusted_threshold == 0.65


@pytest.mark.xdist_group(name="test_rotating_thresholds")
class TestThresholdCalculator:
    """Tests for threshold calculation logic."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_threshold_calculator_exists(self) -> None:
        """
        GIVEN the agent_requests module
        WHEN importing ThresholdCalculator
        THEN the class should exist.
        """
        from mcp_server_langgraph.api.v1.agent_requests import ThresholdCalculator

        assert ThresholdCalculator is not None

    def test_calculate_recommendation_high_approval_rate(self) -> None:
        """
        GIVEN a user with 90% approval rate for requests below threshold
        WHEN calculating threshold recommendation
        THEN should recommend lowering the threshold.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ApprovalHistory,
            ThresholdCalculator,
        )

        calculator = ThresholdCalculator(
            base_threshold=0.7,
            min_threshold=0.5,
            max_threshold=0.9,
        )

        # Create history with 90% approvals at 65% confidence
        history = []
        for i in range(90):
            history.append(
                ApprovalHistory(
                    user_id="user-001",
                    decision="approved",
                    confidence=0.65,
                    threshold=0.7,
                    decided_at=(datetime.now(UTC) - timedelta(hours=i)).isoformat(),
                )
            )
        for i in range(10):
            history.append(
                ApprovalHistory(
                    user_id="user-001",
                    decision="rejected",
                    confidence=0.65,
                    threshold=0.7,
                    decided_at=(datetime.now(UTC) - timedelta(hours=90 + i)).isoformat(),
                )
            )

        recommendation = calculator.calculate_recommendation(history)

        # Should recommend lowering threshold since 90% are approved
        assert recommendation.recommended_threshold < recommendation.current_threshold

    def test_calculate_recommendation_high_rejection_rate(self) -> None:
        """
        GIVEN a user with 80% rejection rate for requests
        WHEN calculating threshold recommendation
        THEN should recommend raising the threshold.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ApprovalHistory,
            ThresholdCalculator,
        )

        calculator = ThresholdCalculator(
            base_threshold=0.7,
            min_threshold=0.5,
            max_threshold=0.9,
        )

        # Create history with 80% rejections
        history = []
        for i in range(20):
            history.append(
                ApprovalHistory(
                    user_id="user-001",
                    decision="approved",
                    confidence=0.65,
                    threshold=0.7,
                    decided_at=(datetime.now(UTC) - timedelta(hours=i)).isoformat(),
                )
            )
        for i in range(80):
            history.append(
                ApprovalHistory(
                    user_id="user-001",
                    decision="rejected",
                    confidence=0.65,
                    threshold=0.7,
                    decided_at=(datetime.now(UTC) - timedelta(hours=20 + i)).isoformat(),
                )
            )

        recommendation = calculator.calculate_recommendation(history)

        # Should recommend raising threshold since 80% are rejected
        assert recommendation.recommended_threshold > recommendation.current_threshold

    def test_calculate_recommendation_respects_min_threshold(self) -> None:
        """
        GIVEN a calculator with min_threshold of 0.5
        WHEN all requests are approved
        THEN recommended threshold should not go below min.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ApprovalHistory,
            ThresholdCalculator,
        )

        calculator = ThresholdCalculator(
            base_threshold=0.55,
            min_threshold=0.5,
            max_threshold=0.9,
        )

        # 100% approval rate
        history = [
            ApprovalHistory(
                user_id="user-001",
                decision="approved",
                confidence=0.52,
                threshold=0.55,
                decided_at=datetime.now(UTC).isoformat(),
            )
            for _ in range(100)
        ]

        recommendation = calculator.calculate_recommendation(history)

        assert recommendation.recommended_threshold >= 0.5

    def test_calculate_recommendation_respects_max_threshold(self) -> None:
        """
        GIVEN a calculator with max_threshold of 0.9
        WHEN all requests are rejected
        THEN recommended threshold should not exceed max.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ApprovalHistory,
            ThresholdCalculator,
        )

        calculator = ThresholdCalculator(
            base_threshold=0.85,
            min_threshold=0.5,
            max_threshold=0.9,
        )

        # 100% rejection rate
        history = [
            ApprovalHistory(
                user_id="user-001",
                decision="rejected",
                confidence=0.8,
                threshold=0.85,
                decided_at=datetime.now(UTC).isoformat(),
            )
            for _ in range(100)
        ]

        recommendation = calculator.calculate_recommendation(history)

        assert recommendation.recommended_threshold <= 0.9

    def test_calculate_recommendation_insufficient_data(self) -> None:
        """
        GIVEN fewer than minimum sample size decisions
        WHEN calculating threshold recommendation
        THEN should return current threshold with low confidence.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            ApprovalHistory,
            ThresholdCalculator,
        )

        calculator = ThresholdCalculator(
            base_threshold=0.7,
            min_threshold=0.5,
            max_threshold=0.9,
            min_sample_size=20,
        )

        # Only 5 decisions
        history = [
            ApprovalHistory(
                user_id="user-001",
                decision="approved",
                confidence=0.65,
                threshold=0.7,
                decided_at=datetime.now(UTC).isoformat(),
            )
            for _ in range(5)
        ]

        recommendation = calculator.calculate_recommendation(history)

        # Should keep current threshold due to insufficient data
        assert recommendation.recommended_threshold == 0.7
        assert recommendation.confidence_level < 0.5


@pytest.mark.xdist_group(name="test_rotating_thresholds")
class TestThresholdEndpoints:
    """Tests for threshold management endpoints."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_threshold_recommendation_endpoint_exists(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking routes
        THEN should have threshold/recommendation endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import agent_request_router

        routes = [route.path for route in agent_request_router.routes]
        matching = [r for r in routes if "threshold" in r and "recommendation" in r]
        assert len(matching) > 0, f"No threshold/recommendation route found in {routes}"

    def test_update_user_threshold_endpoint_exists(self) -> None:
        """
        GIVEN the agent_request_router
        WHEN checking routes
        THEN should have threshold settings update endpoint.
        """
        from mcp_server_langgraph.api.v1.agent_requests import agent_request_router

        routes = [route.path for route in agent_request_router.routes]
        matching = [r for r in routes if "threshold" in r and "settings" in r]
        assert len(matching) > 0, f"No threshold/settings route found in {routes}"

    @pytest.mark.asyncio
    async def test_get_threshold_recommendation_returns_recommendation(self) -> None:
        """
        GIVEN a user with approval history
        WHEN calling the threshold recommendation endpoint
        THEN should return a recommendation.
        """
        from mcp_server_langgraph.api.v1.agent_requests import (
            get_threshold_recommendation,
        )

        mock_user = {"sub": "user@example.com", "user_id": "user-001"}

        # Mock the history store if needed
        response = await get_threshold_recommendation(current_user=mock_user)

        assert response is not None
        assert hasattr(response, "current_threshold")
        assert hasattr(response, "recommended_threshold")
