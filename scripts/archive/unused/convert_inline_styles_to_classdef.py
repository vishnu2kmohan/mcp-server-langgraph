#!/usr/bin/env python3
"""
Convert inline Mermaid `style` statements to reusable `classDef` patterns.

This script finds all inline style statements in Mermaid diagrams and converts them
to classDef declarations with class assignments for better maintainability.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path


def extract_inline_styles(content: str) -> list[tuple[str, str]]:
    """
    Extract inline style statements from Mermaid diagram.

    Returns:
        List of (node_id, style_string) tuples
    """
    pattern = (
        r"^\s*style\s+(\w+)\s+fill:(#[0-9a-fA-F]{6}),"
        r"stroke:(#[0-9a-fA-F]{6}),stroke-width:(\d+)px"
        r"(?:,color:(#[0-9a-fA-F]{3,6}))?"
    )
    styles = []

    for match in re.finditer(pattern, content, re.MULTILINE):
        node_id = match.group(1)
        fill = match.group(2)
        stroke = match.group(3)
        width = match.group(4)
        color = match.group(5) if match.group(5) else "#333"
        style_str = f"fill:{fill},stroke:{stroke},stroke-width:{width}px,color:{color}"
        styles.append((node_id, style_str))

    return styles


def group_styles_by_pattern(styles: list[tuple[str, str]]) -> dict[str, list[str]]:
    """
    Group nodes by their style pattern.

    Returns:
        Dict mapping style_pattern -> list of node_ids
    """
    grouped = defaultdict(list)
    for node_id, style_str in styles:
        grouped[style_str].append(node_id)
    return dict(grouped)


def generate_classdef_section(grouped_styles: dict[str, list[str]]) -> str:
    """
    Generate classDef declarations and class assignments.

    Returns:
        String with classDef and class statements
    """
    lines = ["\n    %% ColorBrewer2 + semantic color palette styling"]
    class_counter = 1
    class_assignments = []

    # Generate classDef declarations
    for style_str, node_ids in grouped_styles.items():
        class_name = f"style{class_counter}"
        lines.append(f"    classDef {class_name} {style_str}")
        class_assignments.append((class_name, node_ids))
        class_counter += 1

    lines.append("")

    # Generate class assignments
    for class_name, node_ids in class_assignments:
        nodes_str = ",".join(node_ids)
        lines.append(f"    class {nodes_str} {class_name}")

    return "\n".join(lines)


def convert_diagram(content: str) -> str:
    """
    Convert inline styles to classDef in a Mermaid diagram block.
    """
    # Extract inline styles
    styles = extract_inline_styles(content)
    if not styles:
        return content

    # Group by pattern
    grouped = group_styles_by_pattern(styles)

    # Generate classDef section
    classdef_section = generate_classdef_section(grouped)

    # Remove inline style statements
    pattern = (
        r"^\s*style\s+\w+\s+fill:#[0-9a-fA-F]{6},stroke:#[0-9a-fA-F]{6},stroke-width:\d+px(?:,color:#[0-9a-fA-F]{3,6})?\n?"
    )
    result = re.sub(pattern, "", content, flags=re.MULTILINE)

    # Insert classDef section before closing ```
    result = re.sub(r"(\n```)", classdef_section + r"\1", result)

    return result


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single file and convert inline styles.

    Returns:
        True if file was modified, False otherwise
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Find all Mermaid blocks
        mermaid_blocks = list(re.finditer(r"```mermaid\n(.*?)\n```", content, re.DOTALL))

        if not mermaid_blocks:
            return False

        modified = False
        for match in reversed(mermaid_blocks):  # Process in reverse to preserve indices
            block_content = match.group(1)
            converted = convert_diagram(block_content)

            if converted != block_content:
                start, end = match.span(1)
                content = content[:start] + converted + content[end:]
                modified = True

        if modified and not dry_run:
            file_path.write_text(content, encoding="utf-8")
            print(f"✅ Converted: {file_path}")
            return True
        elif modified:
            print(f"🔍 Would convert: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert inline Mermaid styles to classDef")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be changed")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files with inline styles
    mdx_files = []
    for f in docs_path.rglob("*.mdx"):
        if ".mintlify/templates" in str(f):
            continue
        content = f.read_text(encoding="utf-8")
        if re.search(r"^\s*style\s+\w+\s+fill:", content, re.MULTILINE):
            mdx_files.append(f)

    if not mdx_files:
        print("No files with inline styles found")
        return

    print(f"Found {len(mdx_files)} files with inline styles\n")

    converted_count = 0
    for file_path in sorted(mdx_files):
        if process_file(file_path, args.dry_run):
            converted_count += 1

    print(f"\n{'Would convert' if args.dry_run else 'Converted'} {converted_count}/{len(mdx_files)} files")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
