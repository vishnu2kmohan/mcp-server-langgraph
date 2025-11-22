"""
Tests for configuration validation

Validates that fallback models have proper credentials configured
and that missing credentials are detected at startup.
"""

import gc

import pytest

from mcp_server_langgraph.core.config import Settings

pytestmark = pytest.mark.unit

# Test model constants - use obviously fake names to prevent time-bomb failures
# when real models are released (e.g., when OpenAI actually releases GPT-5)
TEST_NONEXISTENT_OPENAI_MODEL = "gpt-999-test-nonexistent"
TEST_NONEXISTENT_GOOGLE_MODEL = "gemini-999-test-nonexistent"


@pytest.mark.unit
@pytest.mark.xdist_group(name="config_validation_tests")
class TestFallbackModelValidation:
    """Test fallback model credential validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_fallback_credentials_all_present(self, caplog):
        """Test that validation passes when all credentials are present."""
        settings = Settings(
            # Anthropic
            anthropic_api_key="test-anthropic-key",
            # OpenAI
            openai_api_key="test-openai-key",
            # Fallback models that match the credentials
            enable_fallback=True,
            fallback_models=["claude-3-haiku-20240307", TEST_NONEXISTENT_OPENAI_MODEL],
        )

        # Should not log warnings when all credentials present
        settings._validate_fallback_credentials()

        # Check no warnings were logged
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        fallback_warnings = [log for log in warning_logs if "fallback" in log.message.lower()]
        assert len(fallback_warnings) == 0

    def test_validate_fallback_credentials_missing_anthropic(self, caplog):
        """Test that missing Anthropic credentials are detected."""
        settings = Settings(
            # Missing anthropic_api_key
            anthropic_api_key=None,
            openai_api_key="test-openai-key",
            enable_fallback=True,
            fallback_models=["claude-3-haiku-20240307", TEST_NONEXISTENT_OPENAI_MODEL],
        )

        settings._validate_fallback_credentials()

        # Should log warning about missing Anthropic credentials
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert any("claude-3-haiku-20240307" in log.message for log in warning_logs)
        assert any("ANTHROPIC_API_KEY" in log.message for log in warning_logs)

    def test_validate_fallback_credentials_missing_openai(self, caplog):
        """Test that missing OpenAI credentials are detected."""
        settings = Settings(
            anthropic_api_key="test-anthropic-key",
            openai_api_key=None,  # Missing
            enable_fallback=True,
            fallback_models=["claude-3-haiku-20240307", TEST_NONEXISTENT_OPENAI_MODEL],
        )

        settings._validate_fallback_credentials()

        # Should log warning about missing OpenAI credentials
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert any(TEST_NONEXISTENT_OPENAI_MODEL in log.message for log in warning_logs)
        assert any("OPENAI_API_KEY" in log.message for log in warning_logs)

    def test_validate_fallback_credentials_no_fallback_enabled(self, caplog):
        """Test that validation is skipped when fallback is disabled."""
        settings = Settings(
            enable_fallback=False,  # Disabled
            fallback_models=["claude-3-haiku-20240307"],
            anthropic_api_key=None,  # Missing, but should not warn
        )

        settings._validate_fallback_credentials()

        # Should not log warnings when fallback disabled
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) == 0

    def test_validate_fallback_credentials_empty_list(self, caplog):
        """Test that validation is skipped with empty fallback list."""
        settings = Settings(
            enable_fallback=True,
            fallback_models=[],  # Empty list
            anthropic_api_key=None,  # Missing, but should not warn
        )

        settings._validate_fallback_credentials()

        # Should not log warnings with empty fallback list
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) == 0

    def test_validate_fallback_credentials_multiple_missing(self, caplog):
        """Test detection of multiple missing credentials."""
        settings = Settings(
            # All missing
            anthropic_api_key=None,
            openai_api_key=None,
            google_api_key=None,
            enable_fallback=True,
            fallback_models=[
                "claude-3-haiku-20240307",  # Needs anthropic_api_key
                TEST_NONEXISTENT_OPENAI_MODEL,  # Needs openai_api_key
                TEST_NONEXISTENT_GOOGLE_MODEL,  # Needs google_api_key
            ],
        )

        settings._validate_fallback_credentials()

        # Should log warnings for all three missing credentials
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]

        # Check for each model warning
        assert any("claude-3-haiku-20240307" in log.message for log in warning_logs)
        assert any(TEST_NONEXISTENT_OPENAI_MODEL in log.message for log in warning_logs)
        assert any(TEST_NONEXISTENT_GOOGLE_MODEL in log.message for log in warning_logs)

        # Check for credential names
        assert any("ANTHROPIC_API_KEY" in log.message for log in warning_logs)
        assert any("OPENAI_API_KEY" in log.message for log in warning_logs)
        assert any("GOOGLE_API_KEY" in log.message for log in warning_logs)

    def test_fallback_models_use_latest_stable(self):
        """Test that default fallback models use latest stable production versions."""
        import re

        settings = Settings()

        # Should use Claude 4.5 models (latest as of October 2025)
        # Verified against https://docs.claude.com/en/docs/about-claude/models
        has_claude_4_5 = any(
            "claude-haiku-4-5" in model.lower() or "claude-sonnet-4-5" in model.lower() for model in settings.fallback_models
        )
        assert has_claude_4_5, f"Should include at least one Claude 4.5 model. Found: {settings.fallback_models}"

        # Verify date stamps are reasonable (after 2024-01-01, before 2027-01-01)
        for model in settings.fallback_models:
            if "claude" in model.lower():
                # Extract date stamp (YYYYMMDD format)
                date_match = re.search(r"(\d{8})", model)
                if date_match:
                    date_str = date_match.group(1)
                    year = int(date_str[:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])

                    # Validate year range
                    assert 2024 <= year <= 2027, f"Model {model} has unexpected year: {year}"

                    # Validate month/day
                    assert 1 <= month <= 12, f"Model {model} has invalid month: {month}"
                    assert 1 <= day <= 31, f"Model {model} has invalid day: {day}"


@pytest.mark.unit
@pytest.mark.xdist_group(name="config_validation_tests")
class TestCORSValidation:
    """Test CORS configuration validation."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_cors_validation_wildcard_in_production(self):
        """Test that wildcard CORS is rejected in production."""
        # Wildcard CORS is rejected during Settings initialization
        with pytest.raises(ValueError, match="Wildcard CORS.*not allowed in production"):
            _ = Settings(
                environment="production",
                cors_allowed_origins=["*"],  # Wildcard
                auth_provider="keycloak",  # Required for production
                gdpr_storage_backend="postgres",  # Required for production
                jwt_secret_key="test-secret-key-min-32-chars-long-for-security",  # Required for production
            )

    def test_cors_validation_wildcard_in_development(self, caplog):
        """Test that wildcard CORS is allowed but warned in development."""
        settings = Settings(
            environment="development",
            cors_allowed_origins=["*"],
        )

        # Should not raise, but should warn
        settings.validate_cors_config()

        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert any("Wildcard CORS" in log.message for log in warning_logs)

    def test_cors_validation_specific_origins(self):
        """Test that specific origins are accepted."""
        settings = Settings(
            environment="production",
            cors_allowed_origins=["https://example.com", "https://app.example.com"],
            auth_provider="keycloak",  # Required for production
            gdpr_storage_backend="postgres",  # Required for production
            jwt_secret_key="test-secret-key-min-32-chars-long-for-security",  # Required for production
        )

        # Should not raise
        settings.validate_cors_config()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
