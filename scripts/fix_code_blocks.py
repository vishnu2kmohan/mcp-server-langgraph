#!/usr/bin/env python3
"""
Add language specifiers to code blocks without language tags.

This script processes MDX files and adds appropriate language tags to code blocks
based on their content.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def detect_language(code: str) -> str:
    """Detect programming language from code block content."""
    code = code.strip()

    # Empty blocks
    if not code:
        return "text"

    # Bash/shell commands
    if any(
        code.startswith(cmd)
        for cmd in [
            "curl ",
            "wget ",
            "apt-",
            "yum ",
            "brew ",
            "pip ",
            "npm ",
            "docker ",
            "kubectl ",
            "helm ",
            "git ",
            "cd ",
            "ls ",
            "mkdir ",
            "chmod ",
            "chown ",
            "export ",
            "echo ",
            "cat ",
            "grep ",
            "sed ",
            "awk ",
            "find ",
            "ssh ",
            "scp ",
            "rsync ",
            "tar ",
            "gzip ",
            "python scripts/",
            "bash ",
            "sh ",
            "./scripts/",
            "./deploy",
            "make ",
            "source ",
            "#!/bin/",
        ]
    ):
        return "bash"

    # Check for bash patterns
    if (
        re.search(r"^\$\s+", code, re.MULTILINE)
        or re.search(r"^\#\s+", code, re.MULTILINE)
        or re.search(r"export\s+\w+=", code)
        or "&&" in code
        or "||" in code
    ):
        return "bash"

    # Python
    if (
        code.startswith("import ")
        or code.startswith("from ")
        or "def " in code
        or "class " in code
        or "async def" in code
        or "await " in code
    ):
        return "python"

    # JavaScript/TypeScript
    if (
        code.startswith("const ")
        or code.startswith("let ")
        or code.startswith("var ")
        or "function " in code
        or "=>" in code
        or "async function" in code
        or "await " in code
        and "fetch(" in code
    ):
        return "javascript"

    # YAML
    if (
        re.match(r"^\w+:\s*$", code, re.MULTILINE)
        or re.match(r"^\s+-\s+\w+:", code, re.MULTILINE)
        or code.startswith("apiVersion:")
        or code.startswith("kind:")
        or code.startswith("metadata:")
        or code.startswith("spec:")
    ):
        return "yaml"

    # JSON
    if (code.startswith("{") and code.endswith("}")) or (code.startswith("[") and code.endswith("]")):
        try:
            # Simple check for JSON-like structure
            if '"' in code and ":" in code:
                return "json"
        except:
            pass

    # HTTP requests/responses
    if (
        code.startswith("HTTP/")
        or code.startswith("GET ")
        or code.startswith("POST ")
        or code.startswith("PUT ")
        or code.startswith("DELETE ")
        or code.startswith("PATCH ")
    ):
        return "http"

    # SQL
    if any(keyword in code.upper() for keyword in ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE"]):
        return "sql"

    # Dockerfile
    if code.startswith("FROM ") or "RUN " in code and "COPY " in code:
        return "dockerfile"

    # HTML/XML
    if code.startswith("<") and ">" in code:
        return "xml"

    # Terraform
    if 'resource "' in code or 'variable "' in code or "terraform {" in code:
        return "hcl"

    # Default to bash for command-like content
    if "\n" not in code and code.endswith((".sh", ".py", ".js", ".yaml", ".json")):
        return "bash"

    return "text"


def process_file(file_path: Path) -> Tuple[int, int]:
    """Process a single MDX file and add language specifiers to code blocks.

    Returns:
        Tuple of (total_blocks, modified_blocks)
    """
    content = file_path.read_text()
    total_blocks = 0
    modified_blocks = 0

    # Pattern to find code blocks without language specifier
    # Matches: ```\n or ``` \n but not ```language\n
    pattern = r"```\s*\n(.*?)```"

    def replace_block(match):
        nonlocal total_blocks, modified_blocks
        total_blocks += 1

        code = match.group(1)
        language = detect_language(code)

        modified_blocks += 1
        return f"```{language}\n{code}```"

    new_content = re.sub(pattern, replace_block, content, flags=re.DOTALL)

    if new_content != content:
        file_path.write_text(new_content)
        return (total_blocks, modified_blocks)

    return (0, 0)


def main():
    """Main function to process all MDX files in specified directories."""
    if len(sys.argv) < 2:
        print("Usage: python fix_code_blocks.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])

    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)

    mdx_files = list(directory.rglob("*.mdx"))

    if not mdx_files:
        print(f"No MDX files found in {directory}")
        return

    print(f"Processing {len(mdx_files)} MDX files in {directory}...")

    total_files_modified = 0
    total_blocks = 0
    total_modified = 0

    for file_path in sorted(mdx_files):
        blocks, modified = process_file(file_path)

        if modified > 0:
            total_files_modified += 1
            total_blocks += blocks
            total_modified += modified
            print(f"  ✓ {file_path.relative_to(directory)}: {modified} blocks fixed")

    print(f"\n Summary:")
    print(f"  Files processed: {len(mdx_files)}")
    print(f"  Files modified: {total_files_modified}")
    print(f"  Code blocks found: {total_blocks}")
    print(f"  Code blocks fixed: {total_modified}")


if __name__ == "__main__":
    main()
