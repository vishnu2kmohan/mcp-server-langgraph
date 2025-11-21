"""
TDD Tests for Database Connectivity in Startup Validation

These tests define the expected behavior for integrating database connectivity
checks into the run_startup_validation() function.

Following TDD:
1. Write tests first (this file) - RED
2. Implement database validation in health.py - GREEN
3. Verify all tests pass - REFACTOR

Test Coverage:
- PostgreSQL connectivity is validated during startup
- Database validation failure prevents app startup
- Proper error messages when databases are unavailable
- Success when all databases are accessible
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


@pytest.mark.xdist_group(name="testdatabasestartupvalidation")
class TestDatabaseStartupValidation:
    """Test database connectivity validation in startup checks"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_startup_validation_includes_database_connectivity_check(self):
        """
        Test that run_startup_validation includes database connectivity check

        Behavior:
        - When run_startup_validation() is called
        - Then it should validate PostgreSQL connectivity
        - And include 'database_connectivity' in checks
        """
        from mcp_server_langgraph.api.health import run_startup_validation

        # Mock the database validation to succeed
        with patch("mcp_server_langgraph.api.health.validate_database_connectivity") as mock_validate:
            mock_validate.return_value = (True, "All databases accessible")

            # Should not raise
            run_startup_validation()

            # Database connectivity check should have been called
            mock_validate.assert_called_once()

    def test_database_connectivity_validation_succeeds_when_databases_accessible(self):
        """
        Test that database connectivity validation succeeds when all DBs are accessible

        Behavior:
        - When all databases (gdpr, openfga, keycloak) are accessible
        - Then validate_database_connectivity() returns (True, success_message)
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        # Mock the database infrastructure layer
        with patch(
            "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (True, "PostgreSQL database accessible")

            # Run validation
            is_healthy, message = validate_database_connectivity()

            assert is_healthy is True
            assert "database" in message.lower() or "accessible" in message.lower()
            mock_check.assert_called_once()

    def test_database_connectivity_validation_fails_when_postgres_unreachable(self):
        """
        Test that validation fails when PostgreSQL is unreachable

        Behavior:
        - When PostgreSQL connection fails
        - Then validate_database_connectivity() returns (False, error_message)
        - And error message indicates connection failure
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        # Mock the database infrastructure layer
        with patch(
            "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (False, "PostgreSQL connection failed: Connection refused")

            is_healthy, message = validate_database_connectivity()

            assert is_healthy is False
            assert "connection" in message.lower() or "refused" in message.lower()
            mock_check.assert_called_once()

    def test_startup_validation_fails_when_database_unreachable(self):
        """
        Test that run_startup_validation() fails when database is unreachable

        Behavior:
        - When database connectivity check fails
        - Then run_startup_validation() raises SystemValidationError
        - And error message includes database failure details
        """
        from mcp_server_langgraph.api.health import SystemValidationError, run_startup_validation

        # Mock database validation to fail
        with patch("mcp_server_langgraph.api.health.validate_database_connectivity") as mock_validate:
            mock_validate.return_value = (False, "PostgreSQL connection failed")

            with pytest.raises(SystemValidationError, match="database"):
                run_startup_validation()

    def test_database_connectivity_uses_settings_for_connection(self):
        """
        Test that database connectivity check uses settings for connection parameters

        Behavior:
        - When validate_database_connectivity() is called
        - Then it should use postgres connection settings from config
        - And connect to the correct host/port/database
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        # Mock settings and database infrastructure
        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            with patch(
                "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
            ) as mock_check:
                # Configure mock settings
                mock_settings.gdpr_postgres_url = "postgresql://test:test@testhost:5555/gdpr_test"
                mock_check.return_value = (True, "PostgreSQL database accessible")

                validate_database_connectivity()

                # Should have called check_database_connectivity with the URL from settings
                mock_check.assert_called_once()
                call_args = mock_check.call_args
                assert "postgresql://test:test@testhost:5555/gdpr_test" in str(call_args)

    def test_database_connectivity_validation_is_logged(self):
        """
        Test that database connectivity validation logs results

        Behavior:
        - When validate_database_connectivity() runs
        - Then it should log the validation attempt
        - And log success or failure appropriately
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        with patch("mcp_server_langgraph.api.health.logger") as mock_logger:
            with patch(
                "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
            ) as mock_check:
                mock_check.return_value = (True, "PostgreSQL database accessible")

                validate_database_connectivity()

                # Should have logged something about database validation
                assert mock_logger.debug.called or mock_logger.info.called

    def test_database_connectivity_validation_is_async(self):
        """
        Test that database connectivity validation handles async properly

        Behavior:
        - validate_database_connectivity() should be synchronous wrapper
        - But internally uses async database connections
        - This ensures it works with run_startup_validation()
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        # Function should be callable synchronously
        with patch(
            "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (True, "PostgreSQL database accessible")

            # Should not require await
            result = validate_database_connectivity()

            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)

    def test_health_check_endpoint_includes_database_connectivity(self):
        """
        Test that health check endpoint includes database connectivity check

        Behavior:
        - When /api/v1/health endpoint is called
        - Then response includes 'database_connectivity' in checks
        - And shows current database status
        """
        import asyncio

        from mcp_server_langgraph.api.health import health_check

        # Mock database validation
        with patch("mcp_server_langgraph.api.health.validate_database_connectivity") as mock_validate:
            mock_validate.return_value = (True, "All databases accessible")

            # Call the async endpoint
            result = asyncio.run(health_check())

            # Should include database connectivity in checks
            assert "database_connectivity" in result.checks
            assert result.checks["database_connectivity"] is True

    def test_database_connectivity_check_timeout_handling(self):
        """
        Test that database connectivity check handles connection timeouts

        Behavior:
        - When database connection times out
        - Then validate_database_connectivity() returns (False, timeout_message)
        - And doesn't hang indefinitely
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        # Mock the database infrastructure layer
        with patch(
            "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (False, "PostgreSQL connection timeout (5s)")

            is_healthy, message = validate_database_connectivity()

            assert is_healthy is False
            assert "timeout" in message.lower() or "connection" in message.lower()


@pytest.mark.xdist_group(name="testdatabasevalidationerrors")
class TestDatabaseValidationErrors:
    """Test error handling in database connectivity validation"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_database_validation_handles_invalid_url(self):
        """
        Test that validation handles invalid PostgreSQL URL gracefully

        Behavior:
        - When postgres URL is malformed
        - Then validate_database_connectivity() returns (False, error_message)
        - And doesn't crash the application
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        with patch("mcp_server_langgraph.api.health.settings") as mock_settings:
            mock_settings.gdpr_postgres_url = "invalid://url"

            with patch(
                "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
            ) as mock_check:
                mock_check.return_value = (False, "Invalid PostgreSQL connection string: Invalid connection string")

                is_healthy, message = validate_database_connectivity()

                assert is_healthy is False
                assert "invalid" in message.lower() or "error" in message.lower()

    def test_database_validation_handles_authentication_failure(self):
        """
        Test that validation handles authentication failures

        Behavior:
        - When PostgreSQL authentication fails
        - Then validate_database_connectivity() returns (False, auth_error_message)
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        with patch(
            "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (False, "PostgreSQL authentication failed: Authentication failed")

            is_healthy, message = validate_database_connectivity()

            assert is_healthy is False
            assert "auth" in message.lower() or "password" in message.lower() or "failed" in message.lower()

    def test_database_validation_handles_missing_database(self):
        """
        Test that validation detects when required database doesn't exist

        Behavior:
        - When a required database (gdpr/openfga/keycloak) doesn't exist
        - Then validate_database_connectivity() returns (False, missing_db_message)
        """
        from mcp_server_langgraph.api.health import validate_database_connectivity

        with patch(
            "mcp_server_langgraph.infrastructure.database.check_database_connectivity", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = (False, 'PostgreSQL database does not exist: database "gdpr" does not exist')

            is_healthy, message = validate_database_connectivity()

            assert is_healthy is False
            assert "database" in message.lower() or "exist" in message.lower()
