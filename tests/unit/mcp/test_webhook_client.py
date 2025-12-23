"""
Unit tests for Webhook Client.

Tests the webhook delivery system:
- WebhookClient initialization and configuration
- Payload construction
- HMAC-SHA256 signing
- Delivery with retries
- create_webhook_callback factory

TDD: Tests written FIRST.
"""

from __future__ import annotations

import gc
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.mcp,
]


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def mock_http_manager(mock_http_client):
    """Create a mock HTTP client manager."""
    manager = MagicMock()
    manager.get_client = AsyncMock(return_value=mock_http_client)
    return manager


@pytest.mark.xdist_group(name="webhook_client")
class TestWebhookPayload:
    """Tests for WebhookPayload dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_payload_to_dict_includes_all_fields(self) -> None:
        """
        GIVEN a WebhookPayload with all fields
        WHEN calling to_dict()
        THEN should include all fields in output.
        """
        from mcp_server_langgraph.mcp.webhook_client import WebhookPayload

        payload = WebhookPayload(
            event="PRE_TOOL_USE",
            timestamp="2025-01-01T00:00:00Z",
            tool_name="read_file",
            tool_use_id="tool-123",
            input_data={"path": "/tmp/test.txt"},
            context={"session_id": "session-456"},
        )

        result = payload.to_dict()

        assert result["event"] == "PRE_TOOL_USE"
        assert result["timestamp"] == "2025-01-01T00:00:00Z"
        assert result["tool_name"] == "read_file"
        assert result["tool_use_id"] == "tool-123"
        assert result["input_data"] == {"path": "/tmp/test.txt"}
        assert result["context"] == {"session_id": "session-456"}

    def test_payload_to_dict_handles_none_values(self) -> None:
        """
        GIVEN a WebhookPayload with optional fields as None
        WHEN calling to_dict()
        THEN should include None values.
        """
        from mcp_server_langgraph.mcp.webhook_client import WebhookPayload

        payload = WebhookPayload(
            event="SESSION_START",
            timestamp="2025-01-01T00:00:00Z",
        )

        result = payload.to_dict()

        assert result["event"] == "SESSION_START"
        assert result["tool_name"] is None
        assert result["tool_use_id"] is None
        assert result["input_data"] == {}
        assert result["context"] == {}


@pytest.mark.xdist_group(name="webhook_client")
class TestWebhookClientSignature:
    """Tests for HMAC signature computation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_compute_signature_returns_empty_without_secret(self) -> None:
        """
        GIVEN a WebhookClient without secret
        WHEN computing signature
        THEN should return empty string.
        """
        from mcp_server_langgraph.mcp.webhook_client import (
            WebhookClient,
            WebhookConfig,
        )

        config = WebhookConfig(
            webhook_url="https://example.com/webhook",
            secret=None,
        )
        client = WebhookClient(config)

        signature = client._compute_signature(b'{"test": "data"}')

        assert signature == ""

    def test_compute_signature_with_secret(self) -> None:
        """
        GIVEN a WebhookClient with secret
        WHEN computing signature
        THEN should return valid HMAC-SHA256 signature.
        """
        from mcp_server_langgraph.mcp.webhook_client import (
            WebhookClient,
            WebhookConfig,
        )

        config = WebhookConfig(
            webhook_url="https://example.com/webhook",
            secret="my-secret-key",
        )
        client = WebhookClient(config)

        payload = b'{"test": "data"}'
        signature = client._compute_signature(payload)

        # Verify signature format
        assert signature.startswith("sha256=")

        # Verify signature is correct
        expected = hmac.new(
            b"my-secret-key",
            payload,
            hashlib.sha256,
        ).hexdigest()
        assert signature == f"sha256={expected}"


@pytest.mark.xdist_group(name="webhook_client")
class TestWebhookClientDelivery:
    """Tests for webhook delivery."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_deliver_success(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN a successful HTTP response
        WHEN delivering webhook
        THEN should return True.
        """
        from mcp_server_langgraph.mcp.webhook_client import (
            WebhookClient,
            WebhookConfig,
            WebhookPayload,
        )

        # Setup successful response
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_http_client.post.return_value = mock_response

        config = WebhookConfig(
            webhook_url="https://example.com/webhook",
        )

        with patch(
            "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
            return_value=mock_http_manager,
        ):
            client = WebhookClient(config)

            payload = WebhookPayload(
                event="PRE_TOOL_USE",
                timestamp="2025-01-01T00:00:00Z",
            )

            result = await client.deliver(payload)

        assert result is True
        mock_http_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_deliver_includes_headers(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN a webhook delivery
        WHEN sending request
        THEN should include proper headers.
        """
        from mcp_server_langgraph.mcp.webhook_client import (
            WebhookClient,
            WebhookConfig,
            WebhookPayload,
        )

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_http_client.post.return_value = mock_response

        config = WebhookConfig(
            webhook_url="https://example.com/webhook",
            secret="test-secret",
        )

        with patch(
            "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
            return_value=mock_http_manager,
        ):
            client = WebhookClient(config)

            payload = WebhookPayload(
                event="POST_TOOL_USE",
                timestamp="2025-01-01T12:00:00Z",
            )

            await client.deliver(payload)

        call_kwargs = mock_http_client.post.call_args.kwargs
        headers = call_kwargs["headers"]

        assert headers["Content-Type"] == "application/json"
        assert headers["X-Webhook-Event"] == "POST_TOOL_USE"
        assert headers["X-Webhook-Timestamp"] == "2025-01-01T12:00:00Z"
        assert "X-Webhook-Signature" in headers
        assert headers["X-Webhook-Signature"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_deliver_retries_on_server_error(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN a 500 server error followed by success
        WHEN delivering webhook
        THEN should retry and succeed.
        """
        from mcp_server_langgraph.mcp.webhook_client import (
            WebhookClient,
            WebhookConfig,
            WebhookPayload,
        )

        # First call fails, second succeeds
        error_response = MagicMock()
        error_response.is_success = False
        error_response.status_code = 500

        success_response = MagicMock()
        success_response.is_success = True
        success_response.status_code = 200

        mock_http_client.post.side_effect = [error_response, success_response]

        config = WebhookConfig(
            webhook_url="https://example.com/webhook",
            max_retries=3,
            retry_base_delay=0.01,  # Fast for testing
        )

        with (
            patch(
                "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
                return_value=mock_http_manager,
            ),
            patch(
                "mcp_server_langgraph.mcp.webhook_client._async_sleep",
                new_callable=AsyncMock,
            ),
        ):
            client = WebhookClient(config)

            payload = WebhookPayload(
                event="PRE_TOOL_USE",
                timestamp="2025-01-01T00:00:00Z",
            )

            result = await client.deliver(payload)

        assert result is True
        assert mock_http_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_deliver_no_retry_on_client_error(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN a 400 client error
        WHEN delivering webhook
        THEN should NOT retry.
        """
        from mcp_server_langgraph.mcp.webhook_client import (
            WebhookClient,
            WebhookConfig,
            WebhookPayload,
        )

        error_response = MagicMock()
        error_response.is_success = False
        error_response.status_code = 400

        mock_http_client.post.return_value = error_response

        config = WebhookConfig(
            webhook_url="https://example.com/webhook",
            max_retries=3,
        )

        with patch(
            "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
            return_value=mock_http_manager,
        ):
            client = WebhookClient(config)

            payload = WebhookPayload(
                event="PRE_TOOL_USE",
                timestamp="2025-01-01T00:00:00Z",
            )

            result = await client.deliver(payload)

        assert result is False
        assert mock_http_client.post.call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_deliver_returns_false_after_max_retries(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN persistent server errors
        WHEN max retries exhausted
        THEN should return False.
        """
        from mcp_server_langgraph.mcp.webhook_client import (
            WebhookClient,
            WebhookConfig,
            WebhookPayload,
        )

        error_response = MagicMock()
        error_response.is_success = False
        error_response.status_code = 503

        mock_http_client.post.return_value = error_response

        config = WebhookConfig(
            webhook_url="https://example.com/webhook",
            max_retries=3,
            retry_base_delay=0.01,
        )

        with (
            patch(
                "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
                return_value=mock_http_manager,
            ),
            patch(
                "mcp_server_langgraph.mcp.webhook_client._async_sleep",
                new_callable=AsyncMock,
            ),
        ):
            client = WebhookClient(config)

            payload = WebhookPayload(
                event="PRE_TOOL_USE",
                timestamp="2025-01-01T00:00:00Z",
            )

            result = await client.deliver(payload)

        assert result is False
        assert mock_http_client.post.call_count == 3


@pytest.mark.xdist_group(name="webhook_client")
class TestCreateWebhookCallback:
    """Tests for create_webhook_callback factory."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_callback_returns_hook_result(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN a webhook callback
        WHEN called with input data
        THEN should return HookResult with allow behavior.
        """
        from mcp_server_langgraph.mcp.webhook_client import create_webhook_callback

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_http_client.post.return_value = mock_response

        with patch(
            "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
            return_value=mock_http_manager,
        ):
            callback = create_webhook_callback(
                webhook_url="https://example.com/webhook",
                event_name="PRE_TOOL_USE",
            )

            result = await callback(
                input_data={"tool_name": "read_file", "path": "/tmp/test.txt"},
                tool_use_id="tool-123",
                context=None,
            )

        assert result.behavior == "allow"

    @pytest.mark.asyncio
    async def test_callback_extracts_context(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN a webhook callback with HookContext
        WHEN called
        THEN should include context in payload.
        """
        from mcp_server_langgraph.mcp.webhook_client import create_webhook_callback

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_http_client.post.return_value = mock_response

        # Create mock context
        mock_context = MagicMock()
        mock_context.session_id = "session-123"
        mock_context.user_id = "user-456"
        mock_context.request_id = "request-789"
        mock_context.metadata = {"key": "value"}

        with patch(
            "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
            return_value=mock_http_manager,
        ):
            callback = create_webhook_callback(
                webhook_url="https://example.com/webhook",
                event_name="POST_TOOL_USE",
            )

            await callback(
                input_data={"result": "success"},
                tool_use_id="tool-999",
                context=mock_context,
            )

        # Verify context was included in payload
        call_kwargs = mock_http_client.post.call_args.kwargs
        payload_bytes = call_kwargs["content"]
        payload = json.loads(payload_bytes)

        assert payload["context"]["session_id"] == "session-123"
        assert payload["context"]["user_id"] == "user-456"
        assert payload["context"]["request_id"] == "request-789"
        assert payload["context"]["metadata"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_callback_allows_on_delivery_failure(self, mock_http_manager, mock_http_client) -> None:
        """
        GIVEN a failed webhook delivery
        WHEN callback is called
        THEN should still return allow (fire-and-forget).
        """
        from mcp_server_langgraph.mcp.webhook_client import create_webhook_callback

        # Simulate failure
        mock_http_client.post.side_effect = Exception("Network error")

        with (
            patch(
                "mcp_server_langgraph.mcp.webhook_client.get_http_client_manager",
                return_value=mock_http_manager,
            ),
            patch(
                "mcp_server_langgraph.mcp.webhook_client._async_sleep",
                new_callable=AsyncMock,
            ),
        ):
            callback = create_webhook_callback(
                webhook_url="https://example.com/webhook",
                event_name="PRE_TOOL_USE",
            )

            result = await callback(
                input_data={"test": "data"},
                tool_use_id="tool-123",
                context=None,
            )

        # Should still allow - webhooks are fire-and-forget
        assert result.behavior == "allow"
