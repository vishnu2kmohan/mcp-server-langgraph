#!/bin/bash
# PostgreSQL Database Initialization Script
# =========================================
# Creates multiple test databases and runs migrations
#
# This script runs automatically when the postgres container starts
# via docker-entrypoint-initdb.d
#
# Database Architecture:
# - mcp_test: MCP application data (GDPR tables: user_profiles, conversations, etc.)
# - openfga_test: OpenFGA authorization data (policies, tuples)
# - keycloak_test: Keycloak SSO/authentication data (realms, users, clients)

set -e
set -u

# Function to create database if it doesn't exist
create_database() {
    local database=$1
    echo "Creating database: $database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
}

# Create databases following <service>_test naming convention
echo "Initializing test databases..."
create_database "mcp_test"
create_database "openfga_test"
create_database "keycloak_test"

echo "All test databases created successfully"

# Run GDPR schema migration on mcp_test database
echo "Running GDPR schema migration on mcp_test..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=mcp_test -f /docker-entrypoint-initdb.d/001_gdpr_schema.sql

echo "GDPR schema migration complete on mcp_test database"
