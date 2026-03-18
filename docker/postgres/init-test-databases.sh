#!/bin/bash
# Initialize all required test databases for Agent Studio
#
# This script is run automatically by PostgreSQL during container initialization.
# It creates all databases required by different components:
#   - openfga_test: OpenFGA authorization (created by POSTGRES_DB env var)
#   - keycloak_test: Keycloak authentication
#   - compliance_test: Multi-framework compliance (GDPR, HIPAA, SOC2, FedRAMP)
#   - agent_studio_test: Agent Studio main database (sessions, workflows, audit logs)
#
# IMPORTANT: This script runs as postgres superuser during initdb phase.
# See: https://hub.docker.com/_/postgres (Initialization scripts section)
#
# References:
#   - tests/constants.py: TEST_POSTGRES_DB = "agent_studio_test"
#   - docker-compose.test.yml: postgres-test service
#   - ADR-0067: Grafana LGTM Stack migration

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create additional test databases
    -- Note: openfga_test is already created by POSTGRES_DB environment variable

    CREATE DATABASE keycloak_test;
    GRANT ALL PRIVILEGES ON DATABASE keycloak_test TO postgres;

    -- compliance_test: Multi-framework compliance storage (GDPR, HIPAA, SOC2, FedRAMP)
    -- Renamed from gdpr_test in v2.8 to reflect broader compliance scope
    CREATE DATABASE compliance_test;
    GRANT ALL PRIVILEGES ON DATABASE compliance_test TO postgres;

    -- agent_studio_test: Main Agent Studio database (sessions, workflows, audit logs)
    -- Renamed from mcp_test in project rename to agent-studio
    CREATE DATABASE agent_studio_test;
    GRANT ALL PRIVILEGES ON DATABASE agent_studio_test TO postgres;

    -- Log success
    \echo 'Created test databases: keycloak_test, compliance_test, agent_studio_test'
EOSQL

echo "✓ Test databases created successfully"

# Enable TimescaleDB extension in databases that use time-series data
# TimescaleDB provides hypertables for efficient storage of metrics and cost tracking data
# Reference: ADR for Cost/Metrics feature
echo "Enabling TimescaleDB extension in agent_studio_test database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "agent_studio_test" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS timescaledb;
    \echo 'TimescaleDB extension enabled in agent_studio_test'
EOSQL
echo "✓ TimescaleDB extension enabled"

# Enable pgvector extension for vector similarity search
# Required for execution plan and template embedding search
# TimescaleDB 2.17.2-pg16 includes pgvector as a bundled extension
# Reference: Phase 1 - pgvector Test Image
echo "Enabling pgvector extension in all test databases..."
for db in agent_studio_test compliance_test; do
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS vector;
        \echo 'pgvector extension enabled in $db'
EOSQL
done
echo "✓ pgvector extension enabled in all databases"

# Apply compliance schema to compliance_test database
# The compliance schema is required for E2E tests (test_infrastructure fixture checks for these tables)
# Supports GDPR, HIPAA, SOC2, and FedRAMP compliance data storage
# See: tests/fixtures/docker_fixtures.py - _verify_schema_ready()
if [ -f "/docker-entrypoint-initdb.d/01-migrations/001_gdpr_schema.sql" ]; then
    echo "Applying compliance schema to compliance_test database..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "compliance_test" \
        -f /docker-entrypoint-initdb.d/01-migrations/001_gdpr_schema.sql
    echo "✓ Compliance schema applied to compliance_test"
else
    echo "⚠ Compliance schema migration not found at /docker-entrypoint-initdb.d/01-migrations/001_gdpr_schema.sql"
fi

# NOTE: agent_studio_test database schema is now managed by Alembic (alembic-migrate-test service)
# The alembic-migrate-test service runs AFTER postgres-test is healthy and BEFORE mcp-server-test starts
# This standardizes on Alembic for all production-like database migrations
# See: docker-compose.test.yml - alembic-migrate-test service
# See: alembic/versions/8348487e5796_initial_gdpr_schema_user_profiles_.py
echo "ℹ agent_studio_test database schema will be managed by Alembic (alembic-migrate-test service)"

echo "✓ All test databases initialized successfully"
