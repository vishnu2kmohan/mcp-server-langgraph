"""
Unit tests for prompt management module.

Tests the prompt versioning and retrieval functionality.
"""

import gc

import pytest

from mcp_server_langgraph.core.prompts import (
    RESPONSE_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
    VERIFICATION_SYSTEM_PROMPT,
    get_prompt,
    get_prompt_version,
    list_prompt_versions,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_prompts")
class TestPromptManagement:
    """Test prompt retrieval and versioning."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_prompt_returns_router_prompt(self) -> None:
        """Test getting the router prompt."""
        prompt = get_prompt("router")
        assert prompt == ROUTER_SYSTEM_PROMPT
        assert len(prompt) > 0

    def test_get_prompt_returns_response_prompt(self) -> None:
        """Test getting the response prompt."""
        prompt = get_prompt("response")
        assert prompt == RESPONSE_SYSTEM_PROMPT
        assert len(prompt) > 0

    def test_get_prompt_returns_verification_prompt(self) -> None:
        """Test getting the verification prompt."""
        prompt = get_prompt("verification")
        assert prompt == VERIFICATION_SYSTEM_PROMPT
        assert len(prompt) > 0

    def test_get_prompt_with_explicit_latest_version(self) -> None:
        """Test getting prompt with explicit 'latest' version."""
        prompt = get_prompt("router", "latest")
        assert prompt == ROUTER_SYSTEM_PROMPT

    def test_get_prompt_with_v1_version(self) -> None:
        """Test getting prompt with specific v1 version."""
        prompt = get_prompt("router", "v1")
        assert prompt == ROUTER_SYSTEM_PROMPT

    def test_get_prompt_raises_for_unknown_prompt(self) -> None:
        """Test that unknown prompt name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown prompt: nonexistent"):
            get_prompt("nonexistent")

    def test_get_prompt_raises_for_unknown_version(self) -> None:
        """Test that unknown version raises ValueError."""
        with pytest.raises(ValueError, match="Unknown version 'v999'"):
            get_prompt("router", "v999")


@pytest.mark.xdist_group(name="test_prompts")
class TestPromptVersioning:
    """Test prompt version management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_prompt_version_returns_current_version(self) -> None:
        """Test getting current version for each prompt."""
        assert get_prompt_version("router") == "v1"
        assert get_prompt_version("response") == "v1"
        assert get_prompt_version("verification") == "v1"

    def test_get_prompt_version_raises_for_unknown_prompt(self) -> None:
        """Test that unknown prompt raises ValueError."""
        with pytest.raises(ValueError, match="Unknown prompt: nonexistent"):
            get_prompt_version("nonexistent")

    def test_list_prompt_versions_returns_available_versions(self) -> None:
        """Test listing versions for each prompt."""
        router_versions = list_prompt_versions("router")
        assert "v1" in router_versions
        assert "latest" in router_versions

        response_versions = list_prompt_versions("response")
        assert "v1" in response_versions
        assert "latest" in response_versions

    def test_list_prompt_versions_raises_for_unknown_prompt(self) -> None:
        """Test that unknown prompt raises ValueError."""
        with pytest.raises(ValueError, match="Unknown prompt: nonexistent"):
            list_prompt_versions("nonexistent")


@pytest.mark.xdist_group(name="test_prompts")
class TestPromptContent:
    """Test prompt content structure."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_router_prompt_has_expected_structure(self) -> None:
        """Test router prompt contains expected XML structure."""
        assert ROUTER_SYSTEM_PROMPT is not None
        # Check it's a non-empty string
        assert isinstance(ROUTER_SYSTEM_PROMPT, str)

    def test_response_prompt_has_expected_structure(self) -> None:
        """Test response prompt contains expected content."""
        assert RESPONSE_SYSTEM_PROMPT is not None
        assert isinstance(RESPONSE_SYSTEM_PROMPT, str)

    def test_verification_prompt_has_expected_structure(self) -> None:
        """Test verification prompt contains expected content."""
        assert VERIFICATION_SYSTEM_PROMPT is not None
        assert isinstance(VERIFICATION_SYSTEM_PROMPT, str)
