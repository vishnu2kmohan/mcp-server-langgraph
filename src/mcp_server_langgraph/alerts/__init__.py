"""
Alerts Module.

Real-time infrastructure alert streaming and management for Admin users.

Components:
- AlertBroadcaster: WebSocket broadcast service for alerts
- alert_to_message: Convert Alert dataclass to WebSocket message format
- AIRecommendationService: AI-powered alert recommendation generation
- AIRecommendationQueue: Async queue for background recommendation processing
- RemediationApprovalQueue: Queue for managing remediation approvals
- AlertRouter: Multi-tenant alert routing with escalation
- AlertCorrelationEngine: Pattern detection and root cause analysis
- RecommendationScorer: Quality scoring for AI recommendations
- RemediationFeedback: Structured feedback for AI learning

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from mcp_server_langgraph.alerts.ai_recommendation import (
    AIRecommendation,
    AIRecommendationQueue,
    AIRecommendationService,
    RemediationStep,
    build_recommendation_prompt,
)
from mcp_server_langgraph.alerts.approval_queue import (
    RemediationApprovalQueue,
    RemediationRequest,
    get_approval_queue,
    set_approval_queue,
)
from mcp_server_langgraph.alerts.broadcaster import (
    AlertBroadcaster,
    AlertSubscriber,
    alert_to_message,
)
from mcp_server_langgraph.alerts.correlation import (
    AlertCorrelationEngine,
    CorrelatedAlert,
    CorrelationGroup,
    PatternResult,
    PatternType,
)
from mcp_server_langgraph.alerts.feedback import (
    FeedbackStore,
    InMemoryFeedbackStore,
    RejectionReason,
    RemediationFeedback,
)
from mcp_server_langgraph.alerts.metrics import (
    record_alert_broadcast,
    record_alert_filtered,
    record_alert_received,
    record_command_blocked,
    record_rate_limit_exceeded,
    record_recommendation_generated,
    record_recommendation_regenerated,
    record_recommendation_request,
    record_remediation_execution,
    record_remediation_workflow,
    record_websocket_message,
    update_websocket_connections,
)
from mcp_server_langgraph.alerts.recommendation_scoring import (
    FeedbackData,
    QualityScore,
    RecommendationScorer,
    RejectionPattern,
    ScoringHistory,
    ScoringHistoryRepository,
    ScoringHistoryStore,
)
from mcp_server_langgraph.alerts.routing import (
    Alert,
    AlertRouter,
    EscalationPolicy,
    EscalationResult,
    NotificationPreference,
    RoutingResult,
    RoutingRule,
    Subscription,
    SubscriptionStore,
)

__all__ = [
    # AI Recommendation
    "AIRecommendation",
    "AIRecommendationQueue",
    "AIRecommendationService",
    "RemediationStep",
    "build_recommendation_prompt",
    # Approval Queue
    "RemediationApprovalQueue",
    "RemediationRequest",
    "get_approval_queue",
    "set_approval_queue",
    # Broadcaster
    "AlertBroadcaster",
    "AlertSubscriber",
    "alert_to_message",
    # Correlation
    "AlertCorrelationEngine",
    "CorrelatedAlert",
    "CorrelationGroup",
    "PatternResult",
    "PatternType",
    # Feedback
    "FeedbackStore",
    "InMemoryFeedbackStore",
    "RejectionReason",
    "RemediationFeedback",
    # Metrics
    "record_alert_broadcast",
    "record_alert_filtered",
    "record_alert_received",
    "record_command_blocked",
    "record_rate_limit_exceeded",
    "record_recommendation_generated",
    "record_recommendation_regenerated",
    "record_recommendation_request",
    "record_remediation_execution",
    "record_remediation_workflow",
    "record_websocket_message",
    "update_websocket_connections",
    # Recommendation Scoring
    "FeedbackData",
    "QualityScore",
    "RecommendationScorer",
    "RejectionPattern",
    "ScoringHistory",
    "ScoringHistoryRepository",
    "ScoringHistoryStore",
    # Routing
    "Alert",
    "AlertRouter",
    "EscalationPolicy",
    "EscalationResult",
    "NotificationPreference",
    "RoutingResult",
    "RoutingRule",
    "Subscription",
    "SubscriptionStore",
]
