#!/usr/bin/env python3
"""
Pre-commit hook: Frontend Design System Compliance Checker

This is a thin wrapper that delegates to the unified design-system.py tool.
The unified tool provides comprehensive coverage for all design system violations:

1. Color violations (raw Tailwind, legacy scales, inline hex/rgba)
2. Spacing violations (arbitrary pixel values)
3. Typography violations (arbitrary font sizes)
4. Border, shadow, z-index violations
5. Animation violations (arbitrary durations)

Usage:
    As a pre-commit hook (see .pre-commit-config.yaml)
    Or standalone: python .pre-commit-hooks/check_frontend_design_system.py [files...]

Exit codes:
    0: All validations passed (no blocking errors)
    1: Found blocking validation errors
    2: Usage/configuration error

For comprehensive auditing and auto-fixing, use the unified tool directly:
    python src/mcp_server_langgraph/studio/frontend/scripts/design-system.py check [files...]
    python src/mcp_server_langgraph/studio/frontend/scripts/design-system.py audit
    python src/mcp_server_langgraph/studio/frontend/scripts/design-system.py fix --dry-run
"""

import subprocess
import sys
from pathlib import Path

# Path to the unified design system tool
UNIFIED_TOOL = Path(__file__).parent.parent / "src/mcp_server_langgraph/studio/frontend/scripts/design-system.py"


def main() -> int:
    """Delegate to the unified design-system.py tool."""
    # Check if unified tool exists
    if not UNIFIED_TOOL.exists():
        print(
            f"Warning: Unified design-system.py not found at {UNIFIED_TOOL}",
            file=sys.stderr,
        )
        print("Falling back to basic validation...", file=sys.stderr)
        return fallback_check(sys.argv[1:])

    # Build command
    cmd = [sys.executable, str(UNIFIED_TOOL), "check"]

    # Pass through file arguments from pre-commit
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    # Run the unified tool
    try:
        result = subprocess.run(cmd, capture_output=False)
        return result.returncode
    except Exception as e:
        print(f"Error running design-system.py: {e}", file=sys.stderr)
        return 2


def fallback_check(files: list[str]) -> int:
    """Minimal fallback if unified tool is unavailable."""
    import re

    # Only check for the most critical violations
    CRITICAL_PATTERNS = [
        (r"\b(text|bg|border|ring)-(white|black)\b", "raw-tailwind-color"),
        (r'style\s*=\s*\{\s*\{[^}]*(?:color|background|backgroundColor)\s*:\s*["\']?#[0-9a-fA-F]{3,8}', "inline-hex-color"),
        (r'\b(?:stroke|fill|color|backgroundColor|bgColor|textColor|borderColor|nodeColor|maskColor)\s*=\s*["{]["\']?#[0-9a-fA-F]{3,8}', "jsx-prop-hex-color"),
        (r'\b(?:stroke|fill|color|backgroundColor|bgColor|textColor|borderColor|nodeColor|maskColor)\s*=\s*["\'`]rgba?\([^)]+\)', "jsx-prop-rgba-color"),
        (r'\b(?:stroke|fill|color|backgroundColor|bgColor|textColor|borderColor|nodeColor|maskColor)\s*=\s*["\'`]hsla?\([^)]+\)', "jsx-prop-hsl-color"),
        (r'\b(?:bg|text|border|ring|fill|stroke)-\[#[0-9a-fA-F]{3,8}\]', "arbitrary-hex-class"),
        (r'\b(?:bg|text|border|ring|fill|stroke)-\[rgba?\([^\]]+\)\]', "arbitrary-rgba-class"),
    ]

    SKIP_PATTERNS = {".test.", ".stories.", "node_modules", "__snapshots__"}

    violations = []

    for file_arg in files:
        file_path = Path(file_arg)
        if not file_path.exists() or file_path.suffix not in {".tsx", ".ts"}:
            continue
        if any(skip in str(file_path) for skip in SKIP_PATTERNS):
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        for line_no, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            for pattern, rule in CRITICAL_PATTERNS:
                for match in re.finditer(pattern, line):
                    violations.append((file_path, line_no, match.group(), rule))

    if violations:
        print("\n❌ Frontend Design System Violations:\n", file=sys.stderr)
        for file_path, line_no, match, rule in violations[:10]:
            print(f"  {file_path}:{line_no} [{rule}] {match}", file=sys.stderr)
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
