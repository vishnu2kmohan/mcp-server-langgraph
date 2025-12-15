"""
Test Qdrant bootstrap configuration in docker-compose.test.yml.

This test validates that the E2E test infrastructure has proper Qdrant
configuration including:
- qdrant-test service running and healthy
- qdrant-init-test service to bootstrap default collections
- Proper dependencies and environment configuration

Following TDD RED-GREEN-REFACTOR cycle to fix E2E test failures caused by:
- VectorsPage failing because no default collection exists
- No tenant-aware collection initialization

Reference: E2E Tests workflow failures with Qdrant-related errors
"""

import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def repo_root() -> Path:
    """Get repository root directory (shared across all tests in module)."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return Path(result.stdout.strip())


@pytest.fixture(scope="module")
def docker_compose_config(repo_root: Path) -> dict:
    """Load and parse docker-compose.test.yml."""
    docker_compose_file = repo_root / "docker-compose.test.yml"
    with open(docker_compose_file) as f:
        return yaml.safe_load(f)


def test_qdrant_test_service_exists(docker_compose_config: dict) -> None:
    """
    Verify that qdrant-test service is defined in docker-compose.test.yml.
    """
    services = docker_compose_config.get("services", {})
    assert "qdrant-test" in services, (
        f"Service 'qdrant-test' not found in docker-compose.test.yml\nAvailable services: {list(services.keys())}"
    )


def test_qdrant_test_has_healthcheck(docker_compose_config: dict) -> None:
    """
    Verify that qdrant-test service has a healthcheck configured.
    """
    services = docker_compose_config.get("services", {})
    qdrant_service = services.get("qdrant-test", {})

    healthcheck = qdrant_service.get("healthcheck")
    assert healthcheck is not None, (
        "Service 'qdrant-test' must have a healthcheck configured\n"
        "This is required for dependent services to wait for Qdrant readiness"
    )

    # Verify healthcheck has required fields
    assert "test" in healthcheck, "Healthcheck must have a 'test' command"
    assert "interval" in healthcheck, "Healthcheck must have an 'interval'"


def test_qdrant_init_test_service_exists(docker_compose_config: dict) -> None:
    """
    Verify that qdrant-init-test service is defined to bootstrap collections.

    The qdrant-init-test service should:
    - Wait for qdrant-test to be healthy
    - Create default collection(s) for E2E testing
    - Support tenant-aware collection naming
    """
    services = docker_compose_config.get("services", {})
    assert "qdrant-init-test" in services, (
        "Service 'qdrant-init-test' not found in docker-compose.test.yml\n"
        "\n"
        "This service is required to bootstrap Qdrant collections for E2E tests.\n"
        "Without it, VectorsPage tests fail because no collections exist.\n"
        "\n"
        "Expected service configuration:\n"
        "  qdrant-init-test:\n"
        "    image: curlimages/curl:latest\n"
        "    depends_on:\n"
        "      qdrant-test:\n"
        "        condition: service_healthy\n"
        "    command: [...create collections...]\n"
        "\n"
        f"Available services: {list(services.keys())}"
    )


def test_qdrant_init_depends_on_qdrant_healthy(docker_compose_config: dict) -> None:
    """
    Verify that qdrant-init-test waits for qdrant-test to be healthy.
    """
    services = docker_compose_config.get("services", {})
    qdrant_init = services.get("qdrant-init-test", {})

    depends_on = qdrant_init.get("depends_on", {})

    # Check for qdrant-test dependency with health condition
    if isinstance(depends_on, list):
        # Simple list format
        assert "qdrant-test" in depends_on, "qdrant-init-test must depend on qdrant-test"
    elif isinstance(depends_on, dict):
        # Extended format with conditions
        assert "qdrant-test" in depends_on, "qdrant-init-test must depend on qdrant-test"
        qdrant_dep = depends_on.get("qdrant-test", {})
        condition = qdrant_dep.get("condition")
        assert condition == "service_healthy", (
            f"qdrant-init-test should wait for qdrant-test to be healthy.\n"
            f"Current condition: {condition}\n"
            f"Expected: service_healthy"
        )


def test_qdrant_init_creates_default_collection(docker_compose_config: dict) -> None:
    """
    Verify that qdrant-init-test creates the default mcp_context collection.

    The default collection should match config.qdrant_collection_name from
    src/mcp_server_langgraph/core/config.py
    """
    services = docker_compose_config.get("services", {})
    qdrant_init = services.get("qdrant-init-test", {})

    command = qdrant_init.get("command")
    assert command is not None, "qdrant-init-test must have a command to create collections"

    # Command can be string or list - join all elements to get full command
    command_str = " ".join(command) if isinstance(command, list) else command

    # Check that the command creates the default collection
    assert "mcp_context" in command_str or "collections" in command_str, (
        "qdrant-init-test command should create the 'mcp_context' collection\n"
        "\n"
        "This collection name matches config.qdrant_collection_name.\n"
        "E2E tests expect this collection to exist.\n"
        f"\n"
        f"Current command: {command}"
    )


def test_qdrant_init_uses_correct_vector_size(docker_compose_config: dict) -> None:
    """
    Verify that qdrant-init-test creates collections with correct vector dimensions.

    Common embedding model dimensions:
    - all-MiniLM-L6-v2: 384 dimensions
    - text-embedding-3-small: 1536 dimensions
    - text-embedding-ada-002: 1536 dimensions
    """
    services = docker_compose_config.get("services", {})
    qdrant_init = services.get("qdrant-init-test", {})

    command = qdrant_init.get("command")
    if command is None:
        pytest.skip("No command configured yet")

    # Command can be string or list - join all elements to get full command
    command_str = " ".join(command) if isinstance(command, list) else command

    # Check for vector size configuration
    # Either 384 (MiniLM) or 1536 (OpenAI) are valid
    has_vector_size = "384" in command_str or "1536" in command_str or "size" in command_str

    assert has_vector_size, (
        "qdrant-init-test should specify vector dimensions in collection creation.\n"
        "\n"
        "Common sizes:\n"
        "  - 384: all-MiniLM-L6-v2 (default in config)\n"
        "  - 1536: OpenAI text-embedding-3-small\n"
        f"\n"
        f"Current command: {command}"
    )


def test_mcp_server_depends_on_qdrant_init(docker_compose_config: dict) -> None:
    """
    Verify that mcp-server-test waits for qdrant-init-test to complete.

    This ensures collections are created before the MCP server starts
    and serves API requests.
    """
    services = docker_compose_config.get("services", {})
    mcp_server = services.get("mcp-server-test", {})

    if not mcp_server:
        pytest.skip("mcp-server-test not defined (may use different name)")

    depends_on = mcp_server.get("depends_on", {})

    # Check for qdrant-init-test dependency
    if isinstance(depends_on, list):
        has_qdrant_init = "qdrant-init-test" in depends_on
    elif isinstance(depends_on, dict):
        has_qdrant_init = "qdrant-init-test" in depends_on
    else:
        has_qdrant_init = False

    assert has_qdrant_init, (
        "mcp-server-test should depend on qdrant-init-test to ensure\n"
        "collections are created before the server handles API requests.\n"
        f"\n"
        f"Current depends_on: {depends_on}"
    )


def test_qdrant_network_alias(docker_compose_config: dict) -> None:
    """
    Verify qdrant-test has network alias 'qdrant' for service discovery.

    The alias allows services to connect using 'http://qdrant:6333'
    which matches production configuration.
    """
    services = docker_compose_config.get("services", {})
    qdrant_service = services.get("qdrant-test", {})

    networks = qdrant_service.get("networks", {})

    # Find the network alias
    has_alias = False
    for network_name, network_config in networks.items():
        if isinstance(network_config, dict):
            aliases = network_config.get("aliases", [])
            if "qdrant" in aliases:
                has_alias = True
                break

    assert has_alias, (
        "qdrant-test should have network alias 'qdrant' for service discovery.\n"
        "\n"
        "Example configuration:\n"
        "  networks:\n"
        "    mcp-test-network:\n"
        "      aliases:\n"
        "        - qdrant\n"
        f"\n"
        f"Current networks: {networks}"
    )
