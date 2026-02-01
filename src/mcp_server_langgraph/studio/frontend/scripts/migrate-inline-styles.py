#!/usr/bin/env python3
"""
Inline Styles Migration Script for Design System Compliance

This script scans TSX files for inline style violations and migrates them
to design system-compliant patterns.

Usage:
    python scripts/migrate-inline-styles.py --dry-run    # Preview changes
    python scripts/migrate-inline-styles.py --apply      # Apply changes
    python scripts/migrate-inline-styles.py --report     # Generate report only

Patterns handled:
1. Progress bars: style={{width: `${x}%`}} -> CSS custom property pattern
2. Indent levels: paddingLeft: `${n}px` -> getIndentClass utility
3. Fixed dimensions: style={{height: "300px"}} -> Tailwind arbitrary or token
4. Static inline styles -> Tailwind classes
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Violation:
    """Represents a single inline style violation."""

    file_path: str
    line_number: int
    line_content: str
    pattern_type: str
    original: str
    suggested_fix: str
    can_auto_fix: bool = False


@dataclass
class MigrationReport:
    """Summary of migration results."""

    files_scanned: int = 0
    files_with_violations: int = 0
    total_violations: int = 0
    auto_fixed: int = 0
    manual_review: int = 0
    violations: list[Violation] = field(default_factory=list)


# Pattern[str] definitions
PATTERNS = {
    # Dynamic percentage width (progress bars)
    "dynamic_width_percent": {
        "regex": r'style=\{\{\s*width:\s*[`\'"]?\$\{([^}]+)\}%[`\'"]?\s*\}\}',
        "description": "Dynamic percentage width",
        "fix_template": "className=\"w-full\" style={{ '--progress': `${{{expr}}}%` } as React.CSSProperties}",
        "can_auto_fix": False,  # Needs className coordination
    },
    # Padding left for indentation
    "padding_left_dynamic": {
        "regex": r'style=\{\{\s*paddingLeft:\s*[`\'"]?\$\{([^}]+)\}px[`\'"]?\s*\}\}',
        "description": "Dynamic padding-left (indentation)",
        "fix_template": "className={getIndentClass({expr})}",
        "can_auto_fix": True,
    },
    # Static height in px
    "static_height_px": {
        "regex": r'style=\{\{\s*height:\s*[\'"](\d+)px[\'"]\s*\}\}',
        "description": "Static height in pixels",
        "fix_template": 'className="h-[{value}px]"',
        "can_auto_fix": True,
    },
    # Static width in px
    "static_width_px": {
        "regex": r'style=\{\{\s*width:\s*[\'"](\d+)px[\'"]\s*\}\}',
        "description": "Static width in pixels",
        "fix_template": 'className="w-[{value}px]"',
        "can_auto_fix": True,
    },
    # Static padding
    "static_padding": {
        "regex": r'style=\{\{\s*padding:\s*[\'"](\d+)px[\'"]\s*\}\}',
        "description": "Static padding",
        "fix_template": 'className="p-[{value}px]"',
        "can_auto_fix": True,
    },
    # Multiple properties in style object
    "multi_property_style": {
        "regex": r"style=\{\{[^}]*,[^}]*\}\}",
        "description": "Multiple properties in style object",
        "fix_template": "Split into className and minimal style",
        "can_auto_fix": False,
    },
    # Background color inline
    "inline_bg_color": {
        "regex": r'style=\{\{\s*backgroundColor:\s*[\'"][#\w]+[\'"]\s*\}\}',
        "description": "Inline background color",
        "fix_template": "Use Tailwind bg-* class",
        "can_auto_fix": False,
    },
    # Color inline
    "inline_color": {
        "regex": r'style=\{\{\s*color:\s*[\'"][#\w]+[\'"]\s*\}\}',
        "description": "Inline text color",
        "fix_template": "Use Tailwind text-* class",
        "can_auto_fix": False,
    },
    # Font family inline
    "inline_font_family": {
        "regex": r'style=\{\{\s*fontFamily:\s*[\'"][^"\']+[\'"]\s*\}\}',
        "description": "Inline font family",
        "fix_template": "Use Tailwind font-sans/font-mono class",
        "can_auto_fix": False,
    },
}

# Mapping of pixel values to Tailwind spacing tokens
PX_TO_TAILWIND = {
    "0": "0",
    "1": "px",
    "2": "0.5",
    "4": "1",
    "6": "1.5",
    "8": "2",
    "10": "2.5",
    "12": "3",
    "14": "3.5",
    "16": "4",
    "20": "5",
    "24": "6",
    "28": "7",
    "32": "8",
    "36": "9",
    "40": "10",
    "48": "12",
    "56": "14",
    "64": "16",
    "80": "20",
    "96": "24",
}


def get_tailwind_spacing(px_value: str) -> str | None:
    """Convert pixel value to Tailwind spacing token if available."""
    return PX_TO_TAILWIND.get(px_value)


def scan_file(file_path: Path) -> list[Violation]:
    """Scan a single file for inline style violations."""
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return violations

    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        for pattern_name, pattern_info in PATTERNS.items():
            matches = re.finditer(pattern_info["regex"], line)
            for match in matches:
                # Generate suggested fix
                if pattern_name == "padding_left_dynamic":
                    expr = match.group(1) if match.lastindex else "depth"
                    suggested = f"className={{getIndentClass({expr})}}"
                elif pattern_name in ("static_height_px", "static_width_px", "static_padding"):
                    value = match.group(1) if match.lastindex else "0"
                    tw_value = get_tailwind_spacing(value)
                    prefix = "h" if "height" in pattern_name else "w" if "width" in pattern_name else "p"
                    if tw_value:
                        suggested = f'className="{prefix}-{tw_value}"'
                    else:
                        suggested = f'className="{prefix}-[{value}px]"'
                elif pattern_name == "dynamic_width_percent":
                    expr = match.group(1) if match.lastindex else "percentage"
                    suggested = f"style={{{{ '--progress': `${{{expr}}}%` }}}} className=\"progress-bar-fill\""
                else:
                    suggested = pattern_info["fix_template"]

                violations.append(
                    Violation(
                        file_path=str(file_path),
                        line_number=line_num,
                        line_content=line.strip(),
                        pattern_type=pattern_name,
                        original=match.group(0),
                        suggested_fix=suggested,
                        can_auto_fix=pattern_info["can_auto_fix"],
                    )
                )

    return violations


def apply_fix(file_path: Path, violations: list[Violation]) -> int:
    """Apply auto-fixes to a file. Returns count of fixes applied."""
    if not violations:
        return 0

    # Only apply auto-fixable violations
    auto_fixable = [v for v in violations if v.can_auto_fix]
    if not auto_fixable:
        return 0

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0

    modified = content
    fixes_applied = 0

    for violation in auto_fixable:
        if violation.pattern_type == "padding_left_dynamic":
            # Replace paddingLeft pattern with getIndentClass
            pattern = r'style=\{\{\s*paddingLeft:\s*[`\'"]?\$\{([^}]+)\}px[`\'"]?\s*\}\}'

            def replace_indent(m: re.Match[str]) -> str:
                expr = m.group(1)
                return f"className={{getIndentClass({expr})}}"

            modified = re.sub(pattern, replace_indent, modified)
            fixes_applied += 1

        elif violation.pattern_type == "static_height_px":
            pattern = r'style=\{\{\s*height:\s*[\'"](\d+)px[\'"]\s*\}\}'

            def replace_height(m: re.Match[str]) -> str:
                value = m.group(1)
                tw = get_tailwind_spacing(value)
                return f'className="h-{tw}"' if tw else f'className="h-[{value}px]"'

            modified = re.sub(pattern, replace_height, modified)
            fixes_applied += 1

        elif violation.pattern_type == "static_width_px":
            pattern = r'style=\{\{\s*width:\s*[\'"](\d+)px[\'"]\s*\}\}'

            def replace_width(m: re.Match[str]) -> str:
                value = m.group(1)
                tw = get_tailwind_spacing(value)
                return f'className="w-{tw}"' if tw else f'className="w-[{value}px]"'

            modified = re.sub(pattern, replace_width, modified)
            fixes_applied += 1

        elif violation.pattern_type == "static_padding":
            pattern = r'style=\{\{\s*padding:\s*[\'"](\d+)px[\'"]\s*\}\}'

            def replace_padding(m: re.Match[str]) -> str:
                value = m.group(1)
                tw = get_tailwind_spacing(value)
                return f'className="p-{tw}"' if tw else f'className="p-[{value}px]"'

            modified = re.sub(pattern, replace_padding, modified)
            fixes_applied += 1

    if modified != content:
        # Check if getIndentClass is used but not imported
        if "getIndentClass" in modified and "import { getIndentClass }" not in modified:
            # Add import at the top
            import_line = "import { getIndentClass } from '@/utils/indent';\n"
            # Find first import and add after
            first_import = modified.find("import ")
            if first_import != -1:
                end_of_imports = modified.find("\n\n", first_import)
                if end_of_imports == -1:
                    end_of_imports = first_import
                # Find the last import line
                last_import_end = modified.rfind("import ", 0, end_of_imports + 100)
                if last_import_end != -1:
                    line_end = modified.find("\n", last_import_end)
                    modified = modified[: line_end + 1] + import_line + modified[line_end + 1 :]

        try:
            file_path.write_text(modified, encoding="utf-8")
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return 0

    return fixes_applied


def scan_directory(src_path: Path) -> MigrationReport:
    """Scan all TSX files in the source directory."""
    report = MigrationReport()

    tsx_files = list(src_path.rglob("*.tsx"))
    report.files_scanned = len(tsx_files)

    for file_path in tsx_files:
        violations = scan_file(file_path)
        if violations:
            report.files_with_violations += 1
            report.total_violations += len(violations)
            report.violations.extend(violations)

    return report


def print_report(report: MigrationReport, verbose: bool = False) -> None:
    """Print migration report."""
    print("\n" + "=" * 70)
    print("INLINE STYLES MIGRATION REPORT")
    print("=" * 70)
    print(f"\nFiles scanned: {report.files_scanned}")
    print(f"Files with violations: {report.files_with_violations}")
    print(f"Total violations: {report.total_violations}")
    print(f"Auto-fixed: {report.auto_fixed}")
    print(f"Manual review needed: {report.manual_review}")

    if verbose and report.violations:
        print("\n" + "-" * 70)
        print("VIOLATIONS BY FILE")
        print("-" * 70)

        # Group by file
        by_file: dict[str, list[Violation]] = {}
        for v in report.violations:
            by_file.setdefault(v.file_path, []).append(v)

        for file_path, violations in sorted(by_file.items()):
            rel_path = file_path.replace(str(Path.cwd()), "")
            print(f"\n{rel_path} ({len(violations)} violations)")
            for v in violations:
                status = "[AUTO-FIX]" if v.can_auto_fix else "[MANUAL]"
                print(f"  Line {v.line_number}: {status} {v.pattern_type}")
                print(f"    Original: {v.original[:80]}...")
                print(f"    Suggested: {v.suggested_fix[:80]}...")

    # Summary by pattern type
    print("\n" + "-" * 70)
    print("VIOLATIONS BY PATTERN TYPE")
    print("-" * 70)

    by_type: dict[str, int] = {}
    for v in report.violations:
        by_type[v.pattern_type] = by_type.get(v.pattern_type, 0) + 1

    for pattern_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        auto_count = sum(1 for v in report.violations if v.pattern_type == pattern_type and v.can_auto_fix)
        print(f"  {pattern_type}: {count} ({auto_count} auto-fixable)")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate inline styles to design system patterns")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply auto-fixes to files",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report only",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed violations",
    )
    parser.add_argument(
        "--src-path",
        type=str,
        default="src",
        help="Source directory to scan (default: src)",
    )

    args = parser.parse_args()

    if not any([args.dry_run, args.apply, args.report]):
        args.dry_run = True  # Default to dry-run

    # Find source directory
    src_path = Path(args.src_path)
    if not src_path.exists():
        # Try relative to script location
        script_dir = Path(__file__).parent.parent
        src_path = script_dir / "src"

    if not src_path.exists():
        print(f"Error: Source directory not found: {src_path}", file=sys.stderr)
        return 1

    print(f"Scanning: {src_path}")

    # Scan for violations
    report = scan_directory(src_path)

    # Count auto-fixable vs manual
    report.manual_review = sum(1 for v in report.violations if not v.can_auto_fix)
    auto_fixable_count = sum(1 for v in report.violations if v.can_auto_fix)

    if args.apply:
        print("\nApplying auto-fixes...")
        # Group violations by file
        by_file: dict[str, list[Violation]] = {}
        for v in report.violations:
            by_file.setdefault(v.file_path, []).append(v)

        for file_path, violations in by_file.items():
            fixes = apply_fix(Path(file_path), violations)
            report.auto_fixed += fixes

        print(f"Applied {report.auto_fixed} fixes")
    else:
        print(f"\n[DRY RUN] Would apply {auto_fixable_count} auto-fixes")
        report.auto_fixed = 0

    # Print report
    print_report(report, verbose=args.verbose or args.report)

    if report.manual_review > 0:
        print(f"\n[WARNING] {report.manual_review} violations require manual review")
        print("Run with --verbose to see details")

    return 0 if report.total_violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
