#!/usr/bin/env python3
"""
Desktop Extension Build Script

CLI wrapper for the ExtensionBuilder to create .mcpb packages for Claude Desktop.

Usage:
    python packaging/build.py --name mcp-server-langgraph --version 1.0.0
    python packaging/build.py --help

See also:
    src/mcp_server_langgraph/packaging/builder.py - Core builder implementation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_server_langgraph.packaging import ExtensionBuilder


def main() -> int:
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description="Build .mcpb extension packages for Claude Desktop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Build with defaults
    python packaging/build.py

    # Build with custom name and version
    python packaging/build.py --name my-extension --version 2.0.0

    # Build for specific platform without venv
    python packaging/build.py --platform windows --no-venv

    # Generate manifest only
    python packaging/build.py --manifest-only
""",
    )

    parser.add_argument(
        "--name",
        default="mcp-server-langgraph",
        help="Extension name (default: mcp-server-langgraph)",
    )
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="Extension version (default: 1.0.0)",
    )
    parser.add_argument(
        "--description",
        default="LangGraph-based MCP server with multi-agent orchestration",
        help="Extension description",
    )
    parser.add_argument(
        "--author",
        default="Emergence AI",
        help="Extension author",
    )
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux"],
        help="Target platform (default: current platform)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "dist",
        help="Output directory for built packages",
    )
    parser.add_argument(
        "--no-venv",
        action="store_true",
        help="Exclude virtual environment from package",
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Generate manifest.json only, don't build package",
    )
    parser.add_argument(
        "--write-platform-configs",
        action="store_true",
        help="Write platform-specific config files",
    )

    args = parser.parse_args()

    # Initialize builder
    builder = ExtensionBuilder(
        project_dir=project_root,
        output_dir=args.output_dir,
    )

    # Generate manifest
    print(f"Generating manifest for {args.name} v{args.version}...")
    builder.generate_manifest(
        name=args.name,
        version=args.version,
        description=args.description,
        author=args.author,
        user_config=[
            {"name": "api_key", "type": "string", "secret": True, "required": True},
            {"name": "llm_provider", "type": "enum", "values": ["anthropic", "openai", "gemini"]},
        ],
    )

    # Write platform configs if requested
    if args.write_platform_configs:
        paths = builder.write_platform_configs()
        print(f"Wrote {len(paths)} platform config files")
        for p in paths:
            print(f"  - {p}")

    # Manifest-only mode
    if args.manifest_only:
        manifest_path = builder.write_manifest()
        print(f"Manifest written to: {manifest_path}")
        return 0

    # Validate before building
    errors = builder.validate()
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    # Build package
    try:
        package_path = builder.build(
            platform=args.platform,
            include_venv=not args.no_venv,
        )
        print(f"Package built successfully: {package_path}")
        return 0
    except ValueError as e:
        print(f"Build failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
