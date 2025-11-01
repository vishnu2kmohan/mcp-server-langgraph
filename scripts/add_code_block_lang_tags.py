#!/usr/bin/env python3
"""
Automatically add language tags to code blocks missing them.

Intelligently detects the appropriate language from content context.
"""

import re
import sys
from pathlib import Path


def detect_language_from_content(content: str, context_before: str = "") -> str:  # noqa: C901
    """
    Detect programming language from code block content and surrounding context.

    Args:
        content: The code block content
        context_before: Text appearing before the code block for context

    Returns:
        Suggested language identifier
    """
    content_lower = content.lower()
    context_lower = context_before.lower()

    # Check Python patterns
    if any(
        pattern in content
        for pattern in [
            "import ",
            "from ",
            "def ",
            "class ",
            'if __name__ == "__main__"',
            "async def",
            "await ",
            "@",
            "pytest",
            "assert ",
        ]
    ):
        return "python"

    # Check shell/bash patterns
    if any(
        pattern in content
        for pattern in [
            "#!/bin/bash",
            "#!/bin/sh",
            "$ ",
            "export ",
            "echo ",
            "kubectl ",
            "docker ",
            "helm ",
            "gcloud ",
            "aws ",
            "curl ",
            "wget ",
            "ssh ",
            "git ",
            "npm ",
            "pip ",
            "apt-get ",
            "yum ",
            "systemctl ",
        ]
    ):
        return "bash"

    # Check if context mentions shell/terminal/command
    if any(x in context_lower for x in ["command:", "terminal:", "shell:", "run:", "execute:"]):
        return "bash"

    # Check for platform-specific query languages
    if "fields @timestamp" in content or "filter level" in content or "stats count()" in content:
        return "sql"  # CloudWatch Insights (SQL-like)

    if "promql" in context_lower or re.search(r'\{.*=".*"\}', content):
        return "promql"  # Prometheus queries

    if "logql" in context_lower or re.search(r"\|=.*\|", content):
        return "logql"  # Loki queries

    # Check YAML patterns
    if re.search(r"^\w+:\s*$", content, re.MULTILINE) and not content.strip().startswith("{"):
        if "---" in content or "apiVersion:" in content or "kind:" in content:
            return "yaml"

    # Check JSON patterns
    if content.strip().startswith("{") and content.strip().endswith("}"):
        if '"' in content and ":" in content:
            return "json"

    # Check JavaScript/TypeScript
    if any(
        pattern in content
        for pattern in [
            "const ",
            "let ",
            "var ",
            "function ",
            "=>",
            "import {",
            "export ",
            "interface ",
            "type ",
        ]
    ):
        if "interface " in content or "type " in content:
            return "typescript"
        return "javascript"

    # Check SQL
    if any(
        pattern in content_lower for pattern in ["select ", "insert ", "update ", "delete ", "create table", "alter table"]
    ):
        return "sql"

    # Check Dockerfile
    if any(pattern in content for pattern in ["FROM ", "RUN ", "COPY ", "WORKDIR ", "EXPOSE ", "CMD "]):
        return "dockerfile"

    # Check environment variables
    if re.match(r"^[A-Z_]+=", content.strip()):
        return "bash"

    # Check if it's output/logs (indented text, no code patterns)
    if all(line.startswith(" " * 4) or not line.strip() for line in content.split("\n")):
        return "text"

    # Check HTTP requests/responses
    if any(x in content for x in ["GET ", "POST ", "PUT ", "DELETE ", "HTTP/1.1", "Content-Type:"]):
        return "http"

    # Default to text for unclear cases
    return "text"


def add_language_tags(filepath: Path, dry_run: bool = False) -> int:
    """
    Add language tags to code blocks in a file.

    Returns:
        Number of blocks fixed
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.split("\n")
        modified_lines = []
        fixes = 0
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check for code block start without language tag
            if re.match(r"^(\s*)```\s*$", line):
                indent_match = re.match(r"^(\s*)```\s*$", line)
                indent = indent_match.group(1) if indent_match else ""

                # Get context before (up to 3 lines)
                context_before = "\n".join(lines[max(0, i - 3) : i])

                # Get code block content for language detection
                code_content_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    code_content_lines.append(lines[j])
                    j += 1

                code_content = "\n".join(code_content_lines)

                # Only add language tag if there's actual content (not a closing fence)
                if code_content.strip():
                    # Detect language
                    detected_lang = detect_language_from_content(code_content, context_before)

                    # Replace line with language-tagged version
                    modified_lines.append(f"{indent}```{detected_lang}")
                    fixes += 1
                else:
                    # This is a closing fence or empty block, keep as-is
                    modified_lines.append(line)
            else:
                modified_lines.append(line)

            i += 1

        if fixes > 0:
            if not dry_run:
                new_content = "\n".join(modified_lines)
                filepath.write_text(new_content, encoding="utf-8")
                print(f"✅ Fixed {fixes} blocks in {filepath}")
            else:
                print(f"🔍 Would fix {fixes} blocks in {filepath}")

        return fixes

    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}", file=sys.stderr)
        return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Add language tags to code blocks")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be changed")
    parser.add_argument("--limit", type=int, help="Limit number of files to process")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all markdown files
    md_files = list(docs_path.rglob("*.md")) + list(docs_path.rglob("*.mdx"))
    md_files = [f for f in md_files if ".mintlify/templates" not in str(f)]

    if args.limit:
        md_files = md_files[: args.limit]

    print(f"Processing {len(md_files)} documentation files...")
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made\n")

    total_fixes = 0
    files_modified = 0

    for filepath in sorted(md_files):
        fixes = add_language_tags(filepath, args.dry_run)
        if fixes > 0:
            total_fixes += fixes
            files_modified += 1

    print(f"\n{'=' * 80}")
    msg = f"{'Would fix' if args.dry_run else 'Fixed'} {total_fixes} code blocks"
    print(f"{msg} in {files_modified} files")
    print(f"{'=' * 80}")

    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
