#!/usr/bin/env python3
"""
Detect code blocks missing language tags in Markdown/MDX files.

Code blocks without language tags appear as:
```
code here
```

They should have language identifiers:
```python
code here
```
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def find_code_blocks_without_lang(content: str, filepath: Path) -> list[tuple[int, str]]:
    """
    Find code blocks without language tags.

    Returns:
        List of (line_number, preview) tuples for blocks missing language tags
    """
    lines = content.split("\n")
    issues = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for code block start without language tag
        if re.match(r"^\s*```\s*$", line):
            # Get preview of code block content
            preview_lines = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                preview_lines.append(lines[j])
                j += 1
                if len(preview_lines) >= 3:  # Only need first few lines
                    break

            preview = "\n".join(preview_lines[:3])
            if len(preview_lines) > 3:
                preview += "\n..."

            issues.append((i + 1, preview))  # Line numbers start at 1

        i += 1

    return issues


def detect_language_from_content(preview: str) -> str:
    """
    Attempt to detect language from code block content.

    Returns:
        Suggested language tag
    """
    # Common patterns
    if any(x in preview for x in ["import ", "from ", "def ", "class ", "if __name__"]):
        return "python"
    if any(x in preview for x in ["const ", "let ", "function ", "=>", "import {"]):
        return "javascript"
    if any(x in preview for x in ["#!/bin/bash", "#!/bin/sh", "export ", "echo "]) or any(
        x in preview for x in ["kubectl ", "docker ", "helm ", "gcloud "]
    ):
        return "bash"
    if "{" in preview and ":" in preview and '"' in preview:
        return "json"
    if "---" in preview and ":" in preview:
        return "yaml"
    if preview.strip().startswith("SELECT") or preview.strip().startswith("INSERT"):
        return "sql"
    if "curl " in preview or "http" in preview.lower():
        return "bash"
    return "text"


def analyze_file(filepath: Path) -> dict:
    """
    Analyze a single file for missing language tags.

    Returns:
        Dictionary with analysis results
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        issues = find_code_blocks_without_lang(content, filepath)

        # Suggest language tags
        suggestions = []
        for line_num, preview in issues:
            suggested_lang = detect_language_from_content(preview)
            suggestions.append({"line": line_num, "preview": preview[:100], "suggested_lang": suggested_lang})

        return {"filepath": filepath, "count": len(issues), "suggestions": suggestions}
    except Exception as e:
        return {"filepath": filepath, "count": 0, "error": str(e)}


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect code blocks missing language tags")
    parser.add_argument("path", nargs="?", default="docs", help="Path to docs directory")
    parser.add_argument("--format", choices=["summary", "detailed", "json"], default="summary", help="Output format")
    parser.add_argument("--fix", action="store_true", help="Automatically fix by adding suggested language tags")

    args = parser.parse_args()

    docs_path = Path(args.path)
    if not docs_path.exists():
        print(f"Error: Path '{docs_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all markdown files
    md_files = list(docs_path.rglob("*.md")) + list(docs_path.rglob("*.mdx"))

    # Exclude templates
    md_files = [f for f in md_files if ".mintlify/templates" not in str(f)]

    print(f"Scanning {len(md_files)} documentation files...\n")

    # Analyze files
    results = []
    total_issues = 0

    for filepath in sorted(md_files):
        result = analyze_file(filepath)
        if result["count"] > 0:
            results.append(result)
            total_issues += result["count"]

    # Output results
    if args.format == "summary":
        print(f"\n{'=' * 80}")
        print(f"SUMMARY: Found {total_issues} code blocks without language tags")
        print(f"Affected files: {len(results)}")
        print(f"{'=' * 80}\n")

        print("Top 20 files by issue count:")
        for i, result in enumerate(sorted(results, key=lambda x: x["count"], reverse=True)[:20]):
            rel_path = result["filepath"].relative_to(docs_path)
            print(f"{i + 1:2d}. {rel_path}: {result['count']} blocks")

    elif args.format == "detailed":
        for result in sorted(results, key=lambda x: x["count"], reverse=True):
            rel_path = result["filepath"].relative_to(docs_path)
            print(f"\n{'=' * 80}")
            print(f"File: {rel_path}")
            print(f"Missing language tags: {result['count']}")
            print(f"{'=' * 80}")

            for suggestion in result["suggestions"]:
                print(f"\nLine {suggestion['line']}:")
                print(f"  Suggested: ```{suggestion['suggested_lang']}")
                print(f"  Preview: {suggestion['preview'][:80]}...")

    elif args.format == "json":
        import json

        output = {
            "total_files_scanned": len(md_files),
            "files_with_issues": len(results),
            "total_issues": total_issues,
            "files": [
                {"path": str(r["filepath"].relative_to(docs_path)), "count": r["count"], "suggestions": r["suggestions"]}
                for r in results
            ],
        }
        print(json.dumps(output, indent=2))

    if args.fix:
        print("\n⚠️  --fix option not yet implemented")
        print("Manual review recommended for language tag selection")

    sys.exit(0 if total_issues == 0 else 1)


if __name__ == "__main__":
    main()
