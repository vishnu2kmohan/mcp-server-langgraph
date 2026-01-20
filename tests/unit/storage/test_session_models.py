"""
Storage Session Models Tests

TDD tests for storage/session/models.py to ensure SessionConfig
uses settings from environment, not hardcoded values.

Following 12-Factor App Principle III: Store config in environment, not code.
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_storage_session_models")
@pytest.mark.unit
class TestSessionConfigDefaults:
    """Tests for SessionConfig model using settings defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_config_uses_settings_model_name(self) -> None:
        """Verify SessionConfig uses model_name from settings, not hardcoded."""
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.storage.session.models import SessionConfig

        config = SessionConfig()

        # Should use the configured default, not hardcoded "gpt-4o-mini"
        assert config.model == settings.model_name
        # The settings default is gemini-2.5-flash (or whatever env configures)
        assert config.model != "gpt-4o-mini", "Should not use hardcoded default"

    def test_session_config_uses_settings_max_tokens(self) -> None:
        """Verify SessionConfig uses max_tokens from settings, not hardcoded."""
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.storage.session.models import SessionConfig

        config = SessionConfig()

        # Should use the configured default, not hardcoded 1000
        assert config.max_tokens == settings.model_max_tokens
        # Default in settings is 8192, not 1000
        assert config.max_tokens != 1000, "Should not use hardcoded default"

    def test_session_config_respects_explicit_values(self) -> None:
        """Verify SessionConfig respects explicitly provided values."""
        from mcp_server_langgraph.storage.session.models import SessionConfig

        config = SessionConfig(
            model="claude-3-opus",
            temperature=0.5,
            max_tokens=4096,
        )

        assert config.model == "claude-3-opus"
        assert config.temperature == 0.5
        assert config.max_tokens == 4096

    def test_session_config_with_custom_settings(self) -> None:
        """Verify SessionConfig uses custom settings values."""
        from mcp_server_langgraph.storage.session.models import SessionConfig

        with patch("mcp_server_langgraph.storage.session.models.settings") as mock_settings:
            mock_settings.model_name = "custom-model-v2"
            mock_settings.model_max_tokens = 16384

            config = SessionConfig()

            assert config.model == "custom-model-v2"
            assert config.max_tokens == 16384

    def test_session_config_temperature_default(self) -> None:
        """Verify SessionConfig temperature has valid default."""
        from mcp_server_langgraph.storage.session.models import SessionConfig

        config = SessionConfig()

        assert config.temperature == 0.7
        assert 0.0 <= config.temperature <= 2.0


@pytest.mark.xdist_group(name="test_storage_session_config_execution_mode")
@pytest.mark.unit
class TestSessionConfigExecutionMode:
    """Tests for SessionConfig execution_mode field for bypass mode persistence."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_session_config_execution_mode_defaults_to_default(self) -> None:
        """GIVEN a new SessionConfig
        WHEN no execution_mode is provided
        THEN it should default to 'default'.
        """
        from mcp_server_langgraph.storage.models import SessionConfig

        config = SessionConfig()

        assert config.execution_mode == "default"

    def test_session_config_execution_mode_accepts_valid_modes(self) -> None:
        """GIVEN valid execution mode values
        WHEN creating SessionConfig
        THEN all valid modes should be accepted.
        """
        from mcp_server_langgraph.storage.models import SessionConfig

        valid_modes = ["default", "plan", "auto_accept", "bypass"]

        for mode in valid_modes:
            config = SessionConfig(execution_mode=mode)
            assert config.execution_mode == mode

    def test_session_config_execution_mode_rejects_invalid_modes(self) -> None:
        """GIVEN an invalid execution mode value
        WHEN creating SessionConfig
        THEN it should raise a ValidationError.
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.storage.models import SessionConfig

        with pytest.raises(ValidationError) as exc_info:
            SessionConfig(execution_mode="invalid_mode")

        # Verify the error mentions the field
        error_str = str(exc_info.value)
        assert "execution_mode" in error_str

    def test_session_config_execution_mode_serializes_correctly(self) -> None:
        """GIVEN a SessionConfig with execution_mode
        WHEN serialized to dict/JSON
        THEN execution_mode should be included.
        """
        from mcp_server_langgraph.storage.models import SessionConfig

        config = SessionConfig(execution_mode="bypass")
        data = config.model_dump()

        assert "execution_mode" in data
        assert data["execution_mode"] == "bypass"

    def test_session_preserves_execution_mode_in_config(self) -> None:
        """GIVEN a Session with execution_mode in config
        WHEN serialized and deserialized
        THEN execution_mode should be preserved.
        """
        from mcp_server_langgraph.storage.models import Session, SessionConfig

        session = Session(
            session_id="session-test-123",
            name="Test Session",
            config=SessionConfig(execution_mode="plan"),
        )

        # Serialize and deserialize
        data = session.model_dump()
        restored = Session.model_validate(data)

        assert restored.config.execution_mode == "plan"


@pytest.mark.xdist_group(name="test_storage_unified_models")
@pytest.mark.unit
class TestUnifiedSessionConfigDefaults:
    """Tests for unified storage/models.py SessionConfig using settings defaults."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unified_session_config_uses_settings_model_name(self) -> None:
        """Verify unified SessionConfig uses model_name from settings."""
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.storage.models import SessionConfig

        config = SessionConfig()

        assert config.model == settings.model_name
        assert config.model != "gpt-4o-mini", "Should not use hardcoded default"

    def test_unified_session_config_uses_settings_max_tokens(self) -> None:
        """Verify unified SessionConfig uses max_tokens from settings."""
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.storage.models import SessionConfig

        config = SessionConfig()

        assert config.max_tokens == settings.model_max_tokens
        assert config.max_tokens != 1000, "Should not use hardcoded default"

    def test_unified_session_config_with_custom_settings(self) -> None:
        """Verify unified SessionConfig uses custom settings values."""
        from mcp_server_langgraph.storage.models import SessionConfig

        with patch("mcp_server_langgraph.storage.models.settings") as mock_settings:
            mock_settings.model_name = "test-model-xyz"
            mock_settings.model_max_tokens = 32000

            config = SessionConfig()

            assert config.model == "test-model-xyz"
            assert config.max_tokens == 32000


@pytest.mark.xdist_group(name="test_ai_explanation_models")
@pytest.mark.unit
class TestAIExplanationModelDefault:
    """Tests for AIExplanation model using settings for model_used."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ai_explanation_uses_settings_model_name(self) -> None:
        """Verify AIExplanation uses model_name from settings for model_used."""
        from mcp_server_langgraph.core.config import settings
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="Test uncertainty",
            what_could_go_wrong="Test risk",
        )

        assert explanation.model_used == settings.model_name
        assert explanation.model_used != "gpt-4o-mini", "Should not use hardcoded default"

    def test_ai_explanation_respects_explicit_model(self) -> None:
        """Verify AIExplanation respects explicitly provided model_used."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        explanation = AIExplanation(
            why_uncertain="Test uncertainty",
            what_could_go_wrong="Test risk",
            model_used="custom-explanation-model",
        )

        assert explanation.model_used == "custom-explanation-model"

    def test_ai_explanation_with_custom_settings(self) -> None:
        """Verify AIExplanation uses custom settings for default model."""
        from mcp_server_langgraph.core.interrupts.ai_explanation import AIExplanation

        with patch("mcp_server_langgraph.core.interrupts.ai_explanation.settings") as mock_settings:
            mock_settings.model_name = "gemini-ultra-pro"

            explanation = AIExplanation(
                why_uncertain="Test uncertainty",
                what_could_go_wrong="Test risk",
            )

            assert explanation.model_used == "gemini-ultra-pro"
