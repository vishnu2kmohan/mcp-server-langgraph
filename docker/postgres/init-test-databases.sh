#!/bin/bash
# Initialize all required test databases for MCP Server LangGraph
#
# This script is run automatically by PostgreSQL during container initialization.
# It creates all databases required by different components:
#   - openfga_test: OpenFGA authorization (created by POSTGRES_DB env var)
#   - keycloak_test: Keycloak authentication
#   - gdpr_test: GDPR compliance data
#   - mcp_test: MCP server builder workflows
#
# IMPORTANT: This script runs as postgres superuser during initdb phase.
# See: https://hub.docker.com/_/postgres (Initialization scripts section)
#
# References:
#   - tests/constants.py: TEST_POSTGRES_DB = "mcp_test"
#   - docker-compose.test.yml: postgres-test service
#   - ADR-0067: Grafana LGTM Stack migration

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create additional test databases
    -- Note: openfga_test is already created by POSTGRES_DB environment variable

    CREATE DATABASE keycloak_test;
    GRANT ALL PRIVILEGES ON DATABASE keycloak_test TO postgres;

    CREATE DATABASE gdpr_test;
    GRANT ALL PRIVILEGES ON DATABASE gdpr_test TO postgres;

    CREATE DATABASE mcp_test;
    GRANT ALL PRIVILEGES ON DATABASE mcp_test TO postgres;

    -- Log success
    \echo 'Created test databases: keycloak_test, gdpr_test, mcp_test'
EOSQL

echo "✓ Test databases created successfully"

# Apply GDPR schema to gdpr_test database (legacy - kept for backwards compatibility)
# The GDPR schema is required for E2E tests (test_infrastructure fixture checks for these tables)
# See: tests/fixtures/docker_fixtures.py - _verify_schema_ready()
if [ -f "/docker-entrypoint-initdb.d/01-migrations/001_gdpr_schema.sql" ]; then
    echo "Applying GDPR schema to gdpr_test database..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "gdpr_test" \
        -f /docker-entrypoint-initdb.d/01-migrations/001_gdpr_schema.sql
    echo "✓ GDPR schema applied to gdpr_test"
else
    echo "⚠ GDPR schema migration not found at /docker-entrypoint-initdb.d/01-migrations/001_gdpr_schema.sql"
fi

# NOTE: mcp_test database schema is now managed by Alembic (alembic-migrate-test service)
# The alembic-migrate-test service runs AFTER postgres-test is healthy and BEFORE mcp-server-test starts
# This standardizes on Alembic for all production-like database migrations
# See: docker-compose.test.yml - alembic-migrate-test service
# See: alembic/versions/8348487e5796_initial_gdpr_schema_user_profiles_.py
echo "ℹ mcp_test database schema will be managed by Alembic (alembic-migrate-test service)"

echo "✓ All test databases initialized successfully"
