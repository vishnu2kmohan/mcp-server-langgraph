#!/usr/bin/env python3
"""
Validate all Mermaid diagrams using the Mermaid CLI (mmdc).

Extracts each diagram from .mdx files and validates them individually.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple


def extract_mermaid_diagrams(content: str) -> List[Tuple[int, str]]:
    """
    Extract all Mermaid diagrams from content.

    Returns:
        List of (line_number, diagram_content) tuples
    """
    diagrams = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        if lines[i].strip() == "```mermaid":
            start_line = i + 1
            diagram_lines = []
            i += 1

            while i < len(lines) and lines[i].strip() != "```":
                diagram_lines.append(lines[i])
                i += 1

            if diagram_lines:
                diagrams.append((start_line, "\n".join(diagram_lines)))

        i += 1

    return diagrams


def validate_diagram(diagram_content: str) -> Tuple[bool, str]:
    """
    Validate a Mermaid diagram using mmdc CLI.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
            f.write(diagram_content)
            input_file = f.name

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_file = f.name

        # Run mmdc to validate and render
        result = subprocess.run(["mmdc", "-i", input_file, "-o", output_file], capture_output=True, text=True, timeout=10)

        # Clean up
        Path(input_file).unlink(missing_ok=True)
        Path(output_file).unlink(missing_ok=True)

        if result.returncode != 0:
            # Extract error message
            error_msg = result.stderr or result.stdout
            # Get just the error line
            if "Error:" in error_msg:
                error_lines = [line for line in error_msg.split("\n") if "Error:" in line or "Expecting" in line]
                return False, "\n".join(error_lines[:2])
            return False, error_msg[:200]

        return True, ""

    except subprocess.TimeoutExpired:
        return False, "Validation timeout"
    except Exception as e:
        return False, str(e)


def validate_file(file_path: Path) -> List[Tuple[int, str]]:
    """
    Validate all Mermaid diagrams in a file.

    Returns:
        List of (line_number, error_message) tuples for failed diagrams
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        diagrams = extract_mermaid_diagrams(content)

        errors = []
        for line_num, diagram in diagrams:
            is_valid, error_msg = validate_diagram(diagram)
            if not is_valid:
                errors.append((line_num, error_msg))

        return errors

    except Exception as e:
        return [(0, f"Error reading file: {e}")]


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate all Mermaid diagrams with mmdc CLI")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all diagrams, not just errors")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .mdx files
    mdx_files = [f for f in docs_path.rglob("*.mdx") if ".mintlify/templates" not in str(f)]

    print(f"Validating Mermaid diagrams in {len(mdx_files)} .mdx files...\n")

    total_diagrams = 0
    total_errors = 0
    files_with_errors = []

    for file_path in sorted(mdx_files):
        content = file_path.read_text(encoding="utf-8")
        diagrams = extract_mermaid_diagrams(content)

        if not diagrams:
            continue

        total_diagrams += len(diagrams)
        errors = validate_file(file_path)

        if errors:
            total_errors += len(errors)
            files_with_errors.append(file_path)
            print(f"❌ {file_path} ({len(diagrams)} diagram(s), {len(errors)} error(s))")
            for line_num, error_msg in errors:
                print(f"   Line {line_num}: {error_msg}")
        elif args.verbose:
            print(f"✅ {file_path} ({len(diagrams)} diagram(s))")

    print(f"\n{'=' * 80}")
    print(f"Total diagrams: {total_diagrams}")
    print(f"Valid diagrams: {total_diagrams - total_errors}")
    print(f"Invalid diagrams: {total_errors}")
    print(f"Files with errors: {len(files_with_errors)}")
    print(f"{'=' * 80}")

    if total_errors > 0:
        print("\n❌ Validation failed")
        sys.exit(1)
    else:
        print("\n✅ All Mermaid diagrams are valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
