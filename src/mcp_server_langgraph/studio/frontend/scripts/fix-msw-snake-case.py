#!/usr/bin/env python3
"""
Fix MSW handlers and test fixtures to use snake_case for API responses.

This script converts camelCase property names to snake_case in MSW handler
response objects to match the actual Python backend API format.

Usage: python scripts/fix-msw-snake-case.py
"""

import re
from typing import Any, Match
import sys
from pathlib import Path

# Mapping of camelCase to snake_case for API properties
CAMEL_TO_SNAKE = {
    "inputSchema": "input_schema",
    "createdAt": "created_at",
    "updatedAt": "updated_at",
    "sessionId": "session_id",
    "workflowId": "workflow_id",
    "nodeId": "node_id",
    "nodeName": "node_name",
    "startTime": "start_time",
    "endTime": "end_time",
    "traceId": "trace_id",
    "spanId": "span_id",
    "rawOutput": "raw_output",
    "currentNode": "current_node",
    "showAfterMs": "show_after_ms",
    "targetElement": "target_element",
    "currentStep": "current_step",
    "userId": "user_id",
    "currentStepId": "current_step_id",
}

# Files to process (from audit report)
MSW_HANDLER_FILES = [
    "src/mocks/handlers/mcpHandlers.ts",
    "src/mocks/handlers/canvasHandlers.ts",
    "src/mocks/handlers/canvasHandlers.test.ts",
    "src/mocks/handlers/aiSuggestionsHandlers.test.ts",
    "src/mocks/handlers/aiHandlers.test.ts",
]

TEST_FIXTURE_FILES = [
    "src/store/slices/workflowSlice.test.ts",
    "src/store/slices/__tests__/sessionSlice.crud.test.ts",
    "src/components/Chat/SaveAsWorkflowButton.test.tsx",
]


def fix_file(filepath: Path) -> tuple[int, list[str]]:
    """Fix camelCase to snake_case in a file. Returns (changes_count, changed_lines)."""
    if not filepath.exists():
        print(f"  Skipping {filepath} - file not found")
        return 0, []

    content = filepath.read_text()
    original = content
    changes = []

    for camel, snake in CAMEL_TO_SNAKE.items():
        # Match[str] property assignments like `nodeId:` or `"nodeId":` or `'nodeId':`
        # but NOT in comments or strings describing the property
        patterns = [
            # Object property: nodeId: value
            (rf'(\s+)({camel})(\s*:\s*)', rf'\1{snake}\3'),
            # Quoted property in object: "nodeId": value
            (rf'(["\'])({camel})\1(\s*:\s*)', rf'"{snake}"\3'),
        ]

        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                changes.append(f"  - {camel} -> {snake} ({count} occurrences)")
                content = new_content

    if content != original:
        filepath.write_text(content)
        return len(changes), changes

    return 0, []


def main() -> int:
    print("🔧 Fixing MSW handlers and test fixtures to use snake_case...\n")

    total_files = 0
    total_changes = 0

    # Process MSW handlers
    print("📦 MSW Handlers:")
    for file_path in MSW_HANDLER_FILES:
        path = Path(file_path)
        count, changes = fix_file(path)
        if count > 0:
            total_files += 1
            total_changes += count
            print(f"  ✅ {file_path}")
            for change in changes:
                print(change)
        else:
            print(f"  ⏭️  {file_path} (no changes needed)")

    print("\n🧪 Test Fixtures:")
    for file_path in TEST_FIXTURE_FILES:
        path = Path(file_path)
        count, changes = fix_file(path)
        if count > 0:
            total_files += 1
            total_changes += count
            print(f"  ✅ {file_path}")
            for change in changes:
                print(change)
        else:
            print(f"  ⏭️  {file_path} (no changes needed)")

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: Fixed {total_changes} properties in {total_files} files")
    print("=" * 60)

    if total_changes > 0:
        print("\n⚠️  Remember to run tests to verify the changes:")
        print("   npm test -- --run")

    return 0


if __name__ == "__main__":
    sys.exit(main())
