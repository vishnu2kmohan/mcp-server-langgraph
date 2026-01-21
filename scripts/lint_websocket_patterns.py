#!/usr/bin/env python3
"""
Custom linter for WebSocket handler patterns.

Detects deprecated patterns that should use WebSocketBase helpers instead:
- self._user_id = ... (use self.user_id property instead)
- if self._websocket and self._subscribed: (use is_ready_to_send or send_if_subscribed)
- self._subscribed = ... without BroadcasterMixin (use mixin for subscription state)

Usage:
    uv run python scripts/lint_websocket_patterns.py [files...]

Exit codes:
    0: No issues found
    1: Deprecated patterns detected
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


class DeprecatedPattern:
    """A deprecated pattern to detect."""

    def __init__(self, pattern: str, message: str, replacement: str) -> None:
        self.regex = re.compile(pattern)
        self.message = message
        self.replacement = replacement


# Patterns to detect in WebSocket handlers
DEPRECATED_PATTERNS = [
    DeprecatedPattern(
        pattern=r"self\._user_id\s*=\s*",
        message="Deprecated: Do not store _user_id manually",
        replacement="Use self.user_id property from WebSocketBase instead",
    ),
    DeprecatedPattern(
        pattern=r"self\._user_id:\s*str",
        message="Deprecated: Do not declare _user_id attribute",
        replacement="Use self.user_id property from WebSocketBase instead",
    ),
    DeprecatedPattern(
        pattern=r'MessageEnvelope\(\s*type="subscribed"',
        message="Deprecated: Verbose subscribed response pattern",
        replacement="Use self.create_subscribed_response() instead",
    ),
    DeprecatedPattern(
        pattern=r'type="subscribed".*MessageEnvelope',
        message="Deprecated: Verbose subscribed response pattern",
        replacement="Use self.create_subscribed_response() instead",
    ),
    DeprecatedPattern(
        pattern=r'MessageEnvelope\(\s*type="unsubscribed"',
        message="Deprecated: Verbose unsubscribed response pattern",
        replacement="Use self.create_unsubscribed_response() instead",
    ),
    DeprecatedPattern(
        pattern=r'type="unsubscribed".*MessageEnvelope',
        message="Deprecated: Verbose unsubscribed response pattern",
        replacement="Use self.create_unsubscribed_response() instead",
    ),
]

# Multi-line patterns that need context (checked separately)
MULTILINE_PATTERNS = [
    {
        "trigger": r"if self\._websocket and self\._subscribed:",
        "followed_by": r"send_json",
        "message": "Deprecated: Verbose subscription guard + send_json pattern",
        "replacement": "Use await self.send_if_subscribed() instead",
    },
    {
        "trigger": r"return MessageEnvelope\(",
        "followed_by": r'type="subscribed"',
        "message": "Deprecated: Verbose subscribed response pattern",
        "replacement": "Use self.create_subscribed_response() instead",
    },
    {
        "trigger": r"return MessageEnvelope\(",
        "followed_by": r'type="unsubscribed"',
        "message": "Deprecated: Verbose unsubscribed response pattern",
        "replacement": "Use self.create_unsubscribed_response() instead",
    },
]

# Only check files in websocket/handlers/
HANDLER_PATH_PATTERN = re.compile(r"websocket/handlers/.*\.py$")

# Patterns for BroadcasterMixin check
SUBSCRIBED_USAGE_PATTERN = re.compile(r"self\._subscribed\s*[=!]")
BROADCASTER_MIXIN_PATTERN = re.compile(r"BroadcasterMixin")
WEBSOCKET_BASE_CLASS_PATTERN = re.compile(r"class\s+\w+\s*\([^)]*WebSocketBase[^)]*\)")
# Excluded handlers that intentionally don't use the mixin pattern
MIXIN_EXCLUDED_HANDLERS = {
    "__init__.py",
    "agent_request.py",  # Uses connect/disconnect instead of subscribe/unsubscribe
    "llm_streaming.py",  # Different streaming pattern
}


def check_broadcaster_mixin_usage(filepath: Path, content: str) -> tuple[int, str, str] | None:
    """
    Check if a handler uses _subscribed but doesn't inherit from BroadcasterMixin.

    Returns:
        A violation tuple if the handler should use BroadcasterMixin, None otherwise.
    """
    # Skip excluded handlers
    if filepath.name in MIXIN_EXCLUDED_HANDLERS:
        return None

    # Check if this is a WebSocketBase handler
    if not WEBSOCKET_BASE_CLASS_PATTERN.search(content):
        return None

    # Check if it uses self._subscribed pattern
    uses_subscribed = SUBSCRIBED_USAGE_PATTERN.search(content)
    if not uses_subscribed:
        return None

    # Check if it inherits from BroadcasterMixin
    uses_mixin = BROADCASTER_MIXIN_PATTERN.search(content)
    if uses_mixin:
        return None

    # Find the line number of the class definition for better error reporting
    lines = content.splitlines()
    for i, line in enumerate(lines, start=1):
        if WEBSOCKET_BASE_CLASS_PATTERN.search(line):
            return (
                i,
                line.strip(),
                "Handler uses self._subscribed but doesn't inherit from BroadcasterMixin. "
                "Add BroadcasterMixin for standardized subscription state management.",
            )

    return None


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a single file for deprecated patterns.

    Returns:
        List of (line_number, line, message) tuples for violations.
    """
    violations: list[tuple[int, str, str]] = []

    try:
        content = filepath.read_text()
        lines = content.splitlines()
    except Exception:
        return violations

    # Check single-line patterns
    for i, line in enumerate(lines, start=1):
        for pattern in DEPRECATED_PATTERNS:
            if pattern.regex.search(line):
                violations.append((i, line.strip(), f"{pattern.message}. {pattern.replacement}"))

    # Check multi-line patterns (trigger + followed_by within 5 lines)
    for i, line in enumerate(lines):
        for mp in MULTILINE_PATTERNS:
            trigger = re.compile(mp["trigger"])
            if trigger.search(line):
                # Check next 5 lines for the followed_by pattern
                followed_by = re.compile(mp["followed_by"])
                for j in range(i + 1, min(i + 6, len(lines))):
                    if followed_by.search(lines[j]):
                        violations.append(
                            (i + 1, line.strip(), f"{mp['message']}. {mp['replacement']}")
                        )
                        break

    # Check BroadcasterMixin usage
    mixin_violation = check_broadcaster_mixin_usage(filepath, content)
    if mixin_violation:
        violations.append(mixin_violation)

    return violations


def main() -> int:
    """Run the linter on specified files or all handler files."""
    if len(sys.argv) > 1:
        # Check specified files
        files = [Path(f) for f in sys.argv[1:]]
    else:
        # Check all handler files
        handlers_dir = Path("src/mcp_server_langgraph/websocket/handlers")
        if not handlers_dir.exists():
            print("Error: handlers directory not found")
            return 1
        files = list(handlers_dir.glob("*.py"))

    # Filter to only check handler files
    handler_files = [f for f in files if HANDLER_PATH_PATTERN.search(str(f))]

    all_violations: dict[Path, list[tuple[int, str, str]]] = {}

    for filepath in handler_files:
        violations = check_file(filepath)
        if violations:
            all_violations[filepath] = violations

    if all_violations:
        print("WebSocket handler deprecated pattern violations found:\n")
        for filepath, violations in all_violations.items():
            print(f"{filepath}:")
            for line_num, line, message in violations:
                print(f"  Line {line_num}: {line}")
                print(f"    -> {message}")
            print()

        print(f"Total: {sum(len(v) for v in all_violations.values())} violations in {len(all_violations)} files")
        print("\nSee WebSocketBase API documentation for migration guidance.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
