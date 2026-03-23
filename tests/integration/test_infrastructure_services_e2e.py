"""
End-to-End Infrastructure Services Validation Tests.

Tests that verify concrete docker-compose.test.yml services are correctly
initialized and operational:
1. Qdrant collection initialization (qdrant-init-test creates agent_studio_context)
2. Postgres database initialization (init-test-databases.sh creates 4 databases)
3. Alembic migration completion (alembic-migrate-test runs schema migrations)
4. OpenFGA authorization model seeding (openfga-seed-test loads model + tuples)
5. Keycloak realm initialization (keycloak-init-test configures realm)
6. Redis database isolation (4 databases: sessions, checkpoints, cache, api-keys)
7. Traefik forward-auth middleware (OIDC redirect to Keycloak)

These tests require `make test-infra-full-up` to be running.

Gap Analysis (prior to this file):
-----------------------------------
- Qdrant init: No test verified that agent_studio_context collection exists with 768 dimensions
- Postgres init: No test verified all 3 databases (agent_studio_test, openfga_test, keycloak_test)
- Redis isolation: No test verified all 4 logical databases are configured
- Traefik forward-auth: No test verified OIDC redirect works end-to-end
"""

import gc
import os
import socket

import pytest
import requests

from tests.constants import (
    TEST_KEYCLOAK_PORT,
    TEST_OPENFGA_HTTP_PORT,
    TEST_POSTGRES_DB,
    TEST_POSTGRES_HOST,
    TEST_POSTGRES_PASSWORD,
    TEST_POSTGRES_PORT,
    TEST_POSTGRES_USER,
    TEST_QDRANT_PORT,
    TEST_REDIS_BUILDER_DB,
    TEST_REDIS_CHECKPOINT_DB,
    TEST_REDIS_PORT,
    TEST_REDIS_SESSION_DB,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.slow,
]


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use (service is accessible)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        try:
            sock.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


# ==============================================================================
# Qdrant Collection Initialization
# ==============================================================================


@pytest.mark.xdist_group(name="infra_services_e2e")
class TestQdrantInitialization:
    """
    Validate qdrant-init-test created the expected collections.

    docker-compose.test.yml:qdrant-init-test creates:
    - agent_studio_context: 768 dimensions, Cosine distance
      (matches Vertex AI text-embedding-005 model)
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_qdrant_collection_exists(self) -> None:
        """
        GIVEN qdrant-init-test has completed
        WHEN we query the Qdrant collections API
        THEN agent_studio_context collection should exist
        """
        if not is_port_in_use(TEST_QDRANT_PORT):
            pytest.skip(f"Qdrant not available on port {TEST_QDRANT_PORT}")

        url = f"http://localhost:{TEST_QDRANT_PORT}/collections/agent_studio_context"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, (
            f"Qdrant collection agent_studio_context not found: {response.status_code}. "
            f"Check: docker compose -f docker-compose.test.yml logs qdrant-init-test"
        )

        data = response.json()
        assert data.get("status") == "ok", f"Qdrant response status: {data.get('status')}"

    def test_qdrant_collection_has_correct_dimensions(self) -> None:
        """
        GIVEN agent_studio_context collection exists
        WHEN we query its configuration
        THEN vector size should be 768 (Vertex AI text-embedding-005)
        AND distance should be Cosine
        """
        if not is_port_in_use(TEST_QDRANT_PORT):
            pytest.skip(f"Qdrant not available on port {TEST_QDRANT_PORT}")

        url = f"http://localhost:{TEST_QDRANT_PORT}/collections/agent_studio_context"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            pytest.skip("agent_studio_context collection not found")

        data = response.json()
        result = data.get("result", {})
        config = result.get("config", {})
        params = config.get("params", {})
        vectors = params.get("vectors", {})

        # Vector size should match Vertex AI text-embedding-005
        assert vectors.get("size") == 768, f"Expected vector size 768 (text-embedding-005), got {vectors.get('size')}"

        # Distance should be Cosine (for semantic similarity)
        assert vectors.get("distance") == "Cosine", f"Expected distance 'Cosine', got {vectors.get('distance')}"

    def test_qdrant_collection_accepts_vectors(self) -> None:
        """
        GIVEN agent_studio_context collection exists with 768 dimensions
        WHEN we insert a test vector
        THEN it should be accepted without error
        """
        if not is_port_in_use(TEST_QDRANT_PORT):
            pytest.skip(f"Qdrant not available on port {TEST_QDRANT_PORT}")

        import random

        # Generate a random 768-dimensional vector
        test_vector = [random.uniform(-1, 1) for _ in range(768)]

        url = f"http://localhost:{TEST_QDRANT_PORT}/collections/agent_studio_context/points"
        payload = {
            "points": [
                {
                    "id": 999999,  # Use a high ID to avoid collisions
                    "vector": test_vector,
                    "payload": {"test_marker": "infra_validation_e2e"},
                }
            ]
        }

        response = requests.put(url, json=payload, timeout=10)
        assert response.status_code == 200, f"Failed to insert vector: {response.status_code} {response.text}"

        # Cleanup: delete the test point
        delete_url = f"http://localhost:{TEST_QDRANT_PORT}/collections/agent_studio_context/points/delete"
        requests.post(
            delete_url,
            json={"points": [999999]},
            timeout=10,
        )


# ==============================================================================
# PostgreSQL Database Initialization
# ==============================================================================


@pytest.mark.xdist_group(name="infra_services_e2e")
class TestPostgresInitialization:
    """
    Validate postgres-test initialization created all required databases.

    docker/postgres/init-test-databases.sh creates:
    - agent_studio_test (main application + compliance tables, managed by Alembic)
    - openfga_test (authorization)
    - keycloak_test (authentication)
    """

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def pg_connection_params(self) -> dict:
        """Return connection parameters for test Postgres."""
        return {
            "host": TEST_POSTGRES_HOST,
            "port": TEST_POSTGRES_PORT,
            "user": TEST_POSTGRES_USER,
            "password": TEST_POSTGRES_PASSWORD,
        }

    @pytest.mark.asyncio
    async def test_all_databases_exist(self, pg_connection_params) -> None:
        """
        GIVEN postgres-test and init-test-databases.sh have completed
        WHEN we query pg_database catalog
        THEN all 3 required databases should exist
        """
        if not is_port_in_use(TEST_POSTGRES_PORT):
            pytest.skip(f"Postgres not available on port {TEST_POSTGRES_PORT}")

        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not installed")

        conn = await asyncpg.connect(
            host=pg_connection_params["host"],
            port=pg_connection_params["port"],
            user=pg_connection_params["user"],
            password=pg_connection_params["password"],
            database="postgres",
        )
        try:
            rows = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false")
            db_names = {row["datname"] for row in rows}

            expected_dbs = {"agent_studio_test", "openfga_test", "keycloak_test"}
            missing = expected_dbs - db_names

            assert not missing, (
                f"Missing databases: {missing}. Found: {db_names & expected_dbs}. "
                f"Check: docker/postgres/init-test-databases.sh"
            )
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_pgvector_extension_installed(self, pg_connection_params) -> None:
        """
        GIVEN alembic-migrate-test has completed
        WHEN we check extensions in agent_studio_test database
        THEN pgvector extension should be installed (required for vector operations)
        """
        if not is_port_in_use(TEST_POSTGRES_PORT):
            pytest.skip(f"Postgres not available on port {TEST_POSTGRES_PORT}")

        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not installed")

        conn = await asyncpg.connect(
            host=pg_connection_params["host"],
            port=pg_connection_params["port"],
            user=pg_connection_params["user"],
            password=pg_connection_params["password"],
            database=TEST_POSTGRES_DB,
        )
        try:
            rows = await conn.fetch("SELECT extname FROM pg_extension")
            extensions = {row["extname"] for row in rows}

            assert "vector" in extensions, (
                f"pgvector extension not installed in {TEST_POSTGRES_DB}. "
                f"Found extensions: {extensions}. "
                f"Check: alembic migration for CREATE EXTENSION IF NOT EXISTS vector"
            )
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_alembic_migration_completed(self, pg_connection_params) -> None:
        """
        GIVEN alembic-migrate-test has completed
        WHEN we check for the alembic_version table
        THEN it should exist with a migration version (migrations ran)
        """
        if not is_port_in_use(TEST_POSTGRES_PORT):
            pytest.skip(f"Postgres not available on port {TEST_POSTGRES_PORT}")

        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not installed")

        conn = await asyncpg.connect(
            host=pg_connection_params["host"],
            port=pg_connection_params["port"],
            user=pg_connection_params["user"],
            password=pg_connection_params["password"],
            database=TEST_POSTGRES_DB,
        )
        try:
            # Check alembic_version table exists and has a version
            row = await conn.fetchrow("SELECT version_num FROM alembic_version LIMIT 1")
            assert row is not None, (
                "alembic_version table is empty — migrations did not run. "
                "Check: docker compose -f docker-compose.test.yml logs alembic-migrate-test"
            )
            assert row["version_num"], "alembic_version has no version_num"
        except asyncpg.exceptions.UndefinedTableError:
            pytest.fail(
                "alembic_version table does not exist — Alembic migrations never ran. "
                "Check: docker compose -f docker-compose.test.yml logs alembic-migrate-test"
            )
        finally:
            await conn.close()


# ==============================================================================
# Redis Database Isolation
# ==============================================================================


@pytest.mark.xdist_group(name="infra_services_e2e")
class TestRedisInitialization:
    """
    Validate Redis is running with proper database isolation.

    docker-compose.test.yml redis-test provides 4 logical databases:
    - DB 0: User sessions (AuthMiddleware)
    - DB 1: LangGraph conversation checkpoints
    - DB 2: L2 distributed cache (CacheService)
    - DB 3: API key lookup cache
    """

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.asyncio
    async def test_redis_accepts_connections(self) -> None:
        """
        GIVEN redis-test is running
        WHEN we connect to each logical database
        THEN all connections should succeed
        """
        if not is_port_in_use(TEST_REDIS_PORT):
            pytest.skip(f"Redis not available on port {TEST_REDIS_PORT}")

        try:
            import redis.asyncio as aioredis
        except ImportError:
            pytest.skip("redis[asyncio] not installed")

        databases = [
            (TEST_REDIS_SESSION_DB, "sessions"),
            (TEST_REDIS_CHECKPOINT_DB, "checkpoints"),
            (2, "cache"),
            (TEST_REDIS_BUILDER_DB, "api-keys"),
        ]

        for db_num, purpose in databases:
            client = aioredis.Redis(
                host="localhost",
                port=TEST_REDIS_PORT,
                db=db_num,
                socket_timeout=5,
            )
            try:
                pong = await client.ping()
                assert pong is True, f"Redis DB {db_num} ({purpose}) did not respond to PING"
            finally:
                await client.aclose()

    @pytest.mark.asyncio
    async def test_redis_databases_are_isolated(self) -> None:
        """
        GIVEN redis-test is running with multiple logical databases
        WHEN we write to DB 0 (sessions) and read from DB 1 (checkpoints)
        THEN the key should NOT be visible across databases
        """
        if not is_port_in_use(TEST_REDIS_PORT):
            pytest.skip(f"Redis not available on port {TEST_REDIS_PORT}")

        try:
            import redis.asyncio as aioredis
        except ImportError:
            pytest.skip("redis[asyncio] not installed")

        test_key = "infra_test_isolation_marker"

        # Write to DB 0
        client_db0 = aioredis.Redis(host="localhost", port=TEST_REDIS_PORT, db=0, socket_timeout=5)
        client_db1 = aioredis.Redis(host="localhost", port=TEST_REDIS_PORT, db=1, socket_timeout=5)
        try:
            await client_db0.set(test_key, "from_db0", ex=10)

            # Read from DB 1 - should NOT find the key
            value_db1 = await client_db1.get(test_key)
            assert value_db1 is None, f"Redis DB isolation broken: key '{test_key}' set in DB 0 but found in DB 1"
        finally:
            await client_db0.delete(test_key)
            await client_db0.aclose()
            await client_db1.aclose()

    @pytest.mark.asyncio
    async def test_redis_maxmemory_policy_configured(self) -> None:
        """
        GIVEN redis-test is running with --maxmemory-policy allkeys-lru
        WHEN we query the configuration
        THEN maxmemory-policy should be allkeys-lru (from docker-compose.test.yml)
        """
        if not is_port_in_use(TEST_REDIS_PORT):
            pytest.skip(f"Redis not available on port {TEST_REDIS_PORT}")

        try:
            import redis.asyncio as aioredis
        except ImportError:
            pytest.skip("redis[asyncio] not installed")

        client = aioredis.Redis(host="localhost", port=TEST_REDIS_PORT, db=0, socket_timeout=5)
        try:
            config = await client.config_get("maxmemory-policy")
            policy = config.get("maxmemory-policy", "")
            assert policy == "allkeys-lru", (
                f"Redis maxmemory-policy is '{policy}', expected 'allkeys-lru'. "
                f"Check docker-compose.test.yml redis-test command."
            )
        finally:
            await client.aclose()


# ==============================================================================
# OpenFGA Authorization Model
# ==============================================================================


@pytest.mark.xdist_group(name="infra_services_e2e")
class TestOpenFGAInitialization:
    """
    Validate openfga-seed-test loaded the authorization model and tuples.

    docker-compose.test.yml services:
    - openfga-migrate-test: Creates OpenFGA PostgreSQL schema
    - openfga-seed-test: Loads authorization model + default tuples
    """

    def teardown_method(self) -> None:
        gc.collect()

    def _get_openfga_token(self) -> str | None:
        """Get OAuth2 token for OpenFGA API access (OIDC-protected)."""
        # OpenFGA uses OIDC authentication via Keycloak
        if not is_port_in_use(TEST_KEYCLOAK_PORT):
            return None

        token_url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/default/protocol/openid-connect/token"
        try:
            resp = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": "openfga",
                    "client_secret": "openfga-client-secret",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("access_token")
        except requests.exceptions.RequestException:
            pass
        return None

    def test_openfga_has_stores(self) -> None:
        """
        GIVEN openfga-seed-test has completed
        WHEN we query the OpenFGA stores API
        THEN at least one store should exist
        """
        if not is_port_in_use(TEST_OPENFGA_HTTP_PORT):
            pytest.skip(f"OpenFGA not available on port {TEST_OPENFGA_HTTP_PORT}")

        headers = {}
        token = self._get_openfga_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = f"http://localhost:{TEST_OPENFGA_HTTP_PORT}/stores"
        response = requests.get(url, headers=headers, timeout=10)

        # OpenFGA may require OIDC auth — 401 means OIDC is configured but token invalid
        if response.status_code == 401:
            pytest.skip(
                "OpenFGA requires OIDC authentication. "
                "Could not obtain token from Keycloak (check openfga client credentials)."
            )

        assert response.status_code == 200, f"OpenFGA stores API returned {response.status_code}"

        data = response.json()
        stores = data.get("stores", [])
        assert len(stores) > 0, (
            "No OpenFGA stores found. openfga-seed-test may not have run. "
            "Check: docker compose -f docker-compose.test.yml logs openfga-seed-test"
        )

    def test_openfga_has_authorization_model(self) -> None:
        """
        GIVEN openfga-seed-test has loaded an authorization model
        WHEN we query the authorization models API
        THEN at least one model should exist in the first store
        """
        if not is_port_in_use(TEST_OPENFGA_HTTP_PORT):
            pytest.skip(f"OpenFGA not available on port {TEST_OPENFGA_HTTP_PORT}")

        # First, get the store ID
        headers = {}
        token = self._get_openfga_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        stores_url = f"http://localhost:{TEST_OPENFGA_HTTP_PORT}/stores"
        stores_resp = requests.get(stores_url, headers=headers, timeout=10)

        if stores_resp.status_code in (401, 403):
            pytest.skip("OpenFGA requires OIDC authentication")
        if stores_resp.status_code != 200:
            pytest.skip("Cannot access OpenFGA stores API")

        stores = stores_resp.json().get("stores", [])
        if not stores:
            pytest.skip("No OpenFGA stores found")

        store_id = stores[0].get("id")

        # Query authorization models for this store
        models_url = f"http://localhost:{TEST_OPENFGA_HTTP_PORT}/stores/{store_id}/authorization-models"
        models_resp = requests.get(models_url, headers=headers, timeout=10)

        assert models_resp.status_code == 200, f"OpenFGA models API returned {models_resp.status_code}"

        data = models_resp.json()
        models = data.get("authorization_models", [])
        assert len(models) > 0, (
            "No authorization models found in OpenFGA store. openfga-seed-test may not have loaded the model."
        )


# ==============================================================================
# Keycloak Realm Initialization
# ==============================================================================


@pytest.mark.xdist_group(name="infra_services_e2e")
class TestKeycloakInitialization:
    """
    Validate keycloak-test and keycloak-init-test configured the realm correctly.

    docker-compose.test.yml services:
    - keycloak-test: Starts Keycloak with imported default realm
    - keycloak-init-test: Clears admin required actions, configures IdPs
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_keycloak_default_realm_exists(self) -> None:
        """
        GIVEN keycloak-test has imported the default realm
        WHEN we query the OIDC discovery endpoint
        THEN the realm should be accessible
        """
        if not is_port_in_use(TEST_KEYCLOAK_PORT):
            pytest.skip(f"Keycloak not available on port {TEST_KEYCLOAK_PORT}")

        url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/default/.well-known/openid-configuration"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, (
            f"Keycloak OIDC discovery failed: {response.status_code}. "
            f"Check: docker compose -f docker-compose.test.yml logs keycloak-test"
        )

        data = response.json()
        assert "authorization_endpoint" in data, "OIDC discovery missing authorization_endpoint"
        assert "token_endpoint" in data, "OIDC discovery missing token_endpoint"
        assert "jwks_uri" in data, "OIDC discovery missing jwks_uri"

    def test_keycloak_agent_studio_client_exists(self) -> None:
        """
        GIVEN keycloak-test has imported the realm with agent-studio client
        WHEN we query the admin API for clients
        THEN agent-studio client should exist
        """
        if not is_port_in_use(TEST_KEYCLOAK_PORT):
            pytest.skip(f"Keycloak not available on port {TEST_KEYCLOAK_PORT}")

        # First get an admin token
        token_url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/master/protocol/openid-connect/token"
        token_resp = requests.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "admin",
                "password": os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123"),
            },
            timeout=10,
        )

        if token_resp.status_code != 200:
            pytest.skip("Cannot obtain Keycloak admin token")

        admin_token = token_resp.json().get("access_token")

        # Query clients in the default realm
        clients_url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/admin/realms/default/clients"
        clients_resp = requests.get(
            clients_url,
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"clientId": "agent-studio"},
            timeout=10,
        )

        assert clients_resp.status_code == 200, f"Keycloak admin API returned {clients_resp.status_code}"

        clients = clients_resp.json()
        assert len(clients) > 0, (
            "agent-studio client not found in Keycloak default realm. Check: tests/e2e/default-realm.json client definitions"
        )

    def test_keycloak_test_users_exist(self) -> None:
        """
        GIVEN keycloak-test has imported the realm with test users
        WHEN we query the admin API for users
        THEN at least alice and bob should exist (from default-realm.json)
        """
        if not is_port_in_use(TEST_KEYCLOAK_PORT):
            pytest.skip(f"Keycloak not available on port {TEST_KEYCLOAK_PORT}")

        # Get admin token
        token_url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/realms/master/protocol/openid-connect/token"
        token_resp = requests.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "admin",
                "password": os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin123"),
            },
            timeout=10,
        )

        if token_resp.status_code != 200:
            pytest.skip("Cannot obtain Keycloak admin token")

        admin_token = token_resp.json().get("access_token")

        # Query users
        users_url = f"http://localhost:{TEST_KEYCLOAK_PORT}/authn/admin/realms/default/users"
        users_resp = requests.get(
            users_url,
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )

        assert users_resp.status_code == 200
        users = users_resp.json()
        usernames = {u.get("username") for u in users}

        expected_users = {"alice", "bob"}
        missing = expected_users - usernames

        assert not missing, (
            f"Missing test users: {missing}. Found: {usernames & expected_users}. "
            f"Check: tests/e2e/default-realm.json user definitions"
        )


# ==============================================================================
# Traefik Forward Auth (OIDC Redirect)
# ==============================================================================


@pytest.mark.xdist_group(name="infra_services_e2e")
class TestTraefikForwardAuth:
    """
    Validate Traefik forward-auth middleware redirects to Keycloak OIDC.

    docker-compose.test.yml services:
    - traefik-gateway: API gateway with forward-auth middleware
    - traefik-forward-auth: OAuth2 proxy (thomseddon/traefik-forward-auth:2)
    - keycloak-test: Identity provider (OIDC issuer)
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_protected_route_redirects_to_auth(self) -> None:
        """
        GIVEN Traefik is running with forward-auth middleware
        WHEN we access a protected route (e.g., /studio/) without auth
        THEN we should be redirected to the OIDC login page

        This validates the full authentication chain:
        Browser → Traefik → forward-auth middleware → Keycloak OIDC
        """
        if not is_port_in_use(80):
            pytest.skip("Traefik gateway not available on port 80")

        # Access a protected route without auth - should redirect
        response = requests.get(
            "http://localhost/studio/",
            allow_redirects=False,
            timeout=10,
        )

        # Should get a redirect (302 or 307) to the OIDC authorization endpoint
        assert response.status_code in (302, 307, 401), (
            f"Expected redirect or 401 for unauthenticated access, got {response.status_code}. "
            f"forward-auth middleware may not be configured."
        )

        if response.status_code in (302, 307):
            location = response.headers.get("Location", "")
            # Should redirect to an auth-related endpoint
            # forward-auth may redirect to /login, /_oauth, or directly to Keycloak
            auth_indicators = ["authn", "keycloak", "oauth", "login", "authorize"]
            has_auth_redirect = any(indicator in location.lower() for indicator in auth_indicators)
            assert has_auth_redirect, f"Redirect does not point to an authentication endpoint: {location}"

    def test_traefik_dashboard_accessible(self) -> None:
        """
        GIVEN Traefik is running with dashboard enabled on port 8080
        WHEN we access the dashboard API
        THEN it should return router/service information
        """
        if not is_port_in_use(8080):
            pytest.skip("Traefik dashboard not available on port 8080")

        # Traefik dashboard API
        response = requests.get("http://localhost:8080/api/http/routers", timeout=10)

        assert response.status_code == 200, f"Traefik dashboard API returned {response.status_code}"

        routers = response.json()
        assert isinstance(routers, list), "Expected list of routers"
        assert len(routers) > 0, "No routers configured in Traefik"

    def test_traefik_has_forward_auth_middleware(self) -> None:
        """
        GIVEN Traefik is running with forward-auth middleware
        WHEN we query the middlewares API
        THEN forward-auth middleware should be registered
        """
        if not is_port_in_use(8080):
            pytest.skip("Traefik dashboard not available on port 8080")

        response = requests.get("http://localhost:8080/api/http/middlewares", timeout=10)

        assert response.status_code == 200

        middlewares = response.json()
        middleware_names = [m.get("name", "") for m in middlewares]

        # forward-auth should be registered (may have @docker suffix)
        has_forward_auth = any("forward-auth" in name for name in middleware_names)
        assert has_forward_auth, f"forward-auth middleware not found in Traefik. Found middlewares: {middleware_names}"
