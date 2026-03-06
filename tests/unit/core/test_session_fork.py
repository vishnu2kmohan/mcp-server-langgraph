"""
Unit tests for Session Fork Capability (ADR-0085 / Claude Agent SDK parity)

TDD: RED phase - Tests for session forking functionality.

Session Fork provides:
- Creating a copy of a session at a specific checkpoint
- Branching conversation history
- Exploring alternative paths without affecting original session
- Fork relationship tracking (parent-child)
- Independent continuation from fork point

Reference: Claude Agent SDK Session Fork pattern
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass

pytestmark = [pytest.mark.unit, pytest.mark.sessions]


# =============================================================================
# Feature Flag Tests
# =============================================================================


@pytest.mark.unit
class TestSessionForkFeatureFlag:
    """Test session fork feature flag integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_fork_feature_flag_exists(self) -> None:
        """GIVEN the feature flags module
        WHEN accessing enable_session_fork
        THEN it should exist as a boolean field with default=False
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, "enable_session_fork")
        assert isinstance(flags.enable_session_fork, bool)
        # Default should be False (experimental feature)
        assert flags.enable_session_fork is False


# =============================================================================
# SessionForkManager Module Tests
# =============================================================================


@pytest.mark.unit
class TestSessionForkModule:
    """Test the SessionForkManager module structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_fork_manager_exists(self) -> None:
        """GIVEN the core module
        WHEN importing SessionForkManager
        THEN it should be available
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        assert SessionForkManager is not None

    def test_session_fork_manager_has_required_methods(self) -> None:
        """GIVEN a SessionForkManager class
        WHEN checking for required methods
        THEN it should have fork, get_fork_info, list_forks methods
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        assert hasattr(SessionForkManager, "fork")
        assert callable(getattr(SessionForkManager, "fork", None))
        assert hasattr(SessionForkManager, "get_fork_info")
        assert callable(getattr(SessionForkManager, "get_fork_info", None))
        assert hasattr(SessionForkManager, "list_forks")
        assert callable(getattr(SessionForkManager, "list_forks", None))


# =============================================================================
# Fork Operation Tests
# =============================================================================


@pytest.mark.unit
class TestSessionForkOperations:
    """Test session fork operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fork_creates_new_session(self) -> None:
        """GIVEN a session with messages
        WHEN forking the session
        THEN a new session with a new ID should be created
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()
            parent_session_id = "session-parent-123"

            fork_result = await manager.fork(
                source_session_id=parent_session_id,
            )

            assert fork_result is not None
            assert fork_result.forked_session_id != parent_session_id
            assert fork_result.parent_session_id == parent_session_id

    @pytest.mark.asyncio
    async def test_fork_copies_messages_up_to_checkpoint(self) -> None:
        """GIVEN a session with multiple messages
        WHEN forking at a specific checkpoint
        THEN only messages up to that checkpoint should be copied
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            # Mock session with 5 messages, fork at message 3
            fork_result = await manager.fork(
                source_session_id="session-123",
                checkpoint_id="checkpoint-at-msg-3",
            )

            assert fork_result.message_count == 3

    @pytest.mark.asyncio
    async def test_fork_at_latest_copies_all_messages(self) -> None:
        """GIVEN a session with messages
        WHEN forking without specifying a checkpoint
        THEN all messages should be copied (fork at latest)
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            fork_result = await manager.fork(
                source_session_id="session-123",
                checkpoint_id=None,  # No checkpoint = fork at latest
            )

            assert fork_result.forked_at_latest is True

    @pytest.mark.asyncio
    async def test_fork_preserves_metadata(self) -> None:
        """GIVEN a session with metadata
        WHEN forking the session
        THEN metadata should be preserved in the fork
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            fork_result = await manager.fork(
                source_session_id="session-123",
                preserve_metadata=True,
            )

            assert fork_result.metadata_preserved is True


# =============================================================================
# Fork Relationship Tests
# =============================================================================


@pytest.mark.unit
class TestSessionForkRelationships:
    """Test fork relationship tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fork_tracks_parent_child_relationship(self) -> None:
        """GIVEN a forked session
        WHEN querying fork info
        THEN the parent-child relationship should be available
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            fork_result = await manager.fork(source_session_id="parent-123")
            fork_info = await manager.get_fork_info(fork_result.forked_session_id)

            assert fork_info is not None
            assert fork_info.parent_session_id == "parent-123"
            assert fork_info.is_fork is True

    @pytest.mark.asyncio
    async def test_list_forks_returns_all_forks(self) -> None:
        """GIVEN a session with multiple forks
        WHEN listing forks
        THEN all forks should be returned
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            # Create multiple forks from same parent
            await manager.fork(source_session_id="parent-123")
            await manager.fork(source_session_id="parent-123")
            await manager.fork(source_session_id="parent-123")

            forks = await manager.list_forks(parent_session_id="parent-123")

            assert len(forks) == 3

    @pytest.mark.asyncio
    async def test_fork_can_be_forked(self) -> None:
        """GIVEN a forked session
        WHEN forking the fork
        THEN a nested fork should be created
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            # Fork the original
            fork1 = await manager.fork(source_session_id="original-123")

            # Fork the fork
            fork2 = await manager.fork(source_session_id=fork1.forked_session_id)

            fork2_info = await manager.get_fork_info(fork2.forked_session_id)

            assert fork2_info.parent_session_id == fork1.forked_session_id
            assert fork2_info.fork_depth == 2


# =============================================================================
# Fork Independence Tests
# =============================================================================


@pytest.mark.unit
class TestSessionForkIndependence:
    """Test that forked sessions are independent."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_forked_session_is_independent(self) -> None:
        """GIVEN a forked session
        WHEN adding messages to the fork
        THEN the parent session should not be affected
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            fork_result = await manager.fork(source_session_id="parent-123")

            # The fork and parent should have separate state
            assert fork_result.is_independent is True

    @pytest.mark.asyncio
    async def test_parent_changes_dont_affect_fork(self) -> None:
        """GIVEN a forked session
        WHEN the parent session continues
        THEN the fork should not be affected
        """
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            fork_result = await manager.fork(
                source_session_id="parent-123",
                checkpoint_id="checkpoint-1",
            )

            # Fork should be isolated from parent's future changes
            fork_info = await manager.get_fork_info(fork_result.forked_session_id)
            assert fork_info.isolated_from_parent is True


# =============================================================================
# Fork Validation Tests
# =============================================================================


@pytest.mark.unit
class TestSessionForkValidation:
    """Test fork validation and error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_fork_invalid_session_raises_error(self) -> None:
        """GIVEN a non-existent session ID
        WHEN attempting to fork
        THEN a SessionNotFoundError should be raised
        """
        from mcp_server_langgraph.core.exceptions import SessionNotFoundError
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            with pytest.raises(SessionNotFoundError):
                await manager.fork(source_session_id="nonexistent-session")

    @pytest.mark.asyncio
    async def test_fork_invalid_checkpoint_raises_error(self) -> None:
        """GIVEN a valid session but invalid checkpoint
        WHEN attempting to fork at that checkpoint
        THEN a CheckpointNotFoundError should be raised
        """
        from mcp_server_langgraph.core.exceptions import CheckpointNotFoundError
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = True

            manager = SessionForkManager()

            with pytest.raises(CheckpointNotFoundError):
                await manager.fork(
                    source_session_id="valid-session-123",
                    checkpoint_id="invalid-checkpoint",
                )

    @pytest.mark.asyncio
    async def test_fork_disabled_raises_feature_error(self) -> None:
        """GIVEN feature flag disabled
        WHEN attempting to fork
        THEN a FeatureDisabledError should be raised
        """
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.session_fork import SessionForkManager

        with patch("mcp_server_langgraph.core.session_fork.feature_flags") as mock_flags:
            mock_flags.enable_session_fork = False

            manager = SessionForkManager()

            with pytest.raises(FeatureDisabledError):
                await manager.fork(source_session_id="session-123")


# =============================================================================
# ForkInfo Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestForkInfo:
    """Test ForkInfo data class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_fork_info_has_required_fields(self) -> None:
        """GIVEN a ForkInfo class
        WHEN checking fields
        THEN it should have all required fields
        """
        from mcp_server_langgraph.core.session_fork import ForkInfo

        # Check that the class has required fields
        info = ForkInfo(
            session_id="fork-123",
            parent_session_id="parent-123",
            forked_at="2025-01-01T00:00:00Z",
            fork_depth=1,
            is_fork=True,
        )

        assert info.session_id == "fork-123"
        assert info.parent_session_id == "parent-123"
        assert info.fork_depth == 1


# =============================================================================
# Module Exports Tests
# =============================================================================


@pytest.mark.unit
class TestSessionForkExports:
    """Test module exports for session fork."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_exports_session_fork_manager(self) -> None:
        """GIVEN the core module
        WHEN checking exports
        THEN SessionForkManager should be exported
        """
        from mcp_server_langgraph.core import SessionForkManager

        assert SessionForkManager is not None

    def test_exports_fork_info(self) -> None:
        """GIVEN the core module
        WHEN checking exports
        THEN ForkInfo should be exported
        """
        from mcp_server_langgraph.core import ForkInfo

        assert ForkInfo is not None

    def test_exports_fork_result(self) -> None:
        """GIVEN the core module
        WHEN checking exports
        THEN ForkResult should be exported
        """
        from mcp_server_langgraph.core import ForkResult

        assert ForkResult is not None
