#!/usr/bin/env python3
"""
Script to update imports after package reorganization.
Converts old flat imports to new mcp_server_langgraph.* imports.
"""

import sys
from pathlib import Path


# Import mapping: old_module -> new_module
IMPORT_MAP = {
    "from mcp_server_langgraph.core.config import": "from mcp_server_langgraph.core.config import",
    "import mcp_server_langgraph.core.config as config": "import mcp_server_langgraph.core.config as config",
    "from mcp_server_langgraph.core.feature_flags import": "from mcp_server_langgraph.core.feature_flags import",
    "from mcp_server_langgraph.core.agent import": "from mcp_server_langgraph.core.agent import",
    "from mcp_server_langgraph.auth.middleware import": "from mcp_server_langgraph.auth.middleware import",
    "from mcp_server_langgraph.auth.openfga import": "from mcp_server_langgraph.auth.openfga import",
    "from mcp_server_langgraph.llm.factory import": "from mcp_server_langgraph.llm.factory import",
    "from mcp_server_langgraph.llm.validators import": "from mcp_server_langgraph.llm.validators import",
    "from mcp_server_langgraph.llm.pydantic_agent import": "from mcp_server_langgraph.llm.pydantic_agent import",
    "from mcp_server_langgraph.observability.telemetry import": "from mcp_server_langgraph.observability.telemetry import",
    "from mcp_server_langgraph.observability.langsmith import": "from mcp_server_langgraph.observability.langsmith import",
    "from mcp_server_langgraph.secrets.manager import": "from mcp_server_langgraph.secrets.manager import",
    "from mcp_server_langgraph.health.checks import": "from mcp_server_langgraph.health.checks import",
    "from mcp_server_langgraph.mcp.streaming import": "from mcp_server_langgraph.mcp.streaming import",
}


def update_imports_in_file(filepath: Path) -> bool:
    """Update imports in a single file. Returns True if changes were made."""
    try:
        content = filepath.read_text()
        original = content

        for old_import, new_import in IMPORT_MAP.items():
            content = content.replace(old_import, new_import)

        if content != original:
            filepath.write_text(content)
            print(f"✓ Updated: {filepath}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    """Update imports in all Python files."""
    project_root = Path(__file__).parent.parent

    # Directories to process
    dirs_to_process = [
        project_root / "src" / "mcp_server_langgraph",
        project_root / "tests",
        project_root / "examples",
        project_root / "scripts",
    ]

    files_updated = 0
    for directory in dirs_to_process:
        if not directory.exists():
            continue

        for py_file in directory.rglob("*.py"):
            if update_imports_in_file(py_file):
                files_updated += 1

    print(f"\n✓ Updated {files_updated} files")


if __name__ == "__main__":
    main()
