#!/usr/bin/env python3
"""
Detect Test Time Bombs

Identifies hard-coded future dates, versions, and model names in tests that
will break when those futures become reality (e.g., "gpt-5", "2026-01-01").

Year Threshold:
- Allows up to 25 years in the future (reasonable for JWT/cert expiration tests)
- Years beyond current_year + 25 trigger warnings

Exclusions:
- Expiration/validity contexts (expiration=2099, valid_until=2048)
- Version validation test contexts
- Non-existence testing (testing that gpt-5 doesn't exist yet)
- Lines with # noqa: time-bomb comment

Regression prevention for Codex Finding: Hard-coded "gpt-5" in tests.

Usage:
    python scripts/validate_test_time_bombs.py
    python scripts/validate_test_time_bombs.py --strict  # Fail on warnings
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


# Patterns that indicate potential time bombs
TIME_BOMB_PATTERNS = [
    # Future model names
    (r'"gpt-[5-9]"', "Future OpenAI model name"),
    (r'"gpt-[5-9][.-]', "Future OpenAI model name"),
    (r'"claude-[5-9]"', "Future Anthropic model name"),
    (r'"claude-[5-9][.-]', "Future Anthropic model name"),
    (r'"gemini-[3-9]"', "Future Google model name"),
    (r'"gemini-[3-9][.-]', "Future Google model name"),
    # Future year references (anything > current year + 2)
    (r"20[3-9][0-9]", "Future year reference"),
    # Future version numbers that might become real
    (r'"v?[5-9]\.\d+\.\d+"', "High version number"),
]

# Allowed exceptions (constants that are clearly test/fake values or legitimate test contexts)
ALLOWED_PATTERNS = [
    # Clearly fake/test constants
    r"TEST_.*MODEL",
    r"FAKE_.*MODEL",
    r"NONEXISTENT",
    r"999",
    r"9999",
    r"test-.*-nonexistent",
    # Expiration/validity contexts (legitimate long-term dates)
    r"expir(ation|y|es|ed|es_at|esAt)[\"'\s]*[:=]",  # expiration = 2099, expires_at = "2099", expiresAt
    r"[\"'][^\"']*expir(ation|y|es|ed|es_at|esAt)[^\"']*[\"']",  # "apiKey_expiresAt": "2099"
    r"valid[_\s]*(until|through|to)[\"'\s]*[:=]",  # valid_until = 2048
    r"ttl[\"'\s]*[:=]",  # ttl = 2050
    r"not[_\s]*before[\"'\s]*[:=]",  # not_before = 2025
    r"not[_\s]*after[\"'\s]*[:=]",  # not_after = 2099
    # Parametrized test data (pytest parametrize decorators)
    r"@pytest\.mark\.parametrize",  # Flag whole parametrize blocks (check prior lines)
    r"\[.*,.*,.*\]",  # List of test cases in parametrize
    r"\(.*,.*,.*\)",  # Tuple test cases
    # Version validation test contexts
    r"codecov.*action",  # GitHub Actions version testing
    r"docker.*action",  # Docker action version testing
    r"action.*version",  # Generic action version tests
    # Model name formatting test contexts
    r"model[_\s]*name[\"'\s]*[:=].*[\"'](gpt-|claude-|gemini-)[5-9]",  # model_name = "gpt-5"
    r"provider.*model",  # Testing provider/model combinations
    r"[\"'](openai|anthropic|google)[\"'].*[\"'](gpt-|claude-|gemini-)",  # Provider with model
    # Non-existence/error testing contexts for future models
    r"(invalid|nonexistent|non_existent|fake|test).*[\"'](gpt-|claude-|gemini-)[5-9]",
    r"[\"'](gpt-|claude-|gemini-)[5-9][\"'].*(?:should|must|expected).*(fail|error|invalid|raise)",
    r"[\"'](gpt-|claude-|gemini-)[5-9][\"'].*(?:does.*not|doesn't).*(exist|available)",
]


def check_file(filepath: Path) -> list[dict[str, Any]]:
    """Check a single test file for time bombs."""
    issues = []
    current_year = datetime.now().year
    max_safe_year = current_year + 25  # Allow up to 25 years (reasonable for certs/tokens)

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            # Skip lines with noqa suppression
            if "# noqa: time-bomb" in line or "#noqa: time-bomb" in line:
                continue
            if "# noqa" in line and (
                "gpt-" in line or "claude-" in line or "gemini-" in line or re.search(r"20[3-9][0-9]", line)
            ):
                # Support generic noqa on potential time bomb lines
                continue

            # Check if line is in an allowed context
            is_allowed = any(re.search(pattern, line) for pattern in ALLOWED_PATTERNS)
            if is_allowed:
                continue

            # Check for time bomb patterns
            for pattern, description in TIME_BOMB_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    matched_text = match.group(0)

                    # Special handling for year references
                    if pattern == r"20[3-9][0-9]":
                        try:
                            year = int(matched_text)
                            if year <= max_safe_year:
                                continue  # Reasonable future year, skip
                        except ValueError:
                            continue

                    issues.append(
                        {
                            "file": str(filepath),
                            "line": line_num,
                            "severity": "warning",
                            "pattern": matched_text,
                            "message": f"{description}: '{matched_text}'",
                            "suggestion": "Use clearly fake test constants (e.g., TEST_NONEXISTENT_MODEL = 'gpt-999-test-nonexistent') or add: # noqa: time-bomb",
                        }
                    )

    except Exception as e:
        issues.append(
            {
                "file": str(filepath),
                "line": 0,
                "severity": "error",
                "pattern": "",
                "message": f"Error reading file: {e}",
                "suggestion": "",
            }
        )

    return issues


def main():
    """Main validation function."""
    strict = "--strict" in sys.argv

    test_dir = Path("tests")
    if not test_dir.exists():
        print("❌ tests/ directory not found")
        sys.exit(1)

    all_issues = []
    files_checked = 0

    # Check all test files
    for filepath in test_dir.rglob("test_*.py"):
        issues = check_file(filepath)
        all_issues.extend(issues)
        files_checked += 1

    # Report results
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]

    if errors or warnings:
        print(f"\n🔍 Test Time Bomb Detection Report")
        print(f"Files checked: {files_checked}")
        print(f"Issues found: {len(errors)} errors, {len(warnings)} warnings\n")

        for issue in errors:
            print(f"❌ ERROR: {issue['file']}:{issue['line']}")
            print(f"   {issue['message']}")
            if issue.get("suggestion"):
                print(f"   💡 {issue['suggestion']}\n")

        for issue in warnings:
            print(f"⚠️  WARNING: {issue['file']}:{issue['line']}")
            print(f"   {issue['message']}")
            if issue.get("suggestion"):
                print(f"   💡 {issue['suggestion']}\n")

        if errors or (strict and warnings):
            print("💡 Tip: Replace future model names with clearly fake constants")
            print("   Example: TEST_NONEXISTENT_OPENAI_MODEL = 'gpt-999-test-nonexistent'")
            print("   See tests/test_config_validation.py for reference\n")
            sys.exit(1)
        else:
            print("✅ Passed (warnings are non-blocking)\n")
            sys.exit(0)
    else:
        print(f"✅ Test Time Bomb Detection: All {files_checked} files passed\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
