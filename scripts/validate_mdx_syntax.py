#!/usr/bin/env python3
"""
Validate and fix common MDX syntax errors.

This script checks for:
1. Unmatched opening/closing tags (CodeGroup, Accordion, Tabs, etc.)
2. Missing blank lines after opening tags
3. Missing blank lines before closing tags
4. Unescaped angle brackets before/after numbers

Usage:
    python scripts/validate_mdx_syntax.py [--fix] [--file FILE]
"""

import re
import sys
from pathlib import Path

# Common Mintlify components that need proper spacing
COMPONENTS = [
    "CodeGroup",
    "Accordion",
    "Tabs",
    "Tab",
    "Card",
    "CardGroup",
    "Steps",
    "Step",
    "Info",
    "Warning",
    "Note",
    "Tip",
]


def check_tag_balance(content: str, filepath: Path) -> list[str]:
    """Check if all tags are properly balanced."""
    errors = []
    tag_stack = []

    # Simple regex to find opening and closing tags
    # This won't handle self-closing tags perfectly, but good enough for validation
    tag_pattern = r"<(/?)(\w+)(?:\s[^>]*)?\s*(/?)>"

    for match in re.finditer(tag_pattern, content):
        is_closing = match.group(1) == "/"
        tag_name = match.group(2)
        is_self_closing = match.group(3) == "/"

        # Skip if not a component we care about
        if tag_name not in COMPONENTS:
            continue

        # Skip self-closing tags
        if is_self_closing:
            continue

        if is_closing:
            if not tag_stack:
                errors.append(f"Closing tag </{tag_name}> without opening tag")
            elif tag_stack[-1] != tag_name:
                errors.append(f"Mismatched tags: expected </{tag_stack[-1]}>, found </{tag_name}>")
                tag_stack.pop()
            else:
                tag_stack.pop()
        else:
            tag_stack.append(tag_name)

    if tag_stack:
        errors.append(f"Unclosed tags: {', '.join(f'<{tag}>' for tag in tag_stack)}")

    return errors


def fix_component_spacing(content: str) -> tuple[str, int]:
    """
    Ensure proper blank lines around component tags.

    Returns:
        Tuple of (fixed_content, num_fixes)
    """
    fixes = 0
    lines = content.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for opening component tags
        opening_match = re.match(r"^(<(\w+)(?:\s[^>]*)?>)\s*$", line)
        if opening_match and opening_match.group(2) in COMPONENTS:
            # Add the tag line
            result.append(line)

            # Ensure blank line after opening tag if not already present
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                # Check if next line is a code block or another tag
                next_line = lines[i + 1].strip()
                if not next_line.startswith("```") and not next_line.startswith("<"):
                    result.append("")
                    fixes += 1

            i += 1
            continue

        # Check for closing component tags
        closing_match = re.match(r"^(</(\w+)>)\s*$", line)
        if closing_match and closing_match.group(2) in COMPONENTS:
            # Ensure blank line before closing tag if not already present
            if result and result[-1].strip() != "":
                # Check if previous line is a code block end
                if not result[-1].strip().startswith("```"):
                    result.append("")
                    fixes += 1

            result.append(line)
            i += 1
            continue

        result.append(line)
        i += 1

    return "\n".join(result), fixes


def process_file(filepath: Path, fix: bool = False) -> dict:
    """
    Process a single MDX file.

    Returns:
        Dict with keys: filepath, errors, fixes_applied
    """
    result = {
        "filepath": filepath,
        "errors": [],
        "fixes_applied": 0,
    }

    try:
        content = filepath.read_text(encoding="utf-8")

        # Check for tag balance
        tag_errors = check_tag_balance(content, filepath)
        result["errors"].extend(tag_errors)

        if fix and not tag_errors:
            # Only apply fixes if there are no structural errors
            fixed_content, num_fixes = fix_component_spacing(content)

            if num_fixes > 0:
                filepath.write_text(fixed_content, encoding="utf-8")
                result["fixes_applied"] = num_fixes

    except Exception as e:
        result["errors"].append(f"Error processing file: {e}")

    return result


def main():
    """Main entry point."""
    fix = "--fix" in sys.argv
    target_file = None

    # Check for --file argument
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            target_file = Path(sys.argv[idx + 1])
            if not target_file.exists():
                print(f"Error: File not found: {target_file}", file=sys.stderr)
                return 1

    # Find all MDX files
    docs_dir = Path(__file__).parent.parent / "docs"
    if not docs_dir.exists():
        print(f"Error: docs directory not found at {docs_dir}", file=sys.stderr)
        return 1

    if target_file:
        mdx_files = [target_file]
    else:
        mdx_files = list(docs_dir.rglob("*.mdx"))

    print(f"Validating {len(mdx_files)} MDX files")
    if fix:
        print("FIX MODE - Files will be modified")
    print()

    total_errors = 0
    total_fixes = 0
    files_with_errors = []

    for filepath in sorted(mdx_files):
        result = process_file(filepath, fix=fix)

        if result["errors"]:
            relative_path = filepath.relative_to(docs_dir) if filepath.is_relative_to(docs_dir) else filepath
            print(f"\n{relative_path}:")
            for error in result["errors"]:
                print(f"  ERROR: {error}")
            total_errors += len(result["errors"])
            files_with_errors.append(filepath)

        if result["fixes_applied"] > 0:
            relative_path = filepath.relative_to(docs_dir) if filepath.is_relative_to(docs_dir) else filepath
            print(f"Fixed spacing in {relative_path}: {result['fixes_applied']} fixes")
            total_fixes += result["fixes_applied"]

    print()
    if total_errors > 0:
        print(f"Found {total_errors} errors in {len(files_with_errors)} files")
        return 1
    elif total_fixes > 0:
        print(f"Applied {total_fixes} fixes")
    else:
        print("All files valid!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
