"""Tests for checkpoint configuration startup validation.

This test module ensures that Redis URL configuration errors are detected at
startup with clear error messages, preventing the production incident scenario
where pods crashed during runtime due to malformed URLs.

Implements "fail fast" principle: configuration errors should be caught during
application startup, not during first Redis connection attempt.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.core.checkpoint_validator import (
    CheckpointConfigValidator,
    CheckpointValidationError,
    validate_checkpoint_config,
)
from mcp_server_langgraph.core.config import Settings

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="unit_checkpoint_config_validation_tests")
class TestCheckpointConfigValidator:
    """Test startup validation for checkpoint configuration."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_redis_url_with_unencoded_password_raises_error(self):
        """Test that unencoded special characters in Redis URL raise validation error.

        This prevents the production incident where unencoded / in password
        caused ValueError during runtime.
        """
        validator = CheckpointConfigValidator()

        # URL with unencoded special characters (production incident case)
        malformed_url = "redis://:Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgfGnmi6+s=@10.110.1.4:6379/1"

        with pytest.raises(CheckpointValidationError) as exc_info:
            validator.validate_redis_url(malformed_url)

        # Error message should be descriptive
        error_msg = str(exc_info.value)
        assert "special characters" in error_msg.lower() or "url-encoded" in error_msg.lower()
        assert "/" in error_msg or "percent-encode" in error_msg.lower()

    def test_validate_redis_url_with_encoded_password_passes(self):
        """Test that properly encoded Redis URL passes validation."""
        validator = CheckpointConfigValidator()

        # Properly encoded URL
        encoded_url = "redis://:Du0PmDvmqDWqDTgfGnmi6%2FSKyuQydi3z7cPTgfGnmi6%2Bs%3D@10.110.1.4:6379/1"

        # Should not raise exception
        validator.validate_redis_url(encoded_url)

    def test_validate_redis_url_without_password_passes(self):
        """Test that Redis URL without password passes validation."""
        validator = CheckpointConfigValidator()

        url = "redis://localhost:6379/1"

        # Should not raise exception
        validator.validate_redis_url(url)

    def test_validate_redis_url_with_simple_password_passes(self):
        """Test that Redis URL with simple password (no special chars) passes."""
        validator = CheckpointConfigValidator()

        url = "redis://:simplepassword123@localhost:6379/1"

        # Should not raise exception
        validator.validate_redis_url(url)

    def test_validate_redis_url_detects_multiple_special_chars(self):
        """Test that validator detects all problematic special characters."""
        validator = CheckpointConfigValidator()

        # Test each problematic character individually
        problematic_chars = {
            "/": "redis://:pass/word@localhost:6379/1",
            "+": "redis://:pass+word@localhost:6379/1",
            "=": "redis://:pass=word@localhost:6379/1",
            "@": "redis://:p@ssword@localhost:6379/1",
        }

        for char, url in problematic_chars.items():
            with pytest.raises(CheckpointValidationError) as exc_info:
                validator.validate_redis_url(url)

            error_msg = str(exc_info.value)
            # Error should mention the problematic character or encoding
            assert char in error_msg or "encode" in error_msg.lower()

    def test_validate_invalid_redis_url_format_raises_error(self):
        """Test that completely invalid URL formats are caught."""
        validator = CheckpointConfigValidator()

        invalid_urls = [
            ("not-a-url", ["invalid", "format", "scheme"]),
            ("http://wrong-scheme:6379", ["invalid", "scheme"]),
            ("redis://", ["incomplete", "invalid", "format"]),
            ("", ["empty", "cannot be empty"]),
        ]

        for url, expected_keywords in invalid_urls:
            with pytest.raises(CheckpointValidationError) as exc_info:
                validator.validate_redis_url(url)

            error_msg = str(exc_info.value).lower()
            # At least one keyword should be in the error message
            assert any(keyword in error_msg for keyword in expected_keywords), (
                f"Expected one of {expected_keywords} in error for URL: {url}"
            )

    def test_validator_provides_fix_suggestion(self):
        """Test that validation error provides actionable fix suggestion."""
        validator = CheckpointConfigValidator()

        malformed_url = "redis://:pass/word@localhost:6379/1"

        with pytest.raises(CheckpointValidationError) as exc_info:
            validator.validate_redis_url(url=malformed_url)

        error_msg = str(exc_info.value)
        # Should suggest the fix
        assert "%2F" in error_msg or "percent-encode" in error_msg.lower()
        # Should reference RFC or URL encoding
        assert "RFC 3986" in error_msg or "url-encod" in error_msg.lower()


@pytest.mark.xdist_group(name="unit_checkpoint_config_validation_tests")
class TestCheckpointValidationIntegration:
    """Integration tests for checkpoint validation with settings."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validate_checkpoint_config_with_memory_backend_passes(self):
        """Test that memory backend doesn't require Redis URL validation."""
        settings = Settings.model_construct(
            checkpoint_backend="memory",
        )

        # Should not raise exception
        validate_checkpoint_config(settings)

    def test_validate_checkpoint_config_with_redis_backend_validates_url(self):
        """Test that Redis backend triggers URL validation."""
        settings = Settings.model_construct(
            checkpoint_backend="redis",
            checkpoint_redis_url="redis://:pass/word@localhost:6379/1",  # Invalid
        )

        with pytest.raises(CheckpointValidationError) as exc_info:
            validate_checkpoint_config(settings)

        error_msg = str(exc_info.value)
        assert "redis" in error_msg.lower()

    def test_validate_checkpoint_config_with_valid_redis_url_passes(self):
        """Test that valid Redis configuration passes all checks."""
        settings = Settings.model_construct(
            checkpoint_backend="redis",
            checkpoint_redis_url="redis://:pass%2Fword@localhost:6379/1",  # Encoded
        )

        # Should not raise exception
        validate_checkpoint_config(settings)


@pytest.mark.xdist_group(name="unit_checkpoint_config_validation_tests")
class TestStartupValidationErrorMessages:
    """Test that validation errors have helpful, actionable messages."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_error_message_includes_problematic_url(self):
        """Test that error message includes the problematic URL for debugging."""
        validator = CheckpointConfigValidator()

        malformed_url = "redis://:bad/password@localhost:6379/1"

        with pytest.raises(CheckpointValidationError) as exc_info:
            validator.validate_redis_url(malformed_url)

        error_msg = str(exc_info.value)
        # Should show (sanitized) URL for debugging
        assert "redis://" in error_msg
        # Should NOT show full password (security)
        assert "bad/password" not in error_msg or "****" in error_msg

    def test_error_message_references_production_incident(self):
        """Test that error message references the production incident for context."""
        validator = CheckpointConfigValidator()

        malformed_url = "redis://:pass/word@localhost:6379/1"

        with pytest.raises(CheckpointValidationError) as exc_info:
            validator.validate_redis_url(malformed_url)

        error_msg = str(exc_info.value)
        # Should reference incident or provide context
        assert (
            "staging-758b8f744" in error_msg
            or "production incident" in error_msg.lower()
            or "ValueError" in error_msg
            or "port casting" in error_msg.lower()
        )

    def test_error_message_provides_encoded_example(self):
        """Test that error shows correct encoded format."""
        validator = CheckpointConfigValidator()

        malformed_url = "redis://:pass/word@localhost:6379/1"

        with pytest.raises(CheckpointValidationError) as exc_info:
            validator.validate_redis_url(malformed_url)

        error_msg = str(exc_info.value)
        # Should show encoded example
        assert "pass%2Fword" in error_msg or "%2F" in error_msg


@pytest.mark.xdist_group(name="unit_checkpoint_config_validation_tests")
class TestCheckpointValidatorWithMocking:
    """Test validator behavior with Redis connection mocking."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_validator_can_optionally_test_redis_connectivity(self):
        """Test that validator can optionally test actual Redis connection."""
        validator = CheckpointConfigValidator()

        valid_url = "redis://:encoded%2Fpass@localhost:6379/1"

        # Mock Redis connection
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.ping = MagicMock(return_value=True)

            # Should validate URL format without raising
            validator.validate_redis_url(valid_url, test_connection=False)

    def test_validator_fails_fast_on_connection_error_if_requested(self):
        """Test fail-fast behavior when connection test is enabled."""
        validator = CheckpointConfigValidator()

        valid_url = "redis://:encoded%2Fpass@localhost:6379/1"

        # Mock connection failure - patch where it's imported (inside the method)
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_redis.side_effect = ConnectionError("Cannot connect to Redis")

            with pytest.raises(CheckpointValidationError) as exc_info:
                validator.validate_redis_url(valid_url, test_connection=True)

            error_msg = str(exc_info.value).lower()
            # Should mention connection or connect
            assert "connect" in error_msg or "connection" in error_msg


@pytest.mark.xdist_group(name="unit_checkpoint_config_validation_tests")
class TestRegressionPrevention:
    """Regression tests to ensure validation prevents known issues."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_production_incident_url_is_caught_at_startup(self):
        """Test that exact production incident URL would be caught at startup.

        This is the ultimate regression test: if we had this validation in
        production, the incident would never have occurred.
        """
        validator = CheckpointConfigValidator()

        # Exact production URL that caused the incident
        # gitleaks:allow - Test fixture from documented incident
        production_url = "redis://:Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgfGnmi6+s=@10.110.1.4:6379/1"

        # This MUST raise an error to prevent the incident
        with pytest.raises(CheckpointValidationError) as exc_info:
            validator.validate_redis_url(production_url)

        error_msg = str(exc_info.value)
        # Error must be clear enough for ops team to fix immediately
        assert "encode" in error_msg.lower() or "special character" in error_msg.lower()
        assert "%" in error_msg or "percent" in error_msg.lower()

    def test_all_base64_like_passwords_trigger_validation(self):
        """Test that typical Base64 password patterns are validated.

        Base64 commonly contains +, /, = which need encoding.
        """
        validator = CheckpointConfigValidator()

        # Common Base64 patterns
        base64_passwords = [
            "abc123+def456=",
            "xyz/test+value=",
            "Base64/String+With=Chars",
        ]

        for password in base64_passwords:
            url = f"redis://:{password}@localhost:6379/1"

            # All should trigger validation error
            with pytest.raises(CheckpointValidationError):
                validator.validate_redis_url(url)
