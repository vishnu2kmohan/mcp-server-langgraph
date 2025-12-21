"""
Tests for Interrupt API Endpoint (Phase 2.4)

Following TDD: Write tests FIRST, then implementation.

This module tests the REST API endpoint for interrupt operations:
- POST /api/v1/sessions/{session_id}/interrupt
- GET /api/v1/sessions/{session_id}/interrupt
- DELETE /api/v1/sessions/{session_id}/interrupt
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="interrupt_api")
class TestInterruptEndpointImport:
    """Test interrupt endpoint can be imported."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_interrupt_router_importable(self) -> None:
        """Interrupt router should be importable."""
        from mcp_server_langgraph.api.v1.interrupt import router

        assert router is not None


@pytest.mark.xdist_group(name="interrupt_api")
class TestInterruptEndpointSignal:
    """Test POST /sessions/{session_id}/interrupt endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_signal_interrupt_returns_200(self) -> None:
        """POST interrupt should return 200 OK."""
        from mcp_server_langgraph.api.v1.interrupt import router
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller

        reset_interrupt_controller()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        # Mock auth dependency
        with patch("mcp_server_langgraph.api.v1.interrupt.get_current_user") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            client = TestClient(app)
            response = client.post("/api/v1/sessions/test-session/interrupt")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session"
            assert data["interrupted"] is True

    @pytest.mark.asyncio
    async def test_signal_interrupt_stores_state(self) -> None:
        """POST interrupt should set interrupt state."""
        from mcp_server_langgraph.api.v1.interrupt import router
        from mcp_server_langgraph.core.interrupt import (
            get_interrupt_controller,
            reset_interrupt_controller,
        )

        reset_interrupt_controller()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch("mcp_server_langgraph.api.v1.interrupt.get_current_user") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            client = TestClient(app)
            client.post("/api/v1/sessions/state-test-session/interrupt")

            # Verify state was set by checking via the API
            response = client.get("/api/v1/sessions/state-test-session/interrupt")
            data = response.json()
            assert data["interrupted"] is True


@pytest.mark.xdist_group(name="interrupt_api")
class TestInterruptEndpointCheck:
    """Test GET /sessions/{session_id}/interrupt endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_check_interrupt_returns_status(self) -> None:
        """GET interrupt should return interrupt status."""
        from mcp_server_langgraph.api.v1.interrupt import router
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller

        reset_interrupt_controller()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch("mcp_server_langgraph.api.v1.interrupt.get_current_user") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            client = TestClient(app)
            response = client.get("/api/v1/sessions/check-session/interrupt")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "check-session"
            assert "interrupted" in data

    @pytest.mark.asyncio
    async def test_check_returns_false_initially(self) -> None:
        """GET interrupt should return false for new session."""
        from mcp_server_langgraph.api.v1.interrupt import router
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller

        reset_interrupt_controller()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch("mcp_server_langgraph.api.v1.interrupt.get_current_user") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            client = TestClient(app)
            response = client.get("/api/v1/sessions/new-session/interrupt")

            assert response.status_code == 200
            data = response.json()
            assert data["interrupted"] is False

    @pytest.mark.asyncio
    async def test_check_returns_true_after_signal(self) -> None:
        """GET interrupt should return true after signal."""
        from mcp_server_langgraph.api.v1.interrupt import router
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller

        reset_interrupt_controller()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch("mcp_server_langgraph.api.v1.interrupt.get_current_user") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            client = TestClient(app)
            # Signal first
            client.post("/api/v1/sessions/signaled-session/interrupt")
            # Then check
            response = client.get("/api/v1/sessions/signaled-session/interrupt")

            assert response.status_code == 200
            data = response.json()
            assert data["interrupted"] is True


@pytest.mark.xdist_group(name="interrupt_api")
class TestInterruptEndpointClear:
    """Test DELETE /sessions/{session_id}/interrupt endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_clear_interrupt_returns_200(self) -> None:
        """DELETE interrupt should return 200 OK."""
        from mcp_server_langgraph.api.v1.interrupt import router
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller

        reset_interrupt_controller()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch("mcp_server_langgraph.api.v1.interrupt.get_current_user") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            client = TestClient(app)
            response = client.delete("/api/v1/sessions/clear-session/interrupt")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "clear-session"
            assert data["cleared"] is True

    @pytest.mark.asyncio
    async def test_clear_after_signal_resets_status(self) -> None:
        """DELETE interrupt should reset interrupt status."""
        from mcp_server_langgraph.api.v1.interrupt import router
        from mcp_server_langgraph.core.interrupt import reset_interrupt_controller

        reset_interrupt_controller()

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch("mcp_server_langgraph.api.v1.interrupt.get_current_user") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}

            client = TestClient(app)
            session_id = "reset-session"

            # Signal
            client.post(f"/api/v1/sessions/{session_id}/interrupt")
            # Clear
            client.delete(f"/api/v1/sessions/{session_id}/interrupt")
            # Check should now be false
            response = client.get(f"/api/v1/sessions/{session_id}/interrupt")

            assert response.status_code == 200
            data = response.json()
            assert data["interrupted"] is False
