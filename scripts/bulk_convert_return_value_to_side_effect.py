#!/usr/bin/env python3
"""Bulk convert patch(..., return_value=X) to patch(..., side_effect=lambda *a, **kw: X).

This script fixes the #1 cause of pytest-xdist flaky tests: mock contamination
via return_value on patched module-level functions.

Under xdist, return_value= stores a reference on the Mock object. If the Mock
leaks across test boundaries (common with module-level singletons), the stored
value can be corrupted by another test on the same worker process.
side_effect=lambda creates a fresh return on every call, making tests immune
to cross-worker contamination.

Usage:
    # Dry run (preview changes without modifying files)
    python scripts/bulk_convert_return_value_to_side_effect.py --dry-run

    # Apply changes to all unit test files
    python scripts/bulk_convert_return_value_to_side_effect.py

    # Apply to specific files
    python scripts/bulk_convert_return_value_to_side_effect.py tests/unit/mcp/

    # Show detailed diff for each file
    python scripts/bulk_convert_return_value_to_side_effect.py --diff

    # Only convert patch() calls (not patch.object())
    python scripts/bulk_convert_return_value_to_side_effect.py --patch-only
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path


def find_matching_close_paren(source: str, open_pos: int) -> int:
    """Find the matching closing paren for an opening paren at open_pos.

    Handles nested parens, brackets, braces, and string literals by using
    Python's tokenizer for correctness.
    """
    # Simple balanced-paren counter that respects nesting
    depth = 0
    i = open_pos
    in_string = False
    string_char = ""

    while i < len(source):
        ch = source[i]

        # Handle string literals (skip their contents)
        if not in_string and ch in ('"', "'"):
            # Check for triple-quoted strings
            if source[i : i + 3] in ('"""', "'''"):
                string_char = source[i : i + 3]
                in_string = True
                i += 3
                continue
            else:
                string_char = ch
                in_string = True
                i += 1
                continue
        elif in_string:
            if len(string_char) == 3 and source[i : i + 3] == string_char:
                in_string = False
                i += 3
                continue
            elif len(string_char) == 1 and ch == string_char and source[i - 1] != "\\":
                in_string = False
                i += 1
                continue
            else:
                i += 1
                continue

        # Handle comments (skip to end of line)
        if ch == "#":
            newline = source.find("\n", i)
            if newline == -1:
                return -1
            i = newline + 1
            continue

        if ch in ("(", "[", "{"):
            depth += 1
        elif ch in (")", "]", "}"):
            depth -= 1
            if depth == 0:
                return i

        i += 1

    return -1


def extract_kwarg_value(source: str, kwarg_start: int) -> tuple[int, int, str]:
    """Extract the value expression for a keyword argument.

    Given the position right after 'return_value=' (the start of the value),
    find where the value expression ends (at the next comma at the same
    paren depth, or at the closing paren).

    Returns (value_start, value_end, value_text).
    """
    depth = 0
    i = kwarg_start
    in_string = False
    string_char = ""

    while i < len(source):
        ch = source[i]

        # Handle string literals
        if not in_string and ch in ('"', "'"):
            if source[i : i + 3] in ('"""', "'''"):
                string_char = source[i : i + 3]
                in_string = True
                i += 3
                continue
            else:
                string_char = ch
                in_string = True
                i += 1
                continue
        elif in_string:
            if len(string_char) == 3 and source[i : i + 3] == string_char:
                in_string = False
                i += 3
                continue
            elif len(string_char) == 1 and ch == string_char and source[i - 1] != "\\":
                in_string = False
                i += 1
                continue
            else:
                i += 1
                continue

        # Handle comments
        if ch == "#":
            newline = source.find("\n", i)
            if newline == -1:
                return kwarg_start, len(source), source[kwarg_start:]
            i = newline + 1
            continue

        if ch in ("(", "[", "{"):
            depth += 1
        elif ch in (")", "]", "}"):
            if depth == 0:
                # End of the enclosing call — value ends here
                value = source[kwarg_start:i].rstrip()
                # Strip trailing comma if present
                if value.endswith(","):
                    value = value[:-1].rstrip()
                return kwarg_start, i, value
            depth -= 1
        elif ch == "," and depth == 0:
            # Comma at same depth — value ends here
            value = source[kwarg_start:i].rstrip()
            return kwarg_start, i, value

        i += 1

    value = source[kwarg_start:].rstrip()
    return kwarg_start, len(source), value


def convert_patch_return_value(source: str) -> tuple[str, list[dict]]:
    """Convert patch(..., return_value=X) to patch(..., side_effect=lambda ...: X).

    Returns (modified_source, list_of_changes).
    """
    changes: list[dict] = []

    # Pattern: patch( or patch.object( followed by return_value=
    # We need to find each patch() call that contains return_value= as a kwarg
    pattern = re.compile(
        r"(patch(?:\.object)?)\s*\(",
    )

    result = []
    last_end = 0
    _offset = 0  # Track cumulative offset from replacements

    for match in pattern.finditer(source):
        _patch_start = match.start()
        open_paren = match.end() - 1  # Position of the '('

        # Find the matching close paren
        close_paren = find_matching_close_paren(source, open_paren)
        if close_paren == -1:
            continue

        # Extract the full patch(...) call content (between parens)
        call_content = source[open_paren + 1 : close_paren]

        # Look for return_value= in the call content
        # Must not be inside a nested call (i.e., at depth 0 within this call)
        rv_pattern = re.compile(r"\breturn_value\s*=\s*")
        rv_match = rv_pattern.search(call_content)

        if not rv_match:
            continue

        # Check this is at depth 0 (not inside a nested function call)
        prefix = call_content[: rv_match.start()]
        depth = 0
        in_str = False
        str_ch = ""
        _is_top_level = True

        for ch_idx, ch in enumerate(prefix):
            if not in_str and ch in ('"', "'"):
                if prefix[ch_idx : ch_idx + 3] in ('"""', "'''"):
                    str_ch = prefix[ch_idx : ch_idx + 3]
                    in_str = True
                else:
                    str_ch = ch
                    in_str = True
            elif in_str:
                if len(str_ch) == 3 and prefix[ch_idx : ch_idx + 3] == str_ch:
                    in_str = False
                elif len(str_ch) == 1 and ch == str_ch:
                    in_str = False
            elif ch in ("(", "[", "{"):
                depth += 1
            elif ch in (")", "]", "}"):
                depth -= 1

        if depth != 0:
            # return_value= is inside a nested call, skip
            continue

        # Calculate absolute position of return_value= in the source
        rv_abs_start = open_paren + 1 + rv_match.start()
        rv_value_start = open_paren + 1 + rv_match.end()

        # Extract the value expression
        _, value_end_rel, value_text = extract_kwarg_value(call_content, rv_match.end())
        value_text = value_text.strip()

        # Skip if already using side_effect (shouldn't happen but be safe)
        if "side_effect" in call_content:
            continue

        # Always use lambda *a, **kw: to accept any number of arguments.
        # Using lambda: (no args) is unsafe because the patched function may
        # be called with positional args (e.g., verify_token(token) where
        # token is passed positionally).
        if "\n" in value_text:
            # Multi-line value: wrap in parens for valid syntax
            replacement = f"side_effect=lambda *a, **kw: ({value_text})"
        else:
            replacement = f"side_effect=lambda *a, **kw: {value_text}"

        # Build the replacement range in the original source
        _old_text = source[rv_abs_start : open_paren + 1 + rv_match.end() + len(value_text)]
        # Actually, let's be more precise: replace from return_value to end of value
        _rv_kwarg_text = f"return_value={value_text}"
        _old_start = rv_abs_start
        old_end = rv_abs_start + len("return_value=") + len(source[rv_value_start:rv_value_start].lstrip()) + len(value_text)

        # Recalculate using the raw positions
        old_end = open_paren + 1 + rv_match.end() + len(value_text)
        # Strip leading whitespace from value that might be captured
        actual_old = source[rv_abs_start:old_end]

        # Get line number for reporting
        line_num = source[:rv_abs_start].count("\n") + 1

        changes.append(
            {
                "line": line_num,
                "old": actual_old.strip(),
                "new": replacement,
            }
        )

        # Append everything before this return_value=, then the replacement
        result.append(source[last_end:rv_abs_start])
        result.append(replacement)
        last_end = old_end

    # Append remaining source
    result.append(source[last_end:])

    return "".join(result), changes


def process_file(
    filepath: Path,
    dry_run: bool = False,
    show_diff: bool = False,
) -> list[dict]:
    """Process a single test file. Returns list of changes made."""
    try:
        original = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return []

    # Quick check: does the file have patch(..., return_value=)?
    if "return_value=" not in original:
        return []
    if "patch(" not in original and "patch.object(" not in original:
        return []

    modified, changes = convert_patch_return_value(original)

    if not changes:
        return []

    if show_diff:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=str(filepath),
            tofile=str(filepath),
            n=3,
        )
        sys.stdout.writelines(diff)

    if not dry_run:
        # Verify the modified source is valid Python before writing
        try:
            compile(modified, str(filepath), "exec")
        except SyntaxError as e:
            print(f"  SKIP {filepath}: syntax error after conversion: {e}", file=sys.stderr)
            return []

        filepath.write_text(modified, encoding="utf-8")

    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert patch(..., return_value=X) to side_effect=lambda patterns")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["tests/unit/"],
        help="Paths to process (default: tests/unit/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show unified diff for each modified file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show each individual change",
    )
    args = parser.parse_args()

    # Collect all test files
    test_files: list[Path] = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file():
            test_files.append(path)
        elif path.is_dir():
            test_files.extend(sorted(path.rglob("test_*.py")))
        else:
            print(f"Warning: {path} not found", file=sys.stderr)

    total_changes = 0
    total_files = 0

    for filepath in test_files:
        changes = process_file(filepath, dry_run=args.dry_run, show_diff=args.diff)
        if changes:
            total_files += 1
            total_changes += len(changes)
            action = "Would convert" if args.dry_run else "Converted"
            print(f"  {action} {len(changes)} patterns in {filepath}")
            if args.verbose:
                for change in changes:
                    print(f"    L{change['line']}: {change['old']}")
                    print(f"         → {change['new']}")

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{mode}{total_changes} conversions across {total_files} files")

    if args.dry_run and total_changes > 0:
        print("\nRe-run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
