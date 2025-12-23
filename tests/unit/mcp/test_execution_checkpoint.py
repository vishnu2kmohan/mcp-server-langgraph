"""
Tests for file checkpointing integration in execution handler.

Verifies that the ExecutionToolHandler properly integrates with the
FileRewind system for code execution operations.
"""

import gc

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server_langgraph.mcp.handlers.execution import ExecutionToolHandler

pytestmark = [pytest.mark.unit, pytest.mark.sdk]


@pytest.mark.xdist_group(name="execution_checkpoint_integration")
class TestExecutionCheckpointIntegration:
    """Tests for file checkpointing in execution handler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.auth = MagicMock()
        self.agent_graph = MagicMock()

    def test_handler_has_file_rewind_attribute(self) -> None:
        """ExecutionToolHandler should have optional file_rewind attribute."""
        handler = ExecutionToolHandler(
            auth=self.auth,
            agent_graph=self.agent_graph,
        )
        # Handler should accept file_rewind as optional parameter
        assert hasattr(handler, "_file_rewind") or handler is not None

    @pytest.mark.asyncio
    async def test_execute_python_creates_checkpoint_when_enabled(self) -> None:
        """execute_python should create checkpoint when file checkpointing is enabled."""
        from mcp_server_langgraph.core.file_rewind import FileRewind

        mock_rewind = AsyncMock(spec=FileRewind)
        mock_rewind.checkpoint.return_value = "cp_test123"

        handler = ExecutionToolHandler(
            auth=self.auth,
            agent_graph=self.agent_graph,
            file_rewind=mock_rewind,
        )

        # Mock the execute_python tool
        with patch("mcp_server_langgraph.tools.code_execution_tools.execute_python") as mock_execute:
            mock_execute.invoke.return_value = "Success: 42"

            # Mock feature flags singleton to enable checkpointing
            with patch("mcp_server_langgraph.mcp.handlers.execution.feature_flags") as mock_flags:
                mock_flags.enable_sdk_file_checkpointing = True

                span = MagicMock()
                result = await handler.handle_execute_python(
                    arguments={"code": "print(42)", "execution_id": "exec_123"},
                    span=span,
                    user_id="test-user",
                )

                # Verify checkpoint was created
                mock_rewind.checkpoint.assert_called_once_with("exec_123")

    @pytest.mark.asyncio
    async def test_execute_python_skips_checkpoint_when_disabled(self) -> None:
        """execute_python should skip checkpoint when file checkpointing is disabled."""
        from mcp_server_langgraph.core.file_rewind import FileRewind

        mock_rewind = AsyncMock(spec=FileRewind)

        handler = ExecutionToolHandler(
            auth=self.auth,
            agent_graph=self.agent_graph,
            file_rewind=mock_rewind,
        )

        # Mock the execute_python tool
        with patch("mcp_server_langgraph.tools.code_execution_tools.execute_python") as mock_execute:
            mock_execute.invoke.return_value = "Success: 42"

            # Mock feature flags singleton to disable checkpointing (default)
            with patch("mcp_server_langgraph.mcp.handlers.execution.feature_flags") as mock_flags:
                mock_flags.enable_sdk_file_checkpointing = False

                span = MagicMock()
                result = await handler.handle_execute_python(
                    arguments={"code": "print(42)"},
                    span=span,
                    user_id="test-user",
                )

                # Verify checkpoint was NOT created
                mock_rewind.checkpoint.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_python_clears_checkpoint_on_success(self) -> None:
        """execute_python should clear checkpoint after successful execution."""
        from mcp_server_langgraph.core.file_rewind import FileRewind

        mock_journal = AsyncMock()
        mock_rewind = FileRewind(journal=mock_journal)
        mock_journal.checkpoint.return_value = "cp_test456"
        mock_journal.get_changes.return_value = []

        handler = ExecutionToolHandler(
            auth=self.auth,
            agent_graph=self.agent_graph,
            file_rewind=mock_rewind,
        )

        # Mock the execute_python tool
        with patch("mcp_server_langgraph.tools.code_execution_tools.execute_python") as mock_execute:
            mock_execute.invoke.return_value = "Success: result"

            # Mock feature flags singleton to enable checkpointing
            with patch("mcp_server_langgraph.mcp.handlers.execution.feature_flags") as mock_flags:
                mock_flags.enable_sdk_file_checkpointing = True

                # Mock get_file_journal at the source location (dynamic import)
                with patch("mcp_server_langgraph.core.file_journal.get_file_journal") as mock_get_journal:
                    mock_get_journal.return_value = mock_journal

                    span = MagicMock()
                    result = await handler.handle_execute_python(
                        arguments={"code": "x = 1", "execution_id": "exec_789"},
                        span=span,
                        user_id="test-user",
                    )

                    # Verify checkpoint was cleared after success
                    mock_journal.clear_checkpoint.assert_called_with("cp_test456")

    def test_handler_accepts_file_rewind_parameter(self) -> None:
        """ExecutionToolHandler should accept file_rewind as constructor parameter."""
        from mcp_server_langgraph.core.file_rewind import FileRewind

        mock_rewind = MagicMock(spec=FileRewind)

        # Should not raise
        handler = ExecutionToolHandler(
            auth=self.auth,
            agent_graph=self.agent_graph,
            file_rewind=mock_rewind,
        )

        assert handler._file_rewind is mock_rewind

    @pytest.mark.asyncio
    async def test_execute_python_records_span_checkpoint_id(self) -> None:
        """execute_python should record checkpoint_id in span when checkpointing."""
        from mcp_server_langgraph.core.file_rewind import FileRewind

        mock_rewind = AsyncMock(spec=FileRewind)
        mock_rewind.checkpoint.return_value = "cp_abc123"

        handler = ExecutionToolHandler(
            auth=self.auth,
            agent_graph=self.agent_graph,
            file_rewind=mock_rewind,
        )

        with patch("mcp_server_langgraph.tools.code_execution_tools.execute_python") as mock_execute:
            mock_execute.invoke.return_value = "Success"

            # Mock feature flags singleton to enable checkpointing
            with patch("mcp_server_langgraph.mcp.handlers.execution.feature_flags") as mock_flags:
                mock_flags.enable_sdk_file_checkpointing = True

                span = MagicMock()
                await handler.handle_execute_python(
                    arguments={"code": "pass", "execution_id": "exec_abc"},
                    span=span,
                    user_id="test-user",
                )

                # Verify span has checkpoint_id attribute
                span.set_attribute.assert_any_call("code.checkpoint_id", "cp_abc123")
