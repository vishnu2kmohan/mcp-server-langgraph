"""
Health check endpoints for Kubernetes probes and Prometheus metrics
"""

from datetime import datetime, UTC
from typing import Any

from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.secrets.manager import get_secrets_manager

# Prometheus client for metrics exposition
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_CLIENT_AVAILABLE = True

    # Application metrics for Grafana dashboards
    # These match the expected metric names in langgraph-agent.json

    # Request metrics
    agent_requests_total = Counter(
        name="agent_requests_total",
        documentation="Total number of agent requests",
        labelnames=["method", "endpoint", "status"],
        registry=REGISTRY,
    )

    agent_response_duration_seconds = Histogram(
        name="agent_response_duration_seconds",
        documentation="Agent response time in seconds",
        labelnames=["method", "endpoint"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=REGISTRY,
    )

    # Tool call metrics
    agent_tool_calls_total = Counter(
        name="agent_tool_calls_total",
        documentation="Total number of tool calls",
        labelnames=["tool_name", "status"],
        registry=REGISTRY,
    )

    # Agent call success/failure metrics (for LLM Performance dashboard)
    agent_calls_successful_total = Counter(
        name="agent_calls_successful_total",
        documentation="Total number of successful agent calls",
        labelnames=["agent_type", "model"],
        registry=REGISTRY,
    )

    agent_calls_failed_total = Counter(
        name="agent_calls_failed_total",
        documentation="Total number of failed agent calls",
        labelnames=["agent_type", "model", "error_type"],
        registry=REGISTRY,
    )

    # Error metrics
    agent_errors_total = Counter(
        name="agent_errors_total",
        documentation="Total number of agent errors",
        labelnames=["error_type"],
        registry=REGISTRY,
    )

    # Resource usage metrics (gauges for current values)
    agent_memory_bytes = Gauge(
        name="agent_memory_bytes",
        documentation="Current memory usage in bytes",
        labelnames=["type"],
        registry=REGISTRY,
    )

    agent_active_sessions = Gauge(
        name="agent_active_sessions",
        documentation="Number of active agent sessions",
        registry=REGISTRY,
    )

except ImportError:
    PROMETHEUS_CLIENT_AVAILABLE = False
    generate_latest = None  # type: ignore[assignment]
    CONTENT_TYPE_LATEST = "text/plain"
    REGISTRY = None  # type: ignore[assignment]


# =============================================================================
# Agent Metrics Helper Functions
# =============================================================================


def record_agent_call_success(agent_type: str = "default", model: str = "unknown") -> None:
    """
    Record a successful agent call.

    Args:
        agent_type: Type of agent (e.g., "default", "custom")
        model: LLM model used (e.g., "gpt-4o", "claude-3-opus")
    """
    if not PROMETHEUS_CLIENT_AVAILABLE:
        return

    try:
        agent_calls_successful_total.labels(agent_type=agent_type, model=model).inc()
    except Exception:
        pass  # Silently ignore metric recording errors


def record_agent_call_failure(agent_type: str = "default", model: str = "unknown", error_type: str = "unknown") -> None:
    """
    Record a failed agent call.

    Args:
        agent_type: Type of agent (e.g., "default", "custom")
        model: LLM model used (e.g., "gpt-4o", "claude-3-opus")
        error_type: Type of error (e.g., "timeout", "rate_limit", "api_error")
    """
    if not PROMETHEUS_CLIENT_AVAILABLE:
        return

    try:
        agent_calls_failed_total.labels(agent_type=agent_type, model=model, error_type=error_type).inc()
    except Exception:
        pass


app = FastAPI(title="MCP Server with LangGraph Health")


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str
    timestamp: str
    version: str
    checks: dict[str, Any]


@app.get("/")
async def health_check() -> HealthResponse:
    """
    Liveness probe - returns 200 if application is running

    Used by Kubernetes to determine if pod should be restarted

    NOTE: Mounted at /health in main app, so accessible at /health/
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC).isoformat(),
        version=settings.service_version,
        checks={"application": "running"},
    )


@app.get("/live")
async def liveness_check() -> HealthResponse:
    """
    Liveness probe - same as root health check

    Used by Kubernetes liveness probe at /health/live
    """
    return await health_check()


@app.get("/ready", response_model=None)
async def readiness_check() -> JSONResponse:
    """
    Readiness probe - returns 200 if application can serve traffic

    Used by Kubernetes to determine if pod should receive traffic
    """
    checks = {}
    all_healthy = True

    # Check OpenFGA connection
    if settings.openfga_store_id and settings.openfga_model_id:
        try:
            OpenFGAClient(
                api_url=settings.openfga_api_url, store_id=settings.openfga_store_id, model_id=settings.openfga_model_id
            )
            # Simple check - if client initializes, connection is OK
            checks["openfga"] = {"status": "healthy", "url": settings.openfga_api_url}
        except Exception as e:
            checks["openfga"] = {"status": "unhealthy", "error": str(e)}
            all_healthy = False
            logger.error(f"OpenFGA health check failed: {e}")
    else:
        checks["openfga"] = {"status": "not_configured", "message": "OpenFGA not configured"}

    # Check Infisical connection (optional)
    try:
        secrets_mgr = get_secrets_manager()
        if secrets_mgr.client:
            # Test secret retrieval
            secrets_mgr.get_secret("HEALTH_CHECK_TEST", fallback="ok")
            checks["infisical"] = {"status": "healthy", "url": settings.infisical_site_url}
        else:
            checks["infisical"] = {"status": "not_configured", "message": "Using environment variables"}
    except Exception as e:
        checks["infisical"] = {"status": "degraded", "message": "Fallback mode active", "error": str(e)}
        # Don't fail readiness if Infisical is down (we have fallback)
        logger.warning(f"Infisical health check failed: {e}")

    # Check critical secrets exist
    critical_secrets_missing = []
    if not settings.anthropic_api_key:
        critical_secrets_missing.append("ANTHROPIC_API_KEY")
    if not settings.jwt_secret_key:
        critical_secrets_missing.append("JWT_SECRET_KEY")

    if critical_secrets_missing:
        checks["secrets"] = {"status": "unhealthy", "missing": ", ".join(critical_secrets_missing)}
        all_healthy = False
    else:
        checks["secrets"] = {"status": "healthy", "message": "All critical secrets loaded"}

    response_status = "ready" if all_healthy else "not_ready"
    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content=HealthResponse(
            status=response_status,
            timestamp=datetime.now(UTC).isoformat(),
            version=settings.service_version,
            checks=checks,
        ).model_dump(),
    )


@app.get("/startup", response_model=None)
async def startup_check() -> JSONResponse | dict[str, Any]:
    """
    Startup probe - returns 200 when application has fully started

    Used by Kubernetes to determine when to start liveness/readiness probes

    NOTE: Mounted at /health in main app, so accessible at /health/startup
    """
    # Check if critical components are initialized
    checks = {}

    # Verify settings loaded
    checks["config"] = {"status": "loaded", "service": settings.service_name}

    # Verify logger initialized
    try:
        logger.info("Startup health check")
        checks["logging"] = {"status": "initialized"}
    except Exception as e:
        checks["logging"] = {"status": "failed", "error": str(e)}

        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "starting", "checks": checks})

    return {"status": "started", "timestamp": datetime.now(UTC).isoformat(), "checks": checks}


@app.get("/metrics/prometheus")
async def prometheus_metrics_legacy() -> Response:
    """
    Prometheus metrics endpoint (legacy path)

    Exposes application metrics for scraping.
    Redirects to /metrics for consistency.
    """
    return await prometheus_metrics()


@app.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint

    Exposes application metrics for scraping by Alloy/Prometheus.
    Returns metrics in Prometheus text exposition format.
    """
    import psutil

    if not PROMETHEUS_CLIENT_AVAILABLE or generate_latest is None:
        # Fallback if prometheus_client not installed
        return Response(
            content="# prometheus_client not available\n",
            media_type="text/plain",
        )

    # Update memory gauge with current process memory
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        agent_memory_bytes.labels(type="rss").set(memory_info.rss)
        agent_memory_bytes.labels(type="vms").set(memory_info.vms)
    except Exception:
        pass  # Don't fail metrics if psutil unavailable

    # Generate and return Prometheus-format metrics
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


if __name__ == "__main__":
    import uvicorn

    # Bind to all interfaces for Docker/Kubernetes compatibility
    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 - Required for containerized deployment
        port=int(settings.get_secret("HEALTH_PORT", fallback="8000") or "8000"),
        log_level="info",
    )
