"""
Test E2E Keycloak realm configuration and setup.

This test validates that the E2E test infrastructure has proper Keycloak
configuration including client setup and test user provisioning.

Following TDD RED-GREEN-REFACTOR cycle to fix E2E test failures caused by:
- Missing Keycloak client 'mcp-server'
- Missing test user 'alice' with password 'alice123'
- No automated realm import on Keycloak startup

Reference: E2E Tests workflow failures with 401 authentication errors
"""

import gc
import json
from pathlib import Path

import pytest
import yaml


def test_keycloak_realm_import_file_exists():
    """
    Verify that keycloak-test-realm.json exists in tests/e2e/.

    This file should contain the realm configuration with pre-configured
    client and test users for E2E testing.
    """
    realm_file = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "tests/e2e/keycloak-test-realm.json")

    assert realm_file.exists(), (
        f"Keycloak realm import file not found: {realm_file}\n"
        "\n"
        "Expected file: tests/e2e/keycloak-test-realm.json\n"
        "This file should contain:\n"
        "  - Realm: master\n"
        "  - Client: mcp-server (publicClient, directAccessGrants enabled)\n"
        "  - User: alice with password alice123\n"
        "\n"
        "Fix: Create tests/e2e/keycloak-test-realm.json with realm configuration"
    )

    # Verify it's valid JSON
    with open(realm_file) as f:
        try:
            realm_config = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Realm file is not valid JSON: {e}")

    assert isinstance(realm_config, dict), f"Realm file must contain a JSON object, got: {type(realm_config)}"


def test_realm_json_has_mcp_server_client():
    """
    Verify that the realm configuration includes the 'mcp-server' client.

    The E2E tests expect a client named 'mcp-server' with:
    - enabled: true
    - publicClient: true
    - directAccessGrantsEnabled: true (for password grant flow)
    """
    realm_file = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "tests/e2e/keycloak-test-realm.json")

    with open(realm_file) as f:
        realm_config = json.load(f)

    # Check for clients array
    clients = realm_config.get("clients", [])
    assert isinstance(clients, list), f"Realm 'clients' must be an array, got: {type(clients)}"

    # Find mcp-server client
    mcp_client = None
    for client in clients:
        if client.get("clientId") == "mcp-server":
            mcp_client = client
            break

    assert mcp_client is not None, (
        "Client 'mcp-server' not found in realm configuration.\n"
        "\n"
        "Expected client configuration:\n"
        "{\n"
        '  "clientId": "mcp-server",\n'
        '  "enabled": true,\n'
        '  "publicClient": true,\n'
        '  "directAccessGrantsEnabled": true\n'
        "}\n"
        "\n"
        f"Found clients: {[c.get('clientId') for c in clients]}"
    )

    # Validate client configuration
    assert mcp_client.get("enabled") is True, "Client 'mcp-server' must be enabled"

    assert mcp_client.get("publicClient") is True, "Client 'mcp-server' must be a public client (no secret required)"

    assert (
        mcp_client.get("directAccessGrantsEnabled") is True
    ), "Client 'mcp-server' must have directAccessGrantsEnabled for password grant flow"


def test_realm_json_has_test_users():
    """
    Verify that the realm configuration includes test user 'alice'.

    The E2E tests expect a user 'alice' with:
    - username: alice
    - enabled: true
    - credentials: password = alice123
    """
    realm_file = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "tests/e2e/keycloak-test-realm.json")

    with open(realm_file) as f:
        realm_config = json.load(f)

    # Check for users array
    users = realm_config.get("users", [])
    assert isinstance(users, list), f"Realm 'users' must be an array, got: {type(users)}"

    # Find alice user
    alice_user = None
    for user in users:
        if user.get("username") == "alice":
            alice_user = user
            break

    assert alice_user is not None, (
        "User 'alice' not found in realm configuration.\n"
        "\n"
        "Expected user configuration:\n"
        "{\n"
        '  "username": "alice",\n'
        '  "enabled": true,\n'
        '  "credentials": [{\n'
        '    "type": "password",\n'
        '    "value": "alice123",\n'
        '    "temporary": false\n'
        "  }]\n"
        "}\n"
        "\n"
        f"Found users: {[u.get('username') for u in users]}"
    )

    # Validate user configuration
    assert alice_user.get("enabled") is True, "User 'alice' must be enabled"

    # Check credentials
    credentials = alice_user.get("credentials", [])
    assert len(credentials) > 0, "User 'alice' must have at least one credential"

    password_cred = None
    for cred in credentials:
        if cred.get("type") == "password":
            password_cred = cred
            break

    assert password_cred is not None, "User 'alice' must have a password credential"

    assert password_cred.get("value") == "alice123", "User 'alice' password must be 'alice123'"


def test_docker_compose_imports_realm():
    """
    Verify that docker-compose.test.yml is configured to import the realm.

    The keycloak-test service should:
    - Mount the realm JSON file to /opt/keycloak/data/import/realm.json
    - Use command: start-dev --import-realm
    """
    docker_compose_file = Path("/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/" "docker-compose.test.yml")

    assert docker_compose_file.exists(), f"docker-compose.test.yml not found: {docker_compose_file}"

    with open(docker_compose_file) as f:
        try:
            compose_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"docker-compose.test.yml is not valid YAML: {e}")

    # Find keycloak-test service
    services = compose_config.get("services", {})
    keycloak_service = services.get("keycloak-test")

    assert keycloak_service is not None, (
        "Service 'keycloak-test' not found in docker-compose.test.yml\n" f"Available services: {list(services.keys())}"
    )

    # Check for volume mount
    volumes = keycloak_service.get("volumes", [])
    assert isinstance(volumes, list), f"Service 'keycloak-test' volumes must be an array, got: {type(volumes)}"

    # Look for realm import volume mount
    realm_volume_found = False
    for volume in volumes:
        if isinstance(volume, str):
            # Simple string format
            if "keycloak-test-realm.json" in volume and "/opt/keycloak/data/import" in volume:
                realm_volume_found = True
                break
        elif isinstance(volume, dict):
            # Dict format with source/target
            if volume.get("source") and "keycloak-test-realm.json" in str(volume.get("source")):
                realm_volume_found = True
                break

    assert realm_volume_found, (
        "Volume mount for realm import not found in keycloak-test service.\n"
        "\n"
        "Expected volume mount:\n"
        "  ./tests/e2e/keycloak-test-realm.json:/opt/keycloak/data/import/realm.json\n"
        "\n"
        f"Current volumes: {volumes}\n"
        "\n"
        "Fix: Add volume mount to docker-compose.test.yml:\n"
        "services:\n"
        "  keycloak-test:\n"
        "    volumes:\n"
        "      - ./tests/e2e/keycloak-test-realm.json:/opt/keycloak/data/import/realm.json:ro"
    )

    # Check for import-realm command
    command = keycloak_service.get("command")
    if command is None:
        pytest.fail(
            "Service 'keycloak-test' must specify command: start-dev --import-realm\n"
            "\n"
            "This tells Keycloak to import the realm configuration on startup"
        )

    # Command can be string or list
    command_str = " ".join(command) if isinstance(command, list) else command

    assert "--import-realm" in command_str, (
        "Service 'keycloak-test' command must include --import-realm flag.\n"
        "\n"
        "Expected command: start-dev --import-realm\n"
        f"Current command: {command}\n"
        "\n"
        "This flag tells Keycloak to import realm configuration from /opt/keycloak/data/import/"
    )
