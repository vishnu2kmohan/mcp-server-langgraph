"""Desktop Extension Packaging Models.

Pydantic models for .mcpb extension manifest and configuration.

Cross-platform manifest format for Claude Desktop Extensions.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Server configuration for the extension."""

    type: Literal["python", "node", "binary"] = Field(
        default="python",
        description="Server runtime type",
    )
    entry: str = Field(
        default="server/main.py",
        description="Entry point relative to package root",
    )


class MCPConfig(BaseModel):
    """MCP server configuration."""

    command: str = Field(
        description="Command to run (supports ${__dirname} placeholder)",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command arguments",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )


class UserConfigOption(BaseModel):
    """User-configurable option in the extension."""

    name: str = Field(description="Option name (used as key)")
    type: Literal["string", "number", "boolean", "enum"] = Field(
        default="string",
        description="Option type",
    )
    description: str = Field(
        default="",
        description="Human-readable description",
    )
    required: bool = Field(
        default=False,
        description="Whether this option is required",
    )
    secret: bool = Field(
        default=False,
        description="Whether this option should be stored securely",
    )
    default: Any = Field(
        default=None,
        description="Default value",
    )
    values: list[str] = Field(
        default_factory=list,
        description="Valid values for enum type",
    )


class PlatformOverride(BaseModel):
    """Platform-specific configuration override."""

    command: str | None = Field(
        default=None,
        description="Override command for this platform",
    )
    args: list[str] | None = Field(
        default=None,
        description="Override args for this platform",
    )
    env: dict[str, str] | None = Field(
        default=None,
        description="Additional/override env vars for this platform",
    )


class ToolDefinition(BaseModel):
    """MCP tool definition in manifest."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for parameters",
    )


class PromptDefinition(BaseModel):
    """MCP prompt definition in manifest."""

    name: str = Field(description="Prompt name")
    description: str = Field(description="Prompt description")
    arguments: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Prompt arguments",
    )


class ExtensionManifest(BaseModel):
    """Desktop Extension manifest (manifest.json).

    Follows Anthropic's .mcpb specification for cross-platform
    Claude Desktop extensions.
    """

    name: str = Field(description="Extension name (package identifier)")
    version: str = Field(description="Semantic version")
    description: str = Field(description="Human-readable description")
    author: str = Field(
        default="",
        description="Extension author",
    )
    license: str = Field(
        default="MIT",
        description="License identifier",
    )
    homepage: str = Field(
        default="",
        description="Homepage URL",
    )
    repository: str = Field(
        default="",
        description="Repository URL",
    )
    server: ServerConfig = Field(
        default_factory=ServerConfig,
        description="Server configuration",
    )
    mcp_config: MCPConfig | None = Field(
        default=None,
        description="MCP server configuration",
    )
    platform_overrides: dict[str, PlatformOverride] = Field(
        default_factory=dict,
        description="Platform-specific overrides (windows, macos, linux)",
    )
    user_config: list[UserConfigOption] = Field(
        default_factory=list,
        description="User-configurable options",
    )
    tools: list[ToolDefinition] = Field(
        default_factory=list,
        description="MCP tools provided by extension",
    )
    prompts: list[PromptDefinition] = Field(
        default_factory=list,
        description="MCP prompts provided by extension",
    )
    dependencies: dict[str, str] = Field(
        default_factory=dict,
        description="Python package dependencies",
    )
    min_claude_version: str = Field(
        default="",
        description="Minimum Claude Desktop version required",
    )


class PlatformConfig(BaseModel):
    """Platform-specific configuration."""

    platform: Literal["windows", "macos", "linux"] = Field(
        description="Platform identifier",
    )
    command_suffix: str = Field(
        default="",
        description="Suffix for commands (e.g., .exe for Windows)",
    )
    path_separator: str = Field(
        default="/",
        description="Path separator character",
    )
    keychain_type: str = Field(
        default="",
        description="Keychain/secret store type",
    )
    install_path: str = Field(
        default="",
        description="Default installation path",
    )


def get_platform_configs() -> dict[str, PlatformConfig]:
    """Get configurations for all supported platforms.

    Returns:
        Dictionary mapping platform names to their configs.
    """
    return {
        "windows": PlatformConfig(
            platform="windows",
            command_suffix=".exe",
            path_separator="\\",
            keychain_type="dpapi",
            install_path="%APPDATA%\\Claude\\extensions",
        ),
        "macos": PlatformConfig(
            platform="macos",
            command_suffix="",
            path_separator="/",
            keychain_type="keychain",
            install_path="~/Library/Application Support/Claude/extensions",
        ),
        "linux": PlatformConfig(
            platform="linux",
            command_suffix="",
            path_separator="/",
            keychain_type="secret-service",
            install_path="~/.local/share/claude/extensions",
        ),
    }
