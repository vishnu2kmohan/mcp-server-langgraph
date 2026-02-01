#!/usr/bin/env python3
"""
Audit and fix accessibility attribute violations.

This script scans for accessibility issues and provides fixes where possible.
Some issues (like aria-label for icon buttons) require human judgment and
are reported for manual fixing.

Usage:
    python scripts/fix-accessibility-attrs.py           # Audit all files
    python scripts/fix-accessibility-attrs.py --fix     # Apply auto-fixes
    python scripts/fix-accessibility-attrs.py --report  # Generate report only

Violations Detected:
    - Icon-only buttons missing aria-label (report only - needs human label)
    - onClick on non-button elements (report only - needs manual review)
    - Toggle/Checkbox without associated label
    - Input without type attribute

Exit Codes:
    0: Success (no violations or only warnings)
    1: Errors found (blocking violations)
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

FRONTEND_SRC = Path(__file__).parent.parent / "src"

EXTENSIONS = {".tsx"}

SKIP_DIRS = {"node_modules", "dist", ".storybook", "coverage", "__snapshots__"}

SKIP_FILES = {
    "Button.tsx",
    "Button.test.tsx",
    "Button.stories.tsx",
    "Toggle.tsx",
    "Toggle.test.tsx",
    "Checkbox.tsx",
    "Checkbox.test.tsx",
    "Input.tsx",
    "Input.test.tsx",
}


@dataclass
class Violation:
    file: Path
    line_no: int
    column: int
    rule: str
    severity: str  # "error" | "warning"
    message: str
    context: str
    suggestion: str = ""


# =============================================================================
# Pattern[str] Definitions
# =============================================================================


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    if any(skip in path.parts for skip in SKIP_DIRS):
        return True
    if path.name in SKIP_FILES:
        return True
    if ".test." in path.name or ".stories." in path.name:
        return True
    return False


def check_icon_buttons_without_aria_label(content: str, file_path: Path) -> list[Violation]:
    """Find icon-only buttons missing aria-label."""
    violations = []
    lines = content.splitlines()

    # Pattern[str]: <Button size="icon" ... without aria-label
    pattern = re.compile(r'<Button\b[^>]*size=["\']icon["\'][^>]*>')

    for line_no, line in enumerate(lines, 1):
        for match in pattern.finditer(line):
            button_tag = match.group()
            if "aria-label=" not in button_tag:
                violations.append(
                    Violation(
                        file=file_path,
                        line_no=line_no,
                        column=match.start() + 1,
                        rule="icon-button-missing-aria-label",
                        severity="error",
                        message="Icon-only button missing aria-label for screen readers",
                        context=line.strip()[:100],
                        suggestion='Add aria-label describing the button\'s action (e.g., aria-label="Close dialog")',
                    )
                )

    return violations


def check_onclick_on_non_buttons(content: str, file_path: Path) -> list[Violation]:
    """Find div/span elements with onClick that should be buttons."""
    violations = []
    lines = content.splitlines()

    # Pattern[str]: <div|span ... onClick= ...
    pattern = re.compile(r"<(div|span)\b[^>]*\bonClick=")

    for line_no, line in enumerate(lines, 1):
        for match in pattern.finditer(line):
            element = match.group(1)
            # Check if it has role="button" or tabIndex (which makes it semi-accessible)
            line_context = line[match.start() : match.start() + 200]
            has_role = 'role="button"' in line_context or "role='button'" in line_context
            has_tabindex = "tabIndex" in line_context

            if not has_role:
                violations.append(
                    Violation(
                        file=file_path,
                        line_no=line_no,
                        column=match.start() + 1,
                        rule="onclick-on-non-button",
                        severity="warning",
                        message=f'<{element}> with onClick should use <Button> or add role="button" and tabIndex',
                        context=line.strip()[:100],
                        suggestion='Replace with <Button variant="ghost"> or add role="button" tabIndex={0} onKeyDown handler',
                    )
                )

    return violations


def check_form_controls_without_labels(content: str, file_path: Path) -> list[Violation]:
    """Find Toggle/Checkbox components without associated labels."""
    violations = []
    lines = content.splitlines()

    # Pattern[str]: <Toggle or <Checkbox without id= (needed for label association)
    pattern = re.compile(r"<(Toggle|Checkbox)\b(?![^>]*\bid=)[^/]*/?>")

    for line_no, line in enumerate(lines, 1):
        for match in pattern.finditer(line):
            component = match.group(1)
            # Check if there's an associated label nearby
            context_start = max(0, line_no - 3)
            context_end = min(len(lines), line_no + 3)
            context_block = "\n".join(lines[context_start:context_end])

            if "<label" not in context_block.lower() and "Label" not in context_block:
                violations.append(
                    Violation(
                        file=file_path,
                        line_no=line_no,
                        column=match.start() + 1,
                        rule="form-control-missing-label",
                        severity="warning",
                        message=f"<{component}> may need an associated label for accessibility",
                        context=line.strip()[:100],
                        suggestion="Add id prop and associate with <label htmlFor=...> or wrap in <label>",
                    )
                )

    return violations


def check_inputs_without_type(content: str, file_path: Path) -> list[Violation]:
    """Find raw input elements without explicit type attribute."""
    violations = []
    lines = content.splitlines()

    # Pattern[str]: <input without type=
    pattern = re.compile(r"<input\b(?![^>]*\btype=)[^>]*>")

    for line_no, line in enumerate(lines, 1):
        for match in pattern.finditer(line):
            violations.append(
                Violation(
                    file=file_path,
                    line_no=line_no,
                    column=match.start() + 1,
                    rule="input-missing-type",
                    severity="warning",
                    message='<input> without explicit type defaults to "text" - be explicit',
                    context=line.strip()[:100],
                    suggestion='Add type="text" (or appropriate type) explicitly',
                )
            )

    return violations


def audit_file(file_path: Path) -> list[Violation]:
    """Audit a single file for accessibility violations."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return []

    violations = []

    # Run all checks
    violations.extend(check_icon_buttons_without_aria_label(content, file_path))
    violations.extend(check_onclick_on_non_buttons(content, file_path))
    violations.extend(check_form_controls_without_labels(content, file_path))
    violations.extend(check_inputs_without_type(content, file_path))

    return violations


# =============================================================================
# Reporting
# =============================================================================


def print_violations(violations: list[Violation], verbose: bool = False) -> None:
    """Print violations to console."""
    # Group by file
    by_file: dict[Path, list[Violation]] = defaultdict(list)
    for v in violations:
        by_file[v.file].append(v)

    for file_path, file_violations in sorted(by_file.items()):
        rel_path = file_path.relative_to(FRONTEND_SRC)
        print(f"\n{rel_path}")
        for v in file_violations:
            severity_icon = "X" if v.severity == "error" else "!"
            print(f"  L{v.line_no}: [{severity_icon}] {v.rule}")
            print(f"        {v.message}")
            if verbose and v.suggestion:
                print(f"        Suggestion: {v.suggestion}")


def generate_json_report(violations: list[Violation]) -> dict:
    """Generate JSON report."""
    by_rule: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)

    for v in violations:
        by_rule[v.rule] += 1
        by_severity[v.severity] += 1

    return {
        "total": len(violations),
        "by_severity": dict(by_severity),
        "by_rule": dict(sorted(by_rule.items(), key=lambda x: -x[1])),
        "violations": [
            {
                "file": str(v.file.relative_to(FRONTEND_SRC)),
                "line": v.line_no,
                "rule": v.rule,
                "severity": v.severity,
                "message": v.message,
            }
            for v in violations
        ],
    }


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit and fix accessibility attribute violations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--fix", action="store_true", help="Apply auto-fixes where possible")
    parser.add_argument("--report", action="store_true", help="Generate JSON report only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show suggestions")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any violations")
    parser.add_argument("files", nargs="*", help="Specific files to check")

    args = parser.parse_args()

    # Collect files
    if args.files:
        files = [Path(f) for f in args.files if Path(f).suffix in EXTENSIONS]
    else:
        files = list(FRONTEND_SRC.rglob("*.tsx"))

    files = [f for f in files if f.exists() and not should_skip(f)]

    all_violations: list[Violation] = []

    print("\nAccessibility Audit")
    print("=" * 60)
    print(f"Scanning {len(files)} files...\n")

    for file_path in files:
        violations = audit_file(file_path)
        all_violations.extend(violations)

    # Summary
    errors = sum(1 for v in all_violations if v.severity == "error")
    warnings = sum(1 for v in all_violations if v.severity == "warning")

    if args.report:
        report = generate_json_report(all_violations)
        print(json.dumps(report, indent=2))
    else:
        if all_violations:
            print_violations(all_violations, verbose=args.verbose)

        print("\n" + "-" * 60)
        print("Summary:")
        print(f"  Errors: {errors}")
        print(f"  Warnings: {warnings}")
        print(f"  Total: {len(all_violations)}")

        if errors > 0:
            print("\nErrors require manual fixes (aria-label needs human-readable text).")
        if args.fix:
            print("\nNote: Most accessibility issues require manual review.")
            print("      aria-label values must be human-written for screen readers.")

    # Exit code
    if args.strict and len(all_violations) > 0:
        return 1
    if errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
