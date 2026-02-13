#!/usr/bin/env bash
# Tests for .ai/build-agents.sh
# TDD: Written before implementation changes per project requirements
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_SCRIPT="$SCRIPT_DIR/build-agents.sh"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS="$PROJECT_ROOT/AGENTS.md"

PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  PASS: $desc"
    ((PASS++)) || true
  else
    echo "  FAIL: $desc"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    ((FAIL++)) || true
  fi
}

assert_contains() {
  local desc="$1" haystack="$2" needle="$3"
  if echo "$haystack" | grep -qF "$needle"; then
    echo "  PASS: $desc"
    ((PASS++)) || true
  else
    echo "  FAIL: $desc (needle not found: '$needle')"
    ((FAIL++)) || true
  fi
}

BACKUP_FILE=$(mktemp)
trap 'rm -f "$BACKUP_FILE"' EXIT

echo "=== test_build_agents.sh ==="

# Test 1: --check mode detects stale output
echo "Test 1: --check detects stale AGENTS.md"
cp "$AGENTS" "$BACKUP_FILE"
echo "STALE CONTENT" > "$AGENTS"
if bash "$BUILD_SCRIPT" --check 2>/dev/null; then
  echo "  FAIL: --check should have exited non-zero for stale content"
  ((FAIL++)) || true
else
  echo "  PASS: --check detected stale AGENTS.md"
  ((PASS++)) || true
fi
cp "$BACKUP_FILE" "$AGENTS"

# Test 2: Regeneration produces output containing expected sections
echo "Test 2: Regeneration includes expected content"
OUTPUT=$(bash "$BUILD_SCRIPT" --check 2>&1 && cat "$AGENTS")
assert_contains "contains tool config table" "$OUTPUT" "Tool-Specific Configs"
assert_contains "contains beads reference" "$OUTPUT" "bd ready"
assert_contains "contains gastown reference" "$OUTPUT" "gt convoy"
assert_contains "contains CORE.md reference" "$OUTPUT" ".ai/CORE.md"

# Test 3: Idempotent runs
echo "Test 3: Idempotent regeneration"
bash "$BUILD_SCRIPT" 2>/dev/null
FIRST=$(cat "$AGENTS")
bash "$BUILD_SCRIPT" 2>/dev/null
SECOND=$(cat "$AGENTS")
assert_eq "two runs produce identical output" "$FIRST" "$SECOND"

# Test 4: --check passes after regeneration
echo "Test 4: --check passes after fresh generation"
bash "$BUILD_SCRIPT" 2>/dev/null
if bash "$BUILD_SCRIPT" --check 2>/dev/null; then
  echo "  PASS: --check passes after regeneration"
  ((PASS++)) || true
else
  echo "  FAIL: --check should pass after regeneration"
  ((FAIL++)) || true
fi

# Restore original
cp "$BACKUP_FILE" "$AGENTS"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
