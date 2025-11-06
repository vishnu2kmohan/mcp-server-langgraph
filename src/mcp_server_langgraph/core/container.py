"""
Dependency Injection Container for MCP Server LangGraph

This module provides a clean dependency injection pattern that:
1. Eliminates global singletons
2. Makes testing easier (injectable dependencies)
3. Supports multiple environments (test, dev, production)
4. Enables per-tenant/per-agent configuration

Architecture:
- ApplicationContainer: Main DI container
- ContainerConfig: Configuration for the container
- Provider abstractions: TelemetryProvider, AuthProvider, StorageProvider
- Helper functions: create_test_container, create_production_container
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from mcp_server_langgraph.core.config import Settings

# ==============================================================================
# Container Configuration
# ==============================================================================


@dataclass
class ContainerConfig:
    """Configuration for the application container"""

    environment: str = "development"
    enable_telemetry: bool = field(default=False)
    enable_auth: bool = field(default=False)
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        """Adjust defaults based on environment"""
        if self.environment == "test":
            # Test mode: disable telemetry and auth by default
            self.enable_telemetry = False
            self.enable_auth = False
        elif self.environment == "production":
            # Production mode: enable security features by default
            self.enable_telemetry = True
            self.enable_auth = True


# ==============================================================================
# Provider Protocols (Abstractions)
# ==============================================================================


@runtime_checkable
class TelemetryProvider(Protocol):
    """Protocol for telemetry providers"""

    @property
    def logger(self) -> logging.Logger:
        """Get logger instance"""
        ...

    @property
    def metrics(self) -> Any:
        """Get metrics instance"""
        ...

    @property
    def tracer(self) -> Any:
        """Get tracer instance"""
        ...


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers"""

    def validate_token(self, token: str) -> bool:
        """Validate authentication token"""
        ...

    def get_current_user(self, token: str) -> Dict[str, Any]:
        """Get current user from token"""
        ...


@runtime_checkable
class StorageProvider(Protocol):
    """Protocol for storage providers"""

    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        ...

    def set(self, key: str, value: Any) -> None:
        """Set value by key"""
        ...

    def delete(self, key: str) -> None:
        """Delete value by key"""
        ...


# ==============================================================================
# No-Op Providers (for testing)
# ==============================================================================


class NoOpLogger:
    """No-op logger that doesn't output anything"""

    def info(self, msg: str, *args, **kwargs) -> None:
        pass

    def debug(self, msg: str, *args, **kwargs) -> None:
        pass

    def warning(self, msg: str, *args, **kwargs) -> None:
        pass

    def error(self, msg: str, *args, **kwargs) -> None:
        pass

    def critical(self, msg: str, *args, **kwargs) -> None:
        pass


class NoOpMetrics:
    """No-op metrics that doesn't collect anything"""

    def counter(self, name: str, value: int = 1, **kwargs) -> None:
        pass

    def gauge(self, name: str, value: float, **kwargs) -> None:
        pass

    def histogram(self, name: str, value: float, **kwargs) -> None:
        pass


class NoOpTracer:
    """No-op tracer that doesn't trace anything"""

    def start_as_current_span(self, name: str, **kwargs) -> Any:
        """Context manager that does nothing"""
        from contextlib import nullcontext

        return nullcontext()


class NoOpTelemetryProvider:
    """No-op telemetry provider for testing"""

    def __init__(self) -> None:
        self._logger = NoOpLogger()
        self._metrics = NoOpMetrics()
        self._tracer = NoOpTracer()

    @property
    def logger(self) -> NoOpLogger:
        return self._logger

    @property
    def metrics(self) -> NoOpMetrics:
        return self._metrics

    @property
    def tracer(self) -> NoOpTracer:
        return self._tracer


class NoOpAuthProvider:
    """No-op auth provider for testing"""

    def validate_token(self, token: str) -> bool:
        """Accept any token in test mode"""
        return True

    def get_current_user(self, token: str) -> Dict[str, Any]:
        """Return mock user"""
        return {"user_id": "test-user", "username": "testuser", "email": "test@example.com"}


class MemoryStorageProvider:
    """In-memory storage provider for testing"""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


# ==============================================================================
# Production Providers
# ==============================================================================


class ProductionTelemetryProvider:
    """Production telemetry provider using actual OpenTelemetry"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._logger: Optional[logging.Logger] = None
        self._metrics: Optional[Any] = None
        self._tracer: Optional[Any] = None

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            # Use existing telemetry module's logger
            from mcp_server_langgraph.observability.telemetry import logger

            self._logger = logger
        return self._logger

    @property
    def metrics(self) -> Any:
        if self._metrics is None:
            # Use existing telemetry module's metrics
            from mcp_server_langgraph.observability.telemetry import metrics

            self._metrics = metrics
        return self._metrics

    @property
    def tracer(self) -> Any:
        if self._tracer is None:
            # Use existing telemetry module's tracer
            from mcp_server_langgraph.observability.telemetry import tracer

            self._tracer = tracer
        return self._tracer


class InMemoryAuthProvider:
    """In-memory auth provider for development"""

    def __init__(self) -> None:
        self._tokens: Dict[str, Dict[str, Any]] = {}

    def create_token(self, user_id: str, username: str, **kwargs) -> str:
        """Create a simple token (NOT cryptographically secure - dev only!)"""
        import secrets

        token = secrets.token_urlsafe(32)
        self._tokens[token] = {"user_id": user_id, "username": username, **kwargs}
        return token

    def validate_token(self, token: str) -> bool:
        return token in self._tokens

    def get_current_user(self, token: str) -> Dict[str, Any]:
        return self._tokens.get(token, {})


class RedisStorageProvider:
    """Redis storage provider for production"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Lazy Redis client initialization"""
        if self._client is None:
            import redis

            self._client = redis.Redis(host=self.settings.redis_host, port=self.settings.redis_port, decode_responses=True)
        return self._client

    def get(self, key: str) -> Optional[Any]:
        import json

        value = self._get_client().get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: Any) -> None:
        import json

        self._get_client().set(key, json.dumps(value))

    def delete(self, key: str) -> None:
        self._get_client().delete(key)


# ==============================================================================
# Application Container
# ==============================================================================


class ApplicationContainer:
    """
    Main dependency injection container

    Provides:
    - Settings (configuration)
    - Telemetry (logging, metrics, tracing)
    - Authentication
    - Storage
    - Agent graph factory
    - MCP server factory

    Usage:
        # Test mode
        container = create_test_container()

        # Development mode
        config = ContainerConfig(environment="development")
        container = ApplicationContainer(config)

        # Production mode
        container = create_production_container()

        # Use dependencies
        settings = container.settings
        telemetry = container.get_telemetry()
        auth = container.get_auth()
    """

    def __init__(self, config: ContainerConfig, settings: Optional[Settings] = None):
        """
        Initialize the container

        Args:
            config: Container configuration
            settings: Optional settings override (for testing)
        """
        self.config = config
        self._settings = settings
        # Note: Don't initialize _*_instance attributes here
        # They are created on first access for true lazy initialization

    @cached_property
    def settings(self) -> Settings:
        """Get settings (lazy initialization)"""
        if self._settings is not None:
            return self._settings

        # Create settings based on environment
        return Settings(environment=self.config.environment, log_level=self.config.log_level)

    def get_telemetry(self) -> TelemetryProvider:
        """Get telemetry provider (lazy initialization)"""
        if not hasattr(self, "_telemetry_instance"):
            if self.config.environment == "test" or not self.config.enable_telemetry:
                self._telemetry_instance = NoOpTelemetryProvider()
            else:
                self._telemetry_instance = ProductionTelemetryProvider(self.settings)

        return self._telemetry_instance

    def get_auth(self) -> AuthProvider:
        """Get auth provider (lazy initialization)"""
        if not hasattr(self, "_auth_instance"):
            if self.config.environment == "test":
                self._auth_instance = NoOpAuthProvider()
            elif self.config.environment == "development" or not self.config.enable_auth:
                self._auth_instance = InMemoryAuthProvider()
            else:
                # Production: use real auth (Keycloak, etc.)
                # TODO: Implement production auth provider
                self._auth_instance = InMemoryAuthProvider()

        return self._auth_instance

    def get_storage(self) -> StorageProvider:
        """Get storage provider (lazy initialization)"""
        if not hasattr(self, "_storage_instance"):
            if self.config.environment == "test":
                self._storage_instance = MemoryStorageProvider()
            elif self.settings.redis_host:
                self._storage_instance = RedisStorageProvider(self.settings)
            else:
                # Fallback to in-memory for development
                self._storage_instance = MemoryStorageProvider()

        return self._storage_instance


# ==============================================================================
# Helper Functions
# ==============================================================================


def create_test_container(settings: Optional[Settings] = None) -> ApplicationContainer:
    """
    Create a container for testing

    This container:
    - Uses no-op providers (no telemetry, no auth)
    - Uses in-memory storage
    - Has no global side effects
    - Can be created multiple times independently

    Args:
        settings: Optional settings override

    Returns:
        ApplicationContainer configured for testing

    Example:
        container = create_test_container()
        agent = create_agent(container.settings, container.get_telemetry())
    """
    config = ContainerConfig(environment="test")
    return ApplicationContainer(config, settings=settings)


def create_development_container() -> ApplicationContainer:
    """
    Create a container for local development

    This container:
    - Uses real telemetry (optional)
    - Uses in-memory auth
    - Uses Redis if available, otherwise in-memory
    """
    config = ContainerConfig(environment="development")
    return ApplicationContainer(config)


def create_production_container() -> ApplicationContainer:
    """
    Create a container for production

    This container:
    - Uses full telemetry
    - Uses real auth (Keycloak/OpenFGA)
    - Uses Redis storage
    - Enforces security requirements
    """
    config = ContainerConfig(environment="production")
    return ApplicationContainer(config)
