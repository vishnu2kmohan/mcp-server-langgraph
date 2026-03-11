"""
Tests for auth_required detection module.

Tests the detection logic for when a tool call requires authentication.
"""

import pytest

from mcp_server_langgraph.core.auth_required_detector import (
    AuthRequiredInfo,
    check_and_emit_if_auth_required,
    check_tool_auth_required,
    emit_auth_required_event,
    infer_template_from_tool_name,
)

pytestmark = pytest.mark.unit


class TestInferTemplateFromToolName:
    """Tests for infer_template_from_tool_name function."""

    def test_qualified_name_with_double_colon(self) -> None:
        """Test parsing qualified name with :: separator."""
        assert infer_template_from_tool_name("github::list_pull_requests") == "github"

    def test_qualified_name_with_single_colon(self) -> None:
        """Test parsing qualified name with : separator."""
        assert infer_template_from_tool_name("github:list_pull_requests") == "github"

    def test_unqualified_name_with_underscore(self) -> None:
        """Test parsing unqualified name with underscore prefix."""
        assert infer_template_from_tool_name("slack_send_message") == "slack"

    def test_known_templates_are_recognized(self) -> None:
        """Test all known template mappings."""
        known_templates = [
            ("github:list_prs", "github"),
            ("slack:post_message", "slack"),
            ("notion:create_page", "notion"),
            ("jira:create_issue", "jira"),
            ("linear:list_issues", "linear"),
            ("gitlab:list_mrs", "gitlab"),
        ]
        for tool_name, expected in known_templates:
            assert infer_template_from_tool_name(tool_name) == expected, f"Failed for {tool_name}"

    def test_unknown_tool_returns_none(self) -> None:
        """Test that unknown tools return None."""
        assert infer_template_from_tool_name("unknown_tool") is None
        assert infer_template_from_tool_name("custom:my_tool") is None

    def test_case_insensitive_matching(self) -> None:
        """Test case insensitivity."""
        assert infer_template_from_tool_name("GITHUB:list_prs") == "github"
        assert infer_template_from_tool_name("GitHub:list_prs") == "github"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestAuthRequiredInfo:
    """Tests for AuthRequiredInfo dataclass."""

    def test_create_with_required_fields(self) -> None:
        """Test creating AuthRequiredInfo with required fields."""
        info = AuthRequiredInfo(
            tool_name="github:list_prs",
            connection_id=None,
            template_id="github",
            message="Authentication required",
        )
        assert info.tool_name == "github:list_prs"
        assert info.connection_id is None
        assert info.template_id == "github"
        assert info.message == "Authentication required"
        assert info.retry_message_id is None

    def test_create_with_all_fields(self) -> None:
        """Test creating AuthRequiredInfo with all fields."""
        info = AuthRequiredInfo(
            tool_name="slack:post_message",
            connection_id="conn-123",
            template_id="slack",
            message="Re-authentication needed",
            retry_message_id="msg-456",
        )
        assert info.connection_id == "conn-123"
        assert info.retry_message_id == "msg-456"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestCheckToolAuthRequired:
    """Tests for check_tool_auth_required function."""

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_tool(self) -> None:
        """Test that unknown tools don't require auth."""
        result = await check_tool_auth_required("calculator:add")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_non_mcp_tool(self) -> None:
        """Test that non-MCP tools don't require auth."""
        result = await check_tool_auth_required("search_knowledge_base")
        assert result is None

    @pytest.mark.asyncio
    async def test_known_tool_placeholder_returns_none(self) -> None:
        """Test that known tools currently return None (placeholder).

        This test documents current behavior. When connection lookup
        is implemented, this test should be updated.
        """
        # Currently placeholder returns None
        # In future, this should return AuthRequiredInfo if connection is missing
        result = await check_tool_auth_required("github:list_prs")
        assert result is None  # Placeholder behavior

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestEmitAuthRequiredEvent:
    """Tests for emit_auth_required_event function."""

    @pytest.mark.asyncio
    async def test_emits_custom_event(self, mocker) -> None:
        """Test that auth_required event is emitted correctly."""
        mock_dispatch = mocker.patch(
            "langchain_core.callbacks.manager.adispatch_custom_event",
            side_effect=lambda *a, **kw: None,
        )

        auth_info = AuthRequiredInfo(
            tool_name="github:list_prs",
            connection_id=None,
            template_id="github",
            message="Please authenticate",
        )

        await emit_auth_required_event(auth_info, retry_message_id="msg-123")

        mock_dispatch.assert_awaited_once_with(
            "auth_required",
            {
                "tool_name": "github:list_prs",
                "connection_id": None,
                "template_id": "github",
                "message": "Please authenticate",
                "retry_message_id": "msg-123",
            },
        )

    @pytest.mark.asyncio
    async def test_uses_auth_info_retry_message_id_if_not_provided(self, mocker) -> None:
        """Test that retry_message_id falls back to auth_info value."""
        mock_dispatch = mocker.patch(
            "langchain_core.callbacks.manager.adispatch_custom_event",
            side_effect=lambda *a, **kw: None,
        )

        auth_info = AuthRequiredInfo(
            tool_name="slack:post",
            connection_id="conn-1",
            template_id="slack",
            message="Auth needed",
            retry_message_id="original-msg",
        )

        await emit_auth_required_event(auth_info)

        call_args = mock_dispatch.call_args[0][1]
        assert call_args["retry_message_id"] == "original-msg"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


class TestCheckAndEmitIfAuthRequired:
    """Tests for check_and_emit_if_auth_required convenience function."""

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_tool(self) -> None:
        """Test that unknown tools return False."""
        result = await check_and_emit_if_auth_required("calculator:add")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_auth_required(self) -> None:
        """Test that tools not requiring auth return False."""
        # Currently all known tools return False (placeholder)
        result = await check_and_emit_if_auth_required("github:list_prs")
        assert result is False

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
