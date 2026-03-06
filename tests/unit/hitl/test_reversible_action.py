"""Tests for ReversibleAction and ActionHistoryStore.

TDD: These tests define the contract for reversible actions
with undo/rollback capabilities for HITL workflows.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestReversibleActionBasic:
    """Tests for ReversibleAction basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_reversible_action_exists(self) -> None:
        """Test ReversibleAction class exists."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        assert ReversibleAction is not None

    def test_reversible_action_has_action_id(self) -> None:
        """Test ReversibleAction has action_id field."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write config file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        assert action.action_id == "action-123"

    def test_reversible_action_has_action_type(self) -> None:
        """Test ReversibleAction has action_type field."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="database_update",
            description="Update user record",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        assert action.action_type == "database_update"

    def test_reversible_action_has_description(self) -> None:
        """Test ReversibleAction has description field."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write configuration to config.yaml",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        assert action.description == "Write configuration to config.yaml"

    def test_reversible_action_has_execute_fn(self) -> None:
        """Test ReversibleAction has execute_fn callable."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        mock_execute = AsyncMock(return_value=None)  # noqa: async-mock-config
        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=mock_execute,
            undo_fn=AsyncMock(return_value=None),
        )

        assert action.execute_fn is mock_execute

    def test_reversible_action_has_undo_fn(self) -> None:
        """Test ReversibleAction has undo_fn callable."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        mock_undo = AsyncMock(return_value=None)  # noqa: async-mock-config
        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=mock_undo,
        )

        assert action.undo_fn is mock_undo


@pytest.mark.unit
class TestReversibleActionExecution:
    """Tests for ReversibleAction execute and undo."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_execute_calls_execute_fn(self) -> None:
        """Test execute() calls the execute_fn."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        mock_execute = AsyncMock(return_value={"status": "success"})
        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=mock_execute,
            undo_fn=AsyncMock(return_value=None),
        )

        result = await action.execute()

        mock_execute.assert_called_once()
        assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_undo_calls_undo_fn(self) -> None:
        """Test undo() calls the undo_fn."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        mock_undo = AsyncMock(return_value={"status": "undone"})
        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=mock_undo,
        )

        result = await action.undo()

        mock_undo.assert_called_once()
        assert result == {"status": "undone"}

    @pytest.mark.asyncio
    async def test_execute_updates_executed_at(self) -> None:
        """Test execute() sets executed_at timestamp."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        assert action.executed_at is None
        await action.execute()
        assert action.executed_at is not None
        assert isinstance(action.executed_at, datetime)

    @pytest.mark.asyncio
    async def test_undo_updates_undone_at(self) -> None:
        """Test undo() sets undone_at timestamp."""
        from mcp_server_langgraph.hitl.reversible import ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        assert action.undone_at is None
        await action.undo()
        assert action.undone_at is not None
        assert isinstance(action.undone_at, datetime)


@pytest.mark.unit
class TestReversibleActionState:
    """Tests for ReversibleAction state tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_action_initial_state_is_pending(self) -> None:
        """Test action starts in pending state."""
        from mcp_server_langgraph.hitl.reversible import ActionState, ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        assert action.state == ActionState.PENDING

    @pytest.mark.asyncio
    async def test_execute_transitions_to_executed(self) -> None:
        """Test execute() transitions state to EXECUTED."""
        from mcp_server_langgraph.hitl.reversible import ActionState, ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        await action.execute()

        assert action.state == ActionState.EXECUTED

    @pytest.mark.asyncio
    async def test_undo_transitions_to_undone(self) -> None:
        """Test undo() transitions state to UNDONE."""
        from mcp_server_langgraph.hitl.reversible import ActionState, ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        await action.execute()
        await action.undo()

        assert action.state == ActionState.UNDONE

    @pytest.mark.asyncio
    async def test_execute_failure_transitions_to_failed(self) -> None:
        """Test execute() failure transitions state to FAILED."""
        from mcp_server_langgraph.hitl.reversible import ActionState, ReversibleAction

        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(side_effect=RuntimeError("Write failed")),
            undo_fn=AsyncMock(return_value=None),
        )

        with pytest.raises(RuntimeError):
            await action.execute()

        assert action.state == ActionState.FAILED


@pytest.mark.unit
class TestActionStateEnum:
    """Tests for ActionState enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_action_state_exists(self) -> None:
        """Test ActionState enum exists."""
        from mcp_server_langgraph.hitl.reversible import ActionState

        assert ActionState is not None

    def test_action_state_has_pending(self) -> None:
        """Test ActionState has PENDING value."""
        from mcp_server_langgraph.hitl.reversible import ActionState

        assert hasattr(ActionState, "PENDING")
        assert ActionState.PENDING.value == "pending"

    def test_action_state_has_executed(self) -> None:
        """Test ActionState has EXECUTED value."""
        from mcp_server_langgraph.hitl.reversible import ActionState

        assert hasattr(ActionState, "EXECUTED")
        assert ActionState.EXECUTED.value == "executed"

    def test_action_state_has_undone(self) -> None:
        """Test ActionState has UNDONE value."""
        from mcp_server_langgraph.hitl.reversible import ActionState

        assert hasattr(ActionState, "UNDONE")
        assert ActionState.UNDONE.value == "undone"

    def test_action_state_has_failed(self) -> None:
        """Test ActionState has FAILED value."""
        from mcp_server_langgraph.hitl.reversible import ActionState

        assert hasattr(ActionState, "FAILED")
        assert ActionState.FAILED.value == "failed"


@pytest.mark.unit
class TestActionHistoryStoreBasic:
    """Tests for ActionHistoryStore basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_action_history_store_exists(self) -> None:
        """Test ActionHistoryStore class exists."""
        from mcp_server_langgraph.hitl.reversible import ActionHistoryStore

        assert ActionHistoryStore is not None

    def test_action_history_store_has_add_method(self) -> None:
        """Test ActionHistoryStore has add method."""
        from mcp_server_langgraph.hitl.reversible import ActionHistoryStore

        store = ActionHistoryStore()
        assert hasattr(store, "add")

    def test_action_history_store_has_get_method(self) -> None:
        """Test ActionHistoryStore has get method."""
        from mcp_server_langgraph.hitl.reversible import ActionHistoryStore

        store = ActionHistoryStore()
        assert hasattr(store, "get")

    def test_action_history_store_has_list_for_session_method(self) -> None:
        """Test ActionHistoryStore has list_for_session method."""
        from mcp_server_langgraph.hitl.reversible import ActionHistoryStore

        store = ActionHistoryStore()
        assert hasattr(store, "list_for_session")


@pytest.mark.unit
class TestActionHistoryStoreOperations:
    """Tests for ActionHistoryStore operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_add_stores_action(self) -> None:
        """Test add() stores the action."""
        from mcp_server_langgraph.hitl.reversible import (
            ActionHistoryStore,
            ReversibleAction,
        )

        store = ActionHistoryStore()
        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        store.add(action, session_id="session-456")

        retrieved = store.get("action-123")
        assert retrieved is action

    def test_get_returns_none_for_unknown(self) -> None:
        """Test get() returns None for unknown action_id."""
        from mcp_server_langgraph.hitl.reversible import ActionHistoryStore

        store = ActionHistoryStore()

        result = store.get("unknown-action")

        assert result is None

    def test_list_for_session_returns_session_actions(self) -> None:
        """Test list_for_session returns actions for session."""
        from mcp_server_langgraph.hitl.reversible import (
            ActionHistoryStore,
            ReversibleAction,
        )

        store = ActionHistoryStore()
        action1 = ReversibleAction(
            action_id="action-1",
            action_type="file_write",
            description="Write file 1",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )
        action2 = ReversibleAction(
            action_id="action-2",
            action_type="file_write",
            description="Write file 2",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        store.add(action1, session_id="session-A")
        store.add(action2, session_id="session-A")

        actions = store.list_for_session("session-A")

        assert len(actions) == 2
        assert action1 in actions
        assert action2 in actions

    def test_list_for_session_excludes_other_sessions(self) -> None:
        """Test list_for_session excludes actions from other sessions."""
        from mcp_server_langgraph.hitl.reversible import (
            ActionHistoryStore,
            ReversibleAction,
        )

        store = ActionHistoryStore()
        action1 = ReversibleAction(
            action_id="action-1",
            action_type="file_write",
            description="Write file 1",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )
        action2 = ReversibleAction(
            action_id="action-2",
            action_type="file_write",
            description="Write file 2",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        store.add(action1, session_id="session-A")
        store.add(action2, session_id="session-B")

        actions = store.list_for_session("session-A")

        assert len(actions) == 1
        assert action1 in actions
        assert action2 not in actions


@pytest.mark.unit
class TestActionHistoryUndo:
    """Tests for ActionHistoryStore undo capabilities."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_undoable_returns_only_executed_actions(self) -> None:
        """Test get_undoable returns only executed, non-undone actions."""
        from mcp_server_langgraph.hitl.reversible import (
            ActionHistoryStore,
            ActionState,
            ReversibleAction,
        )

        store = ActionHistoryStore()
        executed_action = ReversibleAction(
            action_id="action-1",
            action_type="file_write",
            description="Executed action",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )
        executed_action._state = ActionState.EXECUTED

        pending_action = ReversibleAction(
            action_id="action-2",
            action_type="file_write",
            description="Pending action",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=AsyncMock(return_value=None),
        )

        store.add(executed_action, session_id="session-A")
        store.add(pending_action, session_id="session-A")

        undoable = store.get_undoable("session-A")

        assert len(undoable) == 1
        assert executed_action in undoable
        assert pending_action not in undoable

    def test_has_undo_method(self) -> None:
        """Test ActionHistoryStore has undo method."""
        from mcp_server_langgraph.hitl.reversible import ActionHistoryStore

        store = ActionHistoryStore()
        assert hasattr(store, "undo")

    @pytest.mark.asyncio
    async def test_undo_calls_action_undo(self) -> None:
        """Test undo() calls the action's undo method."""
        from mcp_server_langgraph.hitl.reversible import (
            ActionHistoryStore,
            ActionState,
            ReversibleAction,
        )

        mock_undo = AsyncMock(return_value=None)  # noqa: async-mock-config
        action = ReversibleAction(
            action_id="action-123",
            action_type="file_write",
            description="Write file",
            execute_fn=AsyncMock(return_value=None),
            undo_fn=mock_undo,
        )
        action._state = ActionState.EXECUTED

        store = ActionHistoryStore()
        store.add(action, session_id="session-A")

        await store.undo("action-123")

        mock_undo.assert_called_once()
