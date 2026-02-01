#!/usr/bin/env python3
"""Migrate testids from ChatInputForm to ChatInput in test files."""

import re
import sys
from pathlib import Path

# Testid mappings from ChatInputForm to ChatInput
TESTID_MAPPINGS = {
    "chat-input-form": "chat-input-pill",
    "chat-input-container": "chat-input-pill",
    "model-selector-button": "model-settings-button",
    "model-selector-loading": "models-loading",
    "kb-focus-button": "kb-focus-selector",
    "enable-thinking-toggle": "thinking-toggle",
    "url-fetch-indicator": "url-fetch-loading",
}


def migrate_file(filepath: Path) -> int:
    """Migrate testids in a file. Returns count of replacements."""
    content = filepath.read_text()
    original = content
    count = 0

    for old_id, new_id in TESTID_MAPPINGS.items():
        # Match[str] patterns like getByTestId("old-id") or queryByTestId("old-id")
        pattern = rf'(getByTestId|queryByTestId|findByTestId)\s*\(\s*["\']({re.escape(old_id)})["\']'
        replacement = rf'\1("{new_id}"'
        new_content, n = re.subn(pattern, replacement, content)
        if n > 0:
            print(f"  Replaced {old_id} -> {new_id}: {n} occurrences")
            count += n
            content = new_content

    if content != original:
        filepath.write_text(content)
        print(f"Updated {filepath}")

    return count


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: migrate-testids.py <file>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    count = migrate_file(filepath)
    print(f"Total replacements: {count}")


if __name__ == "__main__":
    main()
