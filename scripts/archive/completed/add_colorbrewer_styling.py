#!/usr/bin/env python3
"""
Add ColorBrewer2 Set3 palette styling to unstyled flowchart diagrams.

This script identifies flowchart diagrams without classDef styling and adds
semantic ColorBrewer2 Set3 palette styling for visual consistency.
"""

import re
import sys
from pathlib import Path
from typing import Set


def extract_node_ids(content: str) -> set[str]:
    """
    Extract all node IDs from a flowchart diagram.

    Returns:
        Set of node IDs found in the diagram
    """
    node_ids = set()

    # Pattern for node definitions: NodeID[Label] or NodeID(Label) etc.
    node_patterns = [
        r"(\w+)\[",  # NodeID[Label]
        r"(\w+)\(",  # NodeID(Label)
        r"(\w+)\{",  # NodeID{Label}
        r"(\w+)>",  # NodeID>Label]
        r"(\w+)\[\[",  # NodeID[[Label]]
    ]

    for pattern in node_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            node_ids.add(match.group(1))

    # Also extract from connections: A --> B
    connection_pattern = r"(\w+)\s*[-=.]+>+\s*(\w+)"
    matches = re.finditer(connection_pattern, content)
    for match in matches:
        node_ids.add(match.group(1))
        node_ids.add(match.group(2))

    return node_ids


def categorize_nodes(node_ids: set[str]) -> dict:
    """
    Categorize nodes by semantic meaning based on naming conventions.

    Returns:
        Dict mapping category -> list of node IDs
    """
    categories = {
        "client": [],
        "server": [],
        "data": [],
        "cache": [],
        "infra": [],
        "security": [],
        "default": [],
    }

    for node_id in node_ids:
        lower_id = node_id.lower()

        if any(x in lower_id for x in ["client", "user", "browser", "app", "ui", "frontend"]):
            categories["client"].append(node_id)
        elif any(
            x in lower_id
            for x in [
                "server",
                "api",
                "backend",
                "service",
                "handler",
                "controller",
            ]
        ):
            categories["server"].append(node_id)
        elif any(x in lower_id for x in ["db", "database", "postgres", "sql", "storage", "data"]):
            categories["data"].append(node_id)
        elif any(x in lower_id for x in ["redis", "cache", "memcache"]):
            categories["cache"].append(node_id)
        elif any(x in lower_id for x in ["k8s", "kubernetes", "docker", "container", "pod"]):
            categories["infra"].append(node_id)
        elif any(x in lower_id for x in ["auth", "security", "vault", "secret", "key", "token"]):
            categories["security"].append(node_id)
        else:
            categories["default"].append(node_id)

    return categories


def generate_colorbrewer_styling(categories: dict) -> str:
    """
    Generate ColorBrewer2 Set3 palette classDef statements.

    Returns:
        String with classDef declarations and class assignments
    """
    # ColorBrewer2 Set3 palette (WCAG AA compliant)
    styles = {
        "client": "fill:#8dd3c7,stroke:#2a9d8f,stroke-width:2px,color:#333",
        "server": "fill:#fdb462,stroke:#e67e22,stroke-width:2px,color:#333",
        "data": "fill:#80b1d3,stroke:#3498db,stroke-width:2px,color:#333",
        "cache": "fill:#fb8072,stroke:#c0392b,stroke-width:2px,color:#333",
        "infra": "fill:#bebada,stroke:#8e44ad,stroke-width:2px,color:#333",
        "security": "fill:#bc80bd,stroke:#8e44ad,stroke-width:2px,color:#333",
        "default": "fill:#b3de69,stroke:#7cb342,stroke-width:2px,color:#333",
    }

    lines = ["\n    %% ColorBrewer2 Set3 palette styling"]

    # Generate classDef declarations
    for category, style in styles.items():
        if categories.get(category):
            lines.append(f"    classDef {category}Style {style}")

    lines.append("")

    # Generate class assignments
    for category, nodes in categories.items():
        if nodes and category in styles:
            nodes_str = ",".join(sorted(nodes))
            lines.append(f"    class {nodes_str} {category}Style")

    return "\n".join(lines)


def add_styling_to_diagram(content: str) -> str:
    """
    Add ColorBrewer2 styling to a flowchart diagram if it lacks classDef.

    Returns:
        Modified diagram content with styling added
    """
    # Check if already has classDef
    if re.search(r"classDef \w+Style", content):
        return content

    # Extract node IDs
    node_ids = extract_node_ids(content)
    if not node_ids:
        return content

    # Categorize nodes
    categories = categorize_nodes(node_ids)

    # Generate styling
    styling = generate_colorbrewer_styling(categories)

    # Insert before closing ```
    result = re.sub(r"(\n```)", styling + r"\1", content)

    return result


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single file and add ColorBrewer2 styling to flowcharts.

    Returns:
        True if file was modified, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Find all Mermaid flowchart blocks
        pattern = r"(```mermaid\nflowchart .*?\n```)"
        blocks = list(re.finditer(pattern, content, re.DOTALL))

        if not blocks:
            return False

        modified = False
        for match in reversed(blocks):  # Process in reverse to preserve indices
            block_content = match.group(1)
            styled = add_styling_to_diagram(block_content)

            if styled != block_content:
                start, end = match.span(1)
                content = content[:start] + styled + content[end:]
                modified = True

        if modified and not dry_run:
            file_path.write_text(content, encoding="utf-8")
            print(f"✅ Added styling: {file_path}")
            return True
        if modified:
            print(f"🔍 Would add styling: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Add ColorBrewer2 styling to unstyled flowchart diagrams")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be changed")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files with unstyled flowcharts
    mdx_files = []
    for f in docs_path.rglob("*.mdx"):
        if ".mintlify/templates" in str(f):
            continue

        content = f.read_text(encoding="utf-8")
        # Has flowchart but no classDef styling
        if re.search(r"^flowchart ", content, re.MULTILINE) and not re.search(r"classDef \w+Style", content):
            mdx_files.append(f)

    if not mdx_files:
        print("No unstyled flowchart diagrams found")
        return

    print(f"Found {len(mdx_files)} files with unstyled flowcharts\n")

    styled_count = 0
    for file_path in sorted(mdx_files):
        if process_file(file_path, args.dry_run):
            styled_count += 1

    print(f"\n{'Would add styling to' if args.dry_run else 'Added styling to'} {styled_count}/{len(mdx_files)} files")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
