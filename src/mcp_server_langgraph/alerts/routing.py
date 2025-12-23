"""
Multi-Tenant Alert Routing.

Service for routing alerts to appropriate tenants based on labels,
subscriptions, and routing rules.

Features:
- Route alerts by tenant ID
- Filter by severity and labels
- Support subscription-based routing
- Handle alert escalation paths

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol

from opentelemetry import trace

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class Alert:
    """
    Alert data model for routing.

    Attributes:
        alert_id: Unique identifier for the alert.
        name: Alert name/type.
        severity: Alert severity (critical, warning, info).
        labels: Key-value labels for routing.
        message: Alert message text.
        started_at: When the alert started.
        acknowledged: Whether the alert has been acknowledged.
    """

    alert_id: str
    name: str
    severity: str
    labels: dict[str, str]
    message: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    acknowledged: bool = False


@dataclass
class RoutingResult:
    """
    Result of alert routing.

    Attributes:
        tenant_id: Primary tenant ID for the alert.
        routed: Whether the alert was successfully routed.
        filtered: Whether the alert was filtered out by rules.
        target_tenants: List of all target tenant IDs.
        subscribed_users: List of subscribed user IDs.
        notification_channels: Channels per user for notifications.
    """

    tenant_id: str | None = None
    routed: bool = False
    filtered: bool = False
    target_tenants: list[str] = field(default_factory=list)
    subscribed_users: list[str] = field(default_factory=list)
    notification_channels: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class EscalationResult:
    """
    Result of escalation check.

    Attributes:
        should_escalate: Whether the alert should be escalated.
        escalate_to: List of targets to escalate to.
    """

    should_escalate: bool = False
    escalate_to: list[str] = field(default_factory=list)


@dataclass
class NotificationPreference:
    """
    User notification preferences.

    Attributes:
        channels: Preferred notification channels.
        quiet_hours_start: Start of quiet hours (0-23).
        quiet_hours_end: End of quiet hours (0-23).
    """

    channels: list[str] = field(default_factory=lambda: ["email", "push"])
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None


@dataclass
class Subscription:
    """
    User subscription to alerts.

    Attributes:
        user_id: User ID.
        tenant_id: Tenant ID for the subscription.
        alert_types: List of alert types to subscribe to (* for all).
        preference: Notification preferences.
    """

    user_id: str
    tenant_id: str
    alert_types: list[str] = field(default_factory=list)
    preference: NotificationPreference | None = None


@dataclass
class RoutingRule:
    """
    Routing rule for filtering alerts.

    Attributes:
        tenant_id: Tenant this rule applies to.
        severity_filter: List of severities to allow (empty = all).
        label_matchers: Required label key-value pairs.
    """

    tenant_id: str
    severity_filter: list[str] = field(default_factory=list)
    label_matchers: dict[str, str] = field(default_factory=dict)


@dataclass
class EscalationPolicy:
    """
    Escalation policy for alerts.

    Attributes:
        tenant_id: Tenant this policy applies to.
        escalation_after_minutes: Minutes before escalation.
        escalate_to: List of targets to escalate to.
    """

    tenant_id: str
    escalation_after_minutes: int = 15
    escalate_to: list[str] = field(default_factory=list)


# =============================================================================
# Storage Protocol
# =============================================================================


class SubscriptionStore(Protocol):
    """Protocol for subscription storage."""

    async def get_subscriptions(self, tenant_id: str) -> list[Subscription]:
        """Get subscriptions for a tenant."""
        ...


# =============================================================================
# Alert Router
# =============================================================================


class AlertRouter:
    """
    Multi-tenant alert router.

    Routes alerts to appropriate tenants and users based on labels,
    rules, and subscriptions.
    """

    def __init__(
        self,
        default_tenant: str = "default",
        rules: list[RoutingRule] | None = None,
        escalation_policies: list[EscalationPolicy] | None = None,
        subscription_store: SubscriptionStore | None = None,
    ) -> None:
        """
        Initialize the alert router.

        Args:
            default_tenant: Default tenant for alerts without tenant label.
            rules: List of routing rules.
            escalation_policies: List of escalation policies.
            subscription_store: Store for user subscriptions.
        """
        self._default_tenant = default_tenant
        self._rules = rules or []
        self._escalation_policies = escalation_policies or []
        self._subscription_store = subscription_store

        # Index rules by tenant for faster lookup
        self._rules_by_tenant: dict[str, list[RoutingRule]] = {}
        for rule in self._rules:
            if rule.tenant_id not in self._rules_by_tenant:
                self._rules_by_tenant[rule.tenant_id] = []
            self._rules_by_tenant[rule.tenant_id].append(rule)

        # Index escalation policies by tenant
        self._policies_by_tenant: dict[str, EscalationPolicy] = {p.tenant_id: p for p in self._escalation_policies}

    def route(self, alert: Alert) -> RoutingResult:
        """
        Route an alert synchronously.

        Args:
            alert: The alert to route.

        Returns:
            RoutingResult with routing information.
        """
        # Determine tenant from labels
        tenant_id = alert.labels.get("tenant", self._default_tenant)

        with tracer.start_as_current_span(
            "alert.route",
            attributes={
                "routing.alert_id": alert.alert_id,
                "routing.tenant_id": tenant_id,
                "routing.alert_name": alert.name,
                "routing.severity": alert.severity,
            },
        ) as span:
            # Check for broadcast alerts
            target_tenants = self._get_target_tenants(alert, tenant_id)

            # Apply routing rules
            if self._is_filtered_by_rules(alert, tenant_id):
                span.set_attribute("routing.filtered", True)
                return RoutingResult(
                    tenant_id=tenant_id,
                    routed=False,
                    filtered=True,
                    target_tenants=[],
                )

            span.set_attribute("routing.filtered", False)
            span.set_attribute("routing.target_count", len(target_tenants))

            return RoutingResult(
                tenant_id=tenant_id,
                routed=True,
                filtered=False,
                target_tenants=target_tenants,
            )

    async def route_async(self, alert: Alert) -> RoutingResult:
        """
        Route an alert asynchronously with subscription lookup.

        Args:
            alert: The alert to route.

        Returns:
            RoutingResult with routing and subscription information.
        """
        # Get basic routing (this already creates its own span)
        result = self.route(alert)

        if not result.routed or self._subscription_store is None:
            return result

        # Create span for subscription lookup
        with tracer.start_as_current_span(
            "alert.route_async.subscriptions",
            attributes={
                "routing.alert_id": alert.alert_id,
                "routing.tenant_id": result.tenant_id or self._default_tenant,
            },
        ) as span:
            # Look up subscriptions with error handling
            try:
                subscriptions = await self._subscription_store.get_subscriptions(result.tenant_id or self._default_tenant)
            except Exception as e:
                # Record error but continue with basic routing (graceful degradation)
                logger.warning(f"Subscription store error: {e}")
                span.record_exception(e)
                span.set_attribute("routing.subscription_error", True)
                return result

            # Filter subscriptions by alert type
            subscribed_users: list[str] = []
            notification_channels: dict[str, list[str]] = {}

            for sub in subscriptions:
                if self._matches_subscription(alert, sub):
                    subscribed_users.append(sub.user_id)
                    if sub.preference:
                        notification_channels[sub.user_id] = sub.preference.channels

            result.subscribed_users = subscribed_users
            result.notification_channels = notification_channels

            # Set subscription count in span
            span.set_attribute("routing.subscribed_users", len(subscribed_users))

            return result

    def check_escalation(self, alert: Alert) -> EscalationResult:
        """
        Check if an alert should be escalated.

        Args:
            alert: The alert to check.

        Returns:
            EscalationResult with escalation information.
        """
        # Get tenant
        tenant_id = alert.labels.get("tenant", self._default_tenant)

        with tracer.start_as_current_span(
            "alert.check_escalation",
            attributes={
                "escalation.alert_id": alert.alert_id,
                "escalation.tenant_id": tenant_id,
                "escalation.alert_name": alert.name,
                "escalation.acknowledged": alert.acknowledged,
            },
        ) as span:
            # Get escalation policy
            policy = self._policies_by_tenant.get(tenant_id)
            if policy is None:
                span.set_attribute("escalation.has_policy", False)
                return EscalationResult(should_escalate=False)

            span.set_attribute("escalation.has_policy", True)
            span.set_attribute("escalation.threshold_minutes", policy.escalation_after_minutes)

            # Don't escalate acknowledged alerts
            if alert.acknowledged:
                span.set_attribute("escalation.skipped_acknowledged", True)
                return EscalationResult(should_escalate=False)

            # Check if escalation threshold has passed
            escalation_threshold = timedelta(minutes=policy.escalation_after_minutes)
            time_since_start = datetime.now(UTC) - alert.started_at

            if time_since_start >= escalation_threshold:
                span.set_attribute("escalation.triggered", True)
                span.set_attribute("escalation.target_count", len(policy.escalate_to))
                return EscalationResult(
                    should_escalate=True,
                    escalate_to=list(policy.escalate_to),
                )

            span.set_attribute("escalation.triggered", False)
            return EscalationResult(should_escalate=False)

    def _get_target_tenants(self, alert: Alert, primary_tenant: str) -> list[str]:
        """Get list of target tenants for an alert."""
        # Check for broadcast label
        if alert.labels.get("broadcast") == "true":
            tenants_label = alert.labels.get("tenants", "")
            if tenants_label:
                return [t.strip() for t in tenants_label.split(",")]

        return [primary_tenant]

    def _is_filtered_by_rules(self, alert: Alert, tenant_id: str) -> bool:
        """Check if alert is filtered out by routing rules."""
        rules = self._rules_by_tenant.get(tenant_id, [])

        for rule in rules:
            # Check severity filter
            if rule.severity_filter and alert.severity not in rule.severity_filter:
                return True

            # Check label matchers
            for key, value in rule.label_matchers.items():
                if alert.labels.get(key) != value:
                    return True

        return False

    def _matches_subscription(self, alert: Alert, subscription: Subscription) -> bool:
        """Check if alert matches a subscription."""
        # Wildcard matches all
        if "*" in subscription.alert_types:
            return True

        # Check if alert name is in subscribed types
        return alert.name in subscription.alert_types
