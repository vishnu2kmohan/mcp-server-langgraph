"""
Health check endpoints for Kubernetes probes
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mcp_server_langgraph.auth.openfga import OpenFGAClient
from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.secrets.manager import get_secrets_manager

app = FastAPI(title="MCP Server with LangGraph Health")


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str
    timestamp: str
    version: str
    checks: Dict[str, Any]


@app.get("/", response_model=HealthResponse)  # type: ignore[misc]
async def health_check() -> HealthResponse:
    """
    Liveness probe - returns 200 if application is running

    Used by Kubernetes to determine if pod should be restarted

    NOTE: Mounted at /health in main app, so accessible at /health/
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.service_version,
        checks={"application": "running"},
    )


@app.get("/live", response_model=HealthResponse)  # type: ignore[misc]
async def liveness_check() -> HealthResponse:
    """
    Liveness probe - same as root health check

    Used by Kubernetes liveness probe at /health/live
    """
    return await health_check()


@app.get("/ready", response_model=None)  # type: ignore[misc]
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
            timestamp=datetime.now(timezone.utc).isoformat(),
            version=settings.service_version,
            checks=checks,
        ).model_dump(),
    )


@app.get("/startup", response_model=None)  # type: ignore[misc]
async def startup_check() -> JSONResponse | Dict[str, Any]:
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

    return {"status": "started", "timestamp": datetime.now(timezone.utc).isoformat(), "checks": checks}


@app.get("/metrics/prometheus")  # type: ignore[misc]
async def prometheus_metrics() -> Dict[str, Any]:
    """
    Prometheus metrics endpoint

    Exposes application metrics for scraping
    """
    # This would integrate with OpenTelemetry's Prometheus exporter
    # For now, return basic info
    return {
        "metrics": [
            "# HELP langgraph_agent_info Application information",
            "# TYPE langgraph_agent_info gauge",
            f'langgraph_agent_info{{version="{settings.service_version}",service="{settings.service_name}"}} 1',
        ]
    }


if __name__ == "__main__":
    import uvicorn

    # Bind to all interfaces for Docker/Kubernetes compatibility
    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 - Required for containerized deployment
        port=int(settings.get_secret("HEALTH_PORT", fallback="8000") or "8000"),
        log_level="info",
    )
