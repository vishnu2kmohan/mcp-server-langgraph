"""
Unit tests for health check endpoints.

Tests verify that health endpoints follow FastAPI sub-app best practices
and are accessible at the correct paths when mounted.
"""

import gc

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_app_routes_are_root_level():
    """
    Test that health app defines routes at root level (/, /ready, /startup).

    When a FastAPI sub-app is mounted at /health, routes should be defined
    at root level to avoid double-path issues (e.g., /health/health/startup).

    CRITICAL: This prevents production health probe failures.
    """
    from mcp_server_langgraph.health.checks import app as health_app

    # Get all routes from the health app
    routes = [route.path for route in health_app.routes]

    # Routes should be at root level since app is mounted at /health
    assert "/" in routes, "Health app should have root '/' route"
    assert "/ready" in routes, "Health app should have '/ready' route"
    assert "/startup" in routes, "Health app should have '/startup' route"
    assert "/live" in routes, "Health app should have '/live' route"

    # Should NOT have double paths
    assert "/health" not in routes, "Health app should not have '/health' route (mounted at /health already)"
    assert "/health/ready" not in routes, "Health app should not have '/health/ready' route"
    assert "/health/startup" not in routes, "Health app should not have '/health/startup' route"


@pytest.mark.unit
def test_health_endpoints_respond_correctly():
    """
    Test that health endpoints return expected responses.
    """
    from mcp_server_langgraph.health.checks import app as health_app

    client = TestClient(health_app)

    # Test root health endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "started"]
    assert "timestamp" in data

    # Test ready endpoint
    response = client.get("/ready")
    assert response.status_code in [200, 503]  # May be 503 if dependencies not ready
    data = response.json()
    assert "status" in data
    assert "checks" in data

    # Test startup endpoint
    response = client.get("/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "checks" in data

    # Test live endpoint
    response = client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.unit
def test_mounted_health_app_accessible():
    """
    Test that when health app is mounted at /health on main app,
    endpoints are accessible at /health/* paths.
    """
    from fastapi import FastAPI

    from mcp_server_langgraph.health.checks import app as health_app

    # Create main app and mount health app
    main_app = FastAPI()
    main_app.mount("/health", health_app)

    client = TestClient(main_app)

    # Endpoints should be accessible at /health/* paths
    response = client.get("/health/")
    assert response.status_code == 200

    response = client.get("/health/ready")
    assert response.status_code in [200, 503]

    response = client.get("/health/startup")
    assert response.status_code == 200

    response = client.get("/health/live")
    assert response.status_code == 200

    # Double paths should NOT work
    response = client.get("/health/health/startup")
    assert response.status_code == 404, "Double path /health/health/startup should NOT exist"


@pytest.mark.unit
def test_kubernetes_probe_paths():
    """
    Test that Kubernetes health probe paths work correctly.

    Deployment spec configures probes at:
    - Startup: /health/startup
    - Readiness: /health/ready
    - Liveness: /health/live
    """
    from fastapi import FastAPI

    from mcp_server_langgraph.health.checks import app as health_app

    # Simulate main app configuration
    main_app = FastAPI()
    main_app.mount("/health", health_app)

    client = TestClient(main_app)

    # Test Kubernetes probe paths
    startup_response = client.get("/health/startup")
    assert startup_response.status_code == 200, "Startup probe must return 200"

    readiness_response = client.get("/health/ready")
    assert readiness_response.status_code in [200, 503], "Readiness probe must return 200 or 503"

    liveness_response = client.get("/health/live")
    assert liveness_response.status_code == 200, "Liveness probe must return 200"
