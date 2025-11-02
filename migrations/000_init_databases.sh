#!/bin/bash
# PostgreSQL Database Initialization Script
# =========================================
# Creates multiple databases and runs migrations
#
# This script runs automatically when the postgres container starts
# via docker-entrypoint-initdb.d

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

# Create databases
echo "Initializing databases..."
create_database "openfga"
create_database "gdpr"

echo "Databases created successfully"

# Run GDPR schema migration
echo "Running GDPR schema migration..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname=gdpr -f /docker-entrypoint-initdb.d/001_gdpr_schema.sql

echo "GDPR schema migration complete"
