"""ApprovalLearner for learning user approval preferences.

Provides preference learning based on historical approval decisions:
- ApprovalDecision: Records a user's approval/rejection decision
- ApprovalPrediction: Predicts likely approval based on history
- ApprovalLearner: Learns patterns and makes predictions

This enables intelligent auto-approval suggestions based on user
behavior patterns in HITL workflows.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class ApprovalDecision:
    """A recorded approval decision.

    Attributes:
        action_type: Type/category of the action (e.g., 'file_write', 'database_delete')
        action_description: Human-readable description of the action
        approved: Whether the user approved the action
        user_id: Identifier of the user who made the decision
        reason: Optional reason for the decision
        timestamp: When the decision was made
    """

    action_type: str
    action_description: str
    approved: bool
    user_id: str
    reason: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ApprovalPrediction:
    """A prediction for whether an action will be approved.

    Attributes:
        likely_approved: Whether approval is predicted
        confidence: Confidence level (0-1) in the prediction
        similar_decisions: Number of similar decisions used for prediction
    """

    likely_approved: bool
    confidence: float
    similar_decisions: int


class ApprovalLearner:
    """Learns user approval preferences from historical decisions.

    Uses simple pattern matching based on action_type to predict
    whether similar future actions will be approved.

    In a production system, this could be extended to use:
    - Vector embeddings for semantic similarity
    - More sophisticated ML models
    - Cross-user pattern learning
    """

    def __init__(self) -> None:
        """Initialize the ApprovalLearner."""
        # Store decisions per user
        self._user_decisions: dict[str, list[ApprovalDecision]] = {}

    def record_decision(self, decision: ApprovalDecision) -> None:
        """Record an approval decision for learning.

        Args:
            decision: The ApprovalDecision to record
        """
        user_id = decision.user_id
        if user_id not in self._user_decisions:
            self._user_decisions[user_id] = []
        self._user_decisions[user_id].append(decision)

    def predict(
        self,
        *,
        action_type: str,
        action_description: str,
        user_id: str,
    ) -> ApprovalPrediction:
        """Predict whether an action will be approved.

        Uses historical decisions to predict approval likelihood
        based on action_type pattern matching.

        Args:
            action_type: Type of the action to predict for
            action_description: Description of the action
            user_id: User to predict for

        Returns:
            ApprovalPrediction with likelihood and confidence
        """
        # Get user's history for this action type
        similar = self.get_history(user_id=user_id, action_type=action_type)

        if not similar:
            # No history - low confidence neutral prediction
            return ApprovalPrediction(
                likely_approved=True,  # Default to optimistic
                confidence=0.0,
                similar_decisions=0,
            )

        # Count approvals vs rejections
        approved_count = sum(1 for d in similar if d.approved)
        total_count = len(similar)
        approval_rate = approved_count / total_count

        # Confidence increases with more history
        base_confidence = min(total_count / 5.0, 1.0)  # Max out at 5 decisions
        confidence = base_confidence * 0.7 + 0.3 * abs(approval_rate - 0.5) * 2

        return ApprovalPrediction(
            likely_approved=approval_rate >= 0.5,
            confidence=min(confidence, 1.0),
            similar_decisions=total_count,
        )

    def get_history(
        self,
        *,
        user_id: str,
        action_type: str | None = None,
    ) -> list[ApprovalDecision]:
        """Get historical decisions for a user.

        Args:
            user_id: User to get history for
            action_type: Optional filter by action type

        Returns:
            List of ApprovalDecisions matching the criteria
        """
        decisions = self._user_decisions.get(user_id, [])

        if action_type is None:
            return list(decisions)

        return [d for d in decisions if d.action_type == action_type]
