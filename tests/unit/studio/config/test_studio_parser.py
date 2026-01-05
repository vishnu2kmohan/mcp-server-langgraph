"""Tests for STUDIO.md parser.

TDD: These tests define the contract for parsing STUDIO.md files
with YAML frontmatter and Markdown body.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
from textwrap import dedent

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_parser_basic")
class TestStudioParserBasic:
    """Tests for StudioParser basic functionality."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_parser_exists(self) -> None:
        """Test StudioParser class exists."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        assert StudioParser is not None

    def test_studio_parser_has_parse_method(self) -> None:
        """Test StudioParser has parse method."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        parser = StudioParser()
        assert hasattr(parser, "parse")
        assert callable(parser.parse)

    def test_parse_returns_studio_config(self) -> None:
        """Test parse returns a StudioConfig object."""
        from mcp_server_langgraph.studio.config.models import StudioConfig
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test Project
            ---
            # Instructions
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert isinstance(config, StudioConfig)


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_parser_yaml")
class TestStudioParserYAML:
    """Tests for YAML frontmatter parsing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_yaml_frontmatter_extracts_name(self) -> None:
        """Test parsing extracts name from YAML frontmatter."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: My Awesome Project
            ---
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.name == "My Awesome Project"

    def test_parse_yaml_frontmatter_extracts_description(self) -> None:
        """Test parsing extracts description from YAML frontmatter."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            description: A test project for demos
            ---
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.description == "A test project for demos"

    def test_parse_yaml_frontmatter_extracts_version(self) -> None:
        """Test parsing extracts version from YAML frontmatter."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            version: 2.0.0
            ---
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.version == "2.0.0"

    def test_parse_yaml_frontmatter_extracts_tools(self) -> None:
        """Test parsing extracts tools configuration."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            tools:
              enabled:
                - file_reader
                - web_search
              disabled:
                - dangerous_tool
            ---
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.tools is not None
        assert "file_reader" in config.tools.enabled
        assert "web_search" in config.tools.enabled
        assert "dangerous_tool" in config.tools.disabled

    def test_parse_yaml_frontmatter_extracts_skills(self) -> None:
        """Test parsing extracts skills configuration."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            skills:
              enabled:
                - summarize
                - translate
              categories:
                - text
            ---
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.skills is not None
        assert "summarize" in config.skills.enabled
        assert "text" in config.skills.categories

    def test_parse_yaml_frontmatter_extracts_cost(self) -> None:
        """Test parsing extracts cost configuration."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            cost:
              max_tokens: 5000
              max_cost: 1.50
            ---
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.cost is not None
        assert config.cost.max_tokens == 5000
        assert config.cost.max_cost == 1.50


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_parser_markdown")
class TestStudioParserMarkdown:
    """Tests for Markdown body parsing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_markdown_body_as_instructions(self) -> None:
        """Test parsing captures markdown body as instructions."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            ---
            # Instructions

            Follow these guidelines:
            - Be helpful
            - Be accurate
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.instructions is not None
        assert "# Instructions" in config.instructions
        assert "Be helpful" in config.instructions

    def test_parse_empty_markdown_body(self) -> None:
        """Test parsing with empty markdown body."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            ---
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        # Empty or whitespace-only body
        assert config.instructions is None or config.instructions.strip() == ""

    def test_parse_preserves_markdown_formatting(self) -> None:
        """Test parsing preserves markdown formatting in instructions."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Test
            ---
            # Title

            **Bold** and *italic* text.

            ```python
            def hello():
                print("Hello")
            ```
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        assert config.instructions is not None
        assert "**Bold**" in config.instructions
        assert "```python" in config.instructions


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_parser_errors")
class TestStudioParserErrors:
    """Tests for parser error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_missing_frontmatter_uses_defaults(self) -> None:
        """Test parsing without frontmatter raises or uses defaults."""
        from mcp_server_langgraph.studio.config.parser import (
            StudioParseError,
            StudioParser,
        )

        content = "# Just Markdown\n\nNo frontmatter here."
        parser = StudioParser()

        with pytest.raises(StudioParseError):
            parser.parse(content)

    def test_parse_invalid_yaml_raises_error(self) -> None:
        """Test parsing invalid YAML raises StudioParseError."""
        from mcp_server_langgraph.studio.config.parser import (
            StudioParseError,
            StudioParser,
        )

        content = dedent(
            """
            ---
            name: Test
            invalid: yaml: content: here
            ---
            """
        )
        parser = StudioParser()

        with pytest.raises(StudioParseError):
            parser.parse(content)

    def test_parse_missing_required_name_raises_error(self) -> None:
        """Test parsing without required name field raises error."""
        from mcp_server_langgraph.studio.config.parser import (
            StudioParseError,
            StudioParser,
        )

        content = dedent(
            """
            ---
            description: Missing name field
            ---
            """
        )
        parser = StudioParser()

        with pytest.raises(StudioParseError):
            parser.parse(content)

    def test_studio_parse_error_exists(self) -> None:
        """Test StudioParseError exception class exists."""
        from mcp_server_langgraph.studio.config.parser import StudioParseError

        assert StudioParseError is not None
        assert issubclass(StudioParseError, Exception)


@pytest.mark.unit
@pytest.mark.xdist_group(name="studio_parser_complete")
class TestStudioParserComplete:
    """Tests for complete STUDIO.md parsing."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_complete_studio_md(self) -> None:
        """Test parsing a complete STUDIO.md file."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        content = dedent(
            """
            ---
            name: Production Project
            description: A production-ready project
            version: 1.2.0
            tools:
              enabled:
                - file_reader
                - code_search
              disabled:
                - shell_exec
            skills:
              enabled:
                - summarize
                - analyze
              categories:
                - code
                - text
            memory:
              enabled: true
              tiers:
                - working
                - session
            cost:
              max_tokens: 10000
              max_cost: 5.0
              budget_alert_threshold: 0.9
            models:
              default_model: claude-sonnet-4
              allowed_models:
                - claude-haiku-4
                - claude-sonnet-4
            rules:
              - name: no-secrets
                description: Never output secrets or API keys
                severity: error
            ---
            # Project Instructions

            This is a production project. Follow these guidelines:

            1. Always validate user input
            2. Log all operations
            3. Handle errors gracefully
            """
        )
        parser = StudioParser()
        config = parser.parse(content)

        # Verify all sections parsed correctly
        assert config.name == "Production Project"
        assert config.description == "A production-ready project"
        assert config.version == "1.2.0"

        assert config.tools is not None
        assert "file_reader" in config.tools.enabled
        assert "shell_exec" in config.tools.disabled

        assert config.skills is not None
        assert "summarize" in config.skills.enabled
        assert "code" in config.skills.categories

        assert config.memory is not None
        assert config.memory.enabled is True

        assert config.cost is not None
        assert config.cost.max_tokens == 10000
        assert config.cost.max_cost == 5.0

        assert config.models is not None
        assert config.models.default_model == "claude-sonnet-4"

        assert config.rules is not None
        assert len(config.rules) == 1
        assert config.rules[0].name == "no-secrets"

        assert config.instructions is not None
        assert "production project" in config.instructions.lower()
