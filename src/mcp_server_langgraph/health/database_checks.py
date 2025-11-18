"""
Database Structure Validation Module

Validates that all required databases exist with correct schema according to ADR-0056.

This module provides runtime validation of the database architecture to ensure:
1. All required databases exist (gdpr, openfga, keycloak)
2. Environment-specific naming is correct (dev vs test)
3. Required tables exist in each database
4. Schema migrations have been applied correctly

References:
    - ADR-0056: Database Architecture and Naming Convention
    - migrations/000_init_databases.sh: Database initialization script
    - migrations/001_gdpr_schema.sql: GDPR schema definition
"""

import os
from dataclasses import dataclass
from enum import Enum

import asyncpg

from mcp_server_langgraph.observability.telemetry import logger


class Environment(str, Enum):
    """Environment type enum"""

    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseInfo:
    """Information about a required database"""

    name: str
    purpose: str
    required_tables: list[str]
    managed_by: str  # "migrations" or service name (e.g., "openfga", "keycloak")


class DatabaseValidator:
    """
    Database architecture validator.

    Validates that the PostgreSQL instance has the correct database structure
    according to ADR-0056.

    Usage:
        validator = DatabaseValidator(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres"
        )

        result = await validator.validate()
        if result.is_valid:
            print("✅ Database structure is valid")
        else:
            print(f"❌ Validation failed: {result.errors}")
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        environment: Environment | None = None,
    ):
        """
        Initialize database validator.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: PostgreSQL username
            password: PostgreSQL password
            environment: Environment type (auto-detected if None)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.environment = environment or self._detect_environment()

    def _detect_environment(self) -> Environment:
        """
        Detect environment from environment variables.

        Detection logic:
        1. Check ENVIRONMENT env var
        2. Check TESTING env var
        3. Check POSTGRES_DB suffix
        4. Default to DEV

        Returns:
            Detected environment type
        """
        # Check explicit environment variable
        env = os.getenv("ENVIRONMENT", "").lower()
        if env in [e.value for e in Environment]:
            return Environment(env)

        # Check if running in test mode
        if os.getenv("TESTING") == "true" or os.getenv("PYTEST_CURRENT_TEST"):
            return Environment.TEST

        # Check POSTGRES_DB for test suffix
        postgres_db = os.getenv("POSTGRES_DB", "")
        if postgres_db.endswith("_test") or postgres_db == "openfga_test":
            return Environment.TEST

        # Default to development
        return Environment.DEV

    def get_expected_databases(self) -> dict[str, DatabaseInfo]:
        """
        Get expected databases based on environment.

        Returns:
            Dictionary mapping database names to DatabaseInfo objects
        """
        # Determine database name suffix based on environment
        suffix = "_test" if self.environment == Environment.TEST else ""

        return {
            f"gdpr{suffix}": DatabaseInfo(
                name=f"gdpr{suffix}",
                purpose="GDPR compliance storage (user profiles, consents, audit logs)",
                required_tables=["user_profiles", "user_preferences", "consent_records", "conversations", "audit_logs"],
                managed_by="migrations",
            ),
            f"openfga{suffix}": DatabaseInfo(
                name=f"openfga{suffix}",
                purpose="OpenFGA authorization (relationship tuples, policies)",
                required_tables=["tuple", "authorization_model", "store"],
                managed_by="openfga",
            ),
            f"keycloak{suffix}": DatabaseInfo(
                name=f"keycloak{suffix}",
                purpose="Keycloak authentication (users, realms, clients)",
                required_tables=["user_entity", "realm", "client"],
                managed_by="keycloak",
            ),
        }

    async def _check_database_exists(self, conn: asyncpg.Connection, db_name: str) -> bool:
        """
        Check if a database exists.

        Args:
            conn: PostgreSQL connection
            db_name: Database name to check

        Returns:
            True if database exists, False otherwise
        """
        result = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        return result == 1

    async def _check_table_exists(self, conn: asyncpg.Connection, db_name: str, table_name: str) -> bool:
        """
        Check if a table exists in a database.

        Args:
            conn: PostgreSQL connection (connected to the database)
            db_name: Database name (for logging)
            table_name: Table name to check

        Returns:
            True if table exists, False otherwise
        """
        result = await conn.fetchval(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_name = $1
            """,
            table_name,
        )
        return result == 1

    async def validate_database(self, db_info: DatabaseInfo) -> "DatabaseValidationResult":
        """
        Validate a single database.

        Args:
            db_info: Database information to validate

        Returns:
            Validation result for this database
        """
        errors = []
        warnings = []

        try:
            # Connect to postgres database to check if target database exists
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database="postgres",
            )

            try:
                # Check if database exists
                exists = await self._check_database_exists(conn, db_info.name)
                if not exists:
                    errors.append(f"Database '{db_info.name}' does not exist")
                    return DatabaseValidationResult(
                        database_name=db_info.name,
                        exists=False,
                        tables_valid=False,
                        errors=errors,
                        warnings=warnings,
                    )

            finally:
                await conn.close()

            # Connect to the database to check tables
            db_conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=db_info.name,
            )

            try:
                # Check required tables
                missing_tables = []
                for table in db_info.required_tables:
                    exists = await self._check_table_exists(db_conn, db_info.name, table)
                    if not exists:
                        missing_tables.append(table)

                if missing_tables:
                    if db_info.managed_by == "migrations":
                        errors.append(
                            f"Missing tables in '{db_info.name}': {', '.join(missing_tables)}. "
                            f"Schema migration may not have run correctly."
                        )
                    else:
                        warnings.append(
                            f"Missing tables in '{db_info.name}': {', '.join(missing_tables)}. "
                            f"This database is managed by {db_info.managed_by} - "
                            f"tables may not exist yet if service hasn't started."
                        )

                return DatabaseValidationResult(
                    database_name=db_info.name,
                    exists=True,
                    tables_valid=len(missing_tables) == 0,
                    errors=errors,
                    warnings=warnings,
                )

            finally:
                await db_conn.close()

        except asyncpg.PostgresConnectionError as e:
            errors.append(f"Failed to connect to PostgreSQL: {e}")
            return DatabaseValidationResult(
                database_name=db_info.name,
                exists=False,
                tables_valid=False,
                errors=errors,
                warnings=warnings,
            )
        except Exception as e:
            errors.append(f"Unexpected error validating '{db_info.name}': {e}")
            return DatabaseValidationResult(
                database_name=db_info.name,
                exists=False,
                tables_valid=False,
                errors=errors,
                warnings=warnings,
            )

    async def validate(self) -> "ValidationResult":
        """
        Validate all required databases.

        Returns:
            Overall validation result
        """
        logger.info(f"Validating database architecture for {self.environment.value} environment")

        expected_databases = self.get_expected_databases()
        database_results = {}

        for db_name, db_info in expected_databases.items():
            result = await self.validate_database(db_info)
            database_results[db_name] = result

        # Aggregate results
        all_errors = []
        all_warnings = []
        all_valid = True

        for _db_name, result in database_results.items():
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            if not result.is_valid:
                all_valid = False

        return ValidationResult(
            environment=self.environment,
            databases=database_results,
            is_valid=all_valid,
            errors=all_errors,
            warnings=all_warnings,
        )


@dataclass
class DatabaseValidationResult:
    """Result of validating a single database"""

    database_name: str
    exists: bool
    tables_valid: bool
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        """Check if database validation passed (no errors)"""
        return self.exists and len(self.errors) == 0


@dataclass
class ValidationResult:
    """Overall validation result for all databases"""

    environment: Environment
    databases: dict[str, DatabaseValidationResult]
    is_valid: bool
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "environment": self.environment.value,
            "is_valid": self.is_valid,
            "databases": {
                name: {
                    "exists": result.exists,
                    "tables_valid": result.tables_valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                }
                for name, result in self.databases.items()
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


async def validate_database_architecture(
    host: str = "localhost",
    port: int = 5432,
    user: str = "postgres",
    password: str = "postgres",
) -> ValidationResult:
    """
    Convenience function to validate database architecture.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        user: PostgreSQL username
        password: PostgreSQL password

    Returns:
        Validation result

    Example:
        result = await validate_database_architecture()
        if result.is_valid:
            print("✅ All databases valid")
        else:
            for error in result.errors:
                print(f"❌ {error}")
    """
    validator = DatabaseValidator(host=host, port=port, user=user, password=password)
    return await validator.validate()
