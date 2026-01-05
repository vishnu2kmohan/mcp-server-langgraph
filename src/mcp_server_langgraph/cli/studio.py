"""STUDIO.md validation CLI commands.

Provides CLI commands for validating STUDIO.md configuration files.

Usage:
    mcpserver studio validate ./STUDIO.md
    mcpserver studio validate --verbose ./STUDIO.md

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from mcp_server_langgraph.studio.config.parser import StudioParser, StudioParseError


@click.group()
def studio() -> None:
    """STUDIO.md configuration management commands.

    Commands for validating and managing STUDIO.md configuration files.
    """


@studio.command(name="validate")
@click.argument("path", type=click.Path())
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed configuration information",
)
def studio_validate(path: str, verbose: bool) -> None:
    """Validate a STUDIO.md configuration file.

    Parses and validates the STUDIO.md file at PATH, checking for:
    - Valid YAML frontmatter syntax
    - Required configuration fields
    - Tool and skill declarations

    Examples:
        mcpserver studio validate ./STUDIO.md
        mcpserver studio validate --verbose ./STUDIO.md
    """
    file_path = Path(path)

    # Check file exists
    if not file_path.exists():
        click.secho(f"Error: File not found: {path}", fg="red", err=True)
        sys.exit(1)

    # Check it's a file
    if not file_path.is_file():
        click.secho(f"Error: Not a file: {path}", fg="red", err=True)
        sys.exit(1)

    try:
        # Parse the STUDIO.md file
        content = file_path.read_text(encoding="utf-8")
        parser = StudioParser()
        config = parser.parse(content)

        # Success output
        click.secho(f"✓ Valid STUDIO.md: {config.name or 'Unnamed'}", fg="green")

        # Count tools and skills
        tools_enabled = len(config.tools.enabled) if config.tools else 0
        tools_disabled = len(config.tools.disabled) if config.tools else 0
        skills_enabled = len(config.skills.enabled) if config.skills else 0

        click.echo(f"  Tools: {tools_enabled} enabled, {tools_disabled} disabled")
        click.echo(f"  Skills: {skills_enabled} enabled")

        # Verbose output
        if verbose:
            click.echo()
            click.echo("Configuration Details:")

            if config.tools and config.tools.enabled:
                click.echo("  Enabled tools:")
                for tool in config.tools.enabled:
                    click.echo(f"    - {tool}")

            if config.tools and config.tools.disabled:
                click.echo("  Disabled tools:")
                for tool in config.tools.disabled:
                    click.echo(f"    - {tool}")

            if config.skills and config.skills.enabled:
                click.echo("  Enabled skills:")
                for skill in config.skills.enabled:
                    click.echo(f"    - {skill}")

            if config.instructions:
                click.echo(f"  Instructions: {len(config.instructions)} characters")

    except StudioParseError as e:
        click.secho(f"✗ Invalid STUDIO.md: {e}", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"✗ Error reading file: {e}", fg="red", err=True)
        sys.exit(1)
