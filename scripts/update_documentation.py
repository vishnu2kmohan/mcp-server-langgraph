#!/usr/bin/env python3
"""
Script to update documentation files after package reorganization.
Replaces old file references and import paths with new package structure.
"""

from pathlib import Path

# Documentation update mappings
FILE_REPLACEMENTS = {
    "python mcp_server_streamable.py": "python -m mcp_server_langgraph.mcp.server_streamable",
    "python mcp_server.py": "python -m mcp_server_langgraph.mcp.server_stdio",
    "example_client.py": "examples/client_stdio.py",
    "example_openfga_usage.py": "examples/openfga_usage.py",
    "setup_openfga.py": "scripts/setup_openfga.py",
    "setup_infisical.py": "scripts/setup_infisical.py",
    "mcp_server_streamable.py": "src/mcp_server_langgraph/mcp/server_streamable.py",
    "mcp_server.py": "src/mcp_server_langgraph/mcp/server_stdio.py",
    "auth.py": "src/mcp_server_langgraph/auth/middleware.py",
    "agent.py": "src/mcp_server_langgraph/core/agent.py",
    "config.py": "src/mcp_server_langgraph/core/config.py",
}

IMPORT_REPLACEMENTS = {
    "from config import": "from mcp_server_langgraph.core.config import",
    "from agent import": "from mcp_server_langgraph.core.agent import",
    "from auth import": "from mcp_server_langgraph.auth.middleware import",
    "from openfga_client import": "from mcp_server_langgraph.auth.openfga import",
    "from llm_factory import": "from mcp_server_langgraph.llm.factory import",
    "from llm_validators import": "from mcp_server_langgraph.llm.validators import",
    "from pydantic_ai_agent import": "from mcp_server_langgraph.llm.pydantic_agent import",
    "from observability import": "from mcp_server_langgraph.observability.telemetry import",
    "from langsmith_config import": "from mcp_server_langgraph.observability.langsmith import",
    "from secrets_manager import": "from mcp_server_langgraph.secrets.manager import",
    "from health_check import": "from mcp_server_langgraph.health.checks import",
    "from mcp_streaming import": "from mcp_server_langgraph.mcp.streaming import",
}


def update_file(filepath: Path) -> bool:
    """Update a single documentation file. Returns True if changes were made."""
    try:
        content = filepath.read_text()
        original = content

        # Apply file path replacements
        for old, new in FILE_REPLACEMENTS.items():
            content = content.replace(old, new)

        # Apply import replacements
        for old, new in IMPORT_REPLACEMENTS.items():
            content = content.replace(old, new)

        if content != original:
            filepath.write_text(content)
            print(f"✓ Updated: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error updating {filepath}: {e}")
        return False


def main():
    """Update all documentation files."""
    project_root = Path(__file__).parent.parent

    # Files to update
    files_to_update = [
        project_root / "README.md",
        project_root / "CLAUDE.md",
        project_root / "AGENTS.md",
    ]

    # Add all markdown files in docs/
    docs_dir = project_root / "docs"
    if docs_dir.exists():
        files_to_update.extend(docs_dir.rglob("*.md"))

    files_updated = 0
    for doc_file in files_to_update:
        if doc_file.exists() and update_file(doc_file):
            files_updated += 1

    print(f"\n✓ Updated {files_updated} documentation files")


if __name__ == "__main__":
    main()
