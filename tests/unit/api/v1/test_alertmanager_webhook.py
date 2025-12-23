"""
Alertmanager Webhook Receiver Unit Tests.

Tests for the Alertmanager webhook endpoint following TDD methodology.
This endpoint receives alerts from Alertmanager and broadcasts them to Admin WebSocket clients.

Features tested:
- Alertmanager payload parsing (v4 format)
- Alert severity filtering (critical/warning only)
- Broadcasting to AlertBroadcaster
- AI recommendation queueing for critical alerts
- Error handling for malformed payloads

Reference:
- ADR-0026 - Comprehensive Client Resilience Patterns
- https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
"""

from __future__ import annotations

import gc
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from mcp_server_langgraph.observability.query.interfaces import AlertSeverity, AlertState

pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.alerts,
]


# Sample Alertmanager v4 payload (based on Prometheus Alertmanager format)
SAMPLE_ALERTMANAGER_PAYLOAD = {
    "version": "4",
    "groupKey": "alertname=CircuitBreakerOpen:service=redis",
    "truncatedAlerts": 0,
    "status": "firing",
    "receiver": "resilience-webhook",
    "groupLabels": {
        "alertname": "CircuitBreakerOpen",
    },
    "commonLabels": {
        "alertname": "CircuitBreakerOpen",
        "severity": "critical",
        "service": "redis",
    },
    "commonAnnotations": {
        "summary": "Redis circuit breaker is open",
        "runbook_url": "https://runbooks.example.com/cb-redis",
    },
    "externalURL": "http://alertmanager:9093",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "CircuitBreakerOpen",
                "severity": "critical",
                "service": "redis",
                "instance": "redis-primary",
            },
            "annotations": {
                "summary": "Redis circuit breaker is open",
                "description": "The circuit breaker for Redis is open due to repeated failures",
                "runbook_url": "https://runbooks.example.com/cb-redis",
            },
            "startsAt": "2025-12-20T10:30:00.000Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://mimir:9090/graph?g0.expr=circuit_breaker_state%3D%3D1",
            "fingerprint": "a1b2c3d4e5f6",
        }
    ],
}


@pytest.mark.xdist_group(name="test_alertmanager_webhook")
class TestAlertmanagerWebhookEndpoint:
    """Tests for Alertmanager webhook endpoint existence and configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_alertmanager_webhook_router_exists(self) -> None:
        """
        GIVEN the alertmanager webhook module
        WHEN importing the router
        THEN should export alertmanager_webhook_router.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            alertmanager_webhook_router,
        )

        assert alertmanager_webhook_router is not None

    def test_webhook_endpoint_exists(self) -> None:
        """
        GIVEN the alertmanager webhook router
        WHEN checking routes
        THEN should have POST /webhooks/alertmanager endpoint.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            alertmanager_webhook_router,
        )

        routes = [r for r in alertmanager_webhook_router.routes]
        webhook_routes = [r for r in routes if hasattr(r, "path") and "alertmanager" in r.path]
        assert len(webhook_routes) > 0, "Should have /webhooks/alertmanager route"


@pytest.mark.xdist_group(name="test_alertmanager_webhook")
class TestAlertmanagerPayloadParsing:
    """Tests for parsing Alertmanager webhook payloads."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_alertmanager_payload_single_alert(self) -> None:
        """
        GIVEN a valid Alertmanager payload with one alert
        WHEN parsing the payload
        THEN should return list with one Alert object.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        alerts = parse_alertmanager_payload(SAMPLE_ALERTMANAGER_PAYLOAD)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.name == "CircuitBreakerOpen"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.state == AlertState.FIRING
        assert alert.labels["service"] == "redis"
        assert "runbook_url" in alert.annotations

    def test_parse_alertmanager_payload_multiple_alerts(self) -> None:
        """
        GIVEN an Alertmanager payload with multiple alerts
        WHEN parsing the payload
        THEN should return list with all Alert objects.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HTTPPoolExhausted",
                        "severity": "warning",
                        "service": "api",
                    },
                    "annotations": {
                        "summary": "HTTP pool is exhausted",
                    },
                    "startsAt": "2025-12-20T10:35:00.000Z",
                    "endsAt": "0001-01-01T00:00:00Z",
                    "fingerprint": "x1y2z3",
                },
            ],
        }

        alerts = parse_alertmanager_payload(payload)

        assert len(alerts) == 2
        assert alerts[0].name == "CircuitBreakerOpen"
        assert alerts[1].name == "HTTPPoolExhausted"

    def test_parse_alertmanager_payload_resolved_state(self) -> None:
        """
        GIVEN an Alertmanager payload with resolved alert
        WHEN parsing the payload
        THEN should set state to RESOLVED.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "status": "resolved",
            "alerts": [
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "status": "resolved",
                    "endsAt": "2025-12-20T11:00:00.000Z",
                }
            ],
        }

        alerts = parse_alertmanager_payload(payload)

        assert len(alerts) == 1
        assert alerts[0].state == AlertState.RESOLVED
        assert alerts[0].ended_at is not None

    def test_parse_alertmanager_payload_severity_mapping(self) -> None:
        """
        GIVEN Alertmanager payloads with different severity labels
        WHEN parsing the payloads
        THEN should correctly map to AlertSeverity enum.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        for severity_label, expected_severity in [
            ("critical", AlertSeverity.CRITICAL),
            ("warning", AlertSeverity.WARNING),
            ("info", AlertSeverity.INFO),
            ("error", AlertSeverity.ERROR),
        ]:
            payload = {
                **SAMPLE_ALERTMANAGER_PAYLOAD,
                "alerts": [
                    {
                        **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                        "labels": {
                            **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0]["labels"],
                            "severity": severity_label,
                        },
                    }
                ],
            }

            alerts = parse_alertmanager_payload(payload)
            assert alerts[0].severity == expected_severity

    def test_parse_alertmanager_payload_timestamps(self) -> None:
        """
        GIVEN an Alertmanager payload with timestamps
        WHEN parsing the payload
        THEN should correctly parse ISO8601 timestamps.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        alerts = parse_alertmanager_payload(SAMPLE_ALERTMANAGER_PAYLOAD)

        assert alerts[0].started_at is not None
        assert alerts[0].started_at.year == 2025
        assert alerts[0].started_at.month == 12
        assert alerts[0].started_at.day == 20

    def test_parse_alertmanager_payload_fingerprint_as_alert_id(self) -> None:
        """
        GIVEN an Alertmanager payload with fingerprint
        WHEN parsing the payload
        THEN should use fingerprint as alert_id.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        alerts = parse_alertmanager_payload(SAMPLE_ALERTMANAGER_PAYLOAD)

        assert alerts[0].alert_id == "a1b2c3d4e5f6"

    def test_parse_alertmanager_payload_generator_url(self) -> None:
        """
        GIVEN an Alertmanager payload with generatorURL
        WHEN parsing the payload
        THEN should include generator_url in Alert.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        alerts = parse_alertmanager_payload(SAMPLE_ALERTMANAGER_PAYLOAD)

        assert alerts[0].generator_url is not None
        assert "mimir" in alerts[0].generator_url


@pytest.mark.xdist_group(name="test_alertmanager_webhook")
class TestAlertmanagerWebhookFiltering:
    """Tests for alert severity filtering."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_alerts_critical_allowed(self) -> None:
        """
        GIVEN a list of alerts
        WHEN filtering for broadcast
        THEN should include critical severity alerts.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            filter_alerts_for_broadcast,
            parse_alertmanager_payload,
        )

        alerts = parse_alertmanager_payload(SAMPLE_ALERTMANAGER_PAYLOAD)
        filtered = filter_alerts_for_broadcast(alerts)

        assert len(filtered) == 1
        assert filtered[0].severity == AlertSeverity.CRITICAL

    def test_filter_alerts_warning_allowed(self) -> None:
        """
        GIVEN a list of alerts with warning severity
        WHEN filtering for broadcast
        THEN should include warning severity alerts.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            filter_alerts_for_broadcast,
            parse_alertmanager_payload,
        )

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "labels": {
                        **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0]["labels"],
                        "severity": "warning",
                    },
                }
            ],
        }

        alerts = parse_alertmanager_payload(payload)
        filtered = filter_alerts_for_broadcast(alerts)

        assert len(filtered) == 1
        assert filtered[0].severity == AlertSeverity.WARNING

    def test_filter_alerts_info_excluded(self) -> None:
        """
        GIVEN a list of alerts with info severity
        WHEN filtering for broadcast
        THEN should exclude info severity alerts.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            filter_alerts_for_broadcast,
            parse_alertmanager_payload,
        )

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "labels": {
                        **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0]["labels"],
                        "severity": "info",
                    },
                }
            ],
        }

        alerts = parse_alertmanager_payload(payload)
        filtered = filter_alerts_for_broadcast(alerts)

        assert len(filtered) == 0

    def test_filter_alerts_mixed_severities(self) -> None:
        """
        GIVEN a list of alerts with mixed severities
        WHEN filtering for broadcast
        THEN should only include critical and warning.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            filter_alerts_for_broadcast,
            parse_alertmanager_payload,
        )

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "labels": {"alertname": "Critical1", "severity": "critical"},
                    "fingerprint": "crit1",
                },
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "labels": {"alertname": "Warning1", "severity": "warning"},
                    "fingerprint": "warn1",
                },
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "labels": {"alertname": "Info1", "severity": "info"},
                    "fingerprint": "info1",
                },
            ],
        }

        alerts = parse_alertmanager_payload(payload)
        filtered = filter_alerts_for_broadcast(alerts)

        assert len(filtered) == 2
        severities = {a.severity for a in filtered}
        assert AlertSeverity.CRITICAL in severities
        assert AlertSeverity.WARNING in severities
        assert AlertSeverity.INFO not in severities


@pytest.mark.xdist_group(name="test_alertmanager_webhook")
class TestAlertmanagerWebhookBroadcasting:
    """Tests for broadcasting alerts to WebSocket clients."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_handle_webhook_broadcasts_alerts(self) -> None:
        """
        GIVEN a valid Alertmanager payload
        WHEN the webhook is called
        THEN should broadcast filtered alerts.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            handle_alertmanager_webhook,
        )

        mock_broadcaster = AsyncMock()

        result = await handle_alertmanager_webhook(
            payload=SAMPLE_ALERTMANAGER_PAYLOAD,
            broadcaster=mock_broadcaster,
        )

        assert result["status"] == "ok"
        assert result["alerts_received"] == 1
        assert result["alerts_broadcast"] == 1
        mock_broadcaster.broadcast_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_filters_info_alerts(self) -> None:
        """
        GIVEN an Alertmanager payload with only info alerts
        WHEN the webhook is called
        THEN should not broadcast any alerts.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            handle_alertmanager_webhook,
        )

        mock_broadcaster = AsyncMock()
        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "labels": {"alertname": "Info1", "severity": "info"},
                }
            ],
        }

        result = await handle_alertmanager_webhook(
            payload=payload,
            broadcaster=mock_broadcaster,
        )

        assert result["status"] == "ok"
        assert result["alerts_received"] == 1
        assert result["alerts_broadcast"] == 0
        mock_broadcaster.broadcast_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_webhook_queues_ai_recommendation_for_critical(self) -> None:
        """
        GIVEN an Alertmanager payload with critical alert
        WHEN the webhook is called
        THEN should queue AI recommendation generation.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            handle_alertmanager_webhook,
        )

        mock_broadcaster = AsyncMock()
        mock_ai_queue = AsyncMock()

        result = await handle_alertmanager_webhook(
            payload=SAMPLE_ALERTMANAGER_PAYLOAD,
            broadcaster=mock_broadcaster,
            ai_recommendation_queue=mock_ai_queue,
        )

        assert result["ai_recommendations_queued"] == 1
        mock_ai_queue.queue_recommendation.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_skips_ai_for_warning(self) -> None:
        """
        GIVEN an Alertmanager payload with only warning alerts
        WHEN the webhook is called
        THEN should not queue AI recommendation (on-demand only).
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            handle_alertmanager_webhook,
        )

        mock_broadcaster = AsyncMock()
        mock_ai_queue = AsyncMock()

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                {
                    **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0],
                    "labels": {
                        **SAMPLE_ALERTMANAGER_PAYLOAD["alerts"][0]["labels"],
                        "severity": "warning",
                    },
                }
            ],
        }

        result = await handle_alertmanager_webhook(
            payload=payload,
            broadcaster=mock_broadcaster,
            ai_recommendation_queue=mock_ai_queue,
        )

        assert result["ai_recommendations_queued"] == 0
        mock_ai_queue.queue_recommendation.assert_not_called()


@pytest.mark.xdist_group(name="test_alertmanager_webhook")
class TestAlertmanagerWebhookErrorHandling:
    """Tests for error handling in webhook."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_empty_alerts_array(self) -> None:
        """
        GIVEN an Alertmanager payload with empty alerts array
        WHEN parsing the payload
        THEN should return empty list.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        payload = {**SAMPLE_ALERTMANAGER_PAYLOAD, "alerts": []}

        alerts = parse_alertmanager_payload(payload)

        assert len(alerts) == 0

    def test_parse_missing_severity_defaults_to_warning(self) -> None:
        """
        GIVEN an Alertmanager payload without severity label
        WHEN parsing the payload
        THEN should default to warning severity.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "NoSeverity"},
                    "annotations": {},
                    "startsAt": "2025-12-20T10:30:00.000Z",
                    "endsAt": "0001-01-01T00:00:00Z",
                    "fingerprint": "no-sev",
                }
            ],
        }

        alerts = parse_alertmanager_payload(payload)

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_parse_invalid_timestamp_uses_none(self) -> None:
        """
        GIVEN an Alertmanager payload with invalid timestamp
        WHEN parsing the payload
        THEN should use None for timestamp fields.
        """
        from mcp_server_langgraph.api.v1.alertmanager_webhook import (
            parse_alertmanager_payload,
        )

        payload = {
            **SAMPLE_ALERTMANAGER_PAYLOAD,
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "BadTime", "severity": "critical"},
                    "annotations": {},
                    "startsAt": "not-a-timestamp",
                    "endsAt": "also-not-a-timestamp",
                    "fingerprint": "bad-ts",
                }
            ],
        }

        alerts = parse_alertmanager_payload(payload)

        assert len(alerts) == 1
        # Should not raise, should handle gracefully
        assert alerts[0].started_at is None or isinstance(alerts[0].started_at, datetime)
