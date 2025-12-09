"""
MCP Resources Protocol Handler (2025-06-18 Spec).

Implements resources/list and resources/read for servers to expose
data and context to clients. Resources are read-only data endpoints.

Reference: https://modelcontextprotocol.io/specification/2025-06-18/server/resources
"""

import fnmatch
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field


class Resource(BaseModel):
    """A resource exposed by the server."""

    uri: str
    name: str
    description: str | None = None
    mimeType: str | None = None


class ResourceContent(BaseModel):
    """Content returned when reading a resource."""

    uri: str
    mimeType: str | None = None
    text: str | None = None  # For text content
    blob: str | None = None  # For binary content (base64)


class ResourceTemplate(BaseModel):
    """Template for dynamic resource URIs."""

    uriTemplate: str
    name: str
    description: str | None = None
    mimeType: str | None = None


class ResourcesListResponse(BaseModel):
    """Response for resources/list."""

    resources: list[Resource] = Field(default_factory=list)

    def to_jsonrpc(self, request_id: int) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 response format."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": [r.model_dump() for r in self.resources],
            },
        }


class ResourceReadResponse(BaseModel):
    """Response for resources/read."""

    contents: list[ResourceContent] = Field(default_factory=list)

    def to_jsonrpc(self, request_id: int) -> dict[str, Any]:
        """Convert to JSON-RPC 2.0 response format."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "contents": [c.model_dump() for c in self.contents],
            },
        }


# Type alias for resource provider functions
ResourceProvider = Callable[[str], Awaitable[ResourceContent]]


class ResourceHandler:
    """Handler for managing MCP resources."""

    def __init__(self) -> None:
        """Initialize the resource handler."""
        self._resources: dict[str, Resource] = {}
        self._templates: dict[str, ResourceTemplate] = {}
        self._providers: dict[str, ResourceProvider] = {}
        self._subscriptions: dict[str, tuple[str, Callable[..., Any]]] = {}

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> Resource:
        """Register a new resource.

        Args:
            uri: Unique resource URI
            name: Human-readable resource name
            description: Optional resource description
            mime_type: Optional MIME type

        Returns:
            Registered Resource object
        """
        resource = Resource(
            uri=uri,
            name=name,
            description=description,
            mimeType=mime_type,
        )
        self._resources[uri] = resource
        return resource

    def register_template(
        self,
        uri_template: str,
        name: str,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> ResourceTemplate:
        """Register a resource template.

        Args:
            uri_template: URI template with placeholders (e.g., "session/{session_id}/traces")
            name: Human-readable template name
            description: Optional description
            mime_type: Optional MIME type

        Returns:
            Registered ResourceTemplate object
        """
        template = ResourceTemplate(
            uriTemplate=uri_template,
            name=name,
            description=description,
            mimeType=mime_type,
        )
        self._templates[uri_template] = template
        return template

    def register_provider(
        self,
        uri_pattern: str,
        provider: ResourceProvider,
    ) -> None:
        """Register a provider function for a URI pattern.

        Args:
            uri_pattern: Glob pattern for matching URIs (e.g., "playground://session/*/traces")
            provider: Async function that returns ResourceContent for matching URIs
        """
        self._providers[uri_pattern] = provider

    def has_provider(self, uri: str) -> bool:
        """Check if a provider exists for the given URI.

        Args:
            uri: Resource URI to check

        Returns:
            True if a matching provider exists
        """
        return any(fnmatch.fnmatch(uri, pattern) for pattern in self._providers)

    def list_resources(self, filter_pattern: str | None = None) -> list[Resource]:
        """List all registered resources.

        Args:
            filter_pattern: Optional glob pattern to filter resources

        Returns:
            List of matching resources
        """
        if filter_pattern is None:
            return list(self._resources.values())

        return [resource for resource in self._resources.values() if fnmatch.fnmatch(resource.uri, filter_pattern)]

    def list_templates(self) -> list[ResourceTemplate]:
        """List all registered resource templates.

        Returns:
            List of resource templates
        """
        return list(self._templates.values())

    async def read_resource(self, uri: str) -> ResourceContent:
        """Read a resource by URI.

        Args:
            uri: Resource URI to read

        Returns:
            ResourceContent with data

        Raises:
            ValueError: If resource not found or no provider available
        """
        # Find matching provider
        for pattern, provider in self._providers.items():
            if fnmatch.fnmatch(uri, pattern):
                return await provider(uri)

        raise ValueError(f"Resource not found: {uri}")

    def expand_template(
        self,
        uri_template: str,
        args: dict[str, str],
    ) -> str:
        """Expand a URI template with arguments.

        Args:
            uri_template: Template with placeholders
            args: Dictionary of placeholder values

        Returns:
            Expanded URI string
        """
        result = uri_template
        for key, value in args.items():
            result = result.replace(f"{{{key}}}", value)
        return result

    def subscribe(
        self,
        uri: str,
        callback: Callable[..., Any],
    ) -> str:
        """Subscribe to resource changes.

        Args:
            uri: Resource URI to subscribe to
            callback: Function to call when resource changes

        Returns:
            Subscription ID
        """
        subscription_id = str(uuid.uuid4())
        self._subscriptions[subscription_id] = (uri, callback)
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from resource changes.

        Args:
            subscription_id: ID of subscription to cancel
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]

    def has_subscription(self, subscription_id: str) -> bool:
        """Check if a subscription exists.

        Args:
            subscription_id: Subscription ID to check

        Returns:
            True if subscription exists
        """
        return subscription_id in self._subscriptions

    async def notify_change(self, uri: str) -> None:
        """Notify subscribers of a resource change.

        Args:
            uri: URI of changed resource
        """
        for subscribed_uri, callback in self._subscriptions.values():
            if subscribed_uri == uri or fnmatch.fnmatch(uri, subscribed_uri):
                # Call the callback (async if needed)
                if callable(callback):
                    result = callback(uri)
                    # If it's a coroutine, await it
                    if hasattr(result, "__await__"):
                        await result


# =============================================================================
# Playground Resource Factory
# =============================================================================


def create_playground_resource_handler() -> ResourceHandler:
    """Create a ResourceHandler configured for Playground resources.

    Returns:
        ResourceHandler with Playground resource templates registered
    """
    handler = ResourceHandler()

    # Register session resource templates
    handler.register_template(
        uri_template="playground://session/{session_id}/traces",
        name="Session Traces",
        description="OpenTelemetry traces for a specific session",
        mime_type="application/json",
    )

    handler.register_template(
        uri_template="playground://session/{session_id}/logs",
        name="Session Logs",
        description="Structured logs for a specific session",
        mime_type="application/json",
    )

    handler.register_template(
        uri_template="playground://session/{session_id}/metrics",
        name="Session Metrics",
        description="LLM and tool metrics for a specific session",
        mime_type="application/json",
    )

    handler.register_template(
        uri_template="playground://session/{session_id}/alerts",
        name="Session Alerts",
        description="Active alerts for a specific session",
        mime_type="application/json",
    )

    return handler


# =============================================================================
# Resource Providers for Playground
# =============================================================================


async def traces_provider(uri: str) -> ResourceContent:
    """Provider for session traces resource.

    Args:
        uri: Resource URI

    Returns:
        ResourceContent with trace data
    """
    # Extract session_id from URI
    parts = uri.replace("playground://session/", "").split("/")
    session_id = parts[0] if parts else "unknown"

    # In production, this would fetch from the observability backend
    return ResourceContent(
        uri=uri,
        mimeType="application/json",
        text=f'{{"session_id": "{session_id}", "traces": []}}',
    )


async def logs_provider(uri: str) -> ResourceContent:
    """Provider for session logs resource.

    Args:
        uri: Resource URI

    Returns:
        ResourceContent with log data
    """
    parts = uri.replace("playground://session/", "").split("/")
    session_id = parts[0] if parts else "unknown"

    return ResourceContent(
        uri=uri,
        mimeType="application/json",
        text=f'{{"session_id": "{session_id}", "logs": []}}',
    )


async def metrics_provider(uri: str) -> ResourceContent:
    """Provider for session metrics resource.

    Args:
        uri: Resource URI

    Returns:
        ResourceContent with metrics data
    """
    parts = uri.replace("playground://session/", "").split("/")
    session_id = parts[0] if parts else "unknown"

    return ResourceContent(
        uri=uri,
        mimeType="application/json",
        text=f'{{"session_id": "{session_id}", "metrics": {{"llm_calls": 0, "tool_calls": 0}}}}',
    )


async def alerts_provider(uri: str) -> ResourceContent:
    """Provider for session alerts resource.

    Args:
        uri: Resource URI

    Returns:
        ResourceContent with alert data
    """
    parts = uri.replace("playground://session/", "").split("/")
    session_id = parts[0] if parts else "unknown"

    return ResourceContent(
        uri=uri,
        mimeType="application/json",
        text=f'{{"session_id": "{session_id}", "alerts": []}}',
    )
