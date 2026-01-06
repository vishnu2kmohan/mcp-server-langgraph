"""
Test E2E Keycloak realm configuration and setup.

This test validates that the E2E test infrastructure has proper Keycloak
configuration including client setup and test user provisioning.

Following TDD RED-GREEN-REFACTOR cycle to fix E2E test failures caused by:
- Missing Keycloak client 'mcp-server'
- Missing test user 'alice' with password 'alice123'
- No automated realm import on Keycloak startup

Security Updates (ADR-0086):
- ROPC (directAccessGrantsEnabled) is DISABLED per RFC 9700
- Uses Authorization Code + PKCE for user login
- Uses Token Exchange (RFC 8693) for E2E test impersonation
- Uses Client Credentials for service-to-service auth

Reference: E2E Tests workflow failures with 401 authentication errors
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

# Mark as unit+meta test to ensure it runs in CI (validates test infrastructure)
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


def test_keycloak_realm_import_file_exists(repo_root: Path):
    """
    Verify that default-realm.json exists in tests/e2e/.

    This file should contain the realm configuration with pre-configured
    client and test users for E2E testing.
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

    assert realm_file.exists(), (
        f"Keycloak realm import file not found: {realm_file}\n"
        "\n"
        "Expected file: tests/e2e/default-realm.json\n"
        "This file should contain:\n"
        "  - Realm: default (NOT master - --import-realm only creates new realms)\n"
        "  - Client: mcp-server (confidential, serviceAccountsEnabled, ROPC disabled)\n"
        "  - User: alice with password alice123\n"
        "\n"
        "Fix: Create tests/e2e/default-realm.json with realm configuration"
    )

    # Verify it's valid JSON
    with open(realm_file) as f:
        try:
            realm_config: dict = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Realm file is not valid JSON: {e}")
            return  # Unreachable but satisfies static analysis

    assert isinstance(realm_config, dict), f"Realm file must contain a JSON object, got: {type(realm_config)}"


def test_realm_json_has_mcp_server_client(repo_root: Path):
    """
    Verify that the realm configuration includes the 'mcp-server' client.

    The E2E tests expect a client named 'mcp-server' with:
    - enabled: true
    - publicClient: false (confidential client with secret)
    - serviceAccountsEnabled: true (for client_credentials grant)
    - directAccessGrantsEnabled: false (ROPC disabled per RFC 9700/ADR-0086)
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

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
        '  "publicClient": false,\n'
        '  "serviceAccountsEnabled": true,\n'
        '  "directAccessGrantsEnabled": false\n'
        "}\n"
        "\n"
        f"Found clients: {[c.get('clientId') for c in clients]}"
    )

    # Validate client configuration
    assert mcp_client.get("enabled") is True, "Client 'mcp-server' must be enabled"

    # Client must be confidential with service account enabled for Token Exchange
    # ROPC is disabled per RFC 9700 / ADR-0086
    assert mcp_client.get("publicClient") is False, "Client 'mcp-server' must be a confidential client (publicClient: false)"
    assert mcp_client.get("serviceAccountsEnabled") is True, (
        "Client 'mcp-server' must have serviceAccountsEnabled for client_credentials grant"
    )

    # ROPC must be disabled per RFC 9700 / ADR-0086
    assert mcp_client.get("directAccessGrantsEnabled") is False, (
        "Client 'mcp-server' must have directAccessGrantsEnabled: false per RFC 9700. "
        "Use Token Exchange (RFC 8693) or Authorization Code + PKCE for authentication."
    )


def test_realm_json_has_test_users(repo_root: Path):
    """
    Verify that the realm configuration includes test user 'alice'.

    The E2E tests expect a user 'alice' with:
    - username: alice
    - enabled: true
    - credentials: password = alice123
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

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


def test_docker_compose_imports_realm(repo_root: Path):
    """
    Verify that docker-compose.test.yml is configured to import the realm.

    The keycloak-test service should:
    - Mount the realm JSON file to /opt/keycloak/data/import/realm.json
    - Use command: start-dev --import-realm
    """
    docker_compose_file = repo_root / "docker-compose.test.yml"

    assert docker_compose_file.exists(), f"docker-compose.test.yml not found: {docker_compose_file}"

    with open(docker_compose_file) as f:
        try:
            compose_config: dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"docker-compose.test.yml is not valid YAML: {e}")
            return  # Unreachable but satisfies static analysis

    # Find keycloak-test service
    services = compose_config.get("services", {})
    keycloak_service = services.get("keycloak-test")

    assert keycloak_service is not None, (
        f"Service 'keycloak-test' not found in docker-compose.test.yml\nAvailable services: {list(services.keys())}"
    )

    # Check for volume mount
    volumes = keycloak_service.get("volumes", [])
    assert isinstance(volumes, list), f"Service 'keycloak-test' volumes must be an array, got: {type(volumes)}"

    # Look for realm import volume mount
    realm_volume_found = False
    for volume in volumes:
        if isinstance(volume, str):
            # Simple string format
            if "default-realm.json" in volume and "/opt/keycloak/data/import" in volume:
                realm_volume_found = True
                break
        elif isinstance(volume, dict):
            # Dict format with source/target
            if volume.get("source") and "default-realm.json" in str(volume.get("source")):
                realm_volume_found = True
                break

    assert realm_volume_found, (
        "Volume mount for realm import not found in keycloak-test service.\n"
        "\n"
        "Expected volume mount:\n"
        "  ./tests/e2e/default-realm.json:/opt/keycloak/data/import/default-realm.json\n"
        "\n"
        f"Current volumes: {volumes}\n"
        "\n"
        "Fix: Add volume mount to docker-compose.test.yml:\n"
        "services:\n"
        "  keycloak-test:\n"
        "    volumes:\n"
        "      - ./tests/e2e/default-realm.json:/opt/keycloak/data/import/default-realm.json:ro"
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


def test_realm_json_has_webauthn_passwordless_policy(repo_root: Path):
    """
    Verify that the realm configuration includes WebAuthn Passwordless Policy.

    Keycloak 26.4+ supports Passkeys natively. The realm should configure:
    - webAuthnPolicyPasswordlessRpEntityName: Relying party name
    - webAuthnPolicyPasswordlessSignatureAlgorithms: Supported algorithms
    - webAuthnPolicyPasswordlessRequireResidentKey: Discoverable credentials

    Reference: https://www.keycloak.org/2025/09/passkeys-support-26-4
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

    with open(realm_file) as f:
        realm_config = json.load(f)

    # Check for WebAuthn Passwordless Policy settings
    # Keycloak uses flat keys in realm export, not nested objects
    rp_name = realm_config.get("webAuthnPolicyPasswordlessRpEntityName")

    assert rp_name is not None, (
        "WebAuthn Passwordless Policy not configured in realm.\n"
        "\n"
        "Expected settings for Passkey support:\n"
        '  "webAuthnPolicyPasswordlessRpEntityName": "MCP Server LangGraph",\n'
        '  "webAuthnPolicyPasswordlessSignatureAlgorithms": ["ES256"],\n'
        '  "webAuthnPolicyPasswordlessRequireResidentKey": "Yes",\n'
        "\n"
        "Reference: https://keycloak.ch/keycloak-tutorials/tutorial-passkey/"
    )

    # Verify signature algorithms include ES256 (most widely supported)
    sig_algs = realm_config.get("webAuthnPolicyPasswordlessSignatureAlgorithms", [])
    assert "ES256" in sig_algs, f"WebAuthn Passwordless Policy must include ES256 algorithm.\nCurrent algorithms: {sig_algs}"


def test_realm_json_has_webauthn_register_required_action(repo_root: Path):
    """
    Verify that WebAuthn Register Passwordless required action is enabled.

    This allows users to register passkeys/FIDO2 credentials as their
    primary authentication method.

    Reference: https://keycloak.ch/keycloak-tutorials/tutorial-passkey/
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

    with open(realm_file) as f:
        realm_config = json.load(f)

    # Check for required actions
    required_actions = realm_config.get("requiredActions", [])

    # Find webauthn-register-passwordless action
    webauthn_action = None
    for action in required_actions:
        if action.get("alias") == "webauthn-register-passwordless":
            webauthn_action = action
            break

    assert webauthn_action is not None, (
        "WebAuthn Register Passwordless required action not found.\n"
        "\n"
        "Expected required action:\n"
        "{\n"
        '  "alias": "webauthn-register-passwordless",\n'
        '  "name": "Webauthn Register Passwordless",\n'
        '  "providerId": "webauthn-register-passwordless",\n'
        '  "enabled": true,\n'
        '  "defaultAction": false,\n'
        '  "priority": 70\n'
        "}\n"
        "\n"
        f"Found required actions: {[a.get('alias') for a in required_actions]}"
    )

    # Verify action is enabled
    assert webauthn_action.get("enabled") is True, "WebAuthn Register Passwordless action must be enabled"


def test_realm_uses_argon2id_password_hashing(repo_root: Path):
    """
    Verify that the realm uses Argon2id for password hashing.

    Argon2id is the OWASP-recommended password hashing algorithm and has been
    the default in Keycloak since version 25. It provides:
    - Memory-hard hashing (resistant to GPU/ASIC attacks)
    - Better security with lower CPU overhead than PBKDF2

    Reference: https://www.keycloak.org/2024/06/keycloak-2500-released
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

    with open(realm_file) as f:
        realm_config = json.load(f)

    password_policy = realm_config.get("passwordPolicy", "")

    # Check for argon2 in password policy
    assert "argon2" in password_policy.lower(), (
        f"Password policy should use Argon2id hashing.\n"
        f"\n"
        f"Current policy: {password_policy}\n"
        f"\n"
        f'Expected: "passwordPolicy": "hashAlgorithm(argon2)"\n'
        f"\n"
        f"Argon2id is the OWASP-recommended algorithm since Keycloak 25.\n"
        f"Reference: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html"
    )


def test_realm_has_fapi2_client_policies(repo_root: Path):
    """
    Verify that FAPI 2.0 client policies are configured.

    FAPI 2.0 (Financial-grade API) provides enhanced security for APIs handling
    sensitive data. Keycloak 26.4+ includes built-in profiles:
    - fapi-2-security-profile: Base FAPI 2.0 requirements
    - fapi-2-dpop-security-profile: FAPI 2.0 with DPoP sender-constraint

    Reference: https://www.keycloak.org/2025/09/keycloak-2640-released
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

    with open(realm_file) as f:
        realm_config = json.load(f)

    # Check for client policies configuration
    client_policies = realm_config.get("clientPolicies", {})
    policies = client_policies.get("policies", [])

    # Find FAPI 2.0 policy
    fapi_policy = None
    for policy in policies:
        if "fapi" in policy.get("name", "").lower():
            fapi_policy = policy
            break

    assert fapi_policy is not None, (
        "FAPI 2.0 client policy not found in realm configuration.\n"
        "\n"
        "Expected client policy:\n"
        "{\n"
        '  "clientPolicies": {\n'
        '    "policies": [\n'
        "      {\n"
        '        "name": "fapi-2-policy",\n'
        '        "enabled": true,\n'
        '        "profiles": ["fapi-2-dpop-security-profile"]\n'
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n"
        "\n"
        f"Found policies: {[p.get('name') for p in policies]}"
    )

    # Verify policy is enabled
    assert fapi_policy.get("enabled") is True, f"FAPI 2.0 policy '{fapi_policy.get('name')}' must be enabled"

    # Verify it uses FAPI 2.0 profiles
    profiles = fapi_policy.get("profiles", [])
    fapi2_profile_found = any("fapi-2" in p for p in profiles)
    assert fapi2_profile_found, (
        f"FAPI 2.0 policy must use a FAPI 2.0 profile.\n"
        f"Current profiles: {profiles}\n"
        f"Expected one of: fapi-2-security-profile, fapi-2-dpop-security-profile"
    )


def test_realm_json_has_grafana_client(repo_root: Path):
    """
    Verify that the realm configuration includes the 'grafana' client.

    The Grafana dashboard requires an OAuth2 client for Keycloak SSO.
    Without this client, users get "Client not found" error when
    accessing http://localhost/dashboards.

    Reference: docker-compose.test.yml GF_AUTH_GENERIC_OAUTH_CLIENT_ID=grafana
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

    with open(realm_file) as f:
        realm_config = json.load(f)

    clients = realm_config.get("clients", [])

    # Find grafana client
    grafana_client = None
    for client in clients:
        if client.get("clientId") == "grafana":
            grafana_client = client
            break

    assert grafana_client is not None, (
        "Client 'grafana' not found in realm configuration.\n"
        "\n"
        "This causes 'Client not found' error when accessing Grafana dashboards.\n"
        "\n"
        "Expected client configuration:\n"
        "{\n"
        '  "clientId": "grafana",\n'
        '  "enabled": true,\n'
        '  "publicClient": false,\n'
        '  "secret": "test-grafana-secret",\n'
        '  "standardFlowEnabled": true,\n'
        '  "attributes": {"pkce.code.challenge.method": "S256"}\n'
        "}\n"
        "\n"
        f"Found clients: {[c.get('clientId') for c in clients]}"
    )

    # Validate grafana client configuration
    assert grafana_client.get("enabled") is True, "Client 'grafana' must be enabled"
    assert grafana_client.get("standardFlowEnabled") is True, (
        "Client 'grafana' must have standardFlowEnabled for OAuth2 authorization code flow"
    )
    assert grafana_client.get("secret") == "test-grafana-secret", (
        "Client 'grafana' secret must match docker-compose.test.yml GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET"
    )


def test_realm_json_has_openfga_server_client(repo_root: Path):
    """
    Verify that the realm configuration includes the 'openfga-server' client.

    OpenFGA uses OIDC authentication for API access (ADR-0070).
    Without this client, OpenFGA cannot validate JWT tokens.

    Reference: docker-compose.test.yml OPENFGA_OIDC_CLIENT_ID=openfga-server
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"

    with open(realm_file) as f:
        realm_config = json.load(f)

    clients = realm_config.get("clients", [])

    # Find openfga-server client
    openfga_client = None
    for client in clients:
        if client.get("clientId") == "openfga-server":
            openfga_client = client
            break

    assert openfga_client is not None, (
        "Client 'openfga-server' not found in realm configuration.\n"
        "\n"
        "This causes OpenFGA API authentication failures.\n"
        "\n"
        "Expected client configuration:\n"
        "{\n"
        '  "clientId": "openfga-server",\n'
        '  "enabled": true,\n'
        '  "publicClient": false,\n'
        '  "serviceAccountsEnabled": true\n'
        "}\n"
        "\n"
        f"Found clients: {[c.get('clientId') for c in clients]}"
    )

    # Validate openfga-server client configuration
    assert openfga_client.get("enabled") is True, "Client 'openfga-server' must be enabled"
    assert openfga_client.get("serviceAccountsEnabled") is True, (
        "Client 'openfga-server' must have serviceAccountsEnabled for client_credentials grant"
    )


def test_all_required_clients_exist_in_realm(repo_root: Path):
    """
    Comprehensive contract test: Validate ALL required OAuth2 clients from
    docker-compose.test.yml exist in the realm JSON.

    This test extracts CLIENT_ID values from docker-compose.test.yml and
    verifies each one exists in tests/e2e/default-realm.json.

    Why this test exists:
    - Grafana "Client not found" error went undetected because there was no
      contract test validating realm JSON matches docker-compose.test.yml
    - Integration tests only run with Docker infrastructure
    - This meta test runs in CI without Docker, catching issues early

    Reference: GitHub issue - Missing grafana OAuth client
    """
    realm_file = repo_root / "tests" / "e2e" / "default-realm.json"
    docker_compose_file = repo_root / "docker-compose.test.yml"

    # Load realm configuration
    with open(realm_file) as f:
        realm_config = json.load(f)

    realm_clients = {c.get("clientId") for c in realm_config.get("clients", [])}

    # Load docker-compose.test.yml
    with open(docker_compose_file) as f:
        compose_config = yaml.safe_load(f)

    # Extract all CLIENT_ID values from environment variables
    # Patterns: VAR_NAME_CLIENT_ID=xxx (variable name ends with _CLIENT_ID)
    # This avoids matching URLs with client_id= query parameters
    import re

    required_clients: set[str] = set()
    optional_patterns = ["GITHUB", "GOOGLE", "MICROSOFT", "GITLAB"]  # SSO providers are optional

    # Match environment variables like:
    # - OPENFGA_OIDC_CLIENT_ID=openfga-server
    # - GF_AUTH_GENERIC_OAUTH_CLIENT_ID=grafana
    # - PROVIDERS_OIDC_CLIENT_ID=mcp-server
    # But NOT: LOGOUT_REDIRECT=http://...?client_id=mcp-server (URLs)
    client_id_pattern = re.compile(r"^[A-Z_]+_CLIENT_ID=(.+)$", re.IGNORECASE)

    services = compose_config.get("services", {})
    for service_name, service_config in services.items():
        env_vars = service_config.get("environment", [])
        if isinstance(env_vars, list):
            for env in env_vars:
                if isinstance(env, str):
                    match = client_id_pattern.match(env)
                    if match:
                        # Skip optional SSO providers
                        if any(pattern in env.upper() for pattern in optional_patterns):
                            continue
                        client_id = match.group(1).strip()
                        # Skip empty values, placeholders, and shell variables
                        if client_id and not client_id.startswith("$") and not client_id.startswith("{"):
                            required_clients.add(client_id)

    # Validate each required client exists in realm
    missing_clients = required_clients - realm_clients

    assert len(missing_clients) == 0, (
        f"Missing Keycloak clients in tests/e2e/default-realm.json:\n"
        f"\n"
        f"Missing: {sorted(missing_clients)}\n"
        f"\n"
        f"Required by docker-compose.test.yml: {sorted(required_clients)}\n"
        f"Available in realm JSON: {sorted(realm_clients)}\n"
        f"\n"
        f"Fix: Add the missing client(s) to tests/e2e/default-realm.json\n"
        f"\n"
        f"This contract test ensures docker-compose.test.yml and realm JSON stay in sync."
    )
