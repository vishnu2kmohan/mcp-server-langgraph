"""
Tests for feature flag catalog generator.

TDD RED Phase: These tests define the expected behavior of the feature flag
catalog generator before implementation.
"""

import gc
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="feature_flag_catalog")
class TestFeatureFlagExtraction:
    """Test feature flag extraction from FeatureFlags class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_feature_flags_returns_list(self) -> None:
        """Extraction should return a list of FeatureFlagInfo objects."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            FeatureFlagInfo,
        )

        flags = extract_feature_flags()

        assert isinstance(flags, list)
        assert len(flags) > 0
        assert all(isinstance(f, FeatureFlagInfo) for f in flags)

    def test_extract_feature_flags_includes_known_flags(self) -> None:
        """Extraction should include known feature flags."""
        from scripts.validation.generate_feature_flag_catalog import extract_feature_flags

        flags = extract_feature_flags()
        flag_names = {f.name for f in flags}

        # Check for known flags from feature_flags.py
        known_flags = [
            "enable_pydantic_ai_routing",
            "enable_llm_fallback",
            "enable_openfga",
            "enable_keycloak",
            "enable_langsmith",
            "studio_canvas_shell",
            "devtools_panel",
            "enable_ai_suggestions",
            "enable_agent_hitl",
            "enable_websocket_new_base",
        ]

        for flag in known_flags:
            assert flag in flag_names, f"Expected flag '{flag}' not found"

    def test_feature_flag_info_has_required_fields(self) -> None:
        """FeatureFlagInfo should have all required fields."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
        )

        flags = extract_feature_flags()
        flag = flags[0]

        # All flags should have these fields
        assert hasattr(flag, "name")
        assert hasattr(flag, "type")
        assert hasattr(flag, "default")
        assert hasattr(flag, "description")
        assert hasattr(flag, "env_var")

    def test_feature_flag_env_var_format(self) -> None:
        """Environment variable should use FF_ prefix with uppercase name."""
        from scripts.validation.generate_feature_flag_catalog import extract_feature_flags

        flags = extract_feature_flags()

        for flag in flags:
            expected_env_var = f"FF_{flag.name.upper()}"
            assert flag.env_var == expected_env_var, (
                f"Flag '{flag.name}' has incorrect env_var: {flag.env_var}, expected: {expected_env_var}"
            )

    def test_extract_includes_constraints(self) -> None:
        """Extraction should include ge/le constraints for numeric flags."""
        from scripts.validation.generate_feature_flag_catalog import extract_feature_flags

        flags = extract_feature_flags()
        flag_by_name = {f.name: f for f in flags}

        # Check a known numeric flag with constraints
        timeout_flag = flag_by_name.get("llm_timeout_seconds")
        assert timeout_flag is not None
        assert timeout_flag.min_value is not None or timeout_flag.max_value is not None


@pytest.mark.unit
@pytest.mark.xdist_group(name="feature_flag_catalog")
class TestFeatureFlagCategorization:
    """Test feature flag categorization by domain."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_categorize_flags_returns_dict(self) -> None:
        """Categorization should return a dictionary of categories to flags."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            categorize_flags,
        )

        flags = extract_feature_flags()
        categories = categorize_flags(flags)

        assert isinstance(categories, dict)
        assert len(categories) > 0

    def test_categorize_flags_expected_categories(self) -> None:
        """Categorization should include expected domain categories."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            categorize_flags,
        )

        flags = extract_feature_flags()
        categories = categorize_flags(flags)

        expected_categories = [
            "Pydantic AI",
            "LLM",
            "Authorization",
            "Observability",
            "UI Features",
            "DevTools",
            "Agent HITL",
            "WebSocket",
        ]

        for category in expected_categories:
            assert category in categories, f"Expected category '{category}' not found"

    def test_all_flags_categorized(self) -> None:
        """All extracted flags should be assigned to a category."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            categorize_flags,
        )

        flags = extract_feature_flags()
        categories = categorize_flags(flags)

        # Count total flags in all categories
        categorized_count = sum(len(cat_flags) for cat_flags in categories.values())
        assert categorized_count == len(flags), f"Not all flags categorized: {categorized_count} vs {len(flags)}"


@pytest.mark.unit
@pytest.mark.xdist_group(name="feature_flag_catalog")
class TestMarkdownGeneration:
    """Test markdown catalog generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_generate_markdown_catalog_returns_string(self) -> None:
        """Markdown generation should return a string."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            generate_markdown_catalog,
        )

        flags = extract_feature_flags()
        markdown = generate_markdown_catalog(flags)

        assert isinstance(markdown, str)
        assert len(markdown) > 0

    def test_markdown_catalog_has_header(self) -> None:
        """Markdown catalog should have a title header."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            generate_markdown_catalog,
        )

        flags = extract_feature_flags()
        markdown = generate_markdown_catalog(flags)

        assert "# Feature Flag Catalog" in markdown

    def test_markdown_catalog_has_categories(self) -> None:
        """Markdown catalog should have category headers."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            generate_markdown_catalog,
        )

        flags = extract_feature_flags()
        markdown = generate_markdown_catalog(flags)

        # Check for at least one category header (## heading)
        assert "## " in markdown

    def test_markdown_catalog_has_tables(self) -> None:
        """Markdown catalog should use tables for flag documentation."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            generate_markdown_catalog,
        )

        flags = extract_feature_flags()
        markdown = generate_markdown_catalog(flags)

        # Check for markdown table structure
        assert "| Name |" in markdown or "| Flag |" in markdown
        assert "|---" in markdown

    def test_markdown_catalog_includes_env_vars(self) -> None:
        """Markdown catalog should include environment variable names."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            generate_markdown_catalog,
        )

        flags = extract_feature_flags()
        markdown = generate_markdown_catalog(flags)

        # Should include FF_ prefixed env vars
        assert "FF_" in markdown

    def test_markdown_catalog_includes_defaults(self) -> None:
        """Markdown catalog should include default values."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            generate_markdown_catalog,
        )

        flags = extract_feature_flags()
        markdown = generate_markdown_catalog(flags)

        # Should include True/False defaults for boolean flags
        assert "True" in markdown or "true" in markdown
        assert "False" in markdown or "false" in markdown

    def test_markdown_catalog_total_flag_count(self) -> None:
        """Markdown catalog should include total flag count."""
        from scripts.validation.generate_feature_flag_catalog import (
            extract_feature_flags,
            generate_markdown_catalog,
        )

        flags = extract_feature_flags()
        markdown = generate_markdown_catalog(flags)

        # Should mention total count somewhere
        assert str(len(flags)) in markdown or "Total:" in markdown or "flags" in markdown.lower()


@pytest.mark.unit
@pytest.mark.xdist_group(name="feature_flag_catalog")
class TestFlagCount:
    """Test that we're extracting a reasonable number of flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_minimum_flag_count(self) -> None:
        """Should extract at least 100 feature flags (based on current codebase)."""
        from scripts.validation.generate_feature_flag_catalog import extract_feature_flags

        flags = extract_feature_flags()

        # Based on the feature_flags.py analysis, there are 100+ flags
        assert len(flags) >= 100, f"Expected at least 100 flags, got {len(flags)}. If flags were removed, update this test."
