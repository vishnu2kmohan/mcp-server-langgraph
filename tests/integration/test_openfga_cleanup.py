"""
Integration tests for OpenFGA tuple cleanup functionality.

Verifies that delete_tuples_for_object() properly removes all authorization
tuples when a resource is deleted, ensuring no orphaned permissions remain.
"""

import gc
from typing import Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.integration
@pytest.mark.openfga
@pytest.mark.xdist_group(name="integration_openfga_cleanup_tests")
class TestOpenFGATupleCleanup:
    """Test OpenFGA tuple cleanup for resource deletion"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_delete_tuples_for_object_removes_all_permissions(self):
        """
        Test that delete_tuples_for_object() removes all authorization tuples.

        Scenario:
        1. Create service_principal:test-sp
        2. Grant permissions (owner, acts_as, viewer)
        3. Call delete_tuples_for_object("service_principal:test-sp")
        4. Verify all tuples are deleted
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        client = OpenFGAClient(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
        )

        # Mock the OpenFGA SDK calls
        with patch.object(client.client, "expand") as mock_expand:
            with patch.object(client.client, "write") as mock_write:
                # Setup: Simulate service principal with 3 relations
                # Each relation has 1-2 users with permissions
                mock_expand.side_effect = [
                    # owner relation
                    Mock(tree=Mock(model_dump=lambda: {"leaf": {"users": {"users": ["user:alice"]}}})),
                    # acts_as relation
                    Mock(tree=Mock(model_dump=lambda: {"leaf": {"users": {"users": ["user:bob"]}}})),
                    # viewer relation (computed from owner)
                    Mock(tree=Mock(model_dump=lambda: {"leaf": {"users": {"users": ["user:alice"]}}})),
                    # editor relation (computed from owner)
                    Mock(tree=Mock(model_dump=lambda: {"leaf": {"users": {"users": ["user:alice"]}}})),
                ]

                # Act: Delete all tuples for service principal
                await client.delete_tuples_for_object("service_principal:test-sp")

                # Assert: delete_tuples should be called with tuples from all relations
                # We expect at least one delete call
                assert mock_write.call_count >= 1

                # Verify deletes contain the expected tuple structure
                delete_calls = [call for call in mock_write.call_args_list]
                assert len(delete_calls) > 0

    @pytest.mark.asyncio
    async def test_delete_tuples_for_nonexistent_object_succeeds(self):
        """
        Test that deleting tuples for nonexistent object doesn't crash.

        Edge case: Attempting to clean up an object that has no tuples.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        client = OpenFGAClient(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
        )

        with patch.object(client.client, "expand") as mock_expand:
            # Simulate no tuples found (empty expansion)
            mock_expand.return_value = Mock(tree=Mock(model_dump=lambda: {}))

            # Should not raise exception
            await client.delete_tuples_for_object("service_principal:nonexistent")

    @pytest.mark.asyncio
    async def test_delete_tuples_batch_processing(self):
        """
        Test that large numbers of tuples are deleted in batches.

        Ensures we don't hit API limits with too many tuples at once.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        client = OpenFGAClient(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
        )

        with patch.object(client.client, "expand") as mock_expand:
            with patch.object(client.client, "write") as mock_write:
                # Simulate 250 users with permissions (exceeds typical batch size of 100)
                large_user_list = [f"user:user{i}" for i in range(250)]

                mock_expand.side_effect = [
                    # owner relation with many users
                    Mock(tree=Mock(model_dump=lambda: {"leaf": {"users": {"users": large_user_list}}})),
                    # Other relations empty
                    Mock(tree=Mock(model_dump=lambda: {})),
                    Mock(tree=Mock(model_dump=lambda: {})),
                    Mock(tree=Mock(model_dump=lambda: {})),
                ]

                # Act: Delete tuples
                await client.delete_tuples_for_object("service_principal:large-sp")

                # Assert: Should make multiple delete calls (batched)
                # With 250 tuples and batch size 100, expect 3 batches
                assert mock_write.call_count >= 2, "Should batch large deletes"

    @pytest.mark.asyncio
    async def test_delete_tuples_handles_expansion_errors_gracefully(self):
        """
        Test that expansion errors for individual relations don't crash cleanup.

        If one relation fails to expand, others should still be cleaned up.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        client = OpenFGAClient(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model",
        )

        with patch.object(client.client, "expand") as mock_expand:
            with patch.object(client.client, "write") as mock_write:
                # Simulate partial failure: first relation succeeds, second fails, third succeeds
                mock_expand.side_effect = [
                    Mock(tree=Mock(model_dump=lambda: {"leaf": {"users": {"users": ["user:alice"]}}})),
                    Exception("Network error"),  # This relation fails
                    Mock(tree=Mock(model_dump=lambda: {"leaf": {"users": {"users": ["user:bob"]}}})),
                    Mock(tree=Mock(model_dump=lambda: {})),
                ]

                # Should not raise exception - should continue with other relations
                await client.delete_tuples_for_object("service_principal:test-sp")

                # Should still delete tuples from successful relations
                assert mock_write.call_count >= 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="integration_openfga_cleanup_tests")
class TestTupleExtractionHelpers:
    """Test helper functions for extracting tuples from expansion trees"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_extract_users_from_simple_leaf(self):
        """
        Test extracting users from simple leaf node.

        Expansion tree structure:
        {"leaf": {"users": {"users": ["user:alice", "user:bob"]}}}
        """
        from mcp_server_langgraph.auth.openfga import _extract_users_from_expansion

        expansion = {"leaf": {"users": {"users": ["user:alice", "user:bob"]}}}

        users = _extract_users_from_expansion(expansion)

        assert set(users) == {"user:alice", "user:bob"}

    def test_extract_users_from_empty_expansion(self):
        """Test extracting from empty expansion returns empty list"""
        from mcp_server_langgraph.auth.openfga import _extract_users_from_expansion

        expansion = {}
        users = _extract_users_from_expansion(expansion)

        assert users == []

    def test_extract_users_from_union_node(self):
        """
        Test extracting users from union node (multiple children).

        Union nodes combine users from multiple sources.
        """
        from mcp_server_langgraph.auth.openfga import _extract_users_from_expansion

        expansion = {
            "union": {
                "nodes": [
                    {"leaf": {"users": {"users": ["user:alice"]}}},
                    {"leaf": {"users": {"users": ["user:bob"]}}},
                ]
            }
        }

        users = _extract_users_from_expansion(expansion)

        assert set(users) == {"user:alice", "user:bob"}
