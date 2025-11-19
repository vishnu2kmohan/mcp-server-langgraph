#!/usr/bin/env python3
"""
Pre-commit hook to check Mermaid diagrams for ColorBrewer2 Set3 palette styling.

This script ensures all new Mermaid diagrams follow project standards:
1. Modern syntax (flowchart instead of graph)
2. ColorBrewer2 Set3 palette styling
3. Standard comment marker

Exit codes:
- 0: All checks passed
- 1: Issues found (with details)
"""

import sys
from pathlib import Path
from typing import List, Tuple


# ColorBrewer2 Set3 palette hex codes
COLORBREWER2_SET3_COLORS = {
    "#8dd3c7",
    "#ffffb3",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#d9d9d9",
    "#bc80bd",
    "#ccebc5",
}

# Stroke colors (darker variants)
COLORBREWER2_STROKE_COLORS = {
    "#2a9d8f",
    "#f1c40f",
    "#7e5eb0",
    "#e74c3c",
    "#3498db",
    "#e67e22",
    "#7cb342",
    "#ec7ab8",
    "#95a5a6",
    "#8e44ad",
    "#82c99a",
}

REQUIRED_COMMENT_PATTERN = r"%% ColorBrewer2 Set3 palette"


def extract_mermaid_blocks(content: str) -> list[tuple[int, str]]:
    """Extract all Mermaid code blocks with their starting line numbers."""
    blocks = []
    lines = content.split("\n")
    in_mermaid = False
    start_line = 0
    current_block = []

    for i, line in enumerate(lines, 1):
        if line.strip() == "```mermaid":
            in_mermaid = True
            start_line = i
            current_block = []
        elif in_mermaid and line.strip() == "```":
            in_mermaid = False
            blocks.append((start_line, "\n".join(current_block)))
        elif in_mermaid:
            current_block.append(line)

    return blocks


def is_flowchart_diagram(block: str) -> bool:
    """Check if diagram is a flowchart/graph (not sequence diagram)."""
    first_line = block.strip().split("\n")[0] if block.strip() else ""
    return first_line.startswith(("flowchart", "graph"))


def is_sequence_diagram(block: str) -> bool:
    """Check if diagram is a sequence diagram."""
    return "sequenceDiagram" in block or "%%{init:" in block


def uses_deprecated_graph_syntax(block: str) -> bool:
    """Check if diagram uses deprecated 'graph' syntax instead of 'flowchart'."""
    first_line = block.strip().split("\n")[0] if block.strip() else ""
    return first_line.startswith("graph ")


def has_colorbrewer2_styling(block: str) -> bool:
    """Check if diagram has ColorBrewer2 Set3 palette styling."""
    # Check for the required comment
    if REQUIRED_COMMENT_PATTERN not in block:
        return False

    # Check for at least one ColorBrewer2 color
    has_cb2_color = any(color.lower() in block.lower() for color in COLORBREWER2_SET3_COLORS)

    # Check for classDef statements
    has_classdef = "classDef" in block

    return has_cb2_color and has_classdef


def has_sequence_theme(block: str) -> bool:
    """Check if sequence diagram has ColorBrewer2 theme initialization."""
    if not is_sequence_diagram(block):
        return True  # Not applicable to non-sequence diagrams

    # Check for theme initialization with ColorBrewer2 colors
    return "%%{init:" in block and any(color.lower() in block.lower() for color in COLORBREWER2_SET3_COLORS)


def check_file(file_path: Path) -> list[str]:
    """Check a single file for Mermaid diagram styling issues."""
    issues = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{file_path}: ERROR reading file: {e}"]

    blocks = extract_mermaid_blocks(content)

    if not blocks:
        return []  # No Mermaid diagrams in file

    for line_num, block in blocks:
        # Skip if this is an internal doc (not user-facing)
        if "docs-internal" in str(file_path) or "reports/" in str(file_path):
            continue

        # Check for deprecated graph syntax
        if uses_deprecated_graph_syntax(block):
            issues.append(f"{file_path}:{line_num}: ❌ Uses deprecated 'graph' syntax - use 'flowchart TD/TB/LR/BT' instead")

        # Check flowchart diagrams for ColorBrewer2 styling
        if is_flowchart_diagram(block) and not has_colorbrewer2_styling(block):
            issues.append(
                f"{file_path}:{line_num}: ❌ Missing ColorBrewer2 Set3 palette styling\n"
                f"    Add: %% ColorBrewer2 Set3 palette - each component type uniquely colored\n"
                f"    See: docs/.mintlify/MERMAID_OPTIMIZATION_GUIDE.md"
            )

        # Check sequence diagrams for theme
        if is_sequence_diagram(block) and not has_sequence_theme(block):
            issues.append(
                f"{file_path}:{line_num}: ⚠️  Sequence diagram missing ColorBrewer2 theme\n"
                f"    Add %%{{init: ...}}%% block at the start\n"
                f"    See: docs/.mintlify/MERMAID_OPTIMIZATION_GUIDE.md"
            )

    return issues


def main():
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: check_mermaid_styling.py <file1> <file2> ...")
        sys.exit(0)

    all_issues = []

    for file_path in sys.argv[1:]:
        path = Path(file_path)
        if path.suffix in [".mdx", ".md"]:
            issues = check_file(path)
            all_issues.extend(issues)

    if all_issues:
        print("🎨 Mermaid Diagram Styling Issues Found:\n")
        for issue in all_issues:
            print(issue)
        print("\n" + "=" * 80)
        print("📖 See docs/.mintlify/MERMAID_OPTIMIZATION_GUIDE.md for templates")
        print("=" * 80)
        sys.exit(1)
    else:
        print("✅ All Mermaid diagrams follow ColorBrewer2 Set3 standards")
        sys.exit(0)


if __name__ == "__main__":
    main()
