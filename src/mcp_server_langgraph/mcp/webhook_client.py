"""
Webhook Client for Hook Event Delivery.

Provides HTTP webhook delivery for registered hooks with:
- Async POST requests using shared HttpClientManager
- Retry logic with exponential backoff
- Timeout handling
- Request signing (HMAC-SHA256) for security
- OpenTelemetry tracing

Usage:
    from mcp_server_langgraph.mcp.webhook_client import (
        WebhookClient,
        create_webhook_callback,
    )

    # Create callback for hook registration
    callback = create_webhook_callback(
        webhook_url="https://hooks.example.com/events",
        secret="shared-secret-123",
    )

    # Register with hook registry
    registry.register(
        event=HookEvent.PRE_TOOL_USE,
        matcher=HookMatcher(hooks=[callback]),
    )
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from opentelemetry import trace

from mcp_server_langgraph.core.http_client import get_http_client_manager
from mcp_server_langgraph.core.hooks import HookResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class WebhookConfig:
    """Configuration for webhook delivery.

    Attributes:
        webhook_url: Target URL for webhook POST
        secret: Optional shared secret for HMAC signing
        timeout: Request timeout in seconds (default: 10.0)
        max_retries: Maximum retry attempts (default: 3)
        retry_base_delay: Base delay for exponential backoff (default: 0.5s)
    """

    webhook_url: str
    secret: str | None = None
    timeout: float = 10.0
    max_retries: int = 3
    retry_base_delay: float = 0.5


@dataclass
class WebhookPayload:
    """Payload sent to webhook endpoint.

    Attributes:
        event: Hook event type (e.g., "PRE_TOOL_USE")
        timestamp: ISO timestamp of event
        tool_name: Tool name being invoked (if applicable)
        tool_use_id: Unique tool invocation ID
        input_data: Tool input arguments
        context: Hook context (session_id, user_id, etc.)
    """

    event: str
    timestamp: str
    tool_name: str | None = None
    tool_use_id: str | None = None
    input_data: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert payload to dictionary."""
        return {
            "event": self.event,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_use_id": self.tool_use_id,
            "input_data": self.input_data,
            "context": self.context,
        }


class WebhookClient:
    """HTTP client for delivering webhook events.

    Uses the shared HttpClientManager for connection pooling.
    Provides retry logic and optional HMAC signing.
    """

    def __init__(self, config: WebhookConfig) -> None:
        """Initialize webhook client.

        Args:
            config: Webhook configuration
        """
        self.config = config
        self._http_manager = get_http_client_manager()

    def _compute_signature(self, payload_bytes: bytes) -> str:
        """Compute HMAC-SHA256 signature for payload.

        Args:
            payload_bytes: JSON payload bytes

        Returns:
            Hex-encoded signature string
        """
        if not self.config.secret:
            return ""

        signature = hmac.new(
            self.config.secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        )
        return f"sha256={signature.hexdigest()}"

    async def deliver(self, payload: WebhookPayload) -> bool:
        """Deliver webhook payload to configured endpoint.

        Args:
            payload: Webhook payload to deliver

        Returns:
            True if delivery succeeded, False otherwise

        Raises:
            No exceptions - failures are logged and return False
        """
        with tracer.start_as_current_span(
            "webhook.deliver",
            attributes={
                "webhook.url": self.config.webhook_url,
                "webhook.event": payload.event,
            },
        ) as span:
            payload_dict = payload.to_dict()
            payload_json = json.dumps(payload_dict, default=str)
            payload_bytes = payload_json.encode("utf-8")

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": payload.event,
                "X-Webhook-Timestamp": payload.timestamp,
            }

            # Add signature if secret is configured
            if self.config.secret:
                headers["X-Webhook-Signature"] = self._compute_signature(payload_bytes)

            client = await self._http_manager.get_client()
            last_error: Exception | None = None

            for attempt in range(self.config.max_retries):
                try:
                    response = await client.post(
                        self.config.webhook_url,
                        content=payload_bytes,
                        headers=headers,
                        timeout=self.config.timeout,
                    )

                    if response.is_success:
                        span.set_attribute("webhook.status_code", response.status_code)
                        span.set_attribute("webhook.attempt", attempt + 1)
                        logger.debug(
                            "Webhook delivered successfully",
                            extra={
                                "url": self.config.webhook_url,
                                "event": payload.event,
                                "status_code": response.status_code,
                                "attempt": attempt + 1,
                            },
                        )
                        return True

                    # Non-success status - may retry for 5xx
                    if response.status_code >= 500:
                        last_error = Exception(f"Server error: {response.status_code}")
                        logger.warning(
                            "Webhook server error, retrying",
                            extra={
                                "url": self.config.webhook_url,
                                "status_code": response.status_code,
                                "attempt": attempt + 1,
                            },
                        )
                    else:
                        # Client error (4xx) - don't retry
                        span.set_attribute("webhook.status_code", response.status_code)
                        span.set_attribute("webhook.error", f"Client error: {response.status_code}")
                        logger.error(
                            "Webhook client error",
                            extra={
                                "url": self.config.webhook_url,
                                "status_code": response.status_code,
                            },
                        )
                        return False

                except Exception as e:
                    last_error = e
                    logger.warning(
                        "Webhook delivery failed, retrying",
                        extra={
                            "url": self.config.webhook_url,
                            "error": str(e),
                            "attempt": attempt + 1,
                        },
                    )

                # Exponential backoff before retry
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_base_delay * (2**attempt)
                    await _async_sleep(delay)

            # All retries exhausted
            span.set_attribute("webhook.error", str(last_error) if last_error else "Unknown")
            span.set_attribute("webhook.retries_exhausted", True)
            logger.error(
                "Webhook delivery failed after all retries",
                extra={
                    "url": self.config.webhook_url,
                    "event": payload.event,
                    "max_retries": self.config.max_retries,
                    "last_error": str(last_error),
                },
            )
            return False


async def _async_sleep(seconds: float) -> None:
    """Async sleep wrapper for easier testing."""
    import asyncio

    await asyncio.sleep(seconds)


def create_webhook_callback(
    webhook_url: str,
    event_name: str,
    secret: str | None = None,
    timeout: float = 10.0,
    max_retries: int = 3,
) -> Any:
    """Create a webhook callback function for hook registration.

    Creates an async callback that can be registered with the hook registry.
    The callback will POST hook events to the specified webhook URL.

    Args:
        webhook_url: Target URL for webhook POST
        event_name: Hook event name (e.g., "PRE_TOOL_USE")
        secret: Optional shared secret for HMAC signing
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Async callback function compatible with HookRegistry

    Example:
        callback = create_webhook_callback(
            webhook_url="https://hooks.example.com/events",
            event_name="PRE_TOOL_USE",
            secret="shared-secret",
        )
        registry.register(
            event=HookEvent.PRE_TOOL_USE,
            matcher=HookMatcher(hooks=[callback]),
        )
    """
    config = WebhookConfig(
        webhook_url=webhook_url,
        secret=secret,
        timeout=timeout,
        max_retries=max_retries,
    )
    client = WebhookClient(config)

    async def webhook_callback(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: Any,
    ) -> HookResult:
        """Webhook callback that POSTs to the configured URL.

        Args:
            input_data: Tool input arguments
            tool_use_id: Unique tool invocation ID
            context: Hook context (HookContext)

        Returns:
            HookResult with behavior="allow" (webhooks are fire-and-forget)
        """
        # Build context dict from HookContext
        context_dict: dict[str, Any] = {}
        if context is not None:
            if hasattr(context, "session_id"):
                context_dict["session_id"] = context.session_id
            if hasattr(context, "user_id"):
                context_dict["user_id"] = context.user_id
            if hasattr(context, "request_id"):
                context_dict["request_id"] = context.request_id
            if hasattr(context, "metadata"):
                context_dict["metadata"] = context.metadata

        # Extract tool name from input_data if available
        tool_name = input_data.get("tool_name") if isinstance(input_data, dict) else None

        payload = WebhookPayload(
            event=event_name,
            timestamp=datetime.now(UTC).isoformat(),
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            input_data=input_data if isinstance(input_data, dict) else {"data": input_data},
            context=context_dict,
        )

        # Fire and forget - don't block on webhook delivery
        # We allow the hook to proceed regardless of webhook success
        success = await client.deliver(payload)

        if not success:
            logger.warning(
                "Webhook delivery failed but allowing hook to proceed",
                extra={"event": event_name, "webhook_url": webhook_url},
            )

        return HookResult(behavior="allow")

    return webhook_callback
