"""Desktop Extension Packaging.

Tools for creating .mcpb extension packages for Claude Desktop.

Provides cross-platform packaging with:
- Manifest generation (manifest.json)
- Platform-specific configurations
- Virtual environment bundling
- User-configurable options

Usage:
    from mcp_server_langgraph.packaging import ExtensionBuilder, ExtensionManifest

    builder = ExtensionBuilder(project_dir=Path("."))
    manifest = builder.generate_manifest(
        name="my-extension",
        version="1.0.0",
        description="My MCP extension",
    )
    package_path = builder.build()
"""

from mcp_server_langgraph.packaging.builder import ExtensionBuilder
from mcp_server_langgraph.packaging.models import (
    ExtensionManifest,
    MCPConfig,
    PlatformConfig,
    PlatformOverride,
    PromptDefinition,
    ServerConfig,
    ToolDefinition,
    UserConfigOption,
    get_platform_configs,
)

__all__ = [
    # Manifest Models
    "ExtensionManifest",
    "ServerConfig",
    "MCPConfig",
    "UserConfigOption",
    "PlatformOverride",
    "ToolDefinition",
    "PromptDefinition",
    # Platform
    "PlatformConfig",
    "get_platform_configs",
    # Builder
    "ExtensionBuilder",
]
