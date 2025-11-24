#!/usr/bin/env python3
"""
Add ColorBrewer2 styling to unstyled Mermaid flowchart/graph diagrams.

Only adds styling to graphs/flowcharts that lack classDef statements.
"""

import sys
from pathlib import Path

# Standard ColorBrewer2 Set3 palette for diagrams
STANDARD_STYLING = """
    %% ColorBrewer2 Set3 palette for visual consistency
    classDef primaryStyle fill:#8dd3c7,stroke:#2a9d8f,stroke-width:2px,color:#333
    classDef secondaryStyle fill:#fb8072,stroke:#e74c3c,stroke-width:2px,color:#333
    classDef tertiaryStyle fill:#fdb462,stroke:#e67e22,stroke-width:2px,color:#333
    classDef quaternaryStyle fill:#b3de69,stroke:#7cb342,stroke-width:2px,color:#333
    classDef dataStyle fill:#80b1d3,stroke:#3498db,stroke-width:2px,color:#333
    classDef serviceStyle fill:#bebada,stroke:#8e7cc3,stroke-width:2px,color:#333
"""


def add_styling_to_diagram(content: str) -> tuple[str, bool]:
    """
    Add styling to flowchart/graph diagrams that lack it.

    Returns:
        Tuple of (updated_content, was_modified)
    """
    modified = False
    lines = content.split("\n")
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a mermaid graph/flowchart start
        if line.strip() == "```mermaid":
            result_lines.append(line)
            i += 1

            # Check next line for diagram type
            if i < len(lines):
                next_line = lines[i].strip()

                # Only process graph/flowchart diagrams, not sequences
                if next_line.startswith(("graph ", "flowchart ")):
                    # Scan ahead to see if this diagram has classDef
                    has_styling = False
                    j = i
                    while j < len(lines) and lines[j].strip() != "```":
                        if "classDef " in lines[j]:
                            has_styling = True
                            break
                        j += 1

                    # If no styling, we'll add it before the closing ```
                    if not has_styling:
                        # Copy all lines until we hit the closing ```
                        while i < len(lines) and lines[i].strip() != "```":
                            result_lines.append(lines[i])
                            i += 1

                        # Add styling before the closing ```
                        result_lines.append(STANDARD_STYLING)
                        modified = True

                        # Add the closing ```
                        if i < len(lines):
                            result_lines.append(lines[i])
                        i += 1
                        continue

        result_lines.append(line)
        i += 1

    return "\n".join(result_lines), modified


def process_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single .mdx file.

    Returns:
        True if file was modified
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Only process files with mermaid diagrams
        if "```mermaid" not in content:
            return False

        # Skip if it only has sequence diagrams
        if "graph " not in content and "flowchart " not in content:
            return False

        updated_content, modified = add_styling_to_diagram(content)

        if modified:
            if dry_run:
                print(f"[DRY RUN] Would add styling to: {file_path}")
            else:
                file_path.write_text(updated_content, encoding="utf-8")
                print(f"✓ Added styling: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Add ColorBrewer2 styling to unstyled Mermaid diagrams")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files
    mdx_files = [f for f in docs_path.rglob("*.mdx") if ".mintlify/templates" not in str(f)]

    print(f"Scanning {len(mdx_files)} .mdx files for unstyled diagrams...")
    if args.dry_run:
        print("[DRY RUN MODE - No files will be modified]\n")

    modified_count = 0
    for file_path in sorted(mdx_files):
        if process_file(file_path, args.dry_run):
            modified_count += 1

    print(f"\n{'Would add styling to' if args.dry_run else 'Added styling to'}: {modified_count} file(s)")

    if args.dry_run and modified_count > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
