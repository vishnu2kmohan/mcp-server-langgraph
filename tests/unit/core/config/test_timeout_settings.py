"""
Tests for timeout and limit settings with explicit Field aliases and validation ranges.

TDD tests written FIRST to define expected behavior for:
1. Explicit environment variable aliases for timeout settings
2. Validation ranges to prevent misconfiguration
"""

import gc

import pytest

pytestmark = pytest.mark.unit


class TestTimeoutEnvironmentVariables:
    """Verify timeout settings can be configured via explicit env vars."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prometheus_timeout_from_env_var(self, monkeypatch) -> None:
        """PROMETHEUS_TIMEOUT env var should configure prometheus_timeout."""
        monkeypatch.setenv("PROMETHEUS_TIMEOUT", "45")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.prometheus_timeout == 45

    def test_prometheus_retry_attempts_from_env_var(self, monkeypatch) -> None:
        """PROMETHEUS_RETRY_ATTEMPTS env var should configure prometheus_retry_attempts."""
        monkeypatch.setenv("PROMETHEUS_RETRY_ATTEMPTS", "5")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.prometheus_retry_attempts == 5

    def test_model_timeout_from_env_var(self, monkeypatch) -> None:
        """MODEL_TIMEOUT env var should configure model_timeout."""
        monkeypatch.setenv("MODEL_TIMEOUT", "120")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.model_timeout == 120

    def test_keycloak_timeout_from_env_var(self, monkeypatch) -> None:
        """KEYCLOAK_TIMEOUT env var should configure keycloak_timeout."""
        monkeypatch.setenv("KEYCLOAK_TIMEOUT", "60")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.keycloak_timeout == 60

    def test_session_idle_seconds_from_env_var(self, monkeypatch) -> None:
        """SESSION_IDLE_SECONDS env var should configure session_idle_seconds."""
        monkeypatch.setenv("SESSION_IDLE_SECONDS", "3600")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.session_idle_seconds == 3600


class TestTimeoutValidationRanges:
    """Verify timeout settings have proper validation ranges."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prometheus_timeout_minimum_is_1(self, monkeypatch) -> None:
        """prometheus_timeout should reject values less than 1."""
        monkeypatch.setenv("PROMETHEUS_TIMEOUT", "0")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="greater than or equal to 1"):
            Settings()

    def test_prometheus_timeout_maximum_is_300(self, monkeypatch) -> None:
        """prometheus_timeout should reject values greater than 300."""
        monkeypatch.setenv("PROMETHEUS_TIMEOUT", "500")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="less than or equal to 300"):
            Settings()

    def test_prometheus_retry_attempts_minimum_is_0(self, monkeypatch) -> None:
        """prometheus_retry_attempts should accept 0 (no retries)."""
        monkeypatch.setenv("PROMETHEUS_RETRY_ATTEMPTS", "0")

        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.prometheus_retry_attempts == 0

    def test_prometheus_retry_attempts_maximum_is_10(self, monkeypatch) -> None:
        """prometheus_retry_attempts should reject values greater than 10."""
        monkeypatch.setenv("PROMETHEUS_RETRY_ATTEMPTS", "15")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="less than or equal to 10"):
            Settings()

    def test_model_timeout_minimum_is_1(self, monkeypatch) -> None:
        """model_timeout should reject values less than 1."""
        monkeypatch.setenv("MODEL_TIMEOUT", "0")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="greater than or equal to 1"):
            Settings()

    def test_model_timeout_maximum_is_600(self, monkeypatch) -> None:
        """model_timeout should reject values greater than 600 (10 minutes)."""
        monkeypatch.setenv("MODEL_TIMEOUT", "700")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="less than or equal to 600"):
            Settings()

    def test_keycloak_timeout_minimum_is_1(self, monkeypatch) -> None:
        """keycloak_timeout should reject values less than 1."""
        monkeypatch.setenv("KEYCLOAK_TIMEOUT", "0")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="greater than or equal to 1"):
            Settings()

    def test_keycloak_timeout_maximum_is_120(self, monkeypatch) -> None:
        """keycloak_timeout should reject values greater than 120 (2 minutes)."""
        monkeypatch.setenv("KEYCLOAK_TIMEOUT", "180")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="less than or equal to 120"):
            Settings()

    def test_session_idle_seconds_minimum_is_60(self, monkeypatch) -> None:
        """session_idle_seconds should reject values less than 60 (1 minute)."""
        monkeypatch.setenv("SESSION_IDLE_SECONDS", "30")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="greater than or equal to 60"):
            Settings()

    def test_session_idle_seconds_maximum_is_86400(self, monkeypatch) -> None:
        """session_idle_seconds should reject values greater than 86400 (24 hours)."""
        monkeypatch.setenv("SESSION_IDLE_SECONDS", "100000")

        from mcp_server_langgraph.core.config import Settings

        with pytest.raises(ValueError, match="less than or equal to 86400"):
            Settings()


class TestTimeoutDefaults:
    """Verify timeout settings have sensible defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_prometheus_timeout_default_is_30(self) -> None:
        """Default prometheus_timeout should be 30 seconds."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.prometheus_timeout == 30

    def test_prometheus_retry_attempts_default_is_3(self) -> None:
        """Default prometheus_retry_attempts should be 3."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.prometheus_retry_attempts == 3

    def test_model_timeout_default_is_60(self) -> None:
        """Default model_timeout should be 60 seconds."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.model_timeout == 60

    def test_keycloak_timeout_default_is_30(self) -> None:
        """Default keycloak_timeout should be 30 seconds."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.keycloak_timeout == 30

    def test_session_idle_seconds_default_is_1800(self) -> None:
        """Default session_idle_seconds should be 1800 (30 minutes)."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.session_idle_seconds == 1800
