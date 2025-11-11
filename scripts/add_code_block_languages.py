#!/usr/bin/env python3
"""
Add language identifiers to code blocks in Markdown/MDX files.

This script automatically detects and adds language tags to untagged code blocks
based on content patterns. It's designed to be safe and preserve existing formatting.

Usage:
    python scripts/add_code_block_languages.py [files...]
    python scripts/add_code_block_languages.py docs/**/*.mdx
    python scripts/add_code_block_languages.py --dry-run docs/**/*.mdx
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class LanguageDetector:
    """Detect programming language from code block content."""

    # Language detection patterns (ordered by specificity)
    PATTERNS = [
        # Shell/Bash (most specific first)
        (r"^(?:#!/bin/(?:ba)?sh|#!/usr/bin/env (?:ba)?sh)", "bash"),
        (r"^(?:\$ |> |# )", "bash"),  # Shell prompt
        (
            r"\b(?:apt-get|yum|brew|npm|pip|cargo|go|kubectl|docker|helm|git|make|curl|wget|chmod|chown|ls|cd|mkdir|rm|cp|mv|cat|grep|sed|awk|export|source)\s",
            "bash",
        ),
        # Python
        (r"^(?:#!/usr/bin/env python|#!/usr/bin/python)", "python"),
        (r"\b(?:def|class|import|from|async\s+def|yield|lambda|with|as|try|except|finally|raise|assert)\s", "python"),
        (r"^(?:@pytest\.|@dataclass|@property|@staticmethod|@classmethod)", "python"),
        (r"\bprint\s*\(", "python"),
        # JavaScript/TypeScript
        (
            r"\b(?:const|let|var|function|async\s+function|=>|import\s+.*\s+from|export\s+(?:default|const|function))\s",
            "javascript",
        ),
        (r"\b(?:interface|type\s+\w+\s*=|enum|namespace|declare)\s", "typescript"),
        (r"^(?:import|export)\s+.*\s+from\s+['\"]", "javascript"),
        (r"console\.log\(", "javascript"),
        # Go
        (r"^package\s+\w+", "go"),
        (r"\bfunc\s+\w+\s*\(", "go"),
        (r"\b(?:import|var|const|type|struct|interface)\s", "go"),
        # Rust
        (r"\b(?:fn|impl|trait|struct|enum|mod|use|pub)\s", "rust"),
        (r"^#\[derive\(", "rust"),
        # JSON (strict)
        (r"^\s*\{[\s\n]*\"[\w-]+\"\s*:", "json"),
        (r"^\s*\[[\s\n]*\{[\s\n]*\"", "json"),
        # YAML
        (r"^[\w-]+:\s*(?:\||>|-|\[|\{)?", "yaml"),
        (r"^-\s+[\w-]+:", "yaml"),
        (r"^apiVersion:", "yaml"),  # Kubernetes
        (r"^kind:", "yaml"),
        # TOML
        (r"^\[[\w.-]+\]", "toml"),
        (r"^[\w-]+\s*=\s*['\"]", "toml"),
        # Environment files
        (r"^[A-Z_][A-Z0-9_]*=", "bash"),  # Environment variables
        # SQL
        (r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|FROM|WHERE|JOIN|GROUP BY|ORDER BY)\b", "sql"),
        # Dockerfile
        (r"^FROM\s+[\w/:.-]+", "dockerfile"),
        (r"^(?:RUN|CMD|COPY|ADD|WORKDIR|EXPOSE|ENV|ARG|ENTRYPOINT|VOLUME|USER)\s", "dockerfile"),
        # HTML
        (r"^<!DOCTYPE html>", "html"),
        (r"^<(?:html|head|body|div|span|p|a|script|style)", "html"),
        # CSS
        (r"^[\w.-]+\s*\{", "css"),
        (r"^@(?:media|import|font-face|keyframes)", "css"),
        # Makefile
        (r"^[\w-]+:(?:\s|$)", "makefile"),
        (r"^\t(?:@)?(?:cd|mkdir|rm|cp|echo)", "makefile"),
        # XML
        (r"^<\?xml", "xml"),
        # Nginx config
        (r"^server\s*\{", "nginx"),
        (r"^location\s+", "nginx"),
        # INI
        (r"^\[[\w\s.-]+\]", "ini"),
        # Protocol Buffers
        (r"^syntax\s*=\s*\"proto", "protobuf"),
        (r"^message\s+\w+\s*\{", "protobuf"),
    ]

    @classmethod
    def detect(cls, content: str) -> Optional[str]:
        """
        Detect programming language from code block content.

        Args:
            content: The code block content

        Returns:
            Detected language identifier or None
        """
        # Strip leading/trailing whitespace for detection
        content = content.strip()
        if not content:
            return None

        # Try each pattern
        for pattern, language in cls.PATTERNS:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return language

        # Special case: looks like JSON but isn't strict (allow as text)
        if re.match(r"^\s*[\{\[]", content):
            # Could be JSON, but not confident enough
            return "json"

        # Default: no detection
        return None


class CodeBlockProcessor:
    """Process Markdown/MDX files to add language tags to code blocks."""

    # Regex to find code blocks without language tags
    CODE_BLOCK_PATTERN = re.compile(r"^```\s*$\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)

    def __init__(self, dry_run: bool = False):
        """
        Initialize processor.

        Args:
            dry_run: If True, don't modify files, just report
        """
        self.dry_run = dry_run
        self.stats = {
            "files_processed": 0,
            "files_modified": 0,
            "blocks_tagged": 0,
            "blocks_untagged": 0,
        }

    def process_file(self, file_path: Path) -> bool:
        """
        Process a single Markdown/MDX file.

        Args:
            file_path: Path to the file

        Returns:
            True if file was modified
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
            return False

        modified_content, modifications = self._process_content(content)

        self.stats["files_processed"] += 1

        if modifications:
            self.stats["files_modified"] += 1
            self.stats["blocks_tagged"] += len(modifications)

            if self.dry_run:
                print(f"🔍 Would modify {file_path}:")
                for lang, count in modifications.items():
                    print(f"   - Add {count}x '{lang}' tags")
            else:
                try:
                    file_path.write_text(modified_content, encoding="utf-8")
                    print(f"✅ Modified {file_path}:")
                    for lang, count in modifications.items():
                        print(f"   - Added {count}x '{lang}' tags")
                except Exception as e:
                    print(f"❌ Error writing {file_path}: {e}", file=sys.stderr)
                    return False

            return True

        return False

    def _process_content(self, content: str) -> Tuple[str, dict]:
        """
        Process file content to add language tags.

        Args:
            content: File content

        Returns:
            Tuple of (modified_content, modifications_dict)
        """
        modifications = {}

        def replace_block(match: re.Match) -> str:
            """Replace code block with language-tagged version."""
            code_content = match.group(1)

            # Detect language
            detected_lang = LanguageDetector.detect(code_content)

            if detected_lang:
                # Track modification
                modifications[detected_lang] = modifications.get(detected_lang, 0) + 1
                # Return tagged block
                return f"```{detected_lang}\n{code_content}```\n"
            else:
                # No detection - leave as-is
                self.stats["blocks_untagged"] += 1
                return match.group(0)

        modified_content = self.CODE_BLOCK_PATTERN.sub(replace_block, content)

        return modified_content, modifications

    def print_summary(self):
        """Print processing summary."""
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Files processed:     {self.stats['files_processed']}")
        print(f"Files modified:      {self.stats['files_modified']}")
        print(f"Blocks tagged:       {self.stats['blocks_tagged']}")
        print(f"Blocks untagged:     {self.stats['blocks_untagged']}")
        print("=" * 60)

        if self.dry_run:
            print("\n⚠️  DRY RUN - No files were modified")
        else:
            print(f"\n✅ {self.stats['blocks_tagged']} code blocks tagged successfully")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add language tags to code blocks in Markdown/MDX files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all MDX files in docs/
  python scripts/add_code_block_languages.py docs/**/*.mdx

  # Dry run to see what would be changed
  python scripts/add_code_block_languages.py --dry-run docs/**/*.mdx

  # Process specific files
  python scripts/add_code_block_languages.py README.md CONTRIBUTING.md
        """,
    )
    parser.add_argument("files", nargs="+", type=Path, help="Markdown/MDX files to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without modifying files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Expand glob patterns
    files: List[Path] = []
    for file_pattern in args.files:
        # Convert string to Path if needed
        if isinstance(file_pattern, str):
            file_pattern = Path(file_pattern)

        # If it's a glob pattern, expand it
        if "*" in str(file_pattern):
            parent = file_pattern.parent
            pattern = file_pattern.name
            files.extend(parent.glob(pattern))
        elif file_pattern.exists():
            files.append(file_pattern)
        else:
            print(f"⚠️  File not found: {file_pattern}", file=sys.stderr)

    if not files:
        print("❌ No files to process", file=sys.stderr)
        sys.exit(1)

    # Process files
    processor = CodeBlockProcessor(dry_run=args.dry_run)

    for file_path in files:
        if file_path.suffix in {".md", ".mdx"}:
            processor.process_file(file_path)
        else:
            if args.verbose:
                print(f"⏭️  Skipping {file_path} (not a Markdown file)")

    # Print summary
    processor.print_summary()

    # Exit code
    sys.exit(0 if processor.stats["files_modified"] == 0 else 0)


if __name__ == "__main__":
    main()
