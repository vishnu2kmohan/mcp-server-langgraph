"""Desktop Extension Builder.

Build script for creating .mcpb packages for Claude Desktop.

Supports cross-platform packaging with platform-specific configurations.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from mcp_server_langgraph.packaging.models import (
    ExtensionManifest,
    MCPConfig,
    PlatformOverride,
    ServerConfig,
    UserConfigOption,
    get_platform_configs,
)


class ExtensionBuilder:
    """Builder for .mcpb extension packages.

    Creates cross-platform Claude Desktop extension packages
    with bundled dependencies and platform-specific configurations.
    """

    def __init__(
        self,
        project_dir: Path,
        output_dir: Path | None = None,
    ) -> None:
        """Initialize the builder.

        Args:
            project_dir: Project root directory
            output_dir: Output directory for built packages
        """
        self.project_dir = project_dir
        self.output_dir = output_dir or project_dir / "dist"
        self._manifest: ExtensionManifest | None = None

    def _ensure_output_dir(self) -> None:
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_manifest(
        self,
        name: str,
        version: str,
        description: str,
        author: str = "",
        server_type: str = "python",
        entry_point: str = "server/main.py",
        user_config: list[dict[str, Any]] | None = None,
    ) -> ExtensionManifest:
        """Generate an extension manifest.

        Args:
            name: Extension name
            version: Semantic version
            description: Human-readable description
            author: Extension author
            server_type: Server runtime type
            entry_point: Server entry point
            user_config: User-configurable options

        Returns:
            Generated ExtensionManifest
        """
        # Build server config
        server = ServerConfig(type=server_type, entry=entry_point)  # type: ignore[arg-type]

        # Build MCP config
        mcp_config = MCPConfig(
            command="${__dirname}/server/venv/bin/python",
            args=["${__dirname}/server/main.py"],
        )

        # Build platform overrides
        platform_overrides = {
            "windows": PlatformOverride(
                command="${__dirname}\\server\\venv\\Scripts\\python.exe",
            ),
        }

        # Build user config options
        config_options = []
        if user_config:
            for opt in user_config:
                config_options.append(UserConfigOption(**opt))

        manifest = ExtensionManifest(
            name=name,
            version=version,
            description=description,
            author=author,
            server=server,
            mcp_config=mcp_config,
            platform_overrides=platform_overrides,
            user_config=config_options,
        )

        self._manifest = manifest
        return manifest

    def validate(self) -> list[str]:
        """Validate the extension structure.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self._manifest:
            errors.append("No manifest generated")
            return errors

        # Check required fields
        if not self._manifest.name:
            errors.append("Extension name is required")

        if not self._manifest.version:
            errors.append("Extension version is required")

        if not self._manifest.description:
            errors.append("Extension description is required")

        # Check server entry point exists
        entry_path = self.project_dir / self._manifest.server.entry
        if not entry_path.exists():
            errors.append(f"Server entry point not found: {self._manifest.server.entry}")

        return errors

    def build(
        self,
        platform: str | None = None,
        include_venv: bool = True,
    ) -> Path:
        """Build the .mcpb package.

        Args:
            platform: Target platform (None for current)
            include_venv: Whether to include virtual environment

        Returns:
            Path to built package

        Raises:
            ValueError: If manifest not generated or validation fails
        """
        if not self._manifest:
            raise ValueError("Generate manifest before building")

        errors = self.validate()
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        self._ensure_output_dir()

        # Determine package name
        platform_suffix = f"-{platform}" if platform else ""
        package_name = f"{self._manifest.name}-{self._manifest.version}{platform_suffix}.mcpb"
        package_path = self.output_dir / package_name

        # Create package (zip file with .mcpb extension)
        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            manifest_json = self._manifest.model_dump_json(indent=2)
            zf.writestr("manifest.json", manifest_json)

            # Add server directory
            server_dir = self.project_dir / "server"
            if server_dir.exists():
                for file_path in server_dir.rglob("*"):
                    if file_path.is_file():
                        # Skip venv if not including
                        if not include_venv and "venv" in file_path.parts:
                            continue
                        # Skip __pycache__
                        if "__pycache__" in file_path.parts:
                            continue
                        arcname = file_path.relative_to(self.project_dir)
                        zf.write(file_path, arcname)

        return package_path

    def write_manifest(self, output_path: Path | None = None) -> Path:
        """Write manifest.json to disk.

        Args:
            output_path: Output path (defaults to project_dir/manifest.json)

        Returns:
            Path to written manifest
        """
        if not self._manifest:
            raise ValueError("Generate manifest before writing")

        output_path = output_path or self.project_dir / "manifest.json"
        output_path.write_text(self._manifest.model_dump_json(indent=2))
        return output_path

    def write_platform_configs(self, output_dir: Path | None = None) -> list[Path]:
        """Write platform-specific config files.

        Args:
            output_dir: Output directory for platform configs

        Returns:
            List of paths to written config files
        """
        output_dir = output_dir or self.project_dir / "packaging" / "platform"
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = []
        for platform_name, config in get_platform_configs().items():
            config_path = output_dir / f"{platform_name}.json"
            config_path.write_text(config.model_dump_json(indent=2))
            paths.append(config_path)

        return paths
