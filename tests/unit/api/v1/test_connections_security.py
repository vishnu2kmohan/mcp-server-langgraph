"""
Connection Security Tests

TDD tests for validating that sensitive fields are never exposed in API responses.

SECURITY REQUIREMENTS:
- env dict must NEVER be in connection responses (contains secrets)
- oauth2_client_secret must NEVER be in responses
- oauth2_config should NOT expose client_secret
- transport must be included (required field)
"""

import gc

import pytest

from mcp_server_langgraph.api.v1.connections import ConnectionResponse
from mcp_server_langgraph.storage.models import MCPConnection

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestConnectionResponseSecurity:
    """Tests for secure ConnectionResponse model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.unit
    def test_connection_response_excludes_env(self) -> None:
        """SECURITY: env dict must never be in response schema."""
        # GIVEN the ConnectionResponse model
        schema = ConnectionResponse.model_json_schema()

        # THEN 'env' should NOT be in properties
        assert "env" not in schema["properties"]

    @pytest.mark.unit
    def test_connection_response_excludes_oauth_config(self) -> None:
        """SECURITY: oauth2_config (with client_secret) should not be in response."""
        # GIVEN the ConnectionResponse model
        schema = ConnectionResponse.model_json_schema()

        # THEN 'oauth2_config' should NOT be in properties
        assert "oauth2_config" not in schema["properties"]

    @pytest.mark.unit
    def test_connection_response_excludes_command_args(self) -> None:
        """SECURITY: stdio command/args could expose system paths."""
        # GIVEN the ConnectionResponse model
        schema = ConnectionResponse.model_json_schema()

        # THEN command and args should NOT be in properties
        assert "command" not in schema["properties"]
        assert "args" not in schema["properties"]

    @pytest.mark.unit
    def test_connection_response_includes_transport(self) -> None:
        """transport field must be included in response."""
        # GIVEN valid connection response data
        response_data = {
            "id": "conn-123",
            "name": "Test Connection",
            "url": "https://api.example.com",
            "auth_type": "api_key",
            "status": "connected",
            "transport": "streamable_http",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        # WHEN creating a ConnectionResponse
        response = ConnectionResponse(**response_data)

        # THEN transport should be accessible
        assert response.transport == "streamable_http"

    @pytest.mark.unit
    def test_connection_response_transport_in_schema(self) -> None:
        """transport field must be in response schema."""
        # GIVEN the ConnectionResponse model
        schema = ConnectionResponse.model_json_schema()

        # THEN 'transport' should be in properties
        assert "transport" in schema["properties"]

    @pytest.mark.unit
    def test_connection_response_accepts_all_auth_types(self) -> None:
        """ConnectionResponse should accept all valid auth types."""
        for auth_type in ["none", "api_key", "oauth2"]:
            response_data = {
                "id": "conn-123",
                "name": "Test",
                "url": "https://example.com",
                "auth_type": auth_type,
                "status": "connected",
                "transport": "streamable_http",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }

            # WHEN creating a ConnectionResponse
            response = ConnectionResponse(**response_data)

            # THEN it should succeed
            assert response.auth_type == auth_type

    @pytest.mark.unit
    def test_connection_response_accepts_all_status_values(self) -> None:
        """ConnectionResponse should accept all valid status values."""
        for status_value in ["disconnected", "connecting", "connected", "error", "auth_required"]:
            response_data = {
                "id": "conn-123",
                "name": "Test",
                "url": "https://example.com",
                "auth_type": "none",
                "status": status_value,
                "transport": "streamable_http",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }

            # WHEN creating a ConnectionResponse
            response = ConnectionResponse(**response_data)

            # THEN it should succeed
            assert response.status == status_value


class TestMCPConnectionToResponseConversion:
    """Tests for secure conversion from MCPConnection to ConnectionResponse."""

    @pytest.mark.unit
    def test_mcp_connection_has_env_field(self) -> None:
        """Verify MCPConnection has env field that we need to filter out."""
        # GIVEN the MCPConnection model
        schema = MCPConnection.model_json_schema()

        # THEN 'env' should be in MCPConnection (this is what we're protecting against)
        assert "env" in schema["properties"]

    @pytest.mark.unit
    def test_mcp_connection_to_response_excludes_env(self) -> None:
        """Converting MCPConnection to ConnectionResponse must exclude env."""
        # GIVEN a helper function to convert (we'll implement this)
        from mcp_server_langgraph.api.v1.connections import to_connection_response

        # AND an MCPConnection with env set
        from datetime import UTC, datetime

        connection = MCPConnection(
            id="conn-123",
            name="Test Connection",
            url="https://api.example.com",
            transport="stdio",
            auth_type="none",
            status="connected",
            command="/usr/bin/example",
            args=["--server"],
            env={"SECRET_KEY": "super-secret-value", "API_TOKEN": "token123"},
            owner_id="user-123",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # WHEN converting to ConnectionResponse
        response = to_connection_response(connection)

        # THEN response should NOT contain env
        response_dict = response.model_dump()
        assert "env" not in response_dict
        assert "SECRET_KEY" not in str(response_dict)
        assert "super-secret-value" not in str(response_dict)

    @pytest.mark.unit
    def test_mcp_connection_to_response_excludes_oauth_config(self) -> None:
        """Converting MCPConnection to ConnectionResponse must exclude oauth2_config."""
        from datetime import UTC, datetime

        from mcp_server_langgraph.api.v1.connections import to_connection_response
        from mcp_server_langgraph.storage.models import OAuth2Config

        # GIVEN an MCPConnection with oauth2_config
        connection = MCPConnection(
            id="conn-123",
            name="OAuth Connection",
            url="https://oauth.example.com",
            transport="streamable_http",
            auth_type="oauth2",
            status="connected",
            oauth2_config=OAuth2Config(
                client_id="my-client-id",
                # Note: client_secret should never be here in practice
            ),
            owner_id="user-123",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # WHEN converting to ConnectionResponse
        response = to_connection_response(connection)

        # THEN response should NOT contain oauth2_config
        response_dict = response.model_dump()
        assert "oauth2_config" not in response_dict

    @pytest.mark.unit
    def test_mcp_connection_to_response_preserves_safe_fields(self) -> None:
        """Converting MCPConnection should preserve non-sensitive fields."""
        from datetime import UTC, datetime

        from mcp_server_langgraph.api.v1.connections import to_connection_response

        connection = MCPConnection(
            id="conn-123",
            name="Test Connection",
            description="A test connection",
            url="https://api.example.com",
            transport="streamable_http",
            auth_type="api_key",
            status="connected",
            server_name="Example Server",
            server_version="1.0.0",
            tool_count=5,
            resource_count=3,
            prompt_count=2,
            owner_id="user-123",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # WHEN converting to ConnectionResponse
        response = to_connection_response(connection)

        # THEN safe fields should be preserved
        assert response.id == "conn-123"
        assert response.name == "Test Connection"
        assert response.description == "A test connection"
        assert response.url == "https://api.example.com"
        assert response.transport == "streamable_http"
        assert response.auth_type == "api_key"
        assert response.status == "connected"
        assert response.server_name == "Example Server"
        assert response.server_version == "1.0.0"
        assert response.tool_count == 5
        assert response.resource_count == 3
        assert response.prompt_count == 2


class TestConnectionEndpointReturnTypes:
    """Tests for endpoint return type annotations (must return ConnectionResponse)."""

    @pytest.mark.unit
    def test_create_connection_returns_connection_response(self) -> None:
        """POST /connections must return ConnectionResponse type."""
        from mcp_server_langgraph.api.v1.connections import ConnectionResponse, create_connection

        return_annotation = create_connection.__annotations__.get("return")
        assert return_annotation == ConnectionResponse, (
            f"SECURITY: create_connection must return ConnectionResponse, got {return_annotation}"
        )

    @pytest.mark.unit
    def test_get_connection_returns_connection_response(self) -> None:
        """GET /connections/{id} must return ConnectionResponse type."""
        from mcp_server_langgraph.api.v1.connections import ConnectionResponse, get_connection

        return_annotation = get_connection.__annotations__.get("return")
        assert return_annotation == ConnectionResponse, (
            f"SECURITY: get_connection must return ConnectionResponse, got {return_annotation}"
        )

    @pytest.mark.unit
    def test_update_connection_returns_connection_response(self) -> None:
        """PUT /connections/{id} must return ConnectionResponse type."""
        from mcp_server_langgraph.api.v1.connections import ConnectionResponse, update_connection

        return_annotation = update_connection.__annotations__.get("return")
        assert return_annotation == ConnectionResponse, (
            f"SECURITY: update_connection must return ConnectionResponse, got {return_annotation}"
        )


class TestConnectionEndpointSecurity:
    """Tests for endpoint-level security (integration-style unit tests)."""

    @pytest.mark.unit
    def test_connection_response_serialization_excludes_env(self) -> None:
        """JSON serialization should not include env."""
        response_data = {
            "id": "conn-123",
            "name": "Test",
            "url": "https://example.com",
            "auth_type": "none",
            "status": "connected",
            "transport": "streamable_http",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = ConnectionResponse(**response_data)

        # WHEN serializing to JSON
        json_str = response.model_dump_json()

        # THEN env should not appear
        assert "env" not in json_str

    @pytest.mark.unit
    def test_connection_response_dict_excludes_env(self) -> None:
        """Dict serialization should not include env."""
        response_data = {
            "id": "conn-123",
            "name": "Test",
            "url": "https://example.com",
            "auth_type": "none",
            "status": "connected",
            "transport": "streamable_http",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

        response = ConnectionResponse(**response_data)

        # WHEN converting to dict
        data = response.model_dump()

        # THEN env should not be a key
        assert "env" not in data
