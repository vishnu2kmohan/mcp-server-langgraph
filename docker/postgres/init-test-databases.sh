#!/bin/bash
# Initialize all required test databases for Agent Studio
#
# This script is run automatically by PostgreSQL during container initialization.
# It creates all databases required by different components:
#   - openfga_test: OpenFGA authorization (created by POSTGRES_DB env var)
#   - keycloak_test: Keycloak authentication
#   - agent_studio_test: Agent Studio main database (sessions, workflows, compliance, audit logs)
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

    -- agent_studio_test: Main Agent Studio database (sessions, workflows, compliance, audit logs)
    -- All compliance tables (GDPR, HIPAA, SOC2, FedRAMP) are consolidated here.
    -- Schema managed by Alembic (alembic-migrate-test service).
    CREATE DATABASE agent_studio_test;
    GRANT ALL PRIVILEGES ON DATABASE agent_studio_test TO postgres;

    -- Log success
    \echo 'Created test databases: keycloak_test, agent_studio_test'
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
echo "Enabling pgvector extension in agent_studio_test..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "agent_studio_test" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    \echo 'pgvector extension enabled in agent_studio_test'
EOSQL
echo "✓ pgvector extension enabled"

# NOTE: agent_studio_test database schema (including compliance tables) is managed by Alembic
# The alembic-migrate-test service runs AFTER postgres-test is healthy and BEFORE mcp-server-test starts
# SQL migrations in migrations/*.sql are superseded by Alembic migrations
# See: docker-compose.test.yml - alembic-migrate-test service
echo "ℹ agent_studio_test schema will be managed by Alembic (alembic-migrate-test service)"

echo "✓ All test databases initialized successfully"
