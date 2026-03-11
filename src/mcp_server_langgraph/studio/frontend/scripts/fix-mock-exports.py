#!/usr/bin/env python3
"""Bulk fix vi.mock patterns to preserve original module exports.

Transforms inline vi.mock factories that lose original exports:
  vi.mock("../../api", () => ({ useXxx: ... }));
Into importActual-based mocks that preserve all exports:
  vi.mock("../../api", async () => {
    const actual = await vi.importActual("../../api");
    return { ...actual, useXxx: ... };
  });

Targets: api, authSlice, chatConnectionSlice, storage, executionModeSlice,
TelemetryContext, and other commonly broken mock modules.
"""

import re
import sys
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parent.parent / "src"

# Module path patterns to fix (regex fragments matching the quoted path)
TARGET_MODULES = [
    r'["\'][^"\']*\/api["\']',  # ../api, ../../api, etc.
    r'["\'][^"\']*\/authSlice["\']',  # .../authSlice
    r'["\'][^"\']*\/chatConnectionSlice["\']',  # .../chatConnectionSlice
]

# Combined pattern: vi.mock("TARGET", () => ({
MOCK_PATTERN = re.compile(
    r"([ \t]*)"  # capture indent
    r"vi\.mock\(\s*"
    r'(["\'])([^"\']*(?:\/api|\/authSlice|\/chatConnectionSlice|\/storage|\/executionModeSlice|\/TelemetryContext|\/personaSlice|\/sessionSlice|\/FeatureFlagContext))\2'  # path
    r"\s*,\s*"
    r"\(\)\s*=>\s*\(\{"  # () => ({
)


def find_matching_brace(text: str, start: int) -> int:
    """Find the index of the closing } that matches the { at `start`.

    Handles nested braces, string literals (", ', `), template literals,
    and comments (// and /* */).
    """
    depth = 1
    i = start + 1
    while i < len(text):
        ch = text[i]

        # String literals
        if ch in ('"', "'"):
            i += 1
            while i < len(text) and text[i] != ch:
                if text[i] == "\\":
                    i += 1  # skip escaped char
                i += 1
            i += 1  # skip closing quote
            continue

        # Template literals
        if ch == "`":
            i += 1
            while i < len(text) and text[i] != "`":
                if text[i] == "\\":
                    i += 1
                elif text[i] == "$" and i + 1 < len(text) and text[i + 1] == "{":
                    # Template expression - count braces inside
                    i += 2
                    tmpl_depth = 1
                    while i < len(text) and tmpl_depth > 0:
                        if text[i] == "{":
                            tmpl_depth += 1
                        elif text[i] == "}":
                            tmpl_depth -= 1
                        elif text[i] == "\\":
                            i += 1
                        i += 1
                    continue
                i += 1
            i += 1  # skip closing backtick
            continue

        # Line comments
        if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            i += 2
            while i < len(text) and text[i] != "\n":
                i += 1
            continue

        # Block comments
        if ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
            i += 2
            while i < len(text) - 1 and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i

        i += 1
    return -1


def transform_mock(content: str) -> tuple[str, list[str]]:
    """Transform all matching vi.mock blocks in content. Returns (new_content, list_of_paths_fixed)."""
    fixed_paths: list[str] = []
    result = content

    # Process one match at a time (positions shift after each replacement)
    while True:
        match = MOCK_PATTERN.search(result)
        if not match:
            break

        indent = match.group(1)
        mod_path = match.group(3)

        # Skip if this mock block already uses importActual/importOriginal
        # Check a reasonable window after the match
        window_end = min(match.end() + 200, len(result))
        window = result[match.end() : window_end]
        if "importActual" in window or "importOriginal" in window:
            # Skip this match - insert a marker to prevent re-matching
            # Replace the opening () => ({ with a unique marker temporarily
            result = result[: match.start()] + "/*SKIP*/" + result[match.start() :]
            continue

        # Find the { that opens the mock body (the { in `({`)
        body_brace_pos = match.end() - 1  # The { at the end of the match
        body_close_pos = find_matching_brace(result, body_brace_pos)
        if body_close_pos == -1:
            print(f"  WARNING: Could not find matching brace for mock at offset {match.start()}", file=sys.stderr)
            result = result[: match.start()] + "/*SKIP*/" + result[match.start() :]
            continue

        # The full mock ends with })); or }) ); or similar
        # After body_close_pos (the }), we expect ));
        rest = result[body_close_pos + 1 :]
        close_match = re.match(r"\s*\)\s*\)\s*;?\s*\n?", rest)
        if not close_match:
            print(f"  WARNING: Unexpected closing pattern after body for '{mod_path}'", file=sys.stderr)
            result = result[: match.start()] + "/*SKIP*/" + result[match.start() :]
            continue

        block_end = body_close_pos + 1 + close_match.end()

        # Extract body content (between the braces)
        body = result[body_brace_pos + 1 : body_close_pos]

        # Re-indent body: add 2 extra spaces to each non-empty line
        body_lines = body.split("\n")
        reindented_body = []
        for line in body_lines:
            if line.strip():
                reindented_body.append("  " + line)
            else:
                reindented_body.append(line)
        body_reindented = "\n".join(reindented_body)

        # Build the replacement
        new_block = f'{indent}vi.mock("{mod_path}", async () => {{\n'
        new_block += f'{indent}  const actual = await vi.importActual("{mod_path}");\n'
        new_block += f"{indent}  return {{\n"
        new_block += f"{indent}    ...actual,"
        new_block += body_reindented
        new_block += f"\n{indent}  }};\n"
        new_block += f"{indent}}});\n"

        result = result[: match.start()] + new_block + result[block_end:]
        fixed_paths.append(mod_path)

    # Remove skip markers
    result = result.replace("/*SKIP*/", "")

    return result, fixed_paths


def add_telemetry_exports(content: str) -> tuple[str, bool]:
    """Add missing useWebVitals and useTelemetry to TelemetryContext mocks."""
    # Find vi.mock for TelemetryContext
    pattern = re.compile(
        r'vi\.mock\(\s*["\']([^"\']*TelemetryContext)["\']'
        r"\s*,\s*(?:\(\)\s*=>|async\s*\([^)]*\)\s*=>)\s*"
        r"(?:\(\{|\{)"  # Either ({ for inline or { for async body
    )
    match = pattern.search(content)
    if not match:
        return content, False

    # Check if useWebVitals already exists in the mock
    # Look for the end of this mock block
    mock_start = match.start()
    # Find the end - look for })); or }); after mock_start
    rest = content[mock_start:]
    # Find a reasonable window (up to 2000 chars)
    window = rest[:2000]

    has_web_vitals = "useWebVitals" in window
    has_use_telemetry = "useTelemetry" in window

    if has_web_vitals and has_use_telemetry:
        return content, False

    # Find the last property in the mock object before the closing
    # We need to insert before the closing }));
    # Strategy: find `useSessionTelemetry:` and after its block, add the missing exports

    additions = []
    if not has_web_vitals:
        additions.append(
            "  useWebVitals: () => ({\n"
            "    start: vi.fn(),\n"
            "    stop: vi.fn(),\n"
            "    getMetrics: () => ({ fcp: null, lcp: null, cls: null, inp: null }),\n"
            "  }),"
        )
    if not has_use_telemetry:
        additions.append(
            "  useTelemetry: () => ({\n"
            "    sessionTelemetry: { trackSessionCreation: vi.fn(), getMetrics: () => ({}) },\n"
            "    webVitals: { start: vi.fn(), stop: vi.fn(), getMetrics: () => ({}) },\n"
            "  }),"
        )

    if not additions:
        return content, False

    addition_text = "\n".join(additions)

    # Find the closing of the mock's return object
    # Look for patterns like:
    #   }),  (end of useSessionTelemetry block, last property)
    #   })); (end of the vi.mock)
    # We want to insert BEFORE the final }));

    # Find the closing })); for this mock
    # Strategy: find the last })); or }; }); after the mock start
    # Use bracket counting from the vi.mock( opening

    paren_start = content.index("(", mock_start + len("vi.mock"))
    brace_end = find_matching_brace(content, paren_start)
    if brace_end == -1:
        # Try finding })); pattern
        close_patterns = ["}));", "};\n});"]
        for cp in close_patterns:
            idx = content.find(cp, mock_start)
            if idx != -1:
                brace_end = idx
                break

    if brace_end == -1:
        return content, False

    # Find the line before the closing
    # We want to insert just before the } that closes the return object
    # Look backwards from brace_end for the right insertion point
    # Find the } that's part of })); - go back to find a good insertion point
    insert_pos = content.rfind("\n", mock_start, brace_end)
    if insert_pos == -1:
        return content, False

    # Get indentation from surrounding lines
    line_after = content[insert_pos + 1 : brace_end]
    indent_match = re.match(r"(\s*)", line_after)
    base_indent = indent_match.group(1) if indent_match else "  "

    # Re-indent the additions
    indented_additions = []
    for line in addition_text.split("\n"):
        if line.strip():
            indented_additions.append(base_indent + line)
        else:
            indented_additions.append(line)
    indented_text = "\n".join(indented_additions)

    new_content = content[:insert_pos] + "\n" + indented_text + content[insert_pos:]
    return new_content, True


def process_file(filepath: Path, dry_run: bool = False) -> dict:
    """Process a single test file. Returns summary of changes."""
    content = filepath.read_text()
    changes = {}

    # 1. Fix API / authSlice / chatConnectionSlice mocks
    new_content, fixed_paths = transform_mock(content)
    if fixed_paths:
        changes["importActual"] = fixed_paths
        content = new_content

    # 2. Fix TelemetryContext mocks
    new_content, telemetry_fixed = add_telemetry_exports(content)
    if telemetry_fixed:
        changes["telemetry"] = True
        content = new_content

    if changes and not dry_run:
        filepath.write_text(content)

    return changes


def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    # Find all test files
    test_files = sorted(FRONTEND_SRC.rglob("*.test.ts"))
    test_files += sorted(FRONTEND_SRC.rglob("*.test.tsx"))

    total_files = 0
    total_api = 0
    total_telemetry = 0
    fixed_files = []

    for filepath in test_files:
        try:
            changes = process_file(filepath, dry_run=dry_run)
        except Exception as e:
            print(f"ERROR processing {filepath.relative_to(FRONTEND_SRC)}: {e}", file=sys.stderr)
            continue

        if changes:
            total_files += 1
            rel = filepath.relative_to(FRONTEND_SRC)
            fixed_files.append(str(rel))

            if "importActual" in changes:
                total_api += len(changes["importActual"])
                if verbose:
                    for p in changes["importActual"]:
                        print(f"  FIXED {rel}: importActual for {p}")

            if "telemetry" in changes:
                total_telemetry += 1
                if verbose:
                    print(f"  FIXED {rel}: added missing TelemetryContext exports")

    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\n{'=' * 60}")
    print(f"Mock Export Fix Summary ({mode})")
    print(f"{'=' * 60}")
    print(f"Files scanned:  {len(test_files)}")
    print(f"Files fixed:    {total_files}")
    print(f"  importActual: {total_api} mock blocks")
    print(f"  telemetry:    {total_telemetry} files")
    print(f"{'=' * 60}")

    if fixed_files and verbose:
        print("\nFixed files:")
        for f in fixed_files:
            print(f"  {f}")

    return 0 if total_files > 0 or not fixed_files else 1


if __name__ == "__main__":
    sys.exit(main())
