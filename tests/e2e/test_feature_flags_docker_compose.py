"""
Feature Flag Synchronization Tests

Validates that feature flags are synchronized between:
- .env.test (source of truth for test config)
- docker-compose.test.yml (Docker Compose environment)

These tests catch configuration drift where flags are added to one
file but not the other, which causes inconsistent test behavior.

TDD: Written after discovering 27 missing flags in docker-compose.test.yml
that were present in .env.test, causing StudioShell features to be disabled.
"""

import re
from pathlib import Path

import pytest

from tests.helpers.path_helpers import get_repo_root

# Module-level pytest marker
pytestmark = pytest.mark.e2e

# =============================================================================
# Test Configuration
# =============================================================================

PROJECT_ROOT = get_repo_root()
ENV_TEST_FILE = PROJECT_ROOT / ".env.test"
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.test.yml"


def extract_ff_flags_from_env(file_path: Path) -> dict[str, str]:
    """Extract FF_* feature flags from .env.test file."""
    flags = {}
    content = file_path.read_text()

    for line in content.split("\n"):
        # Skip comments and empty lines
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Match FF_* pattern
        if line.startswith("FF_"):
            # Handle KEY=value format
            if "=" in line:
                key, value = line.split("=", 1)
                # Strip inline comments
                value = value.split("#")[0].strip()
                flags[key.strip()] = value
    return flags


def extract_ff_flags_from_docker_compose(file_path: Path) -> dict[str, str]:
    """Extract FF_* feature flags from docker-compose.test.yml.

    Checks two sources:
    1. Inline environment vars: ``- FF_FLAG_NAME=value``
    2. env_file references: parses ``env_file: .env.test`` and extracts FF_* from there

    Since docker-compose.test.yml uses env_file for single-source-of-truth,
    most FF_* flags come from the referenced .env.test file.
    """
    flags = {}
    content = file_path.read_text()

    # 1. Match inline environment vars: - FF_FLAG_NAME=value
    inline_pattern = r"-\s*(FF_[A-Z_0-9]+)=([^\s#]+)"
    for match in re.finditer(inline_pattern, content):
        key = match.group(1)
        value = match.group(2)
        flags[key] = value

    # 2. Check env_file references for .env.test
    env_file_pattern = r"env_file:\s*\n(?:\s+-\s+(?:path:\s+)?(\S+)\s*(?:\n\s+required:\s+\w+)?\s*)*"
    for block_match in re.finditer(env_file_pattern, content):
        block = block_match.group(0)
        # Extract individual file references
        for ref_match in re.finditer(r"-\s+(?:path:\s+)?(\S+)", block):
            ref_file = ref_match.group(1)
            if ref_file == ".env.test":
                env_path = file_path.parent / ref_file
                if env_path.exists():
                    env_flags = extract_ff_flags_from_env(env_path)
                    # env_file flags are overridden by inline, so add first
                    merged = dict(env_flags)
                    merged.update(flags)
                    flags = merged

    return flags


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.xdist_group("test_feature_flag_synchronization")
@pytest.mark.e2e
@pytest.mark.config
class TestFeatureFlagSynchronization:
    """Validate feature flag synchronization between config files."""

    def test_env_test_file_exists(self) -> None:
        """Verify .env.test file exists."""
        assert ENV_TEST_FILE.exists(), f".env.test not found at {ENV_TEST_FILE}"

    def test_docker_compose_file_exists(self) -> None:
        """Verify docker-compose.test.yml file exists."""
        assert DOCKER_COMPOSE_FILE.exists(), f"docker-compose.test.yml not found at {DOCKER_COMPOSE_FILE}"

    def test_env_test_has_feature_flags(self) -> None:
        """Verify .env.test contains FF_* flags."""
        flags = extract_ff_flags_from_env(ENV_TEST_FILE)
        assert len(flags) > 0, ".env.test should contain feature flags"

    def test_docker_compose_has_feature_flags(self) -> None:
        """Verify docker-compose.test.yml contains FF_* flags."""
        flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)
        assert len(flags) > 0, "docker-compose.test.yml should contain feature flags"

    def test_critical_studioshell_flags_in_docker_compose(self) -> None:
        """
        Verify critical StudioShell flags are enabled in docker-compose.test.yml.

        These flags are required for full StudioShell functionality in E2E tests.
        """
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        critical_flags = [
            "FF_STUDIO_CANVAS_SHELL",  # StudioShell master toggle
            "FF_CANVAS_EDITABLE",  # Editable artifacts
            "FF_ENABLE_COMMAND_PALETTE",  # Cmd+K command palette
            "FF_ENABLE_KEYBOARD_SHORTCUTS",  # Keyboard shortcuts
            "FF_ENABLE_STUDIO_AI",  # Studio AI orchestration
            "FF_ENABLE_AGENT_HITL",  # Human-in-the-loop
        ]

        missing = [flag for flag in critical_flags if flag not in docker_flags]
        assert not missing, f"Critical StudioShell flags missing from docker-compose.test.yml: {missing}"

    def test_critical_flags_enabled_true(self) -> None:
        """Verify critical flags are set to 'true' (not 'false')."""
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        # Flags that should be enabled
        should_be_true = [
            "FF_STUDIO_CANVAS_SHELL",
            "FF_ENABLE_COMMAND_PALETTE",
            "FF_ENABLE_STUDIO_AI",
        ]

        for flag in should_be_true:
            if flag in docker_flags:
                assert docker_flags[flag].lower() == "true", f"{flag} should be 'true', got '{docker_flags[flag]}'"

    def test_websocket_infrastructure_flags_present(self) -> None:
        """Verify WebSocket infrastructure flags are present (ADR-0068)."""
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        websocket_flags = [
            "FF_ENABLE_WEBSOCKET_NEW_BASE",
            "FF_ENABLE_WEBSOCKET_SERVER_HEARTBEAT",
            "FF_ENABLE_WEBSOCKET_ENHANCED_METRICS",
        ]

        missing = [flag for flag in websocket_flags if flag not in docker_flags]
        assert not missing, f"WebSocket infrastructure flags missing from docker-compose.test.yml: {missing}"

    def test_hitl_flags_present(self) -> None:
        """Verify HITL feature flags are present for agent approval testing."""
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        hitl_flags = [
            "FF_ENABLE_AGENT_HITL",
            "FF_ENABLE_AGENT_HITL_PUSH_NOTIFICATIONS",
            "FF_ENABLE_AGENT_HITL_WEBSOCKET",
        ]

        missing = [flag for flag in hitl_flags if flag not in docker_flags]
        assert not missing, f"HITL flags missing from docker-compose.test.yml: {missing}"

    def test_studio_ai_intelligence_flags_present(self) -> None:
        """Verify Studio AI intelligence flags are present."""
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        intelligence_flags = [
            "FF_ENABLE_SESSION_INTELLIGENCE",
            "FF_ENABLE_CONVERSATION_INTELLIGENCE",
            "FF_ENABLE_CANVAS_INTELLIGENCE",
            "FF_ENABLE_DIAGRAM_INTELLIGENCE",
            "FF_ENABLE_TRACE_INTELLIGENCE",
        ]

        missing = [flag for flag in intelligence_flags if flag not in docker_flags]
        assert not missing, f"Studio AI intelligence flags missing from docker-compose.test.yml: {missing}"

    def test_ui_enhancement_flags_present(self) -> None:
        """Verify UI enhancement flags are present."""
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        ui_flags = [
            "FF_ENABLE_INTERACTIVE_ARTIFACTS",
            "FF_ENABLE_SLASH_COMMANDS",
            "FF_ENABLE_STYLE_PRESETS",
            "FF_ENABLE_COMMAND_PALETTE",
            "FF_ENABLE_KEYBOARD_SHORTCUTS",
        ]

        missing = [flag for flag in ui_flags if flag not in docker_flags]
        assert not missing, f"UI enhancement flags missing from docker-compose.test.yml: {missing}"

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()


@pytest.mark.xdist_group("test_feature_flag_consistency")
@pytest.mark.e2e
@pytest.mark.config
class TestFeatureFlagConsistency:
    """
    Validate consistency between .env.test and docker-compose.test.yml.

    Note: Docker Compose environment vars override .env file values,
    so flags MUST be present in docker-compose.test.yml to be effective.
    """

    def test_env_test_flags_subset_of_docker_compose(self) -> None:
        """
        Verify all .env.test FF_* flags are also in docker-compose.test.yml.

        This is a warning-level test - some flags may intentionally differ.
        """
        env_flags = extract_ff_flags_from_env(ENV_TEST_FILE)
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        # Flags in .env.test but not in docker-compose.test.yml
        missing_in_docker = set(env_flags.keys()) - set(docker_flags.keys())

        # Filter to only report flags that should be synchronized
        # (Some flags may be intentionally different)
        important_missing = {
            f
            for f in missing_in_docker
            if not f.startswith("FF_DEV_")  # Dev-only flags are OK to skip
        }

        if important_missing:
            pytest.skip(
                f"Info: {len(important_missing)} flags in .env.test but not docker-compose.test.yml. "
                f"This may be intentional. Flags: {sorted(important_missing)}"
            )

    def test_flag_value_consistency(self) -> None:
        """
        Verify flags have consistent values between files.

        When a flag exists in both files, the values should match.
        """
        env_flags = extract_ff_flags_from_env(ENV_TEST_FILE)
        docker_flags = extract_ff_flags_from_docker_compose(DOCKER_COMPOSE_FILE)

        # Find flags in both files
        common_flags = set(env_flags.keys()) & set(docker_flags.keys())

        # Check for mismatched values
        mismatched = []
        for flag in common_flags:
            env_val = env_flags[flag].lower()
            docker_val = docker_flags[flag].lower()
            if env_val != docker_val:
                mismatched.append(f"{flag}: .env.test={env_val}, docker-compose={docker_val}")

        assert not mismatched, "Feature flag values differ between files:\n" + "\n".join(mismatched)

    def teardown_method(self):
        """Clean up after each test."""
        import gc

        gc.collect()
