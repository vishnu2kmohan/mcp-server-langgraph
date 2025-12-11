"""
Unit tests for database validation module.

Tests the database architecture validation logic from ADR-0056.

Test Coverage:
- Environment detection (dev, test, staging, production)
- Database existence validation
- Table existence validation
- Error handling and connection failures
- Validation result aggregation
- Integration with PostgreSQL

References:
    - ADR-0056: Database Architecture and Naming Convention
    - src/mcp_server_langgraph/health/database_checks.py
"""

import gc
import os
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest

from mcp_server_langgraph.health.database_checks import (
    DatabaseInfo,
    DatabaseValidationResult,
    DatabaseValidator,
    Environment,
    ValidationResult,
    validate_database_architecture,
)

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="testenvironmentdetection")
class TestEnvironmentDetection:
    """Tests for environment detection logic"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_environment_from_ENVIRONMENT_variable(self):
        """Should detect environment from ENVIRONMENT variable"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            validator = DatabaseValidator(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
            )
            assert validator.environment == Environment.PRODUCTION

    def test_detect_environment_from_TESTING_variable(self):
        """Should detect test environment from TESTING=true"""
        with patch.dict(os.environ, {"TESTING": "true"}, clear=True):
            validator = DatabaseValidator(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
            )
            assert validator.environment == Environment.TEST

    def test_detect_environment_from_PYTEST_CURRENT_TEST(self):
        """Should detect test environment from PYTEST_CURRENT_TEST"""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"}, clear=True):
            validator = DatabaseValidator(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
            )
            assert validator.environment == Environment.TEST

    def test_detect_environment_from_POSTGRES_DB_suffix(self):
        """Should detect test environment from POSTGRES_DB ending with _test"""
        with patch.dict(os.environ, {"POSTGRES_DB": "gdpr_test"}, clear=True):
            validator = DatabaseValidator(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
            )
            assert validator.environment == Environment.TEST

    def test_detect_environment_from_POSTGRES_DB_openfga_test(self):
        """Should detect test environment from POSTGRES_DB=openfga_test (backward compat)"""
        with patch.dict(os.environ, {"POSTGRES_DB": "openfga_test"}, clear=True):
            validator = DatabaseValidator(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
            )
            assert validator.environment == Environment.TEST

    def test_detect_environment_defaults_to_dev(self):
        """Should default to development environment"""
        with patch.dict(os.environ, {}, clear=True):
            validator = DatabaseValidator(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
            )
            assert validator.environment == Environment.DEV

    def test_explicit_environment_override(self):
        """Should use explicitly provided environment"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            validator = DatabaseValidator(
                host="localhost",
                port=5432,
                user="postgres",
                password="postgres",
                environment=Environment.TEST,
            )
            assert validator.environment == Environment.TEST


@pytest.mark.unit
@pytest.mark.xdist_group(name="testexpecteddatabasesconfiguration")
class TestExpectedDatabasesConfiguration:
    """Tests for expected database configuration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_get_expected_databases_dev_environment(self):
        """Should return databases without _test suffix in dev environment"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        databases = validator.get_expected_databases()

        assert "gdpr" in databases
        assert "openfga" in databases
        assert "keycloak" in databases
        assert "gdpr_test" not in databases

    def test_get_expected_databases_test_environment(self):
        """Should return databases with _test suffix in test environment"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.TEST,
        )

        databases = validator.get_expected_databases()

        assert "gdpr_test" in databases
        assert "openfga_test" in databases
        assert "keycloak_test" in databases
        assert "gdpr" not in databases

    def test_gdpr_database_info_structure(self):
        """Should configure GDPR database with correct metadata"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        databases = validator.get_expected_databases()
        gdpr_db = databases["gdpr"]

        assert gdpr_db.name == "gdpr"
        assert "GDPR compliance" in gdpr_db.purpose
        assert "user_profiles" in gdpr_db.required_tables
        assert "user_preferences" in gdpr_db.required_tables
        assert "consent_records" in gdpr_db.required_tables
        assert "conversations" in gdpr_db.required_tables
        assert "audit_logs" in gdpr_db.required_tables
        assert gdpr_db.managed_by == "migrations"

    def test_openfga_database_info_structure(self):
        """Should configure OpenFGA database with correct metadata"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        databases = validator.get_expected_databases()
        openfga_db = databases["openfga"]

        assert openfga_db.name == "openfga"
        assert "OpenFGA" in openfga_db.purpose
        assert "tuple" in openfga_db.required_tables
        assert "authorization_model" in openfga_db.required_tables
        assert "store" in openfga_db.required_tables
        assert openfga_db.managed_by == "openfga"

    def test_keycloak_database_info_structure(self):
        """Should configure Keycloak database with correct metadata"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        databases = validator.get_expected_databases()
        keycloak_db = databases["keycloak"]

        assert keycloak_db.name == "keycloak"
        assert "Keycloak" in keycloak_db.purpose
        assert "user_entity" in keycloak_db.required_tables
        assert "realm" in keycloak_db.required_tables
        assert "client" in keycloak_db.required_tables
        assert keycloak_db.managed_by == "keycloak"


@pytest.mark.unit
@pytest.mark.xdist_group(name="testdatabasevalidation")
class TestDatabaseValidation:
    """Tests for database validation logic"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_database_when_database_exists_and_all_tables_present(self):
        """Should return valid result when database exists with all required tables"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        db_info = DatabaseInfo(
            name="gdpr",
            purpose="GDPR compliance",
            required_tables=["user_profiles", "audit_logs"],
            managed_by="migrations",
        )

        # Mock PostgreSQL connections
        mock_postgres_conn = AsyncMock(spec=asyncpg.Connection)
        mock_postgres_conn.fetchval = AsyncMock(return_value=1)  # Database exists
        mock_postgres_conn.close = AsyncMock()

        mock_db_conn = AsyncMock(spec=asyncpg.Connection)
        mock_db_conn.fetchval = AsyncMock(return_value=1)  # All tables exist
        mock_db_conn.close = AsyncMock()

        with patch("asyncpg.connect") as mock_connect:
            mock_connect.side_effect = [mock_postgres_conn, mock_db_conn]

            result = await validator.validate_database(db_info)

            assert result.is_valid
            assert result.exists
            assert result.tables_valid
            assert len(result.errors) == 0
            assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_validate_database_when_database_does_not_exist(self):
        """Should return error when database does not exist"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        db_info = DatabaseInfo(
            name="gdpr",
            purpose="GDPR compliance",
            required_tables=["user_profiles"],
            managed_by="migrations",
        )

        # Mock PostgreSQL connection
        mock_postgres_conn = AsyncMock(spec=asyncpg.Connection)
        mock_postgres_conn.fetchval = AsyncMock(return_value=None)  # Database doesn't exist
        mock_postgres_conn.close = AsyncMock()

        with patch("asyncpg.connect", return_value=mock_postgres_conn):
            result = await validator.validate_database(db_info)

            assert not result.is_valid
            assert not result.exists
            assert not result.tables_valid
            assert len(result.errors) > 0
            assert "does not exist" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_database_when_migration_managed_tables_missing(self):
        """Should return error when migration-managed tables are missing"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        db_info = DatabaseInfo(
            name="gdpr",
            purpose="GDPR compliance",
            required_tables=["user_profiles", "audit_logs"],
            managed_by="migrations",
        )

        # Mock PostgreSQL connections
        mock_postgres_conn = AsyncMock(spec=asyncpg.Connection)
        mock_postgres_conn.fetchval = AsyncMock(return_value=1)  # Database exists
        mock_postgres_conn.close = AsyncMock()

        mock_db_conn = AsyncMock(spec=asyncpg.Connection)
        # First call returns 1 (user_profiles exists), second call returns None (audit_logs missing)
        mock_db_conn.fetchval = AsyncMock(side_effect=[1, None])
        mock_db_conn.close = AsyncMock()

        with patch("asyncpg.connect") as mock_connect:
            mock_connect.side_effect = [mock_postgres_conn, mock_db_conn]

            result = await validator.validate_database(db_info)

            assert not result.is_valid
            assert result.exists
            assert not result.tables_valid
            assert len(result.errors) > 0
            assert "audit_logs" in result.errors[0]
            assert "Schema migration" in result.errors[0]

    @pytest.mark.asyncio
    async def test_validate_database_when_service_managed_tables_missing(self):
        """Should return warning (not error) when service-managed tables are missing"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        db_info = DatabaseInfo(
            name="openfga",
            purpose="OpenFGA authorization",
            required_tables=["tuple", "store"],
            managed_by="openfga",
        )

        # Mock PostgreSQL connections
        mock_postgres_conn = AsyncMock(spec=asyncpg.Connection)
        mock_postgres_conn.fetchval = AsyncMock(return_value=1)  # Database exists
        mock_postgres_conn.close = AsyncMock()

        mock_db_conn = AsyncMock(spec=asyncpg.Connection)
        # Both tables missing
        mock_db_conn.fetchval = AsyncMock(return_value=None)
        mock_db_conn.close = AsyncMock()

        with patch("asyncpg.connect") as mock_connect:
            mock_connect.side_effect = [mock_postgres_conn, mock_db_conn]

            result = await validator.validate_database(db_info)

            assert result.is_valid  # Still valid because tables are service-managed
            assert result.exists
            assert not result.tables_valid
            assert len(result.errors) == 0  # No errors
            assert len(result.warnings) > 0  # But warnings
            assert "openfga" in result.warnings[0]
            assert "service hasn't started" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_validate_database_when_connection_fails(self):
        """Should return error when PostgreSQL connection fails"""
        import asyncpg

        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        db_info = DatabaseInfo(
            name="gdpr",
            purpose="GDPR compliance",
            required_tables=["user_profiles"],
            managed_by="migrations",
        )

        with patch("asyncpg.connect", side_effect=asyncpg.PostgresConnectionError("Connection refused")):
            result = await validator.validate_database(db_info)

            assert not result.is_valid
            assert not result.exists
            assert not result.tables_valid
            assert len(result.errors) > 0
            assert "Failed to connect" in result.errors[0]


@pytest.mark.unit
@pytest.mark.xdist_group(name="testoverallvalidation")
class TestOverallValidation:
    """Tests for overall validation of all databases"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_all_databases_when_all_valid(self):
        """Should return overall valid result when all databases are valid"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        # Mock all database validations to succeed
        mock_result = DatabaseValidationResult(
            database_name="test_db",
            exists=True,
            tables_valid=True,
            errors=[],
            warnings=[],
        )

        with patch.object(validator, "validate_database", return_value=mock_result):
            result = await validator.validate()

            assert result.is_valid
            assert result.environment == Environment.DEV
            assert len(result.errors) == 0
            assert len(result.databases) == 3  # gdpr, openfga, keycloak

    @pytest.mark.asyncio
    async def test_validate_aggregates_errors_from_all_databases(self):
        """Should aggregate all errors from database validations"""
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            environment=Environment.DEV,
        )

        # Mock database validations with different errors
        mock_results = [
            DatabaseValidationResult(
                database_name="gdpr",
                exists=False,
                tables_valid=False,
                errors=["gdpr error 1", "gdpr error 2"],
                warnings=[],
            ),
            DatabaseValidationResult(
                database_name="openfga",
                exists=True,
                tables_valid=False,
                errors=["openfga error 1"],
                warnings=["openfga warning 1"],
            ),
            DatabaseValidationResult(
                database_name="keycloak",
                exists=True,
                tables_valid=True,
                errors=[],
                warnings=[],
            ),
        ]

        with patch.object(validator, "validate_database", side_effect=mock_results):
            result = await validator.validate()

            assert not result.is_valid
            assert len(result.errors) == 3  # 2 from gdpr + 1 from openfga
            assert "gdpr error 1" in result.errors
            assert "gdpr error 2" in result.errors
            assert "openfga error 1" in result.errors
            assert len(result.warnings) == 1
            assert "openfga warning 1" in result.warnings


@pytest.mark.unit
@pytest.mark.xdist_group(name="testvalidationresultserialization")
class TestValidationResultSerialization:
    """Tests for validation result serialization"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validation_result_to_dict(self):
        """Should serialize validation result to dictionary"""
        result = ValidationResult(
            environment=Environment.TEST,
            databases={
                "gdpr_test": DatabaseValidationResult(
                    database_name="gdpr_test",
                    exists=True,
                    tables_valid=True,
                    errors=[],
                    warnings=[],
                ),
                "openfga_test": DatabaseValidationResult(
                    database_name="openfga_test",
                    exists=True,
                    tables_valid=False,
                    errors=["Missing table"],
                    warnings=["Service not started"],
                ),
            },
            is_valid=False,
            errors=["Missing table"],
            warnings=["Service not started"],
        )

        result_dict = result.to_dict()

        assert result_dict["environment"] == "test"
        assert result_dict["is_valid"] is False
        assert len(result_dict["databases"]) == 2
        assert result_dict["databases"]["gdpr_test"]["exists"] is True
        assert result_dict["databases"]["openfga_test"]["tables_valid"] is False
        assert len(result_dict["errors"]) == 1
        assert len(result_dict["warnings"]) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="testconveniencefunction")
class TestConvenienceFunction:
    """Tests for the convenience function"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_database_architecture_convenience_function(self):
        """Should provide convenient validation with default parameters"""
        mock_result = ValidationResult(
            environment=Environment.DEV,
            databases={},
            is_valid=True,
            errors=[],
            warnings=[],
        )
        # IMPORTANT: Don't use AsyncMock(spec=...) - spec introspection doesn't detect
        # async methods correctly, causing MagicMock to be used instead of AsyncMock
        # for the validate() method. Use a plain mock and explicitly set async methods.
        from unittest.mock import MagicMock

        mock_validator = MagicMock()
        mock_validator.validate = AsyncMock(return_value=mock_result)

        with patch("mcp_server_langgraph.health.database_checks.DatabaseValidator", return_value=mock_validator):
            result = await validate_database_architecture()

            assert result.is_valid
            assert result.environment == Environment.DEV

    @pytest.mark.asyncio
    async def test_validate_database_architecture_with_custom_parameters(self):
        """Should accept custom connection parameters"""
        mock_result = ValidationResult(
            environment=Environment.DEV,
            databases={},
            is_valid=True,
            errors=[],
            warnings=[],
        )
        # IMPORTANT: Don't use AsyncMock(spec=...) - spec introspection doesn't detect
        # async methods correctly, causing MagicMock to be used instead of AsyncMock
        # for the validate() method. Use a plain mock and explicitly set async methods.
        from unittest.mock import MagicMock

        mock_validator = MagicMock()
        mock_validator.validate = AsyncMock(return_value=mock_result)

        with patch("mcp_server_langgraph.health.database_checks.DatabaseValidator", return_value=mock_validator) as mock_class:
            result = await validate_database_architecture(
                host="custom-host",
                port=9432,
                user="custom-user",
                password="custom-pass",
            )

            # Verify custom parameters were passed
            mock_class.assert_called_once_with(
                host="custom-host",
                port=9432,
                user="custom-user",
                password="custom-pass",
            )
            assert result.is_valid


@pytest.mark.unit
@pytest.mark.xdist_group(name="testdatabasevalidationresultproperty")
class TestDatabaseValidationResultProperty:
    """Tests for DatabaseValidationResult.is_valid property"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_is_valid_when_exists_and_no_errors(self):
        """Should be valid when database exists and has no errors"""
        result = DatabaseValidationResult(
            database_name="gdpr",
            exists=True,
            tables_valid=True,
            errors=[],
            warnings=["Some warning"],
        )

        assert result.is_valid

    def test_is_valid_false_when_database_does_not_exist(self):
        """Should be invalid when database doesn't exist"""
        result = DatabaseValidationResult(
            database_name="gdpr",
            exists=False,
            tables_valid=False,
            errors=[],
            warnings=[],
        )

        assert not result.is_valid

    def test_is_valid_false_when_errors_present(self):
        """Should be invalid when errors are present"""
        result = DatabaseValidationResult(
            database_name="gdpr",
            exists=True,
            tables_valid=False,
            errors=["Missing table"],
            warnings=[],
        )

        assert not result.is_valid
