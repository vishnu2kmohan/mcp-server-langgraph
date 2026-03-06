"""
Unit tests for RouterRegistry integration with app.py.

TDD Cycle: RED -> GREEN -> REFACTOR

Testing the integration of RouterRegistry pattern into the application.

Reference: Follow-up work from Phase 2.3 OCP
"""

import gc

import pytest


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


class TestRouterRegistryIntegration:
    """Test RouterRegistry integration with application routers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()
        # Reset global registry
        from mcp_server_langgraph.api.router_registry import reset_router_registry

        reset_router_registry()

    def test_default_routers_registered(self):
        """
        GIVEN: Application router registration
        WHEN: Getting default routers
        THEN: Should include all core routers
        """
        from mcp_server_langgraph.api.router_registry import (
            get_router_registry,
            reset_router_registry,
        )
        from mcp_server_langgraph.api.routers import register_default_routers

        # Arrange
        reset_router_registry()
        registry = get_router_registry()

        # Act
        register_default_routers(registry)
        routers = registry.get_all()

        # Assert - should have core routers
        prefixes = [r.prefix for r in routers]
        assert "" in prefixes or any("health" in str(r.tags) for r in routers)

    def test_v1_router_registered_with_prefix(self):
        """
        GIVEN: Application router registration
        WHEN: Getting v1 router
        THEN: Should have /api/v1 prefix
        """
        from mcp_server_langgraph.api.router_registry import (
            get_router_registry,
            reset_router_registry,
        )
        from mcp_server_langgraph.api.routers import register_default_routers

        # Arrange
        reset_router_registry()
        registry = get_router_registry()

        # Act
        register_default_routers(registry)
        routers = registry.get_all()

        # Assert - v1 router should have prefix
        v1_routers = [r for r in routers if r.prefix == "/api/v1"]
        assert len(v1_routers) == 1

    def test_registry_can_be_extended(self):
        """
        GIVEN: Application router registration
        WHEN: Adding custom router after default registration
        THEN: Custom router should be included
        """
        from fastapi import APIRouter

        from mcp_server_langgraph.api.router_registry import (
            get_router_registry,
            reset_router_registry,
        )
        from mcp_server_langgraph.api.routers import register_default_routers

        # Arrange
        reset_router_registry()
        registry = get_router_registry()
        register_default_routers(registry)
        initial_count = len(registry.get_all())

        # Act - add custom router
        custom_router = APIRouter()
        registry.register(custom_router, prefix="/custom", tags=["custom"])

        # Assert
        assert len(registry.get_all()) == initial_count + 1
        custom_routers = [r for r in registry.get_all() if r.prefix == "/custom"]
        assert len(custom_routers) == 1
