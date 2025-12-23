"""
Tests for can_use_tool callback in auth middleware.

Implements Claude Agent SDK can_use_tool pattern for dynamic tool
permission checks beyond static OpenFGA rules.
"""

import gc

import pytest
from unittest.mock import AsyncMock, patch

pytestmark = [pytest.mark.unit, pytest.mark.sdk]


@pytest.mark.xdist_group(name="can_use_tool_auth")
class TestCanUseTool:
    """Tests for can_use_tool callback pattern."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_auth_middleware_accepts_can_use_tool_callback(self) -> None:
        """AuthMiddleware should accept can_use_tool callback parameter."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        async def my_callback(tool: str, input: dict, context: dict) -> dict:
            return {"behavior": "allow"}

        # Should not raise
        middleware = AuthMiddleware(
            secret_key="test-secret-key",
            can_use_tool=my_callback,
        )

        assert middleware._can_use_tool_callback is my_callback

    def test_auth_middleware_can_use_tool_is_optional(self) -> None:
        """can_use_tool callback should be optional (defaults to None)."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(secret_key="test-secret-key")

        assert middleware._can_use_tool_callback is None

    @pytest.mark.asyncio
    async def test_can_use_tool_returns_allow_by_default(self) -> None:
        """can_use_tool should return allow when no callback configured."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        middleware = AuthMiddleware(secret_key="test-secret-key")

        result = await middleware.can_use_tool(
            tool="calculator",
            input={"expression": "2+2"},
            context={"user_id": "alice"},
        )

        assert result["behavior"] == "allow"

    @pytest.mark.asyncio
    async def test_can_use_tool_invokes_callback(self) -> None:
        """can_use_tool should invoke callback when configured and flag enabled."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        callback = AsyncMock(return_value={"behavior": "allow", "updatedInput": {"expression": "4"}})

        middleware = AuthMiddleware(
            secret_key="test-secret-key",
            can_use_tool=callback,
        )

        # Enable feature flag
        with patch("mcp_server_langgraph.auth.middleware.feature_flags") as mock_flags:
            mock_flags.enable_sdk_can_use_tool = True

            result = await middleware.can_use_tool(
                tool="calculator",
                input={"expression": "2+2"},
                context={"user_id": "alice"},
            )

            callback.assert_called_once_with(
                "calculator",
                {"expression": "2+2"},
                {"user_id": "alice"},
            )
            assert result["behavior"] == "allow"
            assert result["updatedInput"] == {"expression": "4"}

    @pytest.mark.asyncio
    async def test_can_use_tool_deny_behavior(self) -> None:
        """can_use_tool should support deny behavior with message."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        async def deny_dangerous(tool: str, input: dict, context: dict) -> dict:
            if tool == "Write" and "/system/" in input.get("file_path", ""):
                return {"behavior": "deny", "message": "System writes blocked"}
            return {"behavior": "allow"}

        middleware = AuthMiddleware(
            secret_key="test-secret-key",
            can_use_tool=deny_dangerous,
        )

        # Enable feature flag
        with patch("mcp_server_langgraph.auth.middleware.feature_flags") as mock_flags:
            mock_flags.enable_sdk_can_use_tool = True

            # Allowed path
            result = await middleware.can_use_tool(
                tool="Write",
                input={"file_path": "/home/user/file.txt"},
                context={"user_id": "alice"},
            )
            assert result["behavior"] == "allow"

            # Denied path
            result = await middleware.can_use_tool(
                tool="Write",
                input={"file_path": "/system/config.ini"},
                context={"user_id": "alice"},
            )
            assert result["behavior"] == "deny"
            assert result["message"] == "System writes blocked"

    @pytest.mark.asyncio
    async def test_can_use_tool_modify_input(self) -> None:
        """can_use_tool should support modifying input via updatedInput."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        async def sanitize_input(tool: str, input: dict, context: dict) -> dict:
            # Sanitize file paths
            if tool == "Read" and "file_path" in input:
                sanitized_path = input["file_path"].replace("..", "")
                return {"behavior": "allow", "updatedInput": {"file_path": sanitized_path}}
            return {"behavior": "allow"}

        middleware = AuthMiddleware(
            secret_key="test-secret-key",
            can_use_tool=sanitize_input,
        )

        # Enable feature flag
        with patch("mcp_server_langgraph.auth.middleware.feature_flags") as mock_flags:
            mock_flags.enable_sdk_can_use_tool = True

            result = await middleware.can_use_tool(
                tool="Read",
                input={"file_path": "/home/../etc/passwd"},
                context={"user_id": "alice"},
            )

            assert result["behavior"] == "allow"
            assert result["updatedInput"]["file_path"] == "/home//etc/passwd"

    @pytest.mark.asyncio
    async def test_can_use_tool_respects_feature_flag(self) -> None:
        """can_use_tool should be gated by enable_sdk_can_use_tool feature flag."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware
        from unittest.mock import patch

        callback = AsyncMock(return_value={"behavior": "deny", "message": "Blocked"})

        middleware = AuthMiddleware(
            secret_key="test-secret-key",
            can_use_tool=callback,
        )

        # When feature flag is disabled, callback should not be invoked
        with patch("mcp_server_langgraph.auth.middleware.feature_flags") as mock_flags:
            mock_flags.enable_sdk_can_use_tool = False

            result = await middleware.can_use_tool(
                tool="Write",
                input={"file_path": "/test"},
                context={"user_id": "alice"},
            )

            # Should return allow without invoking callback
            assert result["behavior"] == "allow"
            callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_can_use_tool_callback_error_handling(self) -> None:
        """can_use_tool should handle callback errors gracefully."""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware
        from unittest.mock import patch

        async def failing_callback(tool: str, input: dict, context: dict) -> dict:
            raise RuntimeError("Callback failed")

        middleware = AuthMiddleware(
            secret_key="test-secret-key",
            can_use_tool=failing_callback,
        )

        # When callback raises, should deny for safety
        with patch("mcp_server_langgraph.auth.middleware.feature_flags") as mock_flags:
            mock_flags.enable_sdk_can_use_tool = True

            result = await middleware.can_use_tool(
                tool="Write",
                input={"file_path": "/test"},
                context={"user_id": "alice"},
            )

            # Should deny on error for safety
            assert result["behavior"] == "deny"
            assert "error" in result["message"].lower()
