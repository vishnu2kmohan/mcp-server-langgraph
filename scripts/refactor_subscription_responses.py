#!/usr/bin/env python3
"""
Refactor WebSocket handlers to use create_subscribed_response/create_unsubscribed_response.

This script finds and refactors patterns like:
    return MessageEnvelope(
        type="subscribed",
        payload={"message": "Successfully subscribed..."},
        id=message.id,
    )

To:
    return self.create_subscribed_response(
        correlation_id=message.id,
        message="Successfully subscribed...",
    )

Usage:
    uv run python scripts/refactor_subscription_responses.py [--dry-run]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def refactor_file(filepath: Path, dry_run: bool = False) -> int:
    """Refactor a single file to use subscription response helpers."""
    content = filepath.read_text()
    changes = 0

    # Pattern 1: Simple subscribed response
    # MessageEnvelope(
    #     type="subscribed",
    #     payload={"message": "..."},
    #     id=message.id,
    # )
    subscribed_pattern = re.compile(
        r"MessageEnvelope\(\s*"
        r'type="subscribed",\s*'
        r'payload=\{"message":\s*"([^"]+)"\},\s*'
        r"id=(\S+?),?\s*"  # Non-greedy match to exclude trailing comma
        r"\)",
        re.MULTILINE | re.DOTALL,
    )

    def replace_subscribed(match: re.Match[str]) -> str:
        message = match.group(1)
        correlation_id = match.group(2).rstrip(",")  # Remove trailing comma
        nonlocal changes
        changes += 1
        # Use default message if it matches standard pattern
        if message in ("Successfully subscribed", "Successfully subscribed to alerts"):
            return f"self.create_subscribed_response(correlation_id={correlation_id})"
        return f'self.create_subscribed_response(\n            correlation_id={correlation_id},\n            message="{message}",\n        )'

    content = subscribed_pattern.sub(replace_subscribed, content)

    # Pattern 2: Simple unsubscribed response
    unsubscribed_pattern = re.compile(
        r"MessageEnvelope\(\s*"
        r'type="unsubscribed",\s*'
        r'payload=\{"message":\s*"([^"]+)"\},\s*'
        r"id=(\S+?),?\s*"  # Non-greedy match to exclude trailing comma
        r"\)",
        re.MULTILINE | re.DOTALL,
    )

    def replace_unsubscribed(match: re.Match[str]) -> str:
        message = match.group(1)
        correlation_id = match.group(2).rstrip(",")  # Remove trailing comma
        nonlocal changes
        changes += 1
        # Use default message if it matches standard pattern
        if message in ("Successfully unsubscribed", "Successfully unsubscribed from alerts"):
            return f"self.create_unsubscribed_response(correlation_id={correlation_id})"
        return f'self.create_unsubscribed_response(\n            correlation_id={correlation_id},\n            message="{message}",\n        )'

    content = unsubscribed_pattern.sub(replace_unsubscribed, content)

    if changes > 0:
        print(f"{filepath}: {changes} changes")
        if not dry_run:
            filepath.write_text(content)

    return changes


def main() -> int:
    """Run the refactoring on all handler files."""
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    handlers_dir = Path("src/mcp_server_langgraph/websocket/handlers")
    if not handlers_dir.exists():
        print(f"Error: {handlers_dir} not found")
        return 1

    total_changes = 0
    files_changed = 0

    for filepath in handlers_dir.glob("*.py"):
        if filepath.name == "__init__.py":
            continue

        changes = refactor_file(filepath, dry_run=dry_run)
        if changes > 0:
            files_changed += 1
            total_changes += changes

    print(f"\nTotal: {total_changes} changes in {files_changed} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
