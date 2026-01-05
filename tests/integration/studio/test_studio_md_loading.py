"""Integration tests for STUDIO.md loading flow.

Tests the complete flow of STUDIO.md configuration loading,
parsing, storage, and retrieval.

ADR-0092: Hierarchical Capability Architecture
"""

from __future__ import annotations

import gc
import tempfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.xdist_group(name="studio_loading")]


@pytest.mark.integration
class TestStudioConfigModels:
    """Tests for StudioConfig Pydantic models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_config_exists(self) -> None:
        """Test StudioConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioConfig

        assert StudioConfig is not None

    def test_studio_tools_config_exists(self) -> None:
        """Test StudioToolsConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioToolsConfig

        assert StudioToolsConfig is not None

    def test_studio_skills_config_exists(self) -> None:
        """Test StudioSkillsConfig model exists."""
        from mcp_server_langgraph.studio.config.models import StudioSkillsConfig

        assert StudioSkillsConfig is not None

    def test_studio_config_has_tools_section(self) -> None:
        """Test StudioConfig has tools section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioToolsConfig,
        )

        config = StudioConfig(
            name="test",
            tools=StudioToolsConfig(enabled=["search"], disabled=["dangerous_tool"]),
        )

        assert config.tools is not None
        assert "search" in config.tools.enabled
        assert "dangerous_tool" in config.tools.disabled

    def test_studio_config_has_skills_section(self) -> None:
        """Test StudioConfig has skills section."""
        from mcp_server_langgraph.studio.config.models import (
            StudioConfig,
            StudioSkillsConfig,
        )

        config = StudioConfig(
            name="test",
            skills=StudioSkillsConfig(enabled=["code_review"]),
        )

        assert config.skills is not None
        assert "code_review" in config.skills.enabled


@pytest.mark.integration
class TestStudioParser:
    """Tests for STUDIO.md parser."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_parser_exists(self) -> None:
        """Test StudioParser exists."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        assert StudioParser is not None

    def test_parse_valid_yaml_frontmatter(self) -> None:
        """Test parsing STUDIO.md with YAML frontmatter."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        parser = StudioParser()

        content = """---
name: Test Project
tools:
  enabled:
    - search
    - calculator
  disabled:
    - dangerous_tool
skills:
  enabled:
    - code_review
---

# Project Instructions

This is the project-specific configuration.
"""

        config = parser.parse(content)

        assert config.name == "Test Project"
        assert "search" in config.tools.enabled
        assert "code_review" in config.skills.enabled

    def test_parse_without_frontmatter_raises_error(self) -> None:
        """Test parsing STUDIO.md without frontmatter raises error."""
        from mcp_server_langgraph.studio.config.parser import (
            StudioParseError,
            StudioParser,
        )

        parser = StudioParser()

        content = """# Project Instructions

This is a project without YAML frontmatter.
"""

        # Parser requires YAML frontmatter
        with pytest.raises(StudioParseError, match="Missing YAML frontmatter"):
            parser.parse(content)

    def test_parse_extracts_instructions(self) -> None:
        """Test parsing STUDIO.md extracts markdown instructions."""
        from mcp_server_langgraph.studio.config.parser import StudioParser

        parser = StudioParser()

        content = """---
name: Test
---

# Important Instructions

Follow these guidelines when working on this project.
"""

        config = parser.parse(content)

        assert config.instructions is not None
        assert "Important Instructions" in config.instructions


@pytest.mark.integration
class TestStudioDiscovery:
    """Tests for STUDIO.md file discovery."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_discovery_exists(self) -> None:
        """Test StudioDiscovery class exists."""
        from mcp_server_langgraph.studio.config.discovery import StudioDiscovery

        assert StudioDiscovery is not None

    def test_discover_finds_project_studio_md(self) -> None:
        """Test discovery finds STUDIO.md in project root."""
        from mcp_server_langgraph.studio.config.discovery import StudioDiscovery

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            studio_file = project_root / "STUDIO.md"
            studio_file.write_text("---\nname: Test\n---\n# Test")

            discovery = StudioDiscovery()
            files = discovery.discover(start_path=project_root)

            assert len(files) >= 1
            assert any(f[1].name == "STUDIO.md" for f in files)

    def test_discover_returns_scope_path_tuples(self) -> None:
        """Test discovery returns (scope, path) tuples."""
        from mcp_server_langgraph.core.scopes import CapabilityScope
        from mcp_server_langgraph.studio.config.discovery import StudioDiscovery

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            studio_file = project_root / "STUDIO.md"
            studio_file.write_text("---\nname: Test\n---\n# Test")

            discovery = StudioDiscovery()
            files = discovery.discover(start_path=project_root)

            for scope, path in files:
                assert isinstance(scope, CapabilityScope)
                assert isinstance(path, Path)


@pytest.mark.integration
class TestStudioLoader:
    """Tests for STUDIO.md loader."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_loader_exists(self) -> None:
        """Test StudioLoader class exists."""
        from mcp_server_langgraph.studio.config.loader import StudioLoader

        assert StudioLoader is not None

    def test_load_from_file(self) -> None:
        """Test loading StudioConfig from file."""
        from mcp_server_langgraph.studio.config.loader import StudioLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            studio_file = Path(tmpdir) / "STUDIO.md"
            studio_file.write_text("""---
name: Integration Test
tools:
  enabled:
    - search
---

# Integration Test Config
""")

            loader = StudioLoader()
            config = loader.load(studio_file)

            assert config.name == "Integration Test"
            assert "search" in config.tools.enabled

    def test_load_nonexistent_file_returns_default(self) -> None:
        """Test loading nonexistent file returns default config."""
        from mcp_server_langgraph.studio.config.loader import StudioLoader

        loader = StudioLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "MISSING_STUDIO.md"

            # Should not raise, should return default
            config = loader.load_or_default(missing_file)

            assert config is not None


@pytest.mark.integration
class TestStudioStorage:
    """Tests for STUDIO.md configuration storage."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_studio_storage_exists(self) -> None:
        """Test StudioConfigStorage exists."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        assert StudioConfigStorage is not None

    @pytest.mark.asyncio
    async def test_storage_save_and_get(self) -> None:
        """Test storing and retrieving a configuration."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        storage = StudioConfigStorage()

        config = StoredStudioConfig(
            id="test-123",
            scope="project",
            scope_id=None,
            config={"name": "Test", "tools": {"enabled": ["search"]}},
            config_hash="abc123",
        )

        await storage.save(config)

        retrieved = await storage.get(scope="project", scope_id=None)

        assert retrieved is not None
        assert retrieved.id == "test-123"
        assert retrieved.config["name"] == "Test"

    @pytest.mark.asyncio
    async def test_storage_delete(self) -> None:
        """Test deleting a configuration."""
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        storage = StudioConfigStorage()

        config = StoredStudioConfig(
            id="delete-test",
            scope="organization",
            scope_id="org-123",
            config={"name": "Delete Test"},
            config_hash="def456",
        )

        await storage.save(config)
        await storage.delete(scope="organization", scope_id="org-123")

        retrieved = await storage.get(scope="organization", scope_id="org-123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_storage_hash_change_detection(self) -> None:
        """Test detecting configuration changes via hash."""
        from mcp_server_langgraph.studio.config.storage import StudioConfigStorage

        storage = StudioConfigStorage()

        original_config = {"name": "Original", "tools": {"enabled": []}}
        modified_config = {"name": "Modified", "tools": {"enabled": ["search"]}}

        # Store original
        from mcp_server_langgraph.studio.config.storage import StoredStudioConfig

        stored = StoredStudioConfig(
            id="hash-test",
            scope="project",
            scope_id=None,
            config=original_config,
            config_hash=storage.compute_hash(original_config),
        )
        await storage.save(stored)

        # Check if modified config has changed
        has_changed = await storage.has_changed(
            scope="project",
            scope_id=None,
            new_config=modified_config,
        )

        assert has_changed is True


@pytest.mark.integration
class TestEndToEndStudioLoading:
    """End-to-end integration tests for STUDIO.md loading."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_full_loading_flow(self) -> None:
        """Test complete STUDIO.md loading flow."""
        from mcp_server_langgraph.studio.config.discovery import StudioDiscovery
        from mcp_server_langgraph.studio.config.loader import StudioLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            studio_file = project_root / "STUDIO.md"
            studio_file.write_text("""---
name: E2E Test Project
tools:
  enabled:
    - search
    - calculator
  disabled:
    - dangerous_tool
skills:
  enabled:
    - code_review
    - testing
---

# E2E Test Project Instructions

This project uses specific tools and skills.
""")

            # Step 1: Discover STUDIO.md files
            discovery = StudioDiscovery()
            files = discovery.discover(start_path=project_root)

            assert len(files) >= 1

            # Step 2: Load each discovered file
            loader = StudioLoader()
            for scope, path in files:
                if path.name == "STUDIO.md":
                    config = loader.load(path)

                    # Step 3: Verify loaded config
                    assert config.name == "E2E Test Project"
                    assert "search" in config.tools.enabled
                    assert "code_review" in config.skills.enabled

    @pytest.mark.asyncio
    async def test_loading_and_storage_flow(self) -> None:
        """Test loading STUDIO.md and storing in StudioConfigStorage."""
        from mcp_server_langgraph.studio.config.loader import StudioLoader
        from mcp_server_langgraph.studio.config.storage import (
            StoredStudioConfig,
            StudioConfigStorage,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            studio_file = Path(tmpdir) / "STUDIO.md"
            studio_file.write_text("""---
name: Storage Test
tools:
  enabled:
    - test_tool
---
# Test
""")

            # Load the config
            loader = StudioLoader()
            config = loader.load(studio_file)

            # Convert to storage format
            storage = StudioConfigStorage()
            config_dict = {
                "name": config.name,
                "tools": {
                    "enabled": config.tools.enabled,
                    "disabled": config.tools.disabled,
                },
            }

            stored = StoredStudioConfig(
                id="storage-flow-test",
                scope="project",
                scope_id=None,
                config=config_dict,
                config_hash=storage.compute_hash(config_dict),
            )

            # Store it
            await storage.save(stored)

            # Retrieve and verify
            retrieved = await storage.get(scope="project", scope_id=None)
            assert retrieved is not None
            assert retrieved.config["name"] == "Storage Test"
