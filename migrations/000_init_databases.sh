#!/bin/bash
# PostgreSQL Database Initialization Script
# =========================================
# Creates multiple test databases and runs migrations
#
# This script runs automatically when the postgres container starts
# via docker-entrypoint-initdb.d
#
# Database Architecture:
# - gdpr_test: GDPR compliance data (user_profiles, conversations, preferences, consents, audit_logs)
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
create_database "gdpr_test"
create_database "openfga_test"
create_database "keycloak_test"

echo "All test databases created successfully"

# Run GDPR schema migration on gdpr_test database
echo "Running GDPR schema migration on gdpr_test..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=gdpr_test -f /docker-entrypoint-initdb.d/001_gdpr_schema.sql

echo "GDPR schema migration complete on gdpr_test database"
