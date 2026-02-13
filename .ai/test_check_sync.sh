#!/usr/bin/env bash
# Tests for .ai/check-sync.sh
# TDD: Written before implementation changes per project requirements
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_SCRIPT="$SCRIPT_DIR/check-sync.sh"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0

assert_exit() {
  local desc="$1" expected_exit="$2"
  shift 2
  if "$@" >/dev/null 2>&1; then
    actual_exit=0
  else
    actual_exit=$?
  fi
  if [[ "$actual_exit" == "$expected_exit" ]]; then
    echo "  PASS: $desc"
    ((PASS++)) || true
  else
    echo "  FAIL: $desc (expected exit=$expected_exit, got exit=$actual_exit)"
    ((FAIL++)) || true
  fi
}

BACKUP_CURSOR_FILE=$(mktemp)
BACKUP_AGENTS_FILE=$(mktemp)
trap 'rm -f "$BACKUP_CURSOR_FILE" "$BACKUP_AGENTS_FILE"' EXIT

echo "=== test_check_sync.sh ==="

# Test 1: Passes when all configs reference CORE.md
echo "Test 1: Passes with valid configs"
assert_exit "check-sync passes with valid configs" 0 bash "$CHECK_SCRIPT"

# Test 2: Detects missing CORE.md reference
echo "Test 2: Detects missing CORE.md reference"
cp "$PROJECT_ROOT/.cursorrules" "$BACKUP_CURSOR_FILE"
perl -pi -e 's/CORE\.md/PLACEHOLDER/g' "$PROJECT_ROOT/.cursorrules"
assert_exit "check-sync fails with missing CORE.md ref" 1 bash "$CHECK_SCRIPT"
cp "$BACKUP_CURSOR_FILE" "$PROJECT_ROOT/.cursorrules"

# Test 3: Detects stale AGENTS.md
echo "Test 3: Detects stale AGENTS.md"
cp "$PROJECT_ROOT/AGENTS.md" "$BACKUP_AGENTS_FILE"
echo "STALE CONTENT" > "$PROJECT_ROOT/AGENTS.md"
assert_exit "check-sync fails with stale AGENTS.md" 1 bash "$CHECK_SCRIPT"
cp "$BACKUP_AGENTS_FILE" "$PROJECT_ROOT/AGENTS.md"

# Test 4: --fix regenerates stale AGENTS.md
echo "Test 4: --fix regenerates stale AGENTS.md"
cp "$PROJECT_ROOT/AGENTS.md" "$BACKUP_AGENTS_FILE"
echo "STALE CONTENT" > "$PROJECT_ROOT/AGENTS.md"
bash "$CHECK_SCRIPT" --fix >/dev/null 2>&1 || true
AFTER_FIX=$(cat "$PROJECT_ROOT/AGENTS.md")
if [[ "$AFTER_FIX" != "STALE CONTENT" ]]; then
  echo "  PASS: --fix regenerated AGENTS.md"
  ((PASS++)) || true
else
  echo "  FAIL: --fix did not regenerate AGENTS.md"
  ((FAIL++)) || true
fi
cp "$BACKUP_AGENTS_FILE" "$PROJECT_ROOT/AGENTS.md"

# Test 5: Handles missing config files gracefully
echo "Test 5: Handles missing config files gracefully"
# Temporarily remove a config file to exercise the missing-file code path
cp "$PROJECT_ROOT/.cursorrules" "$BACKUP_CURSOR_FILE"
rm "$PROJECT_ROOT/.cursorrules"
assert_exit "check-sync handles missing files" 0 bash "$CHECK_SCRIPT"
cp "$BACKUP_CURSOR_FILE" "$PROJECT_ROOT/.cursorrules"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
