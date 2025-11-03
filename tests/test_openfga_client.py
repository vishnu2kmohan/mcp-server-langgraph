"""Unit tests for openfga_client.py - OpenFGA Integration"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from openfga_sdk.client.models import ClientCheckRequest, ClientTuple, ClientWriteRequest


@pytest.mark.unit
@pytest.mark.openfga
class TestOpenFGAClient:
    """Test OpenFGAClient class"""

    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    def test_init(self, mock_sdk_client):
        """Test OpenFGA client initialization"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        client = OpenFGAClient(api_url="http://localhost:8080", store_id="test-store", model_id="test-model")

        assert client.api_url == "http://localhost:8080"
        assert client.store_id == "test-store"
        assert client.model_id == "test-model"
        mock_sdk_client.assert_called_once()

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_check_permission_allowed(self, mock_sdk_client):
        """Test permission check returns True"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        # Mock the check response
        mock_response = MagicMock()
        mock_response.allowed = True

        mock_instance = AsyncMock()
        mock_instance.check.return_value = mock_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient(api_url="http://localhost:8080", store_id="test-store", model_id="test-model")

        result = await client.check_permission(user="user:alice", relation="executor", object="tool:chat")

        assert result is True
        mock_instance.check.assert_called_once()

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_check_permission_denied(self, mock_sdk_client):
        """Test permission check returns False"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_response = MagicMock()
        mock_response.allowed = False

        mock_instance = AsyncMock()
        mock_instance.check.return_value = mock_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()
        result = await client.check_permission(user="user:bob", relation="admin", object="organization:acme")

        assert result is False

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_check_permission_error(self, mock_sdk_client):
        """Test permission check handles errors (wrapped in RetryExhaustedError after retries)"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient
        from mcp_server_langgraph.core.exceptions import RetryExhaustedError

        mock_instance = AsyncMock()
        mock_instance.check.side_effect = Exception("OpenFGA unavailable")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        # After resilience decorators, exceptions are wrapped in RetryExhaustedError
        with pytest.raises(RetryExhaustedError, match="Retry exhausted after 3 attempts"):
            await client.check_permission(user="user:alice", relation="executor", object="tool:chat")

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_write_tuples_success(self, mock_sdk_client):
        """Test writing relationship tuples"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_instance = AsyncMock()
        mock_instance.write.return_value = MagicMock()
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        tuples = [
            {"user": "user:alice", "relation": "executor", "object": "tool:chat"},
            {"user": "user:bob", "relation": "member", "object": "organization:acme"},
        ]

        await client.write_tuples(tuples)

        mock_instance.write.assert_called_once()
        call_args = mock_instance.write.call_args[0][0]
        assert isinstance(call_args, ClientWriteRequest)
        assert len(call_args.writes) == 2

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_write_tuples_error(self, mock_sdk_client):
        """Test write tuples handles errors (wrapped in RetryExhaustedError after retries)"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient
        from mcp_server_langgraph.core.exceptions import RetryExhaustedError

        mock_instance = AsyncMock()
        mock_instance.write.side_effect = Exception("Write failed")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        tuples = [{"user": "user:alice", "relation": "executor", "object": "tool:chat"}]

        # After resilience decorators, exceptions are wrapped in RetryExhaustedError
        with pytest.raises(RetryExhaustedError, match="Retry exhausted after 3 attempts"):
            await client.write_tuples(tuples)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_delete_tuples_success(self, mock_sdk_client):
        """Test deleting relationship tuples"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_instance = AsyncMock()
        mock_instance.write.return_value = MagicMock()
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        tuples = [{"user": "user:alice", "relation": "executor", "object": "tool:chat"}]

        await client.delete_tuples(tuples)

        mock_instance.write.assert_called_once()
        call_args = mock_instance.write.call_args[0][0]
        assert isinstance(call_args, ClientWriteRequest)
        assert len(call_args.deletes) == 1

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_delete_tuples_error(self, mock_sdk_client):
        """Test delete tuples handles errors"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_instance = AsyncMock()
        mock_instance.write.side_effect = Exception("Delete failed")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        tuples = [{"user": "user:alice", "relation": "executor", "object": "tool:chat"}]

        with pytest.raises(Exception, match="Delete failed"):
            await client.delete_tuples(tuples)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_list_objects_success(self, mock_sdk_client):
        """Test listing accessible objects"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_response = MagicMock()
        mock_response.objects = ["tool:chat", "tool:search", "tool:analyze"]

        mock_instance = AsyncMock()
        mock_instance.list_objects.return_value = mock_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        result = await client.list_objects(user="user:alice", relation="executor", object_type="tool")

        assert len(result) == 3
        assert "tool:chat" in result
        assert "tool:search" in result
        assert "tool:analyze" in result

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_list_objects_empty(self, mock_sdk_client):
        """Test listing objects with no results"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_response = MagicMock()
        mock_response.objects = []

        mock_instance = AsyncMock()
        mock_instance.list_objects.return_value = mock_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        result = await client.list_objects(user="user:bob", relation="admin", object_type="organization")

        assert result == []

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_list_objects_error(self, mock_sdk_client):
        """Test list objects handles errors"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_instance = AsyncMock()
        mock_instance.list_objects.side_effect = Exception("List failed")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        with pytest.raises(Exception, match="List failed"):
            await client.list_objects(user="user:alice", relation="executor", object_type="tool")

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_expand_relation_success(self, mock_sdk_client):
        """Test expanding a relation to see all users with access"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_tree = MagicMock()
        mock_tree.model_dump.return_value = {
            "root": {"name": "tool:chat#executor", "leaf": {"users": {"users": ["user:alice", "user:bob"]}}}
        }

        mock_response = MagicMock()
        mock_response.tree = mock_tree

        mock_instance = AsyncMock()
        mock_instance.expand.return_value = mock_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        result = await client.expand_relation(relation="executor", object="tool:chat")

        assert "root" in result
        mock_instance.expand.assert_called_once()

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_expand_relation_empty(self, mock_sdk_client):
        """Test expanding relation with no tree"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_response = MagicMock()
        mock_response.tree = None

        mock_instance = AsyncMock()
        mock_instance.expand.return_value = mock_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        result = await client.expand_relation(relation="executor", object="tool:chat")

        assert result == {}

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_expand_relation_error(self, mock_sdk_client):
        """Test expand relation handles errors"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        mock_instance = AsyncMock()
        mock_instance.expand.side_effect = Exception("Expand failed")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        with pytest.raises(Exception, match="Expand failed"):
            await client.expand_relation(relation="executor", object="tool:chat")


@pytest.mark.unit
@pytest.mark.openfga
class TestOpenFGAAuthorizationModel:
    """Test OpenFGAAuthorizationModel class"""

    def test_get_model_definition(self):
        """Test authorization model definition"""
        from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

        model = OpenFGAAuthorizationModel.get_model_definition()

        assert model["schema_version"] == "1.1"
        assert "type_definitions" in model

        # Check all expected types are defined
        types = [td["type"] for td in model["type_definitions"]]
        assert "user" in types
        assert "organization" in types
        assert "tool" in types
        assert "conversation" in types
        assert "role" in types

    def test_organization_relations(self):
        """Test organization type has correct relations"""
        from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

        model = OpenFGAAuthorizationModel.get_model_definition()
        org_type = next(td for td in model["type_definitions"] if td["type"] == "organization")

        assert "member" in org_type["relations"]
        assert "admin" in org_type["relations"]

    def test_tool_relations(self):
        """Test tool type has correct relations"""
        from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

        model = OpenFGAAuthorizationModel.get_model_definition()
        tool_type = next(td for td in model["type_definitions"] if td["type"] == "tool")

        assert "owner" in tool_type["relations"]
        assert "executor" in tool_type["relations"]
        assert "organization" in tool_type["relations"]

    def test_conversation_relations(self):
        """Test conversation type has correct relations"""
        from mcp_server_langgraph.auth.openfga import OpenFGAAuthorizationModel

        model = OpenFGAAuthorizationModel.get_model_definition()
        conv_type = next(td for td in model["type_definitions"] if td["type"] == "conversation")

        assert "owner" in conv_type["relations"]
        assert "viewer" in conv_type["relations"]
        assert "editor" in conv_type["relations"]


@pytest.mark.unit
@pytest.mark.openfga
class TestOpenFGAUtilityFunctions:
    """Test utility functions for OpenFGA"""

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_initialize_openfga_store(self, mock_sdk_client):
        """Test initializing OpenFGA store with authorization model"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, initialize_openfga_store

        # Mock store creation
        mock_store_response = MagicMock()
        mock_store_response.id = "test-store-id"

        # Mock model creation
        mock_model_response = MagicMock()
        mock_model_response.authorization_model_id = "test-model-id"

        mock_instance = AsyncMock()
        mock_instance.create_store.return_value = mock_store_response
        mock_instance.write_authorization_model.return_value = mock_model_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()
        store_id = await initialize_openfga_store(client)

        assert store_id == "test-store-id"
        assert client.store_id == "test-store-id"
        assert client.model_id == "test-model-id"
        mock_instance.create_store.assert_called_once()
        mock_instance.write_authorization_model.assert_called_once()

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_initialize_openfga_store_error(self, mock_sdk_client):
        """Test initialize store handles errors"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, initialize_openfga_store

        mock_instance = AsyncMock()
        mock_instance.create_store.side_effect = Exception("Store creation failed")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        with pytest.raises(Exception, match="Store creation failed"):
            await initialize_openfga_store(client)

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_seed_sample_data(self, mock_sdk_client):
        """Test seeding sample data"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient, seed_sample_data

        mock_instance = AsyncMock()
        mock_instance.write.return_value = MagicMock()
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()
        await seed_sample_data(client)

        # Verify write was called
        mock_instance.write.assert_called_once()

        # Verify we wrote tuples (sample data has 10 tuples)
        call_args = mock_instance.write.call_args[0][0]
        assert isinstance(call_args, ClientWriteRequest)
        assert len(call_args.writes) == 10


@pytest.mark.integration
@pytest.mark.openfga
class TestOpenFGAIntegration:
    """Integration tests for OpenFGA (requires running OpenFGA instance)"""

    @pytest.mark.skip(reason="Requires running OpenFGA instance")
    @pytest.mark.asyncio
    async def test_full_authorization_flow(self):
        """Test complete authorization flow with real OpenFGA"""
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        # This test requires actual OpenFGA server
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            store_id=None,  # Would need to be created
            model_id=None,  # Would need to be created
        )

        # Write relationship
        await client.write_tuples([{"user": "user:alice", "relation": "executor", "object": "tool:chat"}])

        # Check permission
        allowed = await client.check_permission(user="user:alice", relation="executor", object="tool:chat")
        assert allowed is True

        # List objects
        tools = await client.list_objects(user="user:alice", relation="executor", object_type="tool")
        assert "tool:chat" in tools

        # Delete relationship
        await client.delete_tuples([{"user": "user:alice", "relation": "executor", "object": "tool:chat"}])

        # Verify permission removed
        allowed = await client.check_permission(user="user:alice", relation="executor", object="tool:chat")
        assert allowed is False


@pytest.mark.unit
@pytest.mark.openfga
class TestOpenFGACircuitBreakerCriticality:
    """Test OpenFGA circuit breaker with criticality flag for fail-open/fail-closed behavior"""

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_circuit_breaker_fails_closed_for_critical_resources(self, mock_sdk_client):
        """
        Test circuit breaker denies access (fail-closed) when open for CRITICAL resources.

        SECURITY: Critical resources (admin, delete, etc.) must fail-closed to prevent
        unauthorized access during OpenFGA outages.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

        # Mock OpenFGA to always fail (trigger circuit breaker)
        mock_instance = AsyncMock()
        mock_instance.check.side_effect = Exception("OpenFGA unavailable")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        # Trigger circuit breaker to open (10 failures)
        for _ in range(15):
            try:
                await client.check_permission(user="user:alice", relation="admin", object="system:critical", critical=True)
            except Exception:
                pass  # Ignore errors, just trigger circuit breaker

        # Circuit breaker should now be open
        cb = get_circuit_breaker("openfga")
        # Check circuit breaker is open (state.name should be 'open')
        assert (
            hasattr(cb.state, "name") and cb.state.name == "open"
        ), f"Expected circuit breaker to be open, got state: {cb.state}"

        # Now check permission for critical resource - should return False (fail-closed)
        result = await client.check_permission(user="user:alice", relation="admin", object="system:critical", critical=True)

        assert result is False  # CRITICAL: Must deny access when circuit is open

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_circuit_breaker_fails_open_for_non_critical_resources(self, mock_sdk_client):
        """
        Test circuit breaker allows access (fail-open) when open for NON-CRITICAL resources.

        For non-critical resources (like read-only content), we prefer availability
        over strict security, so we fail-open.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

        # Mock OpenFGA to always fail (trigger circuit breaker)
        mock_instance = AsyncMock()
        mock_instance.check.side_effect = Exception("OpenFGA unavailable")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        # Trigger circuit breaker to open (10 failures)
        for _ in range(15):
            try:
                await client.check_permission(user="user:alice", relation="viewer", object="content:public", critical=False)
            except Exception:
                pass  # Ignore errors, just trigger circuit breaker

        # Circuit breaker should now be open
        cb = get_circuit_breaker("openfga")
        # Check circuit breaker is open (state.name should be 'open')
        assert (
            hasattr(cb.state, "name") and cb.state.name == "open"
        ), f"Expected circuit breaker to be open, got state: {cb.state}"

        # Now check permission for non-critical resource - should return True (fail-open)
        result = await client.check_permission(user="user:alice", relation="viewer", object="content:public", critical=False)

        assert result is True  # Allow access for non-critical resources

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_circuit_breaker_defaults_to_critical_true(self, mock_sdk_client):
        """
        Test circuit breaker defaults to critical=True (fail-closed) if not specified.

        SECURITY: For safety, all resources are considered critical by default.
        Developers must explicitly opt-in to fail-open behavior.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient
        from mcp_server_langgraph.resilience.circuit_breaker import get_circuit_breaker

        # Mock OpenFGA to always fail (trigger circuit breaker)
        mock_instance = AsyncMock()
        mock_instance.check.side_effect = Exception("OpenFGA unavailable")
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        # Trigger circuit breaker to open (10 failures)
        for _ in range(15):
            try:
                # Call without critical parameter (should default to True)
                await client.check_permission(user="user:alice", relation="executor", object="tool:sensitive")
            except Exception:
                pass  # Ignore errors, just trigger circuit breaker

        # Circuit breaker should now be open
        cb = get_circuit_breaker("openfga")
        # Check circuit breaker is open (state.name should be 'open')
        assert (
            hasattr(cb.state, "name") and cb.state.name == "open"
        ), f"Expected circuit breaker to be open, got state: {cb.state}"

        # Check permission without specifying critical parameter
        result = await client.check_permission(user="user:alice", relation="executor", object="tool:sensitive")

        # Should default to critical=True (fail-closed)
        assert result is False

    @pytest.mark.asyncio
    @patch("mcp_server_langgraph.auth.openfga.OpenFgaClient")
    async def test_circuit_breaker_allows_when_closed_regardless_of_criticality(self, mock_sdk_client):
        """
        Test circuit breaker respects OpenFGA response when circuit is CLOSED.

        When circuit breaker is closed (normal operation), criticality flag should have
        no effect - OpenFGA response is always used.
        """
        from mcp_server_langgraph.auth.openfga import OpenFGAClient

        # Mock OpenFGA to return allowed=True
        mock_response = MagicMock()
        mock_response.allowed = True

        mock_instance = AsyncMock()
        mock_instance.check.return_value = mock_response
        mock_sdk_client.return_value = mock_instance

        client = OpenFGAClient()

        # Check both critical and non-critical - both should return OpenFGA response
        result_critical = await client.check_permission(
            user="user:alice", relation="admin", object="system:critical", critical=True
        )
        result_non_critical = await client.check_permission(
            user="user:alice", relation="viewer", object="content:public", critical=False
        )

        assert result_critical is True  # OpenFGA allowed
        assert result_non_critical is True  # OpenFGA allowed
