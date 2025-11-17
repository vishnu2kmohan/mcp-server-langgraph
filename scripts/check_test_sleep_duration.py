#!/usr/bin/env python3
"""
Sleep duration linter for test files.

Prevents test performance regressions by detecting excessively long sleep() calls.

Thresholds:
- Unit tests: max 0.5s sleep
- Integration tests: max 2.0s sleep (default if not explicitly marked)

Exclusions:
- Meta-tests (tests/meta/) are automatically excluded
- Lines with # noqa: sleep-duration comment are skipped

Usage:
    python scripts/check_test_sleep_duration.py tests/
    python scripts/check_test_sleep_duration.py tests/unit/test_file.py
    python scripts/check_test_sleep_duration.py --unit-max 1.0 --integration-max 3.0 tests/
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Sleep duration thresholds (seconds)
UNIT_TEST_MAX_SLEEP = 0.5
INTEGRATION_TEST_MAX_SLEEP = 2.0

# Patterns to detect sleep calls
SLEEP_PATTERNS = [
    r"time\.sleep\((\d+(?:\.\d+)?)\)",  # time.sleep(1.0)
    r"asyncio\.sleep\((\d+(?:\.\d+)?)\)",  # await asyncio.sleep(1.0)
]


def is_unit_test(file_path: str, content: str) -> bool:
    """
    Determine if file contains unit tests.

    Heuristics:
    - Path contains 'unit'
    - Contains @pytest.mark.unit
    - Default to integration test (less strict, fewer false positives)
    """
    # Explicit unit test markers
    if "unit" in file_path or "/unit/" in file_path:
        return True
    if "@pytest.mark.unit" in content:
        return True

    # Explicit integration test markers
    if "@pytest.mark.integration" in content or "integration" in file_path or "/integration/" in file_path:
        return False

    # Default to integration test (less strict, reduces false positives)
    # Rationale: Most tests are integration, unit tests should explicitly mark themselves
    return False


def check_file(content: str, file_path: str, is_unit: bool = True) -> List[str]:
    """
    Check file for sleep duration violations.

    Args:
        content: File content
        file_path: Path to file (for reporting)
        is_unit: Whether this is a unit test (stricter limits)

    Returns:
        List of violation messages
    """
    violations = []
    max_sleep = UNIT_TEST_MAX_SLEEP if is_unit else INTEGRATION_TEST_MAX_SLEEP
    test_type = "unit tests" if is_unit else "integration tests"

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        if line.strip().startswith("#"):
            continue

        # Skip lines with noqa suppression
        if "# noqa: sleep-duration" in line or "#noqa: sleep-duration" in line:
            continue
        if "# noqa" in line and "sleep" in line.lower():
            # Support generic noqa on sleep lines
            continue

        # Check all sleep patterns
        for pattern in SLEEP_PATTERNS:
            matches = re.finditer(pattern, line)
            for match in matches:
                duration = float(match.group(1))
                if duration > max_sleep:
                    violations.append(
                        f"{file_path}:line {line_num}: "
                        f"Sleep duration {duration}s exceeds {max_sleep}s limit for {test_type}\n"
                        f"  Found: {line.strip()}\n"
                        f"  Recommendation: Reduce sleep to <={max_sleep}s or use VirtualClock for instant time advancement\n"
                        f"  Or add: # noqa: sleep-duration"
                    )

    return violations


def check_test_files(file_paths: List[str]) -> List[str]:
    """
    Check multiple test files for sleep violations.

    Args:
        file_paths: List of test file paths

    Returns:
        List of all violations found
    """
    all_violations = []

    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue

        if not file_path.endswith(".py"):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        is_unit = is_unit_test(file_path, content)
        violations = check_file(content, file_path, is_unit)
        all_violations.extend(violations)

    return all_violations


def find_test_files(directory: str) -> List[str]:
    """
    Recursively find all test files in directory.

    Args:
        directory: Root directory to search

    Returns:
        List of test file paths (excluding meta-tests)
    """
    test_files = []

    for root, dirs, files in os.walk(directory):
        # Skip hidden directories, cache directories, and meta-tests
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__" and d != "meta"]

        # Skip meta-test directory files
        if "/meta/" in root or "\\meta\\" in root or root.endswith("/meta") or root.endswith("\\meta"):
            continue

        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(os.path.join(root, file))

    return test_files


def main():
    """Main entry point."""
    global UNIT_TEST_MAX_SLEEP, INTEGRATION_TEST_MAX_SLEEP

    parser = argparse.ArgumentParser(description="Check test files for excessive sleep durations")
    parser.add_argument("paths", nargs="+", help="Test files or directories to check")
    parser.add_argument(
        "--unit-max", type=float, default=UNIT_TEST_MAX_SLEEP, help=f"Max sleep duration for unit tests (default: 0.5s)"
    )
    parser.add_argument(
        "--integration-max",
        type=float,
        default=INTEGRATION_TEST_MAX_SLEEP,
        help=f"Max sleep duration for integration tests (default: 2.0s)",
    )

    args = parser.parse_args()

    # Update module-level thresholds for check_file function
    UNIT_TEST_MAX_SLEEP = args.unit_max
    INTEGRATION_TEST_MAX_SLEEP = args.integration_max

    # Collect all test files
    test_files = []
    for path in args.paths:
        if os.path.isfile(path):
            test_files.append(path)
        elif os.path.isdir(path):
            test_files.extend(find_test_files(path))

    if not test_files:
        print("No test files found")
        return 0

    # Check files
    violations = check_test_files(test_files)

    if violations:
        print("❌ Sleep duration violations found:\n")
        for violation in violations:
            print(violation)
            print()
        print(f"\nTotal violations: {len(violations)}")
        return 1
    else:
        print(f"✅ All {len(test_files)} test files passed sleep duration checks")
        return 0


if __name__ == "__main__":
    sys.exit(main())
