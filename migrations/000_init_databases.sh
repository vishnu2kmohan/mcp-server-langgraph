#!/bin/bash
# PostgreSQL Database Initialization Script
# ==========================================
# Creates multiple databases for different services and runs migrations
#
# This script runs automatically when the postgres container starts
# via docker-entrypoint-initdb.d
#
# Environment Detection:
# - Test environment: Creates gdpr_test, openfga_test, keycloak_test (suffix: _test)
# - Development/Production: Creates gdpr, openfga, keycloak (no suffix)
#
# Detection Logic:
# - If POSTGRES_DB ends with "_test" → Test environment
# - If POSTGRES_DB is "openfga_test" → Test environment (backward compat)
# - Otherwise → Development/Production environment
#
# Database Architecture (see ADR-0056):
# - gdpr / gdpr_test: GDPR compliance data (user_profiles, conversations, preferences, consents, audit_logs)
# - openfga / openfga_test: OpenFGA authorization data (policies, tuples)
# - keycloak / keycloak_test: Keycloak SSO/authentication data (realms, users, clients)
#
# References:
# - ADR-0056: Database Architecture and Naming Convention
# - migrations/001_gdpr_schema.sql: GDPR schema definition

set -e
set -u

# ==============================================================================
# Environment Detection
# ==============================================================================

ENVIRONMENT="dev"  # Default to development
SUFFIX=""          # No suffix for dev/prod

# Detect test environment from POSTGRES_DB
if [[ "${POSTGRES_DB:-}" == *"_test" ]] || [[ "${POSTGRES_DB:-}" == "openfga_test" ]]; then
    ENVIRONMENT="test"
    SUFFIX="_test"
    echo "🧪 Test environment detected (POSTGRES_DB=${POSTGRES_DB})"
else
    echo "🚀 Development/Production environment detected (POSTGRES_DB=${POSTGRES_DB:-postgres})"
fi

# Database names based on environment
GDPR_DB="gdpr${SUFFIX}"
OPENFGA_DB="openfga${SUFFIX}"
KEYCLOAK_DB="keycloak${SUFFIX}"

echo "Database naming convention:"
echo "  - GDPR compliance: ${GDPR_DB}"
echo "  - OpenFGA authorization: ${OPENFGA_DB}"
echo "  - Keycloak authentication: ${KEYCLOAK_DB}"

# ==============================================================================
# Database Creation
# ==============================================================================

# Function to create database if it doesn't exist (idempotent)
create_database() {
    local database=$1
    echo "📦 Creating database: ${database}..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        SELECT 'CREATE DATABASE ${database}'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${database}')\gexec
EOSQL

    # Verify database was created
    if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_database WHERE datname='${database}'" | grep -q 1; then
        echo "✅ Database ${database} created successfully"
    else
        echo "❌ Failed to create database ${database}"
        exit 1
    fi
}

echo ""
echo "🏗️  Initializing databases for ${ENVIRONMENT} environment..."
echo ""

create_database "${GDPR_DB}"
create_database "${OPENFGA_DB}"
create_database "${KEYCLOAK_DB}"

echo ""
echo "✅ All databases created successfully in ${ENVIRONMENT} environment"
echo ""

# ==============================================================================
# Schema Migrations
# ==============================================================================

# Apply GDPR schema migrations to gdpr database
echo "📋 Running GDPR schema migration on ${GDPR_DB}..."

# Check if migration file exists
if [ ! -f "/docker-entrypoint-initdb.d/001_gdpr_schema.sql" ]; then
    echo "⚠️  Warning: GDPR schema migration file not found at /docker-entrypoint-initdb.d/001_gdpr_schema.sql"
    echo "    Skipping GDPR schema migration"
else
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="${GDPR_DB}" \
        -f /docker-entrypoint-initdb.d/001_gdpr_schema.sql

    echo "✅ GDPR schema migration complete on ${GDPR_DB} database"
fi

# ==============================================================================
# Validation
# ==============================================================================

echo ""
echo "🔍 Validating database structure..."

# Validate GDPR tables exist
GDPR_TABLES=("user_profiles" "user_preferences" "consent_records" "conversations" "audit_logs")
for table in "${GDPR_TABLES[@]}"; do
    if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="${GDPR_DB}" \
        -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='${table}'" | grep -q 1; then
        echo "  ✅ Table ${table} exists in ${GDPR_DB}"
    else
        echo "  ❌ Table ${table} NOT FOUND in ${GDPR_DB}"
        exit 1
    fi
done

echo ""
echo "🎉 Database initialization complete!"
echo ""
echo "Summary:"
echo "  Environment: ${ENVIRONMENT}"
echo "  Databases created: ${GDPR_DB}, ${OPENFGA_DB}, ${KEYCLOAK_DB}"
echo "  GDPR schema: ✅ Migrated (5 tables validated)"
echo ""
