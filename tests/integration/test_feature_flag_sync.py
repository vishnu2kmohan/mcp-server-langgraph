"""
Feature Flag Sync Validation Tests.

TDD tests to ensure feature flags are consistent across all layers:
- Backend Python (feature_flags.py)
- API response format (get_ui_features_for_role)
- Frontend TypeScript (api.ts)
- MSW mock handlers (handlers.ts)
- docker-compose.test.yml environment variables
- .env.test environment variables

Following TDD principles:
- RED: Tests will fail if layers are out of sync
- GREEN: Tests will pass when all layers are aligned
- REFACTOR: Provides confidence for safe feature flag changes
"""

import gc
import os
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.helpers.path_helpers import get_repo_root

pytestmark = pytest.mark.integration

PROJECT_ROOT = get_repo_root()


def extract_ff_env_vars_from_compose(compose_path: Path) -> dict[str, str]:
    """Extract FF_* environment variables from docker-compose.test.yml."""
    if not compose_path.exists():
        return {}

    with open(compose_path) as f:
        config = yaml.safe_load(f)

    ff_vars: dict[str, str] = {}

    for service_name, service_config in config.get("services", {}).items():
        env_list = service_config.get("environment", [])
        if isinstance(env_list, list):
            for env_var in env_list:
                if isinstance(env_var, str) and env_var.startswith("FF_"):
                    if "=" in env_var:
                        key, value = env_var.split("=", 1)
                        ff_vars[key] = value

    return ff_vars


def extract_ff_env_vars_from_dotenv(dotenv_path: Path) -> dict[str, str]:
    """Extract FF_* environment variables from .env.test file."""
    if not dotenv_path.exists():
        return {}

    ff_vars: dict[str, str] = {}

    with open(dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("FF_") and "=" in line:
                key, value = line.split("=", 1)
                # Strip inline comments (e.g., "true  # Comment")
                if "#" in value:
                    value = value.split("#", 1)[0]
                ff_vars[key] = value.strip()

    return ff_vars


def get_feature_flag_fields() -> dict[str, Any]:
    """Get all feature flag field names from the FeatureFlags class."""
    from src.mcp_server_langgraph.core.feature_flags import FeatureFlags

    fields = {}
    for field_name, field_info in FeatureFlags.model_fields.items():
        fields[field_name] = {
            "default": field_info.default,
            "description": field_info.description,
        }

    return fields


def get_ui_exposed_flags() -> list[str]:
    """Get the list of flags exposed via get_ui_features_for_role API."""
    from src.mcp_server_langgraph.core.feature_flags import FeatureFlags

    flags = FeatureFlags()
    ui_features = flags.get_ui_features_for_role("admin")
    return list(ui_features.keys())


@pytest.mark.integration
@pytest.mark.xdist_group(name="feature_flag_sync")
class TestFeatureFlagSync:
    """Tests for feature flag synchronization across layers."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_canvas_flags_in_backend(self):
        """
        Test that all canvas phase flags are defined in the backend.

        Canvas phases:
        - Phase 1: canvas_hybrid_shell
        - Phase 2: canvas_editable
        - Phase 4: canvas_agents, canvas_ai_palette
        - Phase 5: canvas_compliance
        - Phase 6: canvas_help
        """
        fields = get_feature_flag_fields()

        expected_canvas_flags = [
            "canvas_hybrid_shell",
            "canvas_editable",
            "canvas_agents",
            "canvas_ai_palette",
            "canvas_compliance",
            "canvas_help",
        ]

        missing = [flag for flag in expected_canvas_flags if flag not in fields]

        assert not missing, (
            f"Missing canvas flags in backend FeatureFlags class:\n"
            f"  {missing}\n\n"
            f"Add these to src/mcp_server_langgraph/core/feature_flags.py"
        )

        print(f"✅ All {len(expected_canvas_flags)} canvas flags present in backend")

    def test_all_canvas_flags_exposed_to_ui(self):
        """
        Test that all canvas phase flags are exposed via get_ui_features_for_role().

        The UI needs access to these flags for conditional rendering.
        """
        ui_flags = get_ui_exposed_flags()

        expected_canvas_flags = [
            "canvas_hybrid_shell",
            "canvas_editable",
            "canvas_agents",
            "canvas_ai_palette",
            "canvas_compliance",
            "canvas_help",
        ]

        missing = [flag for flag in expected_canvas_flags if flag not in ui_flags]

        assert not missing, (
            f"Canvas flags not exposed via get_ui_features_for_role():\n"
            f"  {missing}\n\n"
            f"Add these to the return dict in get_ui_features_for_role() method"
        )

        print(f"✅ All {len(expected_canvas_flags)} canvas flags exposed to UI")

    def test_docker_compose_ff_vars_match_backend_fields(self):
        """
        Test that all FF_* env vars in docker-compose.test.yml map to valid backend fields.

        This catches typos and stale environment variables.
        """
        compose_path = PROJECT_ROOT / "docker-compose.test.yml"

        if not compose_path.exists():
            pytest.skip(f"Compose file not found: {compose_path}")

        ff_vars = extract_ff_env_vars_from_compose(compose_path)
        backend_fields = get_feature_flag_fields()

        invalid_vars = []
        for env_var in ff_vars.keys():
            # Convert FF_CANVAS_HYBRID_SHELL -> canvas_hybrid_shell
            field_name = env_var[3:].lower()  # Remove FF_ prefix and lowercase

            if field_name not in backend_fields:
                invalid_vars.append(f"{env_var} -> {field_name}")

        assert not invalid_vars, (
            f"Invalid FF_* env vars in docker-compose.test.yml (no matching backend field):\n"
            f"  {invalid_vars}\n\n"
            f"Either add the field to FeatureFlags class or remove the env var"
        )

        print(f"✅ All {len(ff_vars)} FF_* vars in docker-compose.test.yml are valid")

    def test_dotenv_ff_vars_match_backend_fields(self):
        """
        Test that all FF_* env vars in .env.test map to valid backend fields.
        """
        dotenv_path = PROJECT_ROOT / ".env.test"

        if not dotenv_path.exists():
            pytest.skip(f".env.test not found: {dotenv_path}")

        ff_vars = extract_ff_env_vars_from_dotenv(dotenv_path)
        backend_fields = get_feature_flag_fields()

        invalid_vars = []
        for env_var in ff_vars.keys():
            # Convert FF_CANVAS_HYBRID_SHELL -> canvas_hybrid_shell
            field_name = env_var[3:].lower()

            if field_name not in backend_fields:
                invalid_vars.append(f"{env_var} -> {field_name}")

        assert not invalid_vars, (
            f"Invalid FF_* env vars in .env.test (no matching backend field):\n"
            f"  {invalid_vars}\n\n"
            f"Either add the field to FeatureFlags class or remove the env var"
        )

        print(f"✅ All {len(ff_vars)} FF_* vars in .env.test are valid")

    def test_canvas_flags_enabled_in_test_environment(self):
        """
        Test that all canvas phase flags are enabled in test environment.

        Canvas flags default to False in production but should be True in tests
        to enable testing of the hybrid canvas UI.
        """
        compose_path = PROJECT_ROOT / "docker-compose.test.yml"
        dotenv_path = PROJECT_ROOT / ".env.test"

        compose_vars = extract_ff_env_vars_from_compose(compose_path)
        dotenv_vars = extract_ff_env_vars_from_dotenv(dotenv_path)

        # Merge: compose vars override dotenv vars
        all_vars = {**dotenv_vars, **compose_vars}

        expected_canvas_flags = [
            "FF_CANVAS_HYBRID_SHELL",
            "FF_CANVAS_EDITABLE",
            "FF_CANVAS_AGENTS",
            "FF_CANVAS_AI_PALETTE",
            "FF_CANVAS_COMPLIANCE",
            "FF_CANVAS_HELP",
        ]

        missing_or_disabled = []
        for flag in expected_canvas_flags:
            if flag not in all_vars:
                missing_or_disabled.append(f"{flag}: missing")
            elif all_vars[flag].lower() != "true":
                missing_or_disabled.append(f"{flag}: {all_vars[flag]} (should be 'true')")

        assert not missing_or_disabled, (
            f"Canvas flags not enabled in test environment:\n"
            f"  {missing_or_disabled}\n\n"
            f"Add these to docker-compose.test.yml or .env.test with value 'true'"
        )

        print(f"✅ All {len(expected_canvas_flags)} canvas flags enabled in test environment")

    def test_experimental_flags_enabled_in_test_environment(self):
        """
        Test that experimental feature flags are enabled in test environment.

        Experimental features should be enabled in tests to ensure full coverage
        of the codebase, even if they're disabled in production.
        """
        compose_path = PROJECT_ROOT / "docker-compose.test.yml"
        dotenv_path = PROJECT_ROOT / ".env.test"

        compose_vars = extract_ff_env_vars_from_compose(compose_path)
        dotenv_vars = extract_ff_env_vars_from_dotenv(dotenv_path)

        all_vars = {**dotenv_vars, **compose_vars}

        # Experimental flags that should be enabled for comprehensive testing
        expected_experimental_flags = [
            "FF_ENABLE_EXPERIMENTAL_FEATURES",
            "FF_ENABLE_MULTI_AGENT_COLLABORATION",
            "FF_ENABLE_TOOL_REFLECTION",
        ]

        missing_or_disabled = []
        for flag in expected_experimental_flags:
            if flag not in all_vars:
                missing_or_disabled.append(f"{flag}: missing")
            elif all_vars[flag].lower() != "true":
                missing_or_disabled.append(f"{flag}: {all_vars[flag]} (should be 'true')")

        assert not missing_or_disabled, (
            f"Experimental flags not enabled in test environment:\n"
            f"  {missing_or_disabled}\n\n"
            f"Add these to .env.test with value 'true' for comprehensive test coverage"
        )

        print(f"✅ All {len(expected_experimental_flags)} experimental flags enabled in test environment")

    def test_ui_enhancement_flags_enabled_in_test_environment(self):
        """
        Test that UI enhancement feature flags are enabled in test environment.

        UI enhancement features should be enabled in tests to validate
        the full user experience.
        """
        compose_path = PROJECT_ROOT / "docker-compose.test.yml"
        dotenv_path = PROJECT_ROOT / ".env.test"

        compose_vars = extract_ff_env_vars_from_compose(compose_path)
        dotenv_vars = extract_ff_env_vars_from_dotenv(dotenv_path)

        all_vars = {**dotenv_vars, **compose_vars}

        # UI enhancement flags for comprehensive testing
        expected_ui_flags = [
            "FF_ENABLE_INTERACTIVE_ARTIFACTS",
            "FF_ENABLE_URL_CONTENT_FETCH",
            "FF_ENABLE_SLASH_COMMANDS",
            "FF_ENABLE_STYLE_PRESETS",
            "FF_ENABLE_COMMAND_PALETTE",
            "FF_ENABLE_KEYBOARD_SHORTCUTS",
        ]

        missing_or_disabled = []
        for flag in expected_ui_flags:
            if flag not in all_vars:
                missing_or_disabled.append(f"{flag}: missing")
            elif all_vars[flag].lower() != "true":
                missing_or_disabled.append(f"{flag}: {all_vars[flag]} (should be 'true')")

        assert not missing_or_disabled, (
            f"UI enhancement flags not enabled in test environment:\n"
            f"  {missing_or_disabled}\n\n"
            f"Add these to .env.test with value 'true' for comprehensive UI testing"
        )

        print(f"✅ All {len(expected_ui_flags)} UI enhancement flags enabled in test environment")


@pytest.mark.integration
@pytest.mark.xdist_group(name="feature_flag_sync")
class TestFeatureFlagNamingConvention:
    """Tests for feature flag naming convention consistency."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ui_flags_use_short_names(self):
        """
        Test that get_ui_features_for_role uses short names (not enable_* prefixes).

        The API returns short names like 'workflows' not 'enable_workflows_feature'.
        This test verifies the naming convention is followed.
        """
        ui_flags = get_ui_exposed_flags()

        # These should NOT be in the UI flags (backend names with enable_ prefix)
        invalid_prefixes = ["enable_"]

        invalid_flags = [
            flag for flag in ui_flags if any(flag.startswith(prefix) for prefix in invalid_prefixes)
        ]

        # Exception: Some flags like enable_* that are intentionally exposed
        # (none currently, but this allows for future exceptions)
        allowed_exceptions: list[str] = []

        actual_invalid = [f for f in invalid_flags if f not in allowed_exceptions]

        assert not actual_invalid, (
            f"UI flags should use SHORT names, not backend field names:\n"
            f"  Invalid: {actual_invalid}\n\n"
            f"The API should return 'workflows' not 'enable_workflows_feature'.\n"
            f"Update get_ui_features_for_role() to use short names."
        )

        print(f"✅ All {len(ui_flags)} UI flags use correct short names")

    def test_ff_env_var_format(self):
        """
        Test that FF_* environment variables follow correct format.

        Format: FF_<FIELD_NAME_UPPER_SNAKE_CASE>
        Example: FF_CANVAS_HYBRID_SHELL, FF_ENABLE_OPENFGA
        """
        compose_path = PROJECT_ROOT / "docker-compose.test.yml"
        dotenv_path = PROJECT_ROOT / ".env.test"

        compose_vars = extract_ff_env_vars_from_compose(compose_path)
        dotenv_vars = extract_ff_env_vars_from_dotenv(dotenv_path)

        all_vars = list(set(compose_vars.keys()) | set(dotenv_vars.keys()))

        # Check format: FF_ prefix, uppercase, underscores only
        invalid_format = []
        for var in all_vars:
            if not re.match(r"^FF_[A-Z][A-Z0-9_]*$", var):
                invalid_format.append(var)

        assert not invalid_format, (
            f"FF_* env vars have invalid format:\n"
            f"  {invalid_format}\n\n"
            f"Expected format: FF_<UPPERCASE_SNAKE_CASE>\n"
            f"Examples: FF_CANVAS_HYBRID_SHELL, FF_ENABLE_OPENFGA"
        )

        print(f"✅ All {len(all_vars)} FF_* env vars have correct format")


@pytest.mark.integration
@pytest.mark.xdist_group(name="feature_flag_sync")
class TestADR0072FeatureFlags:
    """Tests for ADR-0072 Anthropic Best Practices feature flags.

    These tests verify that:
    1. All ADR-0072 flags are defined in the backend
    2. All ADR-0072 flags are enabled in test environment
    3. Feature-gated modules properly enforce their flags
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_adr0072_flags_defined_in_backend(self):
        """
        Test that all ADR-0072 feature flags are defined in FeatureFlags class.

        ADR-0072 flags enable Anthropic engineering best practices:
        - Tool examples, think tool, defer loading
        - Skills system with marketplace
        - PII tokenization
        - Programmatic tools, multi-agent orchestration, agentic memory
        """
        fields = get_feature_flag_fields()

        expected_adr0072_flags = [
            "enable_tool_examples",
            "enable_think_tool",
            "enable_defer_loading",
            "enable_skills_system",
            "enable_skills_marketplace",
            "enable_pii_tokenization",
            "enable_programmatic_tools",
            "enable_multi_agent_orchestration",
            "enable_agentic_memory",
        ]

        missing = [flag for flag in expected_adr0072_flags if flag not in fields]

        assert not missing, (
            f"Missing ADR-0072 flags in backend FeatureFlags class:\n"
            f"  {missing}\n\n"
            f"Add these to src/mcp_server_langgraph/core/feature_flags.py\n"
            f"See: docs-internal/ADR-0072-ANTHROPIC-BEST-PRACTICES.md"
        )

        print(f"✅ All {len(expected_adr0072_flags)} ADR-0072 flags present in backend")

    def test_adr0072_flags_enabled_in_test_environment(self):
        """
        Test that all ADR-0072 feature flags are enabled in test environment.

        ADR-0072 flags should be enabled in docker-compose.test.yml for
        comprehensive integration and e2e testing.
        """
        compose_path = PROJECT_ROOT / "docker-compose.test.yml"
        dotenv_path = PROJECT_ROOT / ".env.test"

        compose_vars = extract_ff_env_vars_from_compose(compose_path)
        dotenv_vars = extract_ff_env_vars_from_dotenv(dotenv_path)

        all_vars = {**dotenv_vars, **compose_vars}

        expected_adr0072_flags = [
            "FF_ENABLE_TOOL_EXAMPLES",
            "FF_ENABLE_THINK_TOOL",
            "FF_ENABLE_DEFER_LOADING",
            "FF_ENABLE_SKILLS_SYSTEM",
            "FF_ENABLE_SKILLS_MARKETPLACE",
            "FF_ENABLE_PII_TOKENIZATION",
            "FF_ENABLE_PROGRAMMATIC_TOOLS",
            "FF_ENABLE_MULTI_AGENT_ORCHESTRATION",
            "FF_ENABLE_AGENTIC_MEMORY",
        ]

        missing_or_disabled = []
        for flag in expected_adr0072_flags:
            if flag not in all_vars:
                missing_or_disabled.append(f"{flag}: missing")
            elif all_vars[flag].lower() != "true":
                missing_or_disabled.append(f"{flag}: {all_vars[flag]} (should be 'true')")

        assert not missing_or_disabled, (
            f"ADR-0072 flags not enabled in test environment:\n"
            f"  {missing_or_disabled}\n\n"
            f"Add these to docker-compose.test.yml with value 'true'\n"
            f"See: docs-internal/ADR-0072-ANTHROPIC-BEST-PRACTICES.md"
        )

        print(f"✅ All {len(expected_adr0072_flags)} ADR-0072 flags enabled in test environment")

    def test_require_feature_raises_when_disabled(self):
        """
        Test that require_feature() raises FeatureDisabledError when flag is disabled.

        This validates the guard mechanism used by ADR-0072 modules.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # Create a flags instance with a specific flag disabled
        with patch.dict(os.environ, {"FF_ENABLE_MULTI_AGENT_ORCHESTRATION": "false"}):
            flags = FeatureFlags()

            with pytest.raises(FeatureDisabledError) as exc_info:
                flags.require_feature(
                    "enable_multi_agent_orchestration",
                    "Multi-Agent Orchestration",
                )

            assert "Multi-Agent Orchestration" in str(exc_info.value)
            assert "FF_ENABLE_MULTI_AGENT_ORCHESTRATION" in str(exc_info.value)

        print("✅ require_feature() properly raises FeatureDisabledError")

    def test_require_feature_passes_when_enabled(self):
        """
        Test that require_feature() passes silently when flag is enabled.
        """
        from unittest.mock import patch

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(os.environ, {"FF_ENABLE_MULTI_AGENT_ORCHESTRATION": "true"}):
            flags = FeatureFlags()

            # Should not raise
            flags.require_feature(
                "enable_multi_agent_orchestration",
                "Multi-Agent Orchestration",
            )

        print("✅ require_feature() passes when flag is enabled")


@pytest.mark.integration
@pytest.mark.xdist_group(name="feature_flag_sync")
class TestADR0072ModuleIntegration:
    """Tests for ADR-0072 module integration with feature flags.

    These tests verify that experimental modules properly check their
    feature flags before executing critical operations.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_orchestrator_requires_multi_agent_flag(self):
        """
        Test that Orchestrator.decompose_task() checks multi-agent flag.

        The @feature_gated decorator uses feature_flags from core module.
        We test by unsetting FF_TEST_MODE env var and disabling the feature flag.
        """
        import os
        from unittest.mock import patch

        from mcp_server_langgraph.agents.orchestrator import Orchestrator
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import feature_flags

        orchestrator = Orchestrator()

        # Save original flag value
        original_flag = feature_flags.enable_multi_agent_orchestration

        try:
            # Disable the feature flag
            feature_flags.enable_multi_agent_orchestration = False

            # Unset FF_TEST_MODE to disable test mode bypass
            env_without_test_mode = {k: v for k, v in os.environ.items() if k != "FF_TEST_MODE"}
            with patch.dict(os.environ, env_without_test_mode, clear=True):
                with pytest.raises(FeatureDisabledError) as exc_info:
                    orchestrator.decompose_task("Test task")

                assert "Multi-Agent Orchestration" in str(exc_info.value)
        finally:
            # Restore original flag value
            feature_flags.enable_multi_agent_orchestration = original_flag

        print("✅ Orchestrator.decompose_task() enforces feature flag")

    @pytest.mark.asyncio
    async def test_subagent_requires_multi_agent_flag(self):
        """
        Test that Subagent.execute() checks multi-agent flag.

        The @feature_gated decorator uses feature_flags from core module.
        We test by unsetting FF_TEST_MODE env var and disabling the feature flag.
        """
        import os
        from unittest.mock import patch

        from mcp_server_langgraph.agents.subagent import Subagent
        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import feature_flags

        subagent = Subagent(task_id="test-1", instructions="Test instructions")

        # Save original flag value
        original_flag = feature_flags.enable_multi_agent_orchestration

        try:
            # Disable the feature flag
            feature_flags.enable_multi_agent_orchestration = False

            # Unset FF_TEST_MODE to disable test mode bypass
            env_without_test_mode = {k: v for k, v in os.environ.items() if k != "FF_TEST_MODE"}
            with patch.dict(os.environ, env_without_test_mode, clear=True):
                with pytest.raises(FeatureDisabledError) as exc_info:
                    await subagent.execute()

                assert "Multi-Agent Orchestration" in str(exc_info.value)
        finally:
            # Restore original flag value
            feature_flags.enable_multi_agent_orchestration = original_flag

        print("✅ Subagent.execute() enforces feature flag")

    def test_notes_manager_requires_agentic_memory_flag(self):
        """
        Test that NotesManager.add_note() checks agentic memory flag.

        The @feature_gated decorator uses feature_flags from core module.
        We test by unsetting FF_TEST_MODE env var and disabling the feature flag.
        """
        import os
        from unittest.mock import patch

        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.memory.notes import NotesManager

        manager = NotesManager()

        # Save original flag value
        original_flag = feature_flags.enable_agentic_memory

        try:
            # Disable the feature flag
            feature_flags.enable_agentic_memory = False

            # Unset FF_TEST_MODE to disable test mode bypass
            env_without_test_mode = {k: v for k, v in os.environ.items() if k != "FF_TEST_MODE"}
            with patch.dict(os.environ, env_without_test_mode, clear=True):
                with pytest.raises(FeatureDisabledError) as exc_info:
                    manager.add_note(content="Test note")

                assert "Agentic Memory" in str(exc_info.value)
        finally:
            # Restore original flag value
            feature_flags.enable_agentic_memory = original_flag

        print("✅ NotesManager.add_note() enforces feature flag")

    def test_checkpoint_manager_requires_agentic_memory_flag(self):
        """
        Test that CheckpointManager.create_checkpoint() checks agentic memory flag.

        The @feature_gated decorator uses feature_flags from core module.
        We test by unsetting FF_TEST_MODE env var and disabling the feature flag.
        """
        import os
        from unittest.mock import patch

        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.memory.checkpoints import CheckpointManager

        manager = CheckpointManager()

        # Save original flag value
        original_flag = feature_flags.enable_agentic_memory

        try:
            # Disable the feature flag
            feature_flags.enable_agentic_memory = False

            # Unset FF_TEST_MODE to disable test mode bypass
            env_without_test_mode = {k: v for k, v in os.environ.items() if k != "FF_TEST_MODE"}
            with patch.dict(os.environ, env_without_test_mode, clear=True):
                with pytest.raises(FeatureDisabledError) as exc_info:
                    manager.create_checkpoint(phase="test", summary="Test summary")

                assert "Agentic Memory" in str(exc_info.value)
        finally:
            # Restore original flag value
            feature_flags.enable_agentic_memory = original_flag

        print("✅ CheckpointManager.create_checkpoint() enforces feature flag")

    @pytest.mark.asyncio
    async def test_tool_bridge_requires_programmatic_tools_flag(self):
        """
        Test that ToolBridge.call_tool() checks programmatic tools flag.

        The @feature_gated decorator uses feature_flags from core module.
        We test by unsetting FF_TEST_MODE env var and disabling the feature flag.
        """
        import os
        from unittest.mock import patch

        from mcp_server_langgraph.core.exceptions import FeatureDisabledError
        from mcp_server_langgraph.core.feature_flags import feature_flags
        from mcp_server_langgraph.execution.tool_bridge import ToolBridge

        bridge = ToolBridge()

        # Save original flag value
        original_flag = feature_flags.enable_programmatic_tools

        try:
            # Disable the feature flag
            feature_flags.enable_programmatic_tools = False

            # Unset FF_TEST_MODE to disable test mode bypass
            env_without_test_mode = {k: v for k, v in os.environ.items() if k != "FF_TEST_MODE"}
            with patch.dict(os.environ, env_without_test_mode, clear=True):
                with pytest.raises(FeatureDisabledError) as exc_info:
                    await bridge.call_tool("test_tool", {})

                assert "Programmatic Tools" in str(exc_info.value)
        finally:
            # Restore original flag value
            feature_flags.enable_programmatic_tools = original_flag

        print("✅ ToolBridge.call_tool() enforces feature flag")
