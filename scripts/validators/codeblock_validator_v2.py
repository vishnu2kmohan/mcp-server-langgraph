#!/usr/bin/env python3
"""
Improved code block validator with state-machine based tracking and smart language detection.

This validator addresses the issues in previous versions:
1. Uses state machine to properly track opening vs closing fences
2. Smarter language detection that avoids inappropriate tagging
3. Distinguishes comment-only, env-var-only, and output blocks
4. Never tags closing fences with language identifiers
5. Comprehensive reporting with dry-run mode

Usage:
    python scripts/validators/codeblock_validator_v2.py [--fix] [--dry-run] [--path PATH]

Examples:
    # Validate only (report issues without fixing)
    python scripts/validators/codeblock_validator_v2.py --path docs

    # Preview fixes
    python scripts/validators/codeblock_validator_v2.py --fix --dry-run --path docs

    # Apply fixes
    python scripts/validators/codeblock_validator_v2.py --fix --path docs
"""

import argparse
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple


class BlockType(Enum):
    """Type of content in a code block."""

    UNKNOWN = "unknown"
    BASH_SCRIPT = "bash"
    PYTHON_CODE = "python"
    JAVASCRIPT_CODE = "javascript"
    TYPESCRIPT_CODE = "typescript"
    YAML_CONFIG = "yaml"
    JSON_DATA = "json"
    ENV_VARS = "env"
    DOCKERFILE = "dockerfile"
    SQL_QUERY = "sql"
    HTML_MARKUP = "html"
    XML_MARKUP = "xml"
    TERRAFORM_HCL = "hcl"
    GO_CODE = "go"
    RUST_CODE = "rust"
    # Special cases
    COMMENT_ONLY = "text"  # Only comments, no actual code
    TREE_STRUCTURE = "text"  # Directory tree output
    COMMAND_OUTPUT = "text"  # Output from running commands
    PLAIN_TEXT = "text"  # Plain text, prose, or mixed content
    EMPTY = ""  # Empty block - no language tag


@dataclass
class CodeBlock:
    """Represents a code block in a Markdown file."""

    start_line: int
    end_line: int
    opening_fence: str
    closing_fence: str
    content: str
    has_language_tag: bool
    language_tag: Optional[str]
    detected_type: BlockType


class SmartLanguageDetector:
    """
    Smart language detector that avoids inappropriate tagging.

    Rules:
    1. Comment-only blocks → text
    2. Environment variables only → env
    3. Tree structure output → text
    4. Empty blocks → no tag
    5. Mixed content → text
    6. Only tag as programming language if confident
    """

    @staticmethod
    def detect(content: str) -> BlockType:
        """
        Detect block type from content.

        Args:
            content: Code block content

        Returns:
            Detected block type
        """
        content = content.strip()

        # Rule 1: Empty blocks
        if not content:
            return BlockType.EMPTY

        lines = [line for line in content.split("\n") if line.strip()]

        if not lines:
            return BlockType.EMPTY

        # Rule 2: Tree structure (uses box-drawing characters)
        if SmartLanguageDetector._is_tree_structure(content):
            return BlockType.TREE_STRUCTURE

        # Rule 3: Comment-only blocks
        if SmartLanguageDetector._is_comment_only(lines):
            return BlockType.COMMENT_ONLY

        # Rule 4: Environment variables only
        if SmartLanguageDetector._is_env_vars_only(lines):
            return BlockType.ENV_VARS

        # Rule 5: Command output (looks like terminal output)
        if SmartLanguageDetector._is_command_output(content):
            return BlockType.COMMAND_OUTPUT

        # Rule 6: Programming languages (high confidence only)
        detected = SmartLanguageDetector._detect_programming_language(content)
        if detected:
            return detected

        # Rule 7: Data formats
        detected = SmartLanguageDetector._detect_data_format(content)
        if detected:
            return detected

        # Default: Plain text for mixed or uncertain content
        return BlockType.PLAIN_TEXT

    @staticmethod
    def _is_tree_structure(content: str) -> bool:
        """Check if content is a directory tree structure."""
        tree_chars = ["├──", "└──", "│", "─"]
        return any(char in content for char in tree_chars)

    @staticmethod
    def _is_comment_only(lines: List[str]) -> bool:
        """Check if all lines are comments (no actual code)."""
        if not lines:
            return False

        comment_patterns = [
            r"^\s*#",  # Shell/Python comment
            r"^\s*//",  # C-style comment
            r"^\s*<!--",  # HTML comment
            r"^\s*\*",  # Block comment continuation
            r"^\s*-\s+",  # Markdown list item (often in comment blocks)
            r"^\s*##",  # Markdown headers (often in comment examples)
        ]

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            # Check if line matches any comment pattern
            is_comment = any(re.match(pattern, line) for pattern in comment_patterns)

            # If we find a non-comment line, it's not comment-only
            if not is_comment:
                return False

        return True

    @staticmethod
    def _is_env_vars_only(lines: List[str]) -> bool:
        """Check if all non-empty lines are environment variable definitions."""
        if not lines:
            return False

        env_var_pattern = r"^[A-Z_][A-Z0-9_]*\s*="

        for line in lines:
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith("#"):
                continue

            # Check if line is an env var assignment
            if not re.match(env_var_pattern, line.strip()):
                return False

        return True

    @staticmethod
    def _is_command_output(content: str) -> bool:
        """
        Check if content looks like command output (not executable commands).

        Indicators of output:
        - Error messages
        - Stack traces
        - Log entries with timestamps
        - HTTP response headers
        - JSON/YAML-like output but with noise
        """
        output_patterns = [
            r"Error:|ERROR:",  # Error messages
            r"Traceback \(most recent call last\):",  # Python traceback
            r"^\s*at\s+.*\(.*:\d+:\d+\)",  # JavaScript stack trace
            r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",  # Timestamp logs
            r"^HTTP/\d\.\d\s+\d{3}",  # HTTP response status
            r"^>\s+",  # Output indicators
        ]

        return any(re.search(pattern, content, re.MULTILINE) for pattern in output_patterns)

    @staticmethod
    def _detect_programming_language(content: str) -> Optional[BlockType]:
        """
        Detect programming language (high confidence only).

        Returns None if not confident enough.
        """
        # Python (high confidence indicators)
        python_indicators = [
            r"^#!/usr/bin/(?:env\s+)?python",
            r"\bdef\s+\w+\s*\(",
            r"\bclass\s+\w+\s*[\(:]",
            r"\basync\s+def\s+\w+",
            r"^from\s+\w+\s+import\s+",
            r"^import\s+\w+",
            r"@pytest\.",
            r"@dataclass\b",
        ]

        if any(re.search(p, content, re.MULTILINE) for p in python_indicators):
            return BlockType.PYTHON_CODE

        # Bash/Shell (high confidence - actual commands, not just comments)
        bash_indicators = [
            r"^#!/bin/(ba)?sh",
            r"^\s*(?:if|then|else|elif|fi|for|while|do|done|case|esac)\s",
            r"^\s*function\s+\w+",
            r"(?:^|\n)\s*(?:export|source)\s+\w+",
        ]

        # Only tag as bash if we see actual shell constructs (not just commands)
        if any(re.search(p, content, re.MULTILINE) for p in bash_indicators):
            return BlockType.BASH_SCRIPT

        # Check for common shell commands (but not if they're only in comments)
        shell_commands = [
            "curl", "wget", "apt-get", "apt", "yum", "brew", "docker", "kubectl",
            "helm", "git", "npm", "yarn", "pnpm", "pip", "uv", "cargo", "go",
            "make", "cmake", "cd", "ls", "pwd", "mkdir", "rm", "cp", "mv",
            "chmod", "chown", "cat", "grep", "sed", "awk", "find", "ssh",
            "scp", "rsync", "tar", "gzip", "gunzip", "unzip", "systemctl",
            "service", "ps", "kill", "top", "htop", "python", "node", "java",
        ]

        # Must have actual command execution (not just mentioned in comments)
        # Check if lines start with these commands (after optional whitespace)
        has_shell_commands = any(
            re.search(rf"^\s*{re.escape(cmd)}\s", content, re.MULTILINE)
            for cmd in shell_commands
        )

        # Check for shell operators (&&, ||, |, ;, etc.)
        has_shell_operators = bool(re.search(r"(?:&&|\|\||;|\|)\s*\w", content))

        # Check for command options/flags pattern (commands with - or --)
        has_command_options = bool(re.search(r"^\s*\w+\s+--?\w", content, re.MULTILINE))

        # If it has shell commands with operators or options, it's likely bash
        if has_shell_commands and (has_shell_operators or has_command_options):
            return BlockType.BASH_SCRIPT

        # Even without operators, if it has multiple shell commands on separate lines, it's bash
        if has_shell_commands:
            command_lines = [
                line for line in content.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]

            # Count how many lines start with shell commands
            shell_command_lines = sum(
                1 for line in command_lines
                if any(line.strip().startswith(f"{cmd} ") or line.strip() == cmd
                       for cmd in shell_commands)
            )

            # If most non-comment lines are shell commands, tag as bash
            if command_lines and shell_command_lines / len(command_lines) > 0.5:
                return BlockType.BASH_SCRIPT

        # JavaScript
        js_indicators = [
            r"\b(?:const|let|var)\s+\w+\s*=",
            r"\bfunction\s+\w+\s*\(",
            r"\basync\s+function\b",
            r"=>\s*\{",
            r"\bconsole\.log\s*\(",
            r"^import\s+.*\s+from\s+['\"]",
        ]

        if any(re.search(p, content, re.MULTILINE) for p in js_indicators):
            return BlockType.JAVASCRIPT_CODE

        # TypeScript
        ts_indicators = [
            r"\binterface\s+\w+\s*\{",
            r"\btype\s+\w+\s*=",
            r"\benum\s+\w+\s*\{",
            r":\s*(?:string|number|boolean|any)\s*[,;=)]",
        ]

        if any(re.search(p, content, re.MULTILINE) for p in ts_indicators):
            return BlockType.TYPESCRIPT_CODE

        # Go
        go_indicators = [
            r"^package\s+\w+",
            r"\bfunc\s+\w+\s*\(",
            r"\btype\s+\w+\s+struct\s*\{",
        ]

        if any(re.search(p, content, re.MULTILINE) for p in go_indicators):
            return BlockType.GO_CODE

        # Rust
        rust_indicators = [
            r"\bfn\s+\w+\s*\(",
            r"\bimpl\s+(?:\w+\s+for\s+)?\w+",
            r"\bpub\s+(?:fn|struct|enum|trait)",
            r"^#\[derive\(",
        ]

        if any(re.search(p, content, re.MULTILINE) for p in rust_indicators):
            return BlockType.RUST_CODE

        # SQL
        sql_indicators = [
            r"\bSELECT\s+.*\s+FROM\b",
            r"\bINSERT\s+INTO\b",
            r"\bUPDATE\s+.*\s+SET\b",
            r"\bCREATE\s+TABLE\b",
        ]

        if any(re.search(p, content, re.IGNORECASE) for p in sql_indicators):
            return BlockType.SQL_QUERY

        # Dockerfile
        dockerfile_indicators = [
            r"^FROM\s+[\w/:.-]+",
            r"^(?:RUN|CMD|COPY|ADD|WORKDIR|EXPOSE|ENV|ARG|ENTRYPOINT)\s",
        ]

        if any(re.search(p, content, re.MULTILINE) for p in dockerfile_indicators):
            return BlockType.DOCKERFILE

        # Terraform/HCL
        hcl_indicators = [
            r'^\s*resource\s+"[\w-]+"',
            r'^\s*variable\s+"[\w-]+"',
            r'^\s*terraform\s*\{',
        ]

        if any(re.search(p, content, re.MULTILINE) for p in hcl_indicators):
            return BlockType.TERRAFORM_HCL

        return None

    @staticmethod
    def _detect_data_format(content: str) -> Optional[BlockType]:
        """Detect data formats (JSON, YAML, XML, HTML)."""
        content_stripped = content.strip()

        # JSON (strict detection)
        if (
            (content_stripped.startswith("{") and content_stripped.endswith("}"))
            or (content_stripped.startswith("[") and content_stripped.endswith("]"))
        ):
            # Additional check: must have JSON-like structure
            if re.search(r'"\s*:\s*["\{\[]', content):
                return BlockType.JSON_DATA

        # YAML (but not comments that look like YAML)
        yaml_indicators = [
            r"^apiVersion:",  # Kubernetes
            r"^kind:",  # Kubernetes
            r"^\w+:\s*(?:\||>)",  # YAML multi-line string
            r"^-\s+\w+:\s+",  # YAML list of objects
        ]

        # Must have multiple YAML indicators to be confident
        yaml_matches = sum(1 for p in yaml_indicators if re.search(p, content, re.MULTILINE))
        if yaml_matches >= 2:
            return BlockType.YAML_CONFIG

        # XML
        if content_stripped.startswith("<?xml") or re.match(r"^<[\w-]+[^>]*>.*</[\w-]+>$", content_stripped, re.DOTALL):
            return BlockType.XML_MARKUP

        # HTML
        html_indicators = [
            r"<!DOCTYPE html>",
            r"^<html[^>]*>",
            r"^<head[^>]*>",
            r"^<body[^>]*>",
        ]

        if any(re.search(p, content, re.MULTILINE | re.IGNORECASE) for p in html_indicators):
            return BlockType.HTML_MARKUP

        return None


class CodeBlockValidator:
    """Validate and optionally fix code block language tags."""

    def __init__(self, fix: bool = False, dry_run: bool = False):
        """
        Initialize validator.

        Args:
            fix: If True, fix issues found
            dry_run: If True, don't modify files (preview mode)
        """
        self.fix = fix
        self.dry_run = dry_run
        self.stats = {
            "files_processed": 0,
            "files_with_issues": 0,
            "files_modified": 0,
            "blocks_found": 0,
            "blocks_untagged": 0,
            "blocks_incorrectly_tagged": 0,
            "blocks_fixed": 0,
        }
        self.issues: List[Tuple[Path, int, str, str]] = []

    def validate_file(self, file_path: Path) -> bool:
        """
        Validate a single Markdown/MDX file.

        Args:
            file_path: Path to the file

        Returns:
            True if file is valid or was fixed
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}", file=sys.stderr)
            return False

        blocks = self._parse_code_blocks(content)
        self.stats["files_processed"] += 1
        self.stats["blocks_found"] += len(blocks)

        issues_found = []
        fixes_applied = []

        for block in blocks:
            issue = self._validate_block(block)

            if issue:
                issues_found.append((block, issue))
                self.stats["blocks_untagged"] += 1

        if issues_found:
            self.stats["files_with_issues"] += 1

            if self.fix:
                # Apply fixes
                fixed_content, fixes = self._fix_blocks(content, blocks, issues_found)

                if fixes:
                    self.stats["files_modified"] += 1
                    self.stats["blocks_fixed"] += len(fixes)

                    if self.dry_run:
                        print(f"🔍 Would fix {file_path}:")
                        for line_num, old_tag, new_tag in fixes:
                            print(f"   Line {line_num}: '{old_tag}' → '{new_tag}'")
                    else:
                        file_path.write_text(fixed_content, encoding="utf-8")
                        print(f"✅ Fixed {file_path}:")
                        for line_num, old_tag, new_tag in fixes:
                            print(f"   Line {line_num}: '{old_tag}' → '{new_tag}'")

                return True
            else:
                # Report only
                for block, issue in issues_found:
                    self.issues.append((file_path, block.start_line, issue, block.opening_fence))
                return False

        return True

    def _parse_code_blocks(self, content: str) -> List[CodeBlock]:
        """
        Parse code blocks from content using state machine.

        Args:
            content: File content

        Returns:
            List of CodeBlock objects
        """
        lines = content.split("\n")
        blocks = []
        in_block = False
        current_block_start = 0
        current_opening_fence = ""
        current_content_lines = []

        for i, line in enumerate(lines, start=1):
            if line.lstrip().startswith("```"):
                fence_match = re.match(r'^(\s*)```(\S+)?\s*$', line)

                if fence_match:
                    if not in_block:
                        # Opening fence
                        current_block_start = i
                        current_opening_fence = line
                        current_content_lines = []
                        in_block = True
                    else:
                        # Closing fence
                        # Parse language tag from opening fence
                        opening_match = re.match(r'^(\s*)```(\S+)?\s*$', current_opening_fence)
                        opening_lang_tag = opening_match.group(2) if opening_match else None

                        block = CodeBlock(
                            start_line=current_block_start,
                            end_line=i,
                            opening_fence=current_opening_fence,
                            closing_fence=line,
                            content="\n".join(current_content_lines),
                            has_language_tag=bool(opening_lang_tag),
                            language_tag=opening_lang_tag,
                            detected_type=BlockType.UNKNOWN,
                        )

                        # Detect actual content type
                        block.detected_type = SmartLanguageDetector.detect(block.content)

                        blocks.append(block)
                        in_block = False
            elif in_block:
                # Content line
                current_content_lines.append(line)

        return blocks

    def _validate_block(self, block: CodeBlock) -> Optional[str]:
        """
        Validate a single code block.

        Args:
            block: CodeBlock to validate

        Returns:
            Issue description if invalid, None if valid
        """
        # Empty blocks should not have tags
        if block.detected_type == BlockType.EMPTY:
            if block.has_language_tag:
                return f"Empty block has unnecessary tag '{block.language_tag}'"
            return None

        # Comment-only, tree structure, and command output should be 'text' or untagged
        if block.detected_type in [BlockType.COMMENT_ONLY, BlockType.TREE_STRUCTURE, BlockType.COMMAND_OUTPUT]:
            if block.language_tag and block.language_tag not in ["text", "plaintext"]:
                return f"Non-code content tagged as '{block.language_tag}', should be 'text'"
            return None

        # Plain text should ideally have 'text' tag
        if block.detected_type == BlockType.PLAIN_TEXT:
            if not block.has_language_tag:
                return "Plain text block without language tag (consider 'text')"
            return None

        # Programming language blocks should have appropriate tags
        if not block.has_language_tag:
            return f"Code block without language tag (detected: {block.detected_type.value})"

        # Check if tag matches detected type
        if block.language_tag != block.detected_type.value:
            # Allow some aliases and compatible tags
            aliases = {
                "sh": "bash",
                "shell": "bash",
                "yml": "yaml",
                "js": "javascript",
                "ts": "typescript",
                "rs": "rust",
                "tf": "hcl",
                "dotenv": "env",
            }

            # Some types can accept multiple valid tags
            compatible_tags = {
                BlockType.ENV_VARS: ["env", "dotenv", "bash", "text"],  # Env vars can be bash or env
                BlockType.PLAIN_TEXT: ["text", "plaintext", "txt"],
                BlockType.COMMENT_ONLY: ["text", "plaintext", "bash"],  # Comments can be text or bash
            }

            normalized_tag = aliases.get(block.language_tag, block.language_tag)

            # Check if the current tag is compatible with detected type
            if block.detected_type in compatible_tags:
                if block.language_tag in compatible_tags[block.detected_type]:
                    return None  # Tag is compatible

            if normalized_tag != block.detected_type.value:
                return f"Tag '{block.language_tag}' doesn't match detected type '{block.detected_type.value}'"

        return None

    def _fix_blocks(
        self, content: str, blocks: List[CodeBlock], issues: List[Tuple[CodeBlock, str]]
    ) -> Tuple[str, List[Tuple[int, str, str]]]:
        """
        Fix code block issues.

        Args:
            content: File content
            blocks: All code blocks
            issues: List of (block, issue_description) tuples

        Returns:
            Tuple of (fixed_content, list of fixes)
            Each fix is (line_number, old_tag, new_tag)
        """
        lines = content.split("\n")
        fixes = []

        for block, issue in issues:
            # Determine the correct tag
            if block.detected_type == BlockType.EMPTY:
                new_tag = ""
            else:
                new_tag = block.detected_type.value

            # Fix the opening fence
            line_idx = block.start_line - 1
            old_fence = lines[line_idx]

            # Extract indentation
            indent_match = re.match(r'^(\s*)```', old_fence)
            indent = indent_match.group(1) if indent_match else ""

            # Create new fence
            if new_tag:
                new_fence = f"{indent}```{new_tag}"
            else:
                new_fence = f"{indent}```"

            if old_fence != new_fence:
                lines[line_idx] = new_fence
                fixes.append((block.start_line, old_fence, new_fence))

        fixed_content = "\n".join(lines)
        return fixed_content, fixes

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("SUMMARY: Code Block Validation")
        print("=" * 70)
        print(f"Files processed:           {self.stats['files_processed']}")
        print(f"Files with issues:         {self.stats['files_with_issues']}")
        print(f"Code blocks found:         {self.stats['blocks_found']}")
        print(f"Blocks untagged/incorrect: {self.stats['blocks_untagged']}")

        if self.fix:
            print(f"Files modified:            {self.stats['files_modified']}")
            print(f"Blocks fixed:              {self.stats['blocks_fixed']}")

        print("=" * 70)

        if self.fix and self.dry_run:
            print("\n⚠️  DRY RUN - No files were modified")
            print("Run without --dry-run to apply changes")
        elif self.fix:
            if self.stats['blocks_fixed'] > 0:
                print(f"\n✅ Successfully fixed {self.stats['blocks_fixed']} code blocks")
            else:
                print("\n✅ No fixes needed")
        else:
            if self.stats['blocks_untagged'] > 0:
                print(f"\n⚠️  Found {self.stats['blocks_untagged']} issues")
                print("Run with --fix to apply fixes")
            else:
                print("\n✅ All code blocks are properly tagged")

    def print_issues(self):
        """Print detailed issue list."""
        if not self.issues:
            return

        print("\n" + "=" * 70)
        print("ISSUES FOUND")
        print("=" * 70)

        for file_path, line_num, issue, fence in self.issues:
            print(f"{file_path}:{line_num}: {issue}")
            print(f"  {fence}")

        print("=" * 70)


def find_markdown_files(path: Path) -> List[Path]:
    """Find all Markdown/MDX files in path."""
    if path.is_file():
        if path.suffix in {".md", ".mdx"}:
            return [path]
        else:
            print(f"⚠️  {path} is not a Markdown file", file=sys.stderr)
            return []
    elif path.is_dir():
        md_files = list(path.rglob("*.md")) + list(path.rglob("*.mdx"))
        return sorted(md_files)
    else:
        print(f"❌ Path not found: {path}", file=sys.stderr)
        return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate and fix code block language tags with smart detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("docs"),
        help="File or directory to process (default: docs/)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix issues found (default: validate only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview fixes without modifying files (requires --fix)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.dry_run and not args.fix:
        print("⚠️  --dry-run requires --fix flag", file=sys.stderr)
        sys.exit(1)

    # Find files
    files = find_markdown_files(args.path)

    if not files:
        print("❌ No Markdown files to process", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Found {len(files)} Markdown files to process\n")

    # Process files
    validator = CodeBlockValidator(fix=args.fix, dry_run=args.dry_run)

    for file_path in files:
        validator.validate_file(file_path)

    # Print results
    if not args.fix:
        validator.print_issues()

    validator.print_summary()

    # Exit code
    if validator.stats["blocks_untagged"] > 0 and not args.fix:
        sys.exit(1)  # Issues found
    elif validator.stats["blocks_fixed"] > 0 and args.dry_run:
        sys.exit(1)  # Fixes needed (dry-run)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
