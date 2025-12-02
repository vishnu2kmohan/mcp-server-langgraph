#!/usr/bin/env python3
"""
Add YAML frontmatter to Claude Code slash commands.

This script adds frontmatter with description and argument-hint
to all markdown files in .claude/commands/ that don't already have it.

Usage:
    python scripts/workflow/add-command-frontmatter.py
    python scripts/workflow/add-command-frontmatter.py --dry-run
"""

import argparse
import re
from pathlib import Path


def extract_description(content: str, filename: str) -> str:
    """Extract a brief description from the command content."""
    # Try to find Purpose or first meaningful line
    lines = content.split("\n")

    for line in lines[:15]:  # Check first 15 lines
        # Skip title and empty lines
        if line.startswith("#") or not line.strip():
            continue
        # Skip usage lines
        if line.lower().startswith("**usage**") or line.startswith("`/"):
            continue
        # Look for Purpose line
        if "**Purpose**" in line or "Purpose:" in line:
            desc = re.sub(r"\*\*Purpose\*\*:?\s*", "", line)
            desc = desc.strip()
            if desc:
                return desc[:100]  # Limit to 100 chars
        # Use first non-empty descriptive line
        if len(line.strip()) > 10 and not line.startswith("**"):
            return line.strip()[:100]

    # Fallback: generate from filename
    name = filename.replace(".md", "").replace("-", " ").title()
    return f"Run {name} workflow"


def extract_argument_hint(content: str) -> str | None:
    """Extract argument hint from usage line."""
    # Look for **Usage**: patterns
    match = re.search(r"\*\*Usage\*\*:?\s*`?/[\w-]+\s+([^`\n]+)", content)
    if match:
        hint = match.group(1).strip()
        # Clean up the hint
        hint = re.sub(r"`$", "", hint)
        hint = re.sub(r"\s+or\s+.*", "", hint)  # Remove "or" alternatives
        if hint and hint != "$ARGUMENTS":
            return hint

    # Check for $ARGUMENTS or $1 patterns
    if "$ARGUMENTS" in content or "$1" in content:
        # Try to find scope/type hints
        if "<scope>" in content.lower():
            return "<scope>"
        if "<type>" in content.lower():
            return "<type>"
        if "<error" in content.lower():
            return "<error>"
        if "<number>" in content.lower() or "<pr" in content.lower():
            return "<number>"
        return "<args>"

    return None


def has_frontmatter(content: str) -> bool:
    """Check if content already has YAML frontmatter."""
    return content.strip().startswith("---")


def add_frontmatter(filepath: Path, dry_run: bool = False) -> bool:
    """Add frontmatter to a command file."""
    content = filepath.read_text()

    if has_frontmatter(content):
        print(f"  ⏭️  {filepath.name} - already has frontmatter")
        return False

    description = extract_description(content, filepath.name)
    argument_hint = extract_argument_hint(content)

    # Build frontmatter
    frontmatter_lines = [
        "---",
        f"description: {description}",
    ]

    if argument_hint:
        frontmatter_lines.append(f"argument-hint: {argument_hint}")

    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines) + "\n"

    new_content = frontmatter + content

    if dry_run:
        print(f"  📝 {filepath.name}")
        print(f"      description: {description}")
        if argument_hint:
            print(f"      argument-hint: {argument_hint}")
    else:
        filepath.write_text(new_content)
        print(f"  ✅ {filepath.name}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Add frontmatter to Claude Code commands")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    # Find repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    commands_dir = repo_root / ".claude" / "commands"

    if not commands_dir.exists():
        print(f"ERROR: Commands directory not found: {commands_dir}")
        return 1

    print(f"{'DRY RUN: ' if args.dry_run else ''}Adding frontmatter to commands in {commands_dir}\n")

    updated = 0
    skipped = 0

    for md_file in sorted(commands_dir.glob("*.md")):
        # Skip README
        if md_file.name == "README.md":
            continue

        if add_frontmatter(md_file, args.dry_run):
            updated += 1
        else:
            skipped += 1

    print(f"\n{'Would update' if args.dry_run else 'Updated'}: {updated} files")
    print(f"Skipped (already have frontmatter): {skipped} files")

    return 0


if __name__ == "__main__":
    exit(main())
