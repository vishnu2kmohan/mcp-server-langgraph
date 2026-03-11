"""Tests for environment utility functions.

Tests for is_developer_mode() which checks if the application is in developer mode.
ONLY 'development' environment returns True - all others are fail-closed.
"""

from unittest.mock import MagicMock

import pytest


pytestmark = pytest.mark.unit


class TestIsDeveloperMode:
    """Tests for is_developer_mode() function."""

    def test_is_developer_mode_returns_true_for_development(self) -> None:
        """ONLY 'development' returns True."""
        from mcp_server_langgraph.core.environment import is_developer_mode

        mock_settings = MagicMock(environment="development")
        assert is_developer_mode(settings=mock_settings) is True

    def test_is_developer_mode_returns_true_for_development_case_insensitive(
        self,
    ) -> None:
        """Case-insensitive match for 'development'."""
        from mcp_server_langgraph.core.environment import is_developer_mode

        mock_settings = MagicMock(environment="DEVELOPMENT")
        assert is_developer_mode(settings=mock_settings) is True

        mock_settings = MagicMock(environment="Development")
        assert is_developer_mode(settings=mock_settings) is True

    @pytest.mark.parametrize(
        "env",
        [
            "test",
            "production",
            "staging",
            "prod",
            "stg",
            "unknown",
            "",
            "dev",  # Close but not exact
            "development ",  # Trailing space
            " development",  # Leading space
        ],
    )
    def test_is_developer_mode_returns_false_for_non_development(self, env: str) -> None:
        """All non-development environments are fail-closed."""
        from mcp_server_langgraph.core.environment import is_developer_mode

        mock_settings = MagicMock(environment=env)
        assert is_developer_mode(settings=mock_settings) is False

    def test_is_developer_mode_uses_get_settings_when_no_settings_passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify get_settings() is called when settings not passed."""
        from mcp_server_langgraph.core import environment

        called = []

        def mock_get_settings():
            called.append(True)
            return MagicMock(environment="development")

        monkeypatch.setattr("mcp_server_langgraph.api.deps.get_settings", mock_get_settings)

        # Call without passing settings
        result = environment.is_developer_mode()

        assert len(called) == 1
        assert result is True

    def test_is_developer_mode_accepts_explicit_settings(self) -> None:
        """Explicit settings parameter overrides any default."""
        from mcp_server_langgraph.core.environment import is_developer_mode

        mock_settings = MagicMock(environment="production")
        result = is_developer_mode(settings=mock_settings)

        assert result is False

    def test_is_developer_mode_with_none_environment(self) -> None:
        """Handle edge case where environment is None."""
        from mcp_server_langgraph.core.environment import is_developer_mode

        mock_settings = MagicMock(environment=None)

        # Should not raise, should return False
        result = is_developer_mode(settings=mock_settings)
        assert result is False

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
