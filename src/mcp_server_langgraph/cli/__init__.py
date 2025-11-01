"""
MCP Server with LangGraph CLI

A command-line interface for scaffolding and managing MCP Server projects.

Usage:
    mcpserver init [--quickstart]
    mcpserver create-agent <name> [--template <type>]
    mcpserver add-tool <name>
    mcpserver migrate --from <framework>
"""

import sys

import click

from .init import init_project


@click.group()
@click.version_option(version="2.8.0", prog_name="mcpserver")
def cli():
    """
    MCP Server with LangGraph CLI

    A production-ready MCP server with enterprise features.

    Examples:
        mcpserver init --quickstart
        mcpserver create-agent my-agent --template research
        mcpserver add-tool calculator
    """
    pass


@cli.command()
@click.option(
    "--quickstart",
    is_flag=True,
    help="Create a minimal quick-start project (no infrastructure)",
)
@click.option(
    "--template",
    type=click.Choice(["quickstart", "production", "enterprise"]),
    default="production",
    help="Project template to use",
)
@click.option(
    "--name",
    prompt="Project name",
    help="Name of your MCP Server project",
)
def init(quickstart: bool, template: str, name: str):
    """
    Initialize a new MCP Server project.

    Creates a new project with the specified template:
    - quickstart: Minimal in-memory setup (2-minute start)
    - production: Full Docker Compose stack (15-minute start)
    - enterprise: Kubernetes with Keycloak + OpenFGA (1-2 hour setup)

    Examples:
        mcpserver init --quickstart --name my-agent
        mcpserver init --template enterprise --name my-enterprise-agent
    """
    if quickstart:
        template = "quickstart"

    click.echo(f"Initializing MCP Server project: {name}")
    click.echo(f"Template: {template}")

    try:
        init_project(name, template)
        click.secho(f"✓ Project '{name}' created successfully!", fg="green")

        if template == "quickstart":
            click.echo("\nNext steps:")
            click.echo(f"  cd {name}")
            click.echo("  uv run python app.py")
            click.echo("\nYour agent will be running at http://localhost:8000")
        elif template == "production":
            click.echo("\nNext steps:")
            click.echo(f"  cd {name}")
            click.echo("  docker compose up -d")
            click.echo("  make setup")
            click.echo("\nSee README.md for full setup instructions")
        else:
            click.echo("\nNext steps:")
            click.echo(f"  cd {name}")
            click.echo("  See DEPLOYMENT.md for Kubernetes setup")

    except Exception as e:
        click.secho(f"✗ Error creating project: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option(
    "--template",
    type=click.Choice(["basic", "research", "customer-support", "code-review", "data-analyst"]),
    default="basic",
    help="Agent template to use",
)
@click.option(
    "--tools",
    multiple=True,
    help="Tools to include (e.g., search, calculator)",
)
def create_agent(name: str, template: str, tools: tuple):
    """
    Create a new agent in the current project.

    Generates an agent file with the specified template and tools.

    Examples:
        mcpserver create-agent my-agent
        mcpserver create-agent researcher --template research --tools search
        mcpserver create-agent support --template customer-support
    """
    click.echo(f"Creating agent: {name}")
    click.echo(f"Template: {template}")
    if tools:
        click.echo(f"Tools: {', '.join(tools)}")

    try:
        from .create_agent import generate_agent

        generate_agent(name, template, list(tools))
        click.secho(f"✓ Agent '{name}' created successfully!", fg="green")
        click.echo(f"\nAgent file: src/agents/{name}_agent.py")
        click.echo("\nNext steps:")
        click.echo(f"  1. Edit src/agents/{name}_agent.py to customize behavior")
        click.echo("  2. Add tools in src/tools/ if needed")
        click.echo("  3. Test with: uv run python src/agents/{name}_agent.py")

    except Exception as e:
        click.secho(f"✗ Error creating agent: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.option(
    "--description",
    prompt="Tool description",
    help="What does this tool do?",
)
def add_tool(name: str, description: str):
    """
    Add a new tool to the current project.

    Generates a tool file with boilerplate code.

    Examples:
        mcpserver add-tool calculator --description "Perform calculations"
        mcpserver add-tool web-scraper --description "Scrape web pages"
    """
    click.echo(f"Creating tool: {name}")
    click.echo(f"Description: {description}")

    try:
        from .add_tool import generate_tool

        generate_tool(name, description)
        click.secho(f"✓ Tool '{name}' created successfully!", fg="green")
        click.echo(f"\nTool file: src/tools/{name}_tool.py")
        click.echo("\nNext steps:")
        click.echo(f"  1. Implement the tool logic in src/tools/{name}_tool.py")
        click.echo("  2. Add the tool to your agent")
        click.echo("  3. Test with: uv run pytest tests/tools/test_{name}_tool.py")

    except Exception as e:
        click.secho(f"✗ Error creating tool: {e}", fg="red", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--from",
    "from_framework",
    type=click.Choice(["crewai", "langchain", "openai-agentkit", "autogpt"]),
    required=True,
    help="Framework to migrate from",
)
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True),
    required=True,
    help="Path to existing project",
)
def migrate(from_framework: str, input_path: str):
    """
    Migrate from another agent framework to MCP Server with LangGraph.

    Converts existing agent code to MCP Server format.

    Examples:
        mcpserver migrate --from crewai --input ./my-crew
        mcpserver migrate --from openai-agentkit --input ./my-agent
    """
    click.echo(f"Migrating from {from_framework}")
    click.echo(f"Input: {input_path}")

    click.secho("⚠ Migration tool coming in Q2 2025", fg="yellow")
    click.echo("\nFor now, see our migration guides:")
    click.echo(f"  https://docs.mcp-server-langgraph.com/comparisons/vs-{from_framework}")

    sys.exit(0)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
