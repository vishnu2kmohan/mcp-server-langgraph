"""Tests for Desktop Extension Packaging (.mcpb).

Tests the manifest schema, build script, and cross-platform packaging.
"""

from __future__ import annotations

import gc
import json
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.desktop_extension
@pytest.mark.xdist_group(name="desktop_extension")
class TestExtensionManifest:
    """Tests for ExtensionManifest model."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_manifest_model_exists(self):
        """Manifest model should be importable."""
        from mcp_server_langgraph.packaging import ExtensionManifest

        assert ExtensionManifest is not None

    def test_manifest_creation_with_required_fields(self):
        """Manifest should be creatable with required fields."""
        from mcp_server_langgraph.packaging import ExtensionManifest

        manifest = ExtensionManifest(
            name="mcp-server-langgraph",
            version="1.0.0",
            description="LangGraph-based MCP server",
        )

        assert manifest.name == "mcp-server-langgraph"
        assert manifest.version == "1.0.0"
        assert manifest.description == "LangGraph-based MCP server"

    def test_manifest_has_server_config(self):
        """Manifest should have server configuration."""
        from mcp_server_langgraph.packaging import ExtensionManifest, ServerConfig

        manifest = ExtensionManifest(
            name="test-extension",
            version="1.0.0",
            description="Test",
            server=ServerConfig(
                type="python",
                entry="server/main.py",
            ),
        )

        assert manifest.server is not None
        assert manifest.server.type == "python"
        assert manifest.server.entry == "server/main.py"

    def test_manifest_has_mcp_config(self):
        """Manifest should have MCP configuration."""
        from mcp_server_langgraph.packaging import ExtensionManifest, MCPConfig

        manifest = ExtensionManifest(
            name="test-extension",
            version="1.0.0",
            description="Test",
            mcp_config=MCPConfig(
                command="${__dirname}/server/venv/bin/python",
                args=["${__dirname}/server/main.py"],
            ),
        )

        assert manifest.mcp_config is not None
        assert "${__dirname}" in manifest.mcp_config.command

    def test_manifest_has_user_config(self):
        """Manifest should support user-configurable options."""
        from mcp_server_langgraph.packaging import (
            ExtensionManifest,
            UserConfigOption,
        )

        manifest = ExtensionManifest(
            name="test-extension",
            version="1.0.0",
            description="Test",
            user_config=[
                UserConfigOption(
                    name="api_key",
                    type="string",
                    secret=True,
                    required=True,
                ),
                UserConfigOption(
                    name="llm_provider",
                    type="enum",
                    values=["anthropic", "openai", "gemini"],
                ),
            ],
        )

        assert len(manifest.user_config) == 2
        assert manifest.user_config[0].secret is True

    def test_manifest_has_platform_overrides(self):
        """Manifest should support platform-specific overrides."""
        from mcp_server_langgraph.packaging import ExtensionManifest, PlatformOverride

        manifest = ExtensionManifest(
            name="test-extension",
            version="1.0.0",
            description="Test",
            platform_overrides={
                "windows": PlatformOverride(
                    command="${__dirname}\\server\\venv\\Scripts\\python.exe",
                ),
            },
        )

        assert "windows" in manifest.platform_overrides
        assert "python.exe" in manifest.platform_overrides["windows"].command

    def test_manifest_to_json(self):
        """Manifest should serialize to JSON."""
        from mcp_server_langgraph.packaging import ExtensionManifest

        manifest = ExtensionManifest(
            name="test-extension",
            version="1.0.0",
            description="Test extension",
            author="Test Author",
        )

        json_str = manifest.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["name"] == "test-extension"
        assert parsed["version"] == "1.0.0"
        assert parsed["author"] == "Test Author"


@pytest.mark.unit
@pytest.mark.desktop_extension
@pytest.mark.xdist_group(name="desktop_extension")
class TestExtensionBuilder:
    """Tests for ExtensionBuilder class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_builder_class_exists(self):
        """ExtensionBuilder should be importable."""
        from mcp_server_langgraph.packaging import ExtensionBuilder

        assert ExtensionBuilder is not None

    def test_builder_initialization_sets_defaults(self):
        """Builder should initialize with project directory."""
        from mcp_server_langgraph.packaging import ExtensionBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = ExtensionBuilder(project_dir=Path(tmpdir))
            assert builder.project_dir == Path(tmpdir)

    def test_builder_has_build_method(self):
        """Builder should have build method."""
        from mcp_server_langgraph.packaging import ExtensionBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = ExtensionBuilder(project_dir=Path(tmpdir))
            assert hasattr(builder, "build")
            assert callable(builder.build)

    def test_builder_has_validate_method(self):
        """Builder should have validate method."""
        from mcp_server_langgraph.packaging import ExtensionBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = ExtensionBuilder(project_dir=Path(tmpdir))
            assert hasattr(builder, "validate")
            assert callable(builder.validate)

    def test_builder_creates_output_directory(self):
        """Builder should create output directory."""
        from mcp_server_langgraph.packaging import ExtensionBuilder

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            output_dir = project_dir / "dist"

            builder = ExtensionBuilder(
                project_dir=project_dir,
                output_dir=output_dir,
            )

            builder._ensure_output_dir()
            assert output_dir.exists()

    def test_builder_generates_manifest(self):
        """Builder should generate manifest.json."""
        from mcp_server_langgraph.packaging import ExtensionBuilder, ExtensionManifest

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = ExtensionBuilder(project_dir=Path(tmpdir))
            manifest = builder.generate_manifest(
                name="test-ext",
                version="1.0.0",
                description="Test",
            )

            assert isinstance(manifest, ExtensionManifest)
            assert manifest.name == "test-ext"


@pytest.mark.unit
@pytest.mark.desktop_extension
@pytest.mark.xdist_group(name="desktop_extension")
class TestPlatformSupport:
    """Tests for platform-specific packaging."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_platform_config_model_exists(self):
        """PlatformConfig should be importable."""
        from mcp_server_langgraph.packaging import PlatformConfig

        assert PlatformConfig is not None

    def test_windows_platform_config(self):
        """Windows config should use backslashes and .exe."""
        from mcp_server_langgraph.packaging import PlatformConfig

        config = PlatformConfig(
            platform="windows",
            command_suffix=".exe",
            path_separator="\\",
        )

        assert config.platform == "windows"
        assert config.command_suffix == ".exe"
        assert config.path_separator == "\\"

    def test_macos_platform_config(self):
        """macOS config should use forward slashes."""
        from mcp_server_langgraph.packaging import PlatformConfig

        config = PlatformConfig(
            platform="macos",
            command_suffix="",
            path_separator="/",
        )

        assert config.platform == "macos"
        assert config.command_suffix == ""

    def test_linux_platform_config(self):
        """Linux config should use forward slashes."""
        from mcp_server_langgraph.packaging import PlatformConfig

        config = PlatformConfig(
            platform="linux",
            command_suffix="",
            path_separator="/",
        )

        assert config.platform == "linux"

    def test_get_platform_configs(self):
        """Should provide configs for all platforms."""
        from mcp_server_langgraph.packaging import get_platform_configs

        configs = get_platform_configs()

        assert "windows" in configs
        assert "macos" in configs
        assert "linux" in configs


@pytest.mark.unit
@pytest.mark.desktop_extension
@pytest.mark.xdist_group(name="desktop_extension")
class TestPackageModule:
    """Tests for packaging module exports."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_exports_available(self):
        """All packaging exports should be importable."""
        from mcp_server_langgraph.packaging import (
            ExtensionManifest,
            ServerConfig,
            MCPConfig,
            UserConfigOption,
            PlatformOverride,
            PlatformConfig,
            ExtensionBuilder,
            get_platform_configs,
        )

        assert ExtensionManifest is not None
        assert ServerConfig is not None
        assert MCPConfig is not None
        assert UserConfigOption is not None
        assert PlatformOverride is not None
        assert PlatformConfig is not None
        assert ExtensionBuilder is not None
        assert get_platform_configs is not None
