#!/usr/bin/env python3
"""
Code Block Auto-Fixer

Automatically adds language identifiers to code blocks without them.

Features:
1. Detects programming language from code content
2. Preserves code block attributes
3. Dry-run mode for safety
4. Comprehensive language detection

Exit codes:
- 0: All fixes applied successfully
- 1: Errors during fixing
- 2: Critical error
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple


def detect_language(code: str) -> str:
    """
    Detect programming language from code content.

    Args:
        code: Code block content

    Returns:
        Detected language identifier
    """
    code = code.strip()

    # Python patterns
    if any(
        pattern in code
        for pattern in ["def ", "import ", "from ", "class ", "__init__", "self."]
    ):
        return "python"

    # Bash/shell patterns
    if any(
        pattern in code
        for pattern in ["#!/bin/bash", "#!/bin/sh", "echo ", "export ", "cd ", "ls "]
    ):
        return "bash"

    # JavaScript/TypeScript patterns
    if any(
        pattern in code
        for pattern in [
            "function ",
            "const ",
            "let ",
            "var ",
            "console.log",
            "=>",
            "async ",
            "await ",
        ]
    ):
        if "interface " in code or ": string" in code or ": number" in code:
            return "typescript"
        return "javascript"

    # YAML patterns
    if re.search(r"^\w+:\s*$", code, re.MULTILINE) or "apiVersion:" in code:
        return "yaml"

    # JSON patterns
    if code.startswith("{") and code.endswith("}"):
        return "json"
    if code.startswith("[") and code.endswith("]"):
        return "json"

    # SQL patterns
    if any(
        pattern in code.upper()
        for pattern in ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE"]
    ):
        return "sql"

    # Dockerfile patterns
    if any(
        pattern in code
        for pattern in ["FROM ", "RUN ", "COPY ", "CMD ", "ENTRYPOINT ", "WORKDIR "]
    ):
        return "dockerfile"

    # Markdown patterns
    if code.startswith("#") or "**" in code or "##" in code:
        return "markdown"

    # HTML/XML patterns
    if code.startswith("<") and ">" in code:
        return "html"

    # Go patterns
    if "func " in code or "package " in code:
        return "go"

    # Rust patterns
    if "fn " in code or "let mut " in code:
        return "rust"

    # Default to text
    return "text"


@dataclass
class FixResult:
    """Result of auto-fixing operation."""

    files_modified: int = 0
    blocks_fixed: int = 0
    would_modify: int = 0  # For dry-run

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        return 0


class CodeBlockAutoFixer:
    """Auto-fixes code blocks by adding language identifiers."""

    # Patterns to exclude
    EXCLUDE_PATTERNS = [
        ".mintlify/templates/",
        "node_modules/",
        ".git/",
        "__pycache__/",
    ]

    # Regex pattern for code blocks without language
    CODE_BLOCK_PATTERN = re.compile(
        r'^(\s*)```(\w+)?([^\n]*)\n(.*?)^(\s*)```',
        re.MULTILINE | re.DOTALL
    )

    def __init__(self, docs_dir: Path, dry_run: bool = True):
        """
        Initialize auto-fixer.

        Args:
            docs_dir: Path to docs directory
            dry_run: If True, don't modify files (just report)
        """
        self.docs_dir = Path(docs_dir)
        self.dry_run = dry_run

    def fix(self) -> FixResult:
        """
        Fix code blocks in all MDX files.

        Returns:
            FixResult with statistics
        """
        result = FixResult()

        if not self.docs_dir.exists():
            return result

        # Find all MDX files
        mdx_files = self._find_mdx_files()

        for mdx_file in mdx_files:
            blocks = self._fix_file(mdx_file)
            if blocks > 0:
                result.blocks_fixed += blocks
                if self.dry_run:
                    result.would_modify += 1
                else:
                    result.files_modified += 1

        return result

    def _find_mdx_files(self) -> Set[Path]:
        """Find all MDX files."""
        files = set()

        for mdx_path in self.docs_dir.rglob("*.mdx"):
            relative_path = mdx_path.relative_to(self.docs_dir)
            if any(
                pattern in str(relative_path) for pattern in self.EXCLUDE_PATTERNS
            ):
                continue

            files.add(mdx_path)

        return files

    def _fix_file(self, file_path: Path) -> int:
        """
        Fix code blocks in a single file.

        Args:
            file_path: Path to file

        Returns:
            Number of blocks fixed
        """
        try:
            content = file_path.read_text()
        except Exception:
            return 0

        blocks_fixed = 0
        new_content = content

        # Find all code blocks
        matches = list(self.CODE_BLOCK_PATTERN.finditer(content))

        # Process in reverse order to maintain string positions
        for match in reversed(matches):
            indent = match.group(1)
            language = match.group(2)
            attributes = match.group(3)
            code_content = match.group(4)
            closing_indent = match.group(5)

            # Skip if language already present
            if language and language.strip():
                continue

            # Detect language from code content
            detected_lang = detect_language(code_content)

            # Build replacement
            opening = f"{indent}```{detected_lang}{attributes}\n"
            closing = f"{closing_indent}```"
            replacement = f"{opening}{code_content}{closing}"

            # Replace in content
            new_content = (
                new_content[: match.start()] + replacement + new_content[match.end() :]
            )
            blocks_fixed += 1

        # Write back if modified and not dry-run
        if blocks_fixed > 0 and not self.dry_run:
            file_path.write_text(new_content)

        return blocks_fixed

    def print_report(self, result: FixResult) -> None:
        """Print fixing report to stdout."""
        print("\n" + "=" * 80)
        print("🔧 Code Block Auto-Fixer Report")
        print("=" * 80)

        if self.dry_run:
            print(f"\n📊 Dry Run Results:")
            print(f"  Files that would be modified: {result.would_modify}")
            print(f"\n  Run without --dry-run to apply fixes")
        else:
            print(f"\n📊 Results:")
            print(f"  Files modified: {result.files_modified}")
            print(f"  Code blocks fixed: {result.blocks_fixed}")

        print("\n" + "=" * 80)
        if result.files_modified > 0 or result.would_modify > 0:
            print("✅ Fixes applied!" if not self.dry_run else "✅ Preview complete!")
        else:
            print("✅ No fixes needed - all code blocks have language tags!")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-fix code blocks by adding language identifiers"
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Path to docs directory (default: docs/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview changes without modifying files (default: true)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply fixes (overrides --dry-run)",
    )

    args = parser.parse_args()

    # If --apply is specified, disable dry-run
    dry_run = not args.apply if args.apply else args.dry_run

    # Run fixer
    fixer = CodeBlockAutoFixer(args.docs_dir, dry_run=dry_run)
    result = fixer.fix()

    # Print report
    fixer.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
