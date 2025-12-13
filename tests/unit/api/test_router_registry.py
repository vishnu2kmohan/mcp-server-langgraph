"""
Unit tests for RouterRegistry pattern.

TDD Cycle: RED -> GREEN -> REFACTOR

Phase 2.3 OCP - Testing router registry for dynamic router registration.

Reference: Plan - Phase 2.3 OCP: Router Registry Pattern
"""

import gc

import pytest
from fastapi import APIRouter, FastAPI


# Mark as unit test
pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
]


@pytest.mark.xdist_group(name="test_router_registry")
class TestRouterRegistry:
    """Test RouterRegistry for dynamic router registration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_register_router_stores_in_registry(self):
        """
        GIVEN: RouterRegistry instance
        WHEN: Registering a router
        THEN: Router should be stored in registry
        """
        from mcp_server_langgraph.api.router_registry import RouterRegistry

        # Arrange
        registry = RouterRegistry()
        router = APIRouter()

        # Act
        registry.register(router, prefix="/api/test", tags=["test"])

        # Assert
        assert len(registry.get_all()) == 1

    def test_register_multiple_routers(self):
        """
        GIVEN: RouterRegistry instance
        WHEN: Registering multiple routers
        THEN: All routers should be stored
        """
        from mcp_server_langgraph.api.router_registry import RouterRegistry

        # Arrange
        registry = RouterRegistry()
        router1 = APIRouter()
        router2 = APIRouter()
        router3 = APIRouter()

        # Act
        registry.register(router1, prefix="/api/v1", tags=["v1"])
        registry.register(router2, prefix="/api/v2", tags=["v2"])
        registry.register(router3)  # No prefix or tags

        # Assert
        assert len(registry.get_all()) == 3

    def test_get_all_returns_router_definitions(self):
        """
        GIVEN: RouterRegistry with registered routers
        WHEN: Getting all routers
        THEN: Should return RouterDefinition objects
        """
        from mcp_server_langgraph.api.router_registry import RouterDefinition, RouterRegistry

        # Arrange
        registry = RouterRegistry()
        router = APIRouter()
        registry.register(router, prefix="/api/test", tags=["test"])

        # Act
        definitions = registry.get_all()

        # Assert
        assert len(definitions) == 1
        assert isinstance(definitions[0], RouterDefinition)
        assert definitions[0].router is router
        assert definitions[0].prefix == "/api/test"
        assert definitions[0].tags == ["test"]

    def test_mount_all_to_app(self):
        """
        GIVEN: RouterRegistry with routers and FastAPI app
        WHEN: Mounting all routers to app
        THEN: All routers should be included in app
        """
        from mcp_server_langgraph.api.router_registry import RouterRegistry

        # Arrange
        registry = RouterRegistry()
        router1 = APIRouter()
        router2 = APIRouter()

        @router1.get("/health")
        async def health():
            return {"status": "ok"}

        @router2.get("/items")
        async def items():
            return {"items": []}

        registry.register(router1, prefix="/api", tags=["health"])
        registry.register(router2, prefix="/api", tags=["items"])

        app = FastAPI()

        # Act
        registry.mount_all(app)

        # Assert - routes should be present
        routes = [route.path for route in app.routes]
        assert "/api/health" in routes
        assert "/api/items" in routes

    def test_router_definition_defaults(self):
        """
        GIVEN: RouterDefinition with minimal arguments
        WHEN: Creating a definition
        THEN: Should have sensible defaults
        """
        from mcp_server_langgraph.api.router_registry import RouterDefinition

        # Arrange
        router = APIRouter()

        # Act
        definition = RouterDefinition(router=router)

        # Assert
        assert definition.router is router
        assert definition.prefix == ""
        assert definition.tags is None

    def test_clear_registry_removes_all_routers(self):
        """
        GIVEN: RouterRegistry with routers
        WHEN: Clearing the registry
        THEN: Should remove all routers
        """
        from mcp_server_langgraph.api.router_registry import RouterRegistry

        # Arrange
        registry = RouterRegistry()
        registry.register(APIRouter(), prefix="/api/test")
        registry.register(APIRouter(), prefix="/api/other")
        assert len(registry.get_all()) == 2

        # Act
        registry.clear()

        # Assert
        assert len(registry.get_all()) == 0


@pytest.mark.xdist_group(name="test_router_registry")
class TestRouterRegistryOrdering:
    """Test RouterRegistry ordering behavior."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_routers_maintain_registration_order(self):
        """
        GIVEN: RouterRegistry with routers registered in order
        WHEN: Getting all routers
        THEN: Should maintain registration order
        """
        from mcp_server_langgraph.api.router_registry import RouterRegistry

        # Arrange
        registry = RouterRegistry()
        prefixes = ["/api/first", "/api/second", "/api/third"]

        for prefix in prefixes:
            registry.register(APIRouter(), prefix=prefix)

        # Act
        definitions = registry.get_all()

        # Assert
        retrieved_prefixes = [d.prefix for d in definitions]
        assert retrieved_prefixes == prefixes
