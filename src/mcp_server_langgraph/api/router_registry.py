"""
RouterRegistry - Dynamic router registration pattern.

Created as part of Phase 2.3 OCP refactoring.

Responsibilities:
- Centralize router registration
- Provide registry for dynamic router mounting
- Support testing via registry isolation

Reference: Plan - Phase 2.3 OCP: Router Registry Pattern
"""

from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, FastAPI


@dataclass
class RouterDefinition:
    """
    Definition of a router to be mounted.

    Encapsulates router instance with its mounting configuration.
    """

    router: APIRouter
    prefix: str = ""
    tags: list[str | Enum] | None = None


class RouterRegistry:
    """
    Registry for dynamic router registration.

    Provides a centralized way to register and mount routers,
    enabling better testability and extensibility.

    Example:
        >>> registry = RouterRegistry()
        >>> registry.register(health_router, prefix="/health", tags=["health"])
        >>> registry.register(api_router, prefix="/api/v1", tags=["api"])
        >>> registry.mount_all(app)
    """

    def __init__(self) -> None:
        """Initialize empty router registry."""
        self._routers: list[RouterDefinition] = []

    def register(
        self,
        router: APIRouter,
        prefix: str = "",
        tags: list[str | Enum] | None = None,
    ) -> None:
        """
        Register a router with the registry.

        Args:
            router: FastAPI APIRouter instance
            prefix: URL prefix for the router (e.g., "/api/v1")
            tags: OpenAPI tags for the router
        """
        definition = RouterDefinition(
            router=router,
            prefix=prefix,
            tags=tags,
        )
        self._routers.append(definition)

    def get_all(self) -> list[RouterDefinition]:
        """
        Get all registered router definitions.

        Returns:
            List of RouterDefinition objects in registration order
        """
        return self._routers.copy()

    def mount_all(self, app: FastAPI) -> None:
        """
        Mount all registered routers to a FastAPI application.

        Args:
            app: FastAPI application instance
        """
        for definition in self._routers:
            app.include_router(
                definition.router,
                prefix=definition.prefix,
                tags=definition.tags,
            )

    def clear(self) -> None:
        """
        Clear all registered routers.

        Useful for testing to reset registry state.
        """
        self._routers.clear()


# Global registry instance for application use
_global_registry: RouterRegistry | None = None


def get_router_registry() -> RouterRegistry:
    """
    Get the global router registry instance.

    Returns:
        RouterRegistry singleton instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = RouterRegistry()
    return _global_registry


def reset_router_registry() -> None:
    """
    Reset the global router registry.

    Useful for testing to ensure clean state.
    """
    global _global_registry
    if _global_registry is not None:
        _global_registry.clear()
    _global_registry = None
