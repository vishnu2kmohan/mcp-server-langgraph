"""
E2E Test Configuration and Fixtures

Provides fixtures for end-to-end tests including:
- OpenFGA tuple seeding for authorization testing
- Real infrastructure client connections
- User journey helper fixtures

These fixtures work with docker-compose.test.yml infrastructure.
"""

import os

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def openfga_seeded_tuples(test_infrastructure):
    """
    Seed OpenFGA with authorization tuples for E2E tests.

    This fixture creates the necessary authorization relationships
    for user 'alice' to execute agent_chat and other MCP tools.

    Tuples created:
    - user:alice executor tool:agent_chat
    - user:alice executor tool:conversation_get
    - user:alice executor tool:conversation_search
    - user:alice viewer conversation:* (pattern)

    Yields:
        dict: Mapping of created tuples for test assertions

    Cleanup:
        Deletes all created tuples after test completes
    """
    if not test_infrastructure["ready"]:
        pytest.skip("E2E infrastructure not ready")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    # Get OpenFGA connection from environment (set by openfga_client_real fixture)
    api_url = os.getenv("OPENFGA_API_URL", "http://localhost:9080")
    store_id = os.getenv("OPENFGA_STORE_ID")
    model_id = os.getenv("OPENFGA_MODEL_ID")

    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized (OPENFGA_STORE_ID not set)")

    config = OpenFGAConfig(api_url=api_url, store_id=store_id, model_id=model_id)
    client = OpenFGAClient(config=config)

    # Define tuples for alice user
    # Note: 'alice' is the username in keycloak-test-realm.json
    tuples_to_create = [
        {"user": "user:alice", "relation": "executor", "object": "tool:agent_chat"},
        {"user": "user:alice", "relation": "executor", "object": "tool:conversation_get"},
        {"user": "user:alice", "relation": "executor", "object": "tool:conversation_search"},
        {"user": "user:alice", "relation": "executor", "object": "tool:search_tools"},
    ]

    # Write tuples to OpenFGA
    try:
        await client.write_tuples(tuples_to_create)
    except Exception as e:
        pytest.skip(f"Failed to seed OpenFGA tuples: {e}")

    yield {
        "tuples": tuples_to_create,
        "user": "user:alice",
        "tools": ["agent_chat", "conversation_get", "conversation_search", "search_tools"],
    }

    # Cleanup: Delete created tuples
    try:
        await client.delete_tuples(tuples_to_create)
    except Exception:
        # Cleanup failure is non-critical - tuples will be orphaned but won't affect other tests
        pass


@pytest_asyncio.fixture
async def openfga_admin_tuples(test_infrastructure):
    """
    Seed OpenFGA with admin-level authorization tuples for E2E tests.

    Creates tuples that allow alice to manage service principals and API keys.

    Tuples created:
    - user:alice admin organization:default
    - organization:default#admin can_manage service_principal:*

    Yields:
        dict: Mapping of created admin tuples

    Cleanup:
        Deletes all created tuples after test completes
    """
    if not test_infrastructure["ready"]:
        pytest.skip("E2E infrastructure not ready")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, OpenFGAConfig

    api_url = os.getenv("OPENFGA_API_URL", "http://localhost:9080")
    store_id = os.getenv("OPENFGA_STORE_ID")
    model_id = os.getenv("OPENFGA_MODEL_ID")

    if not store_id or not model_id:
        pytest.skip("OpenFGA store not initialized")

    config = OpenFGAConfig(api_url=api_url, store_id=store_id, model_id=model_id)
    client = OpenFGAClient(config=config)

    # Define admin tuples for alice
    tuples_to_create = [
        {"user": "user:alice", "relation": "admin", "object": "organization:default"},
    ]

    try:
        await client.write_tuples(tuples_to_create)
    except Exception as e:
        pytest.skip(f"Failed to seed admin OpenFGA tuples: {e}")

    yield {
        "tuples": tuples_to_create,
        "user": "user:alice",
        "is_admin": True,
    }

    # Cleanup
    try:
        await client.delete_tuples(tuples_to_create)
    except Exception:
        pass


@pytest.fixture
def e2e_api_base_url():
    """
    Get the base URL for E2E API calls.

    Returns the MCP server URL for E2E tests.
    Default: http://localhost:8000
    """
    return os.getenv("MCP_SERVER_URL", "http://localhost:8000")


@pytest.fixture
def e2e_keycloak_base_url():
    """
    Get the Keycloak base URL for E2E tests.

    Default: http://localhost:9082/authn
    """
    return os.getenv("KEYCLOAK_URL", "http://localhost:9082/authn")
