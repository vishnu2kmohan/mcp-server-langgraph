"""
OpenFGA Workflow Sharing Integration Tests

TDD tests for syncing workflow shares to OpenFGA authorization tuples.

The integration:
- Writes tuples when a share is created
- Deletes tuples when a share is removed
- Maps permission levels: view→viewer, edit→editor, execute→executor
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from mcp_server_langgraph.auth.workflow_sharing import (
        OpenFGAWorkflowSharingService,
    )

pytestmark = pytest.mark.unit


class TestOpenFGAWorkflowSharingService:
    """Tests for OpenFGAWorkflowSharingService class."""

    def test_service_import_when_called_returns_class(self) -> None:
        """OpenFGAWorkflowSharingService should be importable."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        assert OpenFGAWorkflowSharingService is not None

    def test_service_has_sync_share_method(self) -> None:
        """Service should have sync_share method."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        assert hasattr(OpenFGAWorkflowSharingService, "sync_share")

    def test_service_has_remove_share_method(self) -> None:
        """Service should have remove_share method."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        assert hasattr(OpenFGAWorkflowSharingService, "remove_share")

    def test_service_has_set_workflow_owner_method(self) -> None:
        """Service should have set_workflow_owner method."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        assert hasattr(OpenFGAWorkflowSharingService, "set_workflow_owner")


@pytest.mark.xdist_group(name="test_openfga_workflow_sharing_sync")
class TestOpenFGASyncShare:
    """Tests for syncing shares to OpenFGA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_openfga_client(self) -> MagicMock:
        """Create a mock OpenFGA client."""
        client = MagicMock()
        client.write_tuples = AsyncMock(return_value=None)
        client.delete_tuples = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def service(self, mock_openfga_client: MagicMock) -> OpenFGAWorkflowSharingService:
        """Create service with mocked client."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        return OpenFGAWorkflowSharingService(openfga_client=mock_openfga_client)

    @pytest.mark.asyncio
    async def test_sync_share_writes_viewer_tuple_for_view_permission(
        self,
        service: OpenFGAWorkflowSharingService,
        mock_openfga_client: MagicMock,
    ) -> None:
        """
        GIVEN a share with 'view' permission
        WHEN sync_share is called
        THEN a tuple with 'viewer' relation should be written
        """
        # WHEN
        await service.sync_share(
            workflow_id="wf-123",
            user_id="user-456",
            permission="view",
        )

        # THEN
        mock_openfga_client.write_tuples.assert_called_once()
        call_args = mock_openfga_client.write_tuples.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["user"] == "user:user-456"
        assert call_args[0]["relation"] == "viewer"
        assert call_args[0]["object"] == "workflow:wf-123"

    @pytest.mark.asyncio
    async def test_sync_share_writes_editor_tuple_for_edit_permission(
        self,
        service: OpenFGAWorkflowSharingService,
        mock_openfga_client: MagicMock,
    ) -> None:
        """
        GIVEN a share with 'edit' permission
        WHEN sync_share is called
        THEN a tuple with 'editor' relation should be written
        """
        # WHEN
        await service.sync_share(
            workflow_id="wf-123",
            user_id="user-456",
            permission="edit",
        )

        # THEN
        mock_openfga_client.write_tuples.assert_called_once()
        call_args = mock_openfga_client.write_tuples.call_args[0][0]
        assert call_args[0]["relation"] == "editor"

    @pytest.mark.asyncio
    async def test_sync_share_writes_executor_tuple_for_execute_permission(
        self,
        service: OpenFGAWorkflowSharingService,
        mock_openfga_client: MagicMock,
    ) -> None:
        """
        GIVEN a share with 'execute' permission
        WHEN sync_share is called
        THEN a tuple with 'executor' relation should be written
        """
        # WHEN
        await service.sync_share(
            workflow_id="wf-123",
            user_id="user-456",
            permission="execute",
        )

        # THEN
        mock_openfga_client.write_tuples.assert_called_once()
        call_args = mock_openfga_client.write_tuples.call_args[0][0]
        assert call_args[0]["relation"] == "executor"


@pytest.mark.xdist_group(name="test_openfga_workflow_sharing_remove")
class TestOpenFGARemoveShare:
    """Tests for removing shares from OpenFGA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_openfga_client(self) -> MagicMock:
        """Create a mock OpenFGA client."""
        client = MagicMock()
        client.write_tuples = AsyncMock(return_value=None)
        client.delete_tuples = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def service(self, mock_openfga_client: MagicMock) -> OpenFGAWorkflowSharingService:
        """Create service with mocked client."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        return OpenFGAWorkflowSharingService(openfga_client=mock_openfga_client)

    @pytest.mark.asyncio
    async def test_remove_share_deletes_all_permission_tuples(
        self,
        service: OpenFGAWorkflowSharingService,
        mock_openfga_client: MagicMock,
    ) -> None:
        """
        GIVEN a user has shares on a workflow
        WHEN remove_share is called
        THEN all permission tuples for that user/workflow should be deleted
        """
        # WHEN
        await service.remove_share(
            workflow_id="wf-123",
            user_id="user-456",
        )

        # THEN - Should delete all possible relations
        mock_openfga_client.delete_tuples.assert_called_once()
        call_args = mock_openfga_client.delete_tuples.call_args[0][0]
        # Should delete viewer, editor, executor tuples
        assert len(call_args) == 3
        relations = {t["relation"] for t in call_args}
        assert relations == {"viewer", "editor", "executor"}


@pytest.mark.xdist_group(name="test_openfga_workflow_sharing_owner")
class TestOpenFGASetWorkflowOwner:
    """Tests for setting workflow owner in OpenFGA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_openfga_client(self) -> MagicMock:
        """Create a mock OpenFGA client."""
        client = MagicMock()
        client.write_tuples = AsyncMock(return_value=None)
        client.delete_tuples = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def service(self, mock_openfga_client: MagicMock) -> OpenFGAWorkflowSharingService:
        """Create service with mocked client."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        return OpenFGAWorkflowSharingService(openfga_client=mock_openfga_client)

    @pytest.mark.asyncio
    async def test_set_workflow_owner_writes_owner_tuple(
        self,
        service: OpenFGAWorkflowSharingService,
        mock_openfga_client: MagicMock,
    ) -> None:
        """
        GIVEN a new workflow is created
        WHEN set_workflow_owner is called
        THEN an 'owner' tuple should be written
        """
        # WHEN
        await service.set_workflow_owner(
            workflow_id="wf-123",
            user_id="owner-user",
        )

        # THEN
        mock_openfga_client.write_tuples.assert_called_once()
        call_args = mock_openfga_client.write_tuples.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["user"] == "user:owner-user"
        assert call_args[0]["relation"] == "owner"
        assert call_args[0]["object"] == "workflow:wf-123"


@pytest.mark.xdist_group(name="test_openfga_workflow_sharing_check")
class TestOpenFGACheckWorkflowPermission:
    """Tests for checking workflow permissions via OpenFGA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.fixture
    def mock_openfga_client(self) -> MagicMock:
        """Create a mock OpenFGA client."""
        client = MagicMock()
        client.check_permission = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def service(self, mock_openfga_client: MagicMock) -> OpenFGAWorkflowSharingService:
        """Create service with mocked client."""
        from mcp_server_langgraph.auth.workflow_sharing import (
            OpenFGAWorkflowSharingService,
        )

        return OpenFGAWorkflowSharingService(openfga_client=mock_openfga_client)

    @pytest.mark.asyncio
    async def test_check_permission_calls_openfga(
        self,
        service: OpenFGAWorkflowSharingService,
        mock_openfga_client: MagicMock,
    ) -> None:
        """
        GIVEN an OpenFGA client
        WHEN check_permission is called
        THEN it should delegate to the OpenFGA client
        """
        # WHEN
        result = await service.check_permission(
            workflow_id="wf-123",
            user_id="user-456",
            permission="view",
        )

        # THEN
        assert result is True
        mock_openfga_client.check_permission.assert_called_once_with(
            user="user:user-456",
            relation="viewer",
            object="workflow:wf-123",
        )

    @pytest.mark.asyncio
    async def test_check_permission_returns_false_when_denied(
        self,
        service: OpenFGAWorkflowSharingService,
        mock_openfga_client: MagicMock,
    ) -> None:
        """
        GIVEN OpenFGA denies permission
        WHEN check_permission is called
        THEN it should return False
        """
        # GIVEN
        mock_openfga_client.check_permission = AsyncMock(return_value=False)

        # WHEN
        result = await service.check_permission(
            workflow_id="wf-123",
            user_id="user-456",
            permission="edit",
        )

        # THEN
        assert result is False


class TestPermissionMapping:
    """Tests for permission name to OpenFGA relation mapping."""

    def test_permission_to_relation_mapping_exists(self) -> None:
        """PERMISSION_TO_RELATION mapping should exist."""
        from mcp_server_langgraph.auth.workflow_sharing import PERMISSION_TO_RELATION

        assert "view" in PERMISSION_TO_RELATION
        assert "edit" in PERMISSION_TO_RELATION
        assert "execute" in PERMISSION_TO_RELATION

    def test_permission_to_relation_mapping_values(self) -> None:
        """Mapping should convert permissions to OpenFGA relations."""
        from mcp_server_langgraph.auth.workflow_sharing import PERMISSION_TO_RELATION

        assert PERMISSION_TO_RELATION["view"] == "viewer"
        assert PERMISSION_TO_RELATION["edit"] == "editor"
        assert PERMISSION_TO_RELATION["execute"] == "executor"
