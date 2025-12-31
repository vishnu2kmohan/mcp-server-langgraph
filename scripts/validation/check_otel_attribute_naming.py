#!/usr/bin/env python3
"""
OTEL Attribute Naming Convention Validation Script.

Validates that OTEL span attribute queries (Tempo, Loki) use dot notation
matching OTEL semantic conventions (session.id, user.id, workflow.id).

This script prevents the bug where:
- OTEL spans use: span.set_attribute("session.id", value)
- Tempo/Loki queries incorrectly use: tags={"session_id": value}
- Result: Queries never find any traces/logs

Exit codes:
    0 - All attribute names follow OTEL conventions
    1 - Incorrect attribute names detected (underscore instead of dot)

Usage:
    python scripts/validation/check_otel_attribute_naming.py [files...]

As pre-commit hook:
    - id: check-otel-attribute-naming
      name: Check OTEL Attribute Naming
      entry: python scripts/validation/check_otel_attribute_naming.py
      files: ^src/mcp_server_langgraph/(api/v1|observability)/.*[.]py$
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns that indicate incorrect underscore notation in OTEL query contexts
# These are Tempo/Loki query patterns that should use dot notation
BAD_PATTERNS = [
    # Tempo tag searches
    (r'tags\s*=\s*\{\s*["\']session_id["\']', 'tags={"session_id"'),
    (r'tags\s*=\s*\{\s*["\']user_id["\']', 'tags={"user_id"'),
    (r'tags\s*=\s*\{\s*["\']workflow_id["\']', 'tags={"workflow_id"'),
    (r'tags\s*=\s*\{\s*["\']project_id["\']', 'tags={"project_id"'),
    (r'tags\s*=\s*\{\s*["\']organization_id["\']', 'tags={"organization_id"'),
    # search_by_attribute calls
    (r'attribute\s*=\s*["\']session_id["\']', 'attribute="session_id"'),
    (r'attribute\s*=\s*["\']user_id["\']', 'attribute="user_id"'),
    (r'attribute\s*=\s*["\']workflow_id["\']', 'attribute="workflow_id"'),
    (r'attribute\s*=\s*["\']project_id["\']', 'attribute="project_id"'),
    (r'attribute\s*=\s*["\']organization_id["\']', 'attribute="organization_id"'),
    # tags dict access
    (r'tags\.get\s*\(\s*["\']session_id["\']', 'tags.get("session_id"'),
    (r'tags\.get\s*\(\s*["\']user_id["\']', 'tags.get("user_id"'),
    (r'tags\[["\']session_id["\']\]', 'tags["session_id"]'),
    (r'tags\[["\']user_id["\']\]', 'tags["user_id"]'),
]

# Directories/files to scan
SCAN_PATHS = [
    "src/mcp_server_langgraph/api/v1/",
    "src/mcp_server_langgraph/observability/",
    "src/mcp_server_langgraph/monitoring/",
]

# Files to exclude (test stubs, examples in docstrings, etc.)
EXCLUDE_PATTERNS = [
    r"__pycache__",
    r"\.pyc$",
    r"test_.*\.py$",  # Test files can have example patterns
]


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def should_exclude(file_path: Path) -> bool:
    """Check if file should be excluded from scanning."""
    path_str = str(file_path)
    return any(re.search(pattern, path_str) for pattern in EXCLUDE_PATTERNS)


def is_in_comment_or_docstring(line: str, line_stripped: str) -> bool:
    """Check if the line is a comment or likely in a docstring."""
    # Skip comment lines
    if line_stripped.startswith("#"):
        return True
    # Skip lines that are just string literals (likely docstring continuation)
    if line_stripped.startswith('"""') or line_stripped.startswith("'''"):
        return True
    # Skip lines with just a quote (multiline string)
    if line_stripped in ('"""', "'''", '"', "'"):
        return True
    return False


def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    """
    Scan a file for incorrect OTEL attribute naming patterns.

    Returns:
        List of (line_number, pattern_found, line_content) tuples
    """
    violations: list[tuple[int, str, str]] = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"WARNING: Could not read {file_path}: {e}")
        return violations

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comments and docstrings
        if is_in_comment_or_docstring(line, stripped):
            continue

        # Check each bad pattern
        for pattern_regex, pattern_desc in BAD_PATTERNS:
            if re.search(pattern_regex, line):
                violations.append((line_num, pattern_desc, line.strip()))

    return violations


def scan_files(files: list[Path] | None = None) -> dict[Path, list[tuple[int, str, str]]]:
    """
    Scan files for OTEL attribute naming violations.

    Args:
        files: Optional list of specific files to check.
               If None, scans all files in SCAN_PATHS.

    Returns:
        Dict mapping file paths to their violations
    """
    project_root = get_project_root()
    all_violations: dict[Path, list[tuple[int, str, str]]] = {}

    if files:
        # Scan specific files (pre-commit passes changed files)
        for file_path in files:
            if file_path.suffix == ".py" and not should_exclude(file_path):
                violations = scan_file(file_path)
                if violations:
                    all_violations[file_path] = violations
    else:
        # Scan all files in SCAN_PATHS
        for scan_path in SCAN_PATHS:
            full_path = project_root / scan_path
            if not full_path.exists():
                continue

            for py_file in full_path.rglob("*.py"):
                if should_exclude(py_file):
                    continue

                violations = scan_file(py_file)
                if violations:
                    all_violations[py_file] = violations

    return all_violations


def main() -> int:
    """Main entry point for the validation script."""
    # Parse command line arguments (files passed by pre-commit)
    files: list[Path] | None = None
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if Path(f).suffix == ".py"]

    print("🔍 Checking OTEL attribute naming conventions...")

    violations = scan_files(files)

    if not violations:
        print("✅ All OTEL attribute names follow dot notation conventions")
        return 0

    print("\n❌ Found OTEL attribute naming violations:")
    print("   OTEL uses dot notation (session.id, user.id, workflow.id)")
    print("   Underscore notation (session_id) will not match OTEL spans\n")

    for file_path, file_violations in violations.items():
        print(f"📄 {file_path}:")
        for line_num, pattern, content in file_violations:
            print(f"   Line {line_num}: Found '{pattern}'")
            print(f"           {content[:80]}{'...' if len(content) > 80 else ''}")
        print()

    print("💡 Fix by using dot notation:")
    print("   - session_id → session.id")
    print("   - user_id → user.id")
    print("   - workflow_id → workflow.id")
    print()
    print("📚 Reference: tests/integration/observability/test_otel_tempo_data_flow.py")

    return 1


if __name__ == "__main__":
    sys.exit(main())
