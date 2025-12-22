"""
TDD Tests for Compliance Storage Environment Variable Migration

Tests the backward-compatible migration from GDPR_* to COMPLIANCE_* env vars:
- GDPR_STORAGE_BACKEND -> COMPLIANCE_STORAGE_BACKEND
- GDPR_POSTGRES_URL -> COMPLIANCE_POSTGRES_URL

Following TDD:
1. Write tests first (this file) - RED
2. Implement AliasChoices in Settings - GREEN
3. Verify all tests pass - REFACTOR

Acceptance Criteria:
- New COMPLIANCE_* env vars work as primary names
- Old GDPR_* env vars still work (deprecated but functional)
- New names take precedence when both are set
- Property aliases provide access via both old and new names
"""

import gc
import os
from typing import Any

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.config]


@pytest.mark.xdist_group(name="testcomplianceenvvarmigration")
class TestComplianceEnvVarMigration:
    """Test backward-compatible migration from GDPR_* to COMPLIANCE_* env vars"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    # =========================================================================
    # COMPLIANCE_STORAGE_BACKEND Tests
    # =========================================================================

    def test_compliance_storage_backend_new_env_var_works(self) -> None:
        """
        Test that COMPLIANCE_STORAGE_BACKEND env var is accepted

        Behavior:
        - When COMPLIANCE_STORAGE_BACKEND is set
        - Then settings.compliance_storage_backend returns that value
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            compliance_storage_backend="postgres",
        )

        assert settings.compliance_storage_backend == "postgres"

    def test_gdpr_storage_backend_deprecated_env_var_still_works(self) -> None:
        """
        Test that GDPR_STORAGE_BACKEND env var still works (deprecated)

        Behavior:
        - When GDPR_STORAGE_BACKEND is set (legacy)
        - Then settings.compliance_storage_backend returns that value
        - This ensures backward compatibility for existing deployments
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            gdpr_storage_backend="postgres",  # Legacy name
        )

        assert settings.compliance_storage_backend == "postgres"

    def test_compliance_storage_backend_takes_precedence_over_gdpr(self) -> None:
        """
        Test that COMPLIANCE_STORAGE_BACKEND takes precedence over GDPR_STORAGE_BACKEND

        Behavior:
        - When both COMPLIANCE_STORAGE_BACKEND and GDPR_STORAGE_BACKEND are set
        - Then COMPLIANCE_STORAGE_BACKEND value is used (new takes precedence)
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            compliance_storage_backend="postgres",  # New name (should win)
            gdpr_storage_backend="memory",  # Old name (should be ignored)
        )

        assert settings.compliance_storage_backend == "postgres"

    def test_gdpr_storage_backend_property_alias_works(self) -> None:
        """
        Test that settings.gdpr_storage_backend property alias still works

        Behavior:
        - When compliance_storage_backend is set
        - Then settings.gdpr_storage_backend returns the same value
        - This provides backward compatibility for code using the old property name
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            compliance_storage_backend="postgres",
        )

        # Both names should return the same value
        assert settings.compliance_storage_backend == "postgres"
        assert settings.gdpr_storage_backend == "postgres"

    # =========================================================================
    # COMPLIANCE_POSTGRES_URL Tests
    # =========================================================================

    def test_compliance_postgres_url_new_env_var_works(self) -> None:
        """
        Test that COMPLIANCE_POSTGRES_URL env var is accepted

        Behavior:
        - When COMPLIANCE_POSTGRES_URL is set
        - Then settings.compliance_postgres_url returns that value
        """
        from mcp_server_langgraph.core.config import Settings

        custom_url = "postgresql://user:pass@compliance-db:5432/compliance"

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            compliance_postgres_url=custom_url,
        )

        assert settings.compliance_postgres_url == custom_url

    def test_gdpr_postgres_url_deprecated_env_var_still_works(self) -> None:
        """
        Test that GDPR_POSTGRES_URL env var still works (deprecated)

        Behavior:
        - When GDPR_POSTGRES_URL is set (legacy)
        - Then settings.compliance_postgres_url returns that value
        - This ensures backward compatibility for existing deployments
        """
        from mcp_server_langgraph.core.config import Settings

        legacy_url = "postgresql://user:pass@gdpr-db:5432/gdpr"

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            gdpr_postgres_url=legacy_url,  # Legacy name
        )

        assert settings.compliance_postgres_url == legacy_url

    def test_compliance_postgres_url_takes_precedence_over_gdpr(self) -> None:
        """
        Test that COMPLIANCE_POSTGRES_URL takes precedence over GDPR_POSTGRES_URL

        Behavior:
        - When both COMPLIANCE_POSTGRES_URL and GDPR_POSTGRES_URL are set
        - Then COMPLIANCE_POSTGRES_URL value is used (new takes precedence)
        """
        from mcp_server_langgraph.core.config import Settings

        new_url = "postgresql://user:pass@compliance-db:5432/compliance"
        old_url = "postgresql://user:pass@gdpr-db:5432/gdpr"

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            compliance_postgres_url=new_url,  # New name (should win)
            gdpr_postgres_url=old_url,  # Old name (should be ignored)
        )

        assert settings.compliance_postgres_url == new_url

    def test_gdpr_postgres_url_property_alias_works(self) -> None:
        """
        Test that settings.gdpr_postgres_url property alias still works

        Behavior:
        - When compliance_postgres_url is set
        - Then settings.gdpr_postgres_url returns the same value
        - This provides backward compatibility for code using the old property name
        """
        from mcp_server_langgraph.core.config import Settings

        url = "postgresql://user:pass@compliance-db:5432/compliance"

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            compliance_postgres_url=url,
        )

        # Both names should return the same value
        assert settings.compliance_postgres_url == url
        assert settings.gdpr_postgres_url == url

    # =========================================================================
    # Default Value Tests
    # =========================================================================

    def test_compliance_storage_backend_defaults_to_memory(self) -> None:
        """
        Test that compliance_storage_backend defaults to 'memory' for dev/test

        Behavior:
        - When no env var is set
        - Then default is 'memory' (safe for development)
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
        )

        assert settings.compliance_storage_backend == "memory"

    def test_compliance_postgres_url_has_sensible_default(self) -> None:
        """
        Test that compliance_postgres_url has a sensible default

        Behavior:
        - When no env var is set
        - Then default points to localhost compliance database
        """
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
        )

        # Default should be localhost with compliance database
        assert "localhost" in settings.compliance_postgres_url
        assert "compliance" in settings.compliance_postgres_url or "gdpr" in settings.compliance_postgres_url


@pytest.mark.xdist_group(name="testcomplianceenvvarproduction")
class TestComplianceEnvVarProductionValidation:
    """Test production validation for compliance storage settings"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_production_requires_postgres_backend(self) -> None:
        """
        Test that production environment requires postgres backend

        Behavior:
        - When environment=production and compliance_storage_backend=memory
        - Then validation should fail with clear error message
        """
        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError) as exc_info:
            Settings(
                service_name="test",
                environment="production",
                jwt_secret_key="test-key",
                anthropic_api_key="test-key",
                auth_provider="keycloak",
                keycloak_server_url="http://keycloak:8080",
                compliance_storage_backend="memory",  # Not allowed in production
            )

        error_message = str(exc_info.value)
        assert "memory" in error_message.lower() or "production" in error_message.lower()
