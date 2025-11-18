"""
Integration tests for database validation against real PostgreSQL.

Tests the database validation module against an actual PostgreSQL instance
to ensure it correctly validates the database architecture from ADR-0056.

These tests require:
- Running PostgreSQL instance (via docker-compose.test.yml)
- Database initialization complete (migrations/000_init_databases.sh)
- GDPR schema applied (migrations/001_gdpr_schema.sql)

References:
    - ADR-0056: Database Architecture and Naming Convention
    - src/mcp_server_langgraph/health/database_checks.py
    - migrations/000_init_databases.sh
"""

import os

import pytest

from mcp_server_langgraph.health.database_checks import DatabaseValidator, Environment, validate_database_architecture


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.xdist_group(name="testdatabasevalidationintegration")
class TestDatabaseValidationIntegration:
    """Integration tests for database validation with real PostgreSQL"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, monkeypatch):
        """Ensure we're in test environment for these integration tests"""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("POSTGRES_DB", "gdpr_test")

    async def test_validate_test_environment_databases(self):
        """
        Should successfully validate all test databases.

        Prerequisites:
        - docker-compose.test.yml running
        - migrations/000_init_databases.sh executed
        - Databases: gdpr_test, openfga_test, keycloak_test created
        """
        # Get connection parameters from environment
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")

        # Run validation
        result = await validate_database_architecture(
            host=host,
            port=port,
            user=user,
            password=password,
        )

        # Should detect test environment
        assert result.environment == Environment.TEST

        # Should have all 3 databases
        assert len(result.databases) == 3
        assert "gdpr_test" in result.databases
        assert "openfga_test" in result.databases
        assert "keycloak_test" in result.databases

        # GDPR database should be fully valid (migration-managed)
        gdpr_result = result.databases["gdpr_test"]
        assert gdpr_result.exists, "GDPR database should exist"
        assert gdpr_result.tables_valid, f"GDPR tables should be valid. Errors: {gdpr_result.errors}"
        assert len(gdpr_result.errors) == 0, f"GDPR database should have no errors: {gdpr_result.errors}"

        # OpenFGA database should exist (tables managed by OpenFGA service)
        openfga_result = result.databases["openfga_test"]
        assert openfga_result.exists, "OpenFGA database should exist"
        # Tables may not exist if OpenFGA service hasn't migrated yet (warnings OK)

        # Keycloak database should exist (tables managed by Keycloak service)
        keycloak_result = result.databases["keycloak_test"]
        assert keycloak_result.exists, "Keycloak database should exist"
        # Tables may not exist if Keycloak service hasn't migrated yet (warnings OK)

        # Print validation summary for debugging
        print("\n=== Database Validation Summary ===")
        print(f"Environment: {result.environment.value}")
        print(f"Overall Valid: {result.is_valid}")
        print("\nDatabases:")
        for db_name, db_result in result.databases.items():
            print(f"  - {db_name}:")
            print(f"      Exists: {db_result.exists}")
            print(f"      Tables Valid: {db_result.tables_valid}")
            if db_result.errors:
                print(f"      Errors: {db_result.errors}")
            if db_result.warnings:
                print(f"      Warnings: {db_result.warnings}")

    async def test_gdpr_database_table_validation(self):
        """
        Should validate all required GDPR tables exist.

        This test specifically checks that the GDPR schema migration
        (migrations/001_gdpr_schema.sql) has been applied correctly.
        """
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")

        validator = DatabaseValidator(
            host=host,
            port=port,
            user=user,
            password=password,
            environment=Environment.TEST,
        )

        # Get expected databases
        databases = validator.get_expected_databases()
        gdpr_db_info = databases["gdpr_test"]

        # Validate GDPR database specifically
        result = await validator.validate_database(gdpr_db_info)

        # Should be fully valid
        assert result.is_valid, f"GDPR database validation failed: {result.errors}"
        assert result.exists, "GDPR database should exist"
        assert result.tables_valid, f"GDPR tables should be valid: {result.errors}"

        # Should have all required tables
        required_tables = ["user_profiles", "user_preferences", "consent_records", "conversations", "audit_logs"]
        for table in required_tables:
            assert table in gdpr_db_info.required_tables, f"Missing required table: {table}"

        # Should have no errors
        assert len(result.errors) == 0, f"GDPR database should have no errors: {result.errors}"

    async def test_validation_result_serialization(self):
        """Should serialize validation result to JSON-compatible dict"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")

        result = await validate_database_architecture(
            host=host,
            port=port,
            user=user,
            password=password,
        )

        # Convert to dict (for JSON serialization)
        result_dict = result.to_dict()

        # Should be JSON-serializable
        assert isinstance(result_dict, dict)
        assert "environment" in result_dict
        assert "is_valid" in result_dict
        assert "databases" in result_dict
        assert "errors" in result_dict
        assert "warnings" in result_dict

        # Should contain all databases
        assert len(result_dict["databases"]) == 3
        for db_name in ["gdpr_test", "openfga_test", "keycloak_test"]:
            assert db_name in result_dict["databases"]
            db_info = result_dict["databases"][db_name]
            assert "exists" in db_info
            assert "tables_valid" in db_info
            assert "errors" in db_info
            assert "warnings" in db_info

    async def test_environment_auto_detection_in_integration(self):
        """Should auto-detect test environment from POSTGRES_DB"""
        # Environment variables already set by fixture (POSTGRES_DB=gdpr_test)
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")

        validator = DatabaseValidator(
            host=host,
            port=port,
            user=user,
            password=password,
        )

        # Should auto-detect test environment
        assert validator.environment == Environment.TEST

        # Should expect _test suffix databases
        databases = validator.get_expected_databases()
        assert "gdpr_test" in databases
        assert "openfga_test" in databases
        assert "keycloak_test" in databases


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseValidationFailureCases:
    """Integration tests for validation failure scenarios"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, monkeypatch):
        """Ensure we're in test environment"""
        monkeypatch.setenv("TESTING", "true")
        monkeypatch.setenv("POSTGRES_DB", "gdpr_test")

    async def test_validation_with_wrong_port(self):
        """Should handle connection failure gracefully"""
        # Try to connect to non-existent port
        result = await validate_database_architecture(
            host="localhost",
            port=9999,  # Wrong port
            user="postgres",
            password="postgres",
        )

        # Should detect errors
        assert not result.is_valid
        assert len(result.errors) > 0

        # All databases should fail to validate
        for db_name, db_result in result.databases.items():
            assert not db_result.exists
            assert not db_result.is_valid
            assert len(db_result.errors) > 0

    async def test_validation_with_wrong_credentials(self):
        """Should handle authentication failure gracefully"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))

        # Try with wrong password
        result = await validate_database_architecture(
            host=host,
            port=port,
            user="postgres",
            password="wrong_password",
        )

        # Should detect errors
        assert not result.is_valid
        assert len(result.errors) > 0

        # All databases should fail to validate
        for db_name, db_result in result.databases.items():
            assert not db_result.exists
            assert not db_result.is_valid
            assert len(db_result.errors) > 0
            assert any("connect" in error.lower() or "auth" in error.lower() for error in db_result.errors)
