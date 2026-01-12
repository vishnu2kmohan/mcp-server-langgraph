#!/usr/bin/env python3
"""
Test ID Consistency Validation

Validates that data-testid selectors used in E2E tests match the actual
data-testid attributes defined in React components.

This prevents mismatches like:
- E2E test expects: [data-testid="audit-log-entry"]
- Component uses: [data-testid="audit-log-row"]

Usage:
    python scripts/validation/check_testid_consistency.py

Exit codes:
    0 - All test IDs are consistent
    1 - Mismatches found (selectors in E2E tests not found in components)
    2 - Error during execution
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

# Repository root
REPO_ROOT = Path(__file__).parent.parent.parent

# Frontend paths
FRONTEND_ROOT = REPO_ROOT / "src" / "mcp_server_langgraph" / "studio" / "frontend"
SRC_DIR = FRONTEND_ROOT / "src"  # Search all of src/ for test IDs
E2E_DIR = FRONTEND_ROOT / "e2e"

# Known issues to ignore (pre-existing test ID mismatches tracked for future fix)
# Format: frozenset of test IDs that are allowed to be unmatched
# These use partial matching patterns (data-testid*=) or will be added later
KNOWN_UNMATCHED_TESTIDS: frozenset[str] = frozenset(
    {
        "heart",  # admin-journey.spec.ts:124 - uses partial match
        "metric",  # admin-journey.spec.ts:124 - uses partial match
        "user",  # admin-journey.spec.ts:173 - uses partial match
        "chat-messages",  # api-verification.spec.ts:412 - optional component
        # Studio Canvas WIP - components being developed
        "nav-chat",  # studio-shell-smoke.spec.ts - ActivityBar component
        "nav-admin",  # studio-shell-smoke.spec.ts - ActivityBar component
        "new-chat-button",  # studio-shell-smoke.spec.ts - SessionNav component
        # HITL approval components
        "awaiting-approval-indicator",  # agent-hitl-approval.spec.ts
        "awaiting",  # agent-hitl-approval.spec.ts - partial match
        # MCP/server patterns
        "server",  # alice-*-journey.spec.ts - partial match for MCP servers
        # Sandpack code playground (third-party component)
        "run-code-button",  # artifact-rendering.spec.ts - Sandpack component
        "sandpack-preview",  # artifact-rendering.spec.ts - Sandpack component
        # Layout patterns - partial matches
        "sidebar",  # ios-pwa.spec.ts - layout component
        "left-sidebar",  # ios-pwa.spec.ts - layout component
        # Persona indicator
        "persona-indicator",  # websocket-status.spec.ts - status bar indicator
        # DataFrame rendering e2e tests - fallback selectors for code execution
        "code-artifact",  # dataframe-rendering.spec.ts - fallback for canvas-artifact
        "stdout",  # dataframe-rendering.spec.ts - code execution output
        "stderr",  # dataframe-rendering.spec.ts - code execution error output
        # File operations e2e tests
        "files-page",  # file-operations.spec.ts - files navigation
        # Hallucination reporting e2e tests
        "assistant-message",  # hallucination-reporting.spec.ts - fallback selector
        "user-message",  # hallucination-reporting.spec.ts - fallback selector
    }
)


class TestIdUsage(NamedTuple):
    """Represents a test ID usage."""

    test_id: str
    file: Path
    line_number: int
    context: str


def extract_testids_from_components() -> set[str]:
    """
    Extract all data-testid values from React components.

    Patterns matched:
    - data-testid="..."
    - data-testid={`...`}
    - data-testid={`...-${var}`}
    """
    testids: set[str] = set()

    # Pattern for static data-testid="..."
    static_pattern = re.compile(r'data-testid="([^"]+)"')

    # Pattern for template literal data-testid={`...`}
    # Captures the base pattern before any ${} interpolation
    template_pattern = re.compile(r"data-testid=\{`([^`$]+)")

    # Search all of src/ for data-testid attributes
    if not SRC_DIR.exists():
        return testids

    for tsx_file in SRC_DIR.rglob("*.tsx"):
        content = tsx_file.read_text(encoding="utf-8")

        # Find static test IDs
        for match in static_pattern.finditer(content):
            testids.add(match.group(1))

        # Find template literal base patterns
        for match in template_pattern.finditer(content):
            # Add the base pattern with wildcard indicator
            base = match.group(1).rstrip("-")
            testids.add(f"{base}-*")

    return testids


def extract_testid_selectors_from_e2e() -> list[TestIdUsage]:
    """
    Extract all data-testid selectors used in E2E tests.

    Patterns matched:
    - [data-testid="..."]
    - [data-testid*="..."]
    - getByTestId("...")
    """
    usages: list[TestIdUsage] = []

    # Pattern for CSS-style selectors
    css_pattern = re.compile(r'\[data-testid[*]?="([^"]+)"\]')

    # Pattern for Playwright getByTestId
    playwright_pattern = re.compile(r'getByTestId\([\'"]([^\'"]+)[\'"]\)')

    if not E2E_DIR.exists():
        return usages

    for spec_file in E2E_DIR.rglob("*.spec.ts"):
        content = spec_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find CSS selectors
            for match in css_pattern.finditer(line):
                usages.append(
                    TestIdUsage(
                        test_id=match.group(1),
                        file=spec_file,
                        line_number=line_num,
                        context=line.strip()[:100],
                    )
                )

            # Find Playwright getByTestId calls
            for match in playwright_pattern.finditer(line):
                usages.append(
                    TestIdUsage(
                        test_id=match.group(1),
                        file=spec_file,
                        line_number=line_num,
                        context=line.strip()[:100],
                    )
                )

    return usages


def matches_component_testid(e2e_testid: str, component_testids: set[str]) -> bool:
    """
    Check if an E2E test ID matches any component test ID.

    Handles:
    - Exact matches
    - Wildcard patterns (session-item-* matches session-item-123)
    - Partial matches for dynamic IDs
    """
    # Direct match
    if e2e_testid in component_testids:
        return True

    # Check for wildcard patterns
    for comp_id in component_testids:
        if comp_id.endswith("-*"):
            base = comp_id[:-2]  # Remove -* suffix
            if e2e_testid.startswith(f"{base}-"):
                return True
            # Also check if the selector contains the base pattern
            if base in e2e_testid:
                return True

    # Check if e2e_testid is a prefix pattern (e.g., "session" in "session-item-123")
    for comp_id in component_testids:
        if e2e_testid in comp_id:
            return True

    return False


def main() -> int:
    """Run the test ID consistency check."""
    print("=" * 60)
    print("Test ID Consistency Validation")
    print("=" * 60)
    print()

    # Extract test IDs from components
    print("Scanning React components for data-testid attributes...")
    component_testids = extract_testids_from_components()
    print(f"Found {len(component_testids)} unique test IDs in components")

    if component_testids:
        print("\nComponent test IDs (sample):")
        for tid in sorted(component_testids)[:10]:
            print(f"  - {tid}")
        if len(component_testids) > 10:
            print(f"  ... and {len(component_testids) - 10} more")

    # Extract selectors from E2E tests
    print("\nScanning E2E tests for data-testid selectors...")
    e2e_usages = extract_testid_selectors_from_e2e()
    print(f"Found {len(e2e_usages)} test ID selector usages in E2E tests")

    if not e2e_usages:
        print("\nNo test ID selectors found in E2E tests. Nothing to validate.")
        return 0

    # Find mismatches (excluding known issues)
    mismatches: list[TestIdUsage] = []
    for usage in e2e_usages:
        if usage.test_id in KNOWN_UNMATCHED_TESTIDS:
            continue  # Skip known issues
        if not matches_component_testid(usage.test_id, component_testids):
            mismatches.append(usage)

    # Report results
    print()
    if not mismatches:
        print("✅ All E2E test ID selectors match component test IDs!")
        return 0

    print(f"❌ Found {len(mismatches)} potential mismatches:")
    print()

    # Group by file
    by_file: dict[Path, list[TestIdUsage]] = {}
    for m in mismatches:
        by_file.setdefault(m.file, []).append(m)

    for file_path, usages in sorted(by_file.items()):
        rel_path = file_path.relative_to(REPO_ROOT)
        print(f"  {rel_path}:")
        for usage in usages:
            print(f"    Line {usage.line_number}: {usage.test_id}")
            print(f"      Context: {usage.context[:60]}...")
        print()

    print("Suggestions:")
    print("  1. Check if the component uses a different test ID naming pattern")
    print("  2. Add the missing data-testid attribute to the component")
    print("  3. Update the E2E test to use the correct selector")
    print()
    print("See: .claude/context/testid-naming-convention.md for naming standards")

    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
