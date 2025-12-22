"""
Resilience Remediation Webhook Handler

Receives Alertmanager webhooks and triggers appropriate remediation actions.

Reference: ADR-0026 - Comprehensive Client Resilience Patterns
"""

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.responses import PlainTextResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("remediation-webhook")

# Configuration from environment
NAMESPACE = os.getenv("NAMESPACE", "default")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
SCRIPTS_PATH = os.getenv("SCRIPTS_PATH", "/app/scripts")
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "300"))


# Prometheus metrics
remediation_actions_total = Counter(
    "remediation_actions_total",
    "Total remediation actions triggered",
    ["action", "service", "status"],
)
remediation_skipped_total = Counter(
    "remediation_skipped_total",
    "Total remediation actions skipped",
    ["reason", "service"],
)
remediation_duration_seconds = Histogram(
    "remediation_duration_seconds",
    "Duration of remediation actions",
    ["action", "service"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)
cooldown_remaining_seconds = Gauge(
    "remediation_cooldown_remaining_seconds",
    "Seconds remaining in cooldown for service",
    ["service"],
)


class AlertStatus(str, Enum):
    """Alertmanager alert status."""

    FIRING = "firing"
    RESOLVED = "resolved"


class Alert(BaseModel):
    """Single alert from Alertmanager."""

    status: AlertStatus
    labels: dict[str, str]
    annotations: dict[str, str] = {}
    startsAt: str | None = None
    endsAt: str | None = None
    generatorURL: str | None = None


class AlertmanagerPayload(BaseModel):
    """Alertmanager webhook payload."""

    version: str = "4"
    groupKey: str = ""
    truncatedAlerts: int = 0
    status: AlertStatus = AlertStatus.FIRING
    receiver: str = ""
    groupLabels: dict[str, str] = {}
    commonLabels: dict[str, str] = {}
    commonAnnotations: dict[str, str] = {}
    externalURL: str = ""
    alerts: list[Alert] = []


class RemediationResponse(BaseModel):
    """Response from remediation action."""

    status: str
    message: str
    action: str | None = None
    service: str | None = None
    dry_run: bool = False


@dataclass
class CooldownTracker:
    """Track cooldowns per service/action."""

    last_action: dict[str, float] = field(default_factory=dict)

    def check_cooldown(self, key: str) -> tuple[bool, int]:
        """Check if action is in cooldown. Returns (in_cooldown, remaining_seconds)."""
        if key not in self.last_action:
            return False, 0

        elapsed = time.time() - self.last_action[key]
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            return True, remaining
        return False, 0

    def record_action(self, key: str) -> None:
        """Record that an action was taken."""
        self.last_action[key] = time.time()


# Global cooldown tracker
cooldown_tracker = CooldownTracker()

# FastAPI app
app = FastAPI(
    title="Resilience Remediation Webhook",
    description="Handles Alertmanager webhooks for automated remediation",
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    """Prometheus metrics endpoint."""
    return generate_latest().decode("utf-8")


@app.post("/webhook", response_model=RemediationResponse)
async def handle_webhook(
    payload: AlertmanagerPayload,
    background_tasks: BackgroundTasks,
) -> RemediationResponse:
    """Handle incoming Alertmanager webhook."""
    logger.info(
        "Received webhook: status=%s, alerts=%d",
        payload.status,
        len(payload.alerts),
    )

    # Only process firing alerts
    firing_alerts = [a for a in payload.alerts if a.status == AlertStatus.FIRING]
    if not firing_alerts:
        return RemediationResponse(
            status="skipped",
            message="No firing alerts to process",
        )

    # Process each alert
    actions_triggered = 0
    for alert in firing_alerts:
        alertname = alert.labels.get("alertname", "unknown")
        service = alert.labels.get("service", "unknown")

        logger.info("Processing alert: %s for service: %s", alertname, service)

        # Determine remediation action based on alert
        action = get_remediation_action(alertname, service, alert.labels)

        if action:
            background_tasks.add_task(execute_remediation, action, service, alertname)
            actions_triggered += 1

    if actions_triggered == 0:
        return RemediationResponse(
            status="skipped",
            message="No remediation actions matched",
        )

    return RemediationResponse(
        status="accepted",
        message=f"Triggered {actions_triggered} remediation action(s)",
        dry_run=DRY_RUN,
    )


def get_remediation_action(
    alertname: str,
    service: str,
    labels: dict[str, str],
) -> str | None:
    """Determine which remediation action to take based on alert."""
    # Map alerts to remediation scripts
    alert_action_map = {
        # Circuit breaker alerts
        "CircuitBreakerOpen": "restart-circuit-breaker-pods.sh",
        "CircuitBreakerFlapping": "restart-circuit-breaker-pods.sh",
        "SLOResilienceCircuitBreakerImpact": "restart-circuit-breaker-pods.sh",
        # HTTP pool alerts
        "HTTPPoolExhausted": "scale-deployment.sh",
        "HTTPPoolHighUtilization": "scale-deployment.sh",
        # LLM provider alerts
        "AdaptiveBulkheadAtFloor": "switch-llm-provider.sh",
        "LLMProviderThrottled": "switch-llm-provider.sh",
        # Retry exhaustion
        "RetryExhausted": "restart-circuit-breaker-pods.sh",
        "HighRetryRate": "restart-circuit-breaker-pods.sh",
    }

    return alert_action_map.get(alertname)


async def execute_remediation(action: str, service: str, alertname: str) -> None:
    """Execute remediation script asynchronously."""
    cooldown_key = f"{action}:{service}"

    # Check cooldown
    in_cooldown, remaining = cooldown_tracker.check_cooldown(cooldown_key)
    cooldown_remaining_seconds.labels(service=service).set(remaining)

    if in_cooldown:
        logger.warning(
            "Skipping remediation for %s - cooldown active (%ds remaining)",
            service,
            remaining,
        )
        remediation_skipped_total.labels(reason="cooldown", service=service).inc()
        return

    script_path = os.path.join(SCRIPTS_PATH, action)
    if not os.path.exists(script_path):
        logger.error("Remediation script not found: %s", script_path)
        remediation_actions_total.labels(
            action=action, service=service, status="error"
        ).inc()
        return

    logger.info(
        "Executing remediation: %s for service: %s (alert: %s)",
        action,
        service,
        alertname,
    )

    start_time = time.time()
    try:
        # Build command based on script
        if action == "restart-circuit-breaker-pods.sh":
            cmd = [script_path, service, NAMESPACE]
        elif action == "scale-deployment.sh":
            cmd = [script_path, "mcp-server-langgraph", "", NAMESPACE]
        elif action == "switch-llm-provider.sh":
            # Default fallback provider
            fallback = os.getenv("FALLBACK_LLM_PROVIDER", "ollama")
            cmd = [script_path, fallback, NAMESPACE]
        else:
            cmd = [script_path, service, NAMESPACE]

        # Set environment for script
        env = os.environ.copy()
        env["DRY_RUN"] = "true" if DRY_RUN else "false"
        env["NAMESPACE"] = NAMESPACE

        # Run script
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            ),
        )

        duration = time.time() - start_time
        remediation_duration_seconds.labels(action=action, service=service).observe(
            duration
        )

        if result.returncode == 0:
            logger.info(
                "Remediation successful: %s for %s (%.2fs)",
                action,
                service,
                duration,
            )
            remediation_actions_total.labels(
                action=action, service=service, status="success"
            ).inc()
            cooldown_tracker.record_action(cooldown_key)
        else:
            logger.error(
                "Remediation failed: %s for %s - %s",
                action,
                service,
                result.stderr,
            )
            remediation_actions_total.labels(
                action=action, service=service, status="failure"
            ).inc()

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        logger.error(
            "Remediation timed out: %s for %s after %.2fs",
            action,
            service,
            duration,
        )
        remediation_actions_total.labels(
            action=action, service=service, status="timeout"
        ).inc()
        remediation_duration_seconds.labels(action=action, service=service).observe(
            duration
        )
    except Exception as e:
        logger.exception("Remediation error: %s for %s - %s", action, service, e)
        remediation_actions_total.labels(
            action=action, service=service, status="error"
        ).inc()


@app.get("/cooldowns")
async def get_cooldowns() -> dict[str, Any]:
    """Get current cooldown status for all services."""
    cooldowns = {}
    for key, last_time in cooldown_tracker.last_action.items():
        elapsed = time.time() - last_time
        remaining = max(0, COOLDOWN_SECONDS - int(elapsed))
        cooldowns[key] = {
            "last_action": datetime.fromtimestamp(last_time, tz=timezone.utc).isoformat(),
            "remaining_seconds": remaining,
            "in_cooldown": remaining > 0,
        }
    return {"cooldowns": cooldowns, "cooldown_period": COOLDOWN_SECONDS}


@app.post("/test/{action}/{service}")
async def test_remediation(
    action: str,
    service: str,
    background_tasks: BackgroundTasks,
) -> RemediationResponse:
    """Manually trigger a remediation action for testing."""
    valid_actions = [
        "restart-circuit-breaker-pods.sh",
        "scale-deployment.sh",
        "switch-llm-provider.sh",
        "reset-circuit-breaker.sh",
    ]

    if action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Valid: {valid_actions}",
        )

    background_tasks.add_task(execute_remediation, action, service, "ManualTest")

    return RemediationResponse(
        status="accepted",
        message=f"Triggered remediation: {action} for {service}",
        action=action,
        service=service,
        dry_run=DRY_RUN,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
