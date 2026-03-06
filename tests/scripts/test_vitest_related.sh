#!/bin/bash
# =============================================================================
# Tests for frontend-test hook vitest --related logic (Phase 3.1)
# =============================================================================
# Lightweight bash assertions — no external test framework required.
# Run: bash tests/scripts/test_vitest_related.sh
#
# Tests validate the frontend-test hook entry in .pre-commit-config.yaml
# for correct --related logic: upstream fallback, config-change detection,
# file count threshold, and related-mode invocation.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK_CONFIG="$REPO_ROOT/.pre-commit-config.yaml"

# Counters
PASS=0
FAIL=0
TOTAL=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# -----------------------------------------------------------------------------
# Assertion helpers
# -----------------------------------------------------------------------------
assert_contains() {
    local description="$1"
    local haystack="$2"
    local needle="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$haystack" | grep -qE "$needle"; then
        echo -e "  ${GREEN}PASS${NC}: $description"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}: $description"
        echo -e "    Expected to find: '$needle'"
        echo -e "    In output: $(echo "$haystack" | head -5)"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local description="$1"
    local haystack="$2"
    local needle="$3"
    TOTAL=$((TOTAL + 1))
    if ! echo "$haystack" | grep -qE "$needle"; then
        echo -e "  ${GREEN}PASS${NC}: $description"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}: $description"
        echo -e "    Expected NOT to find: '$needle'"
        echo -e "    In output: $(echo "$haystack" | head -5)"
        FAIL=$((FAIL + 1))
    fi
}

# =============================================================================
# Extract the frontend-test hook entry from .pre-commit-config.yaml
# =============================================================================
# Extract from "id: frontend-test" to the next hook (next "- id:")
hook_entry=$(sed -n '/- id: frontend-test$/,/^  - id:/p' "$HOOK_CONFIG" | head -n -1)

if [ -z "$hook_entry" ]; then
    echo -e "${RED}FATAL${NC}: Could not find 'id: frontend-test' hook in $HOOK_CONFIG"
    exit 1
fi

# =============================================================================
# Test Suite 1: Upstream fallback (first push / no upstream)
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 1: Upstream fallback ===${NC}"

assert_contains "Has upstream detection via @{push}" "$hook_entry" '@\{push\}'
assert_contains "Falls back to full suite when no upstream" "$hook_entry" 'No upstream tracking branch'
assert_contains "Runs sharded suite on fallback" "$hook_entry" 'run-tests-sharded.sh'

# =============================================================================
# Test Suite 2: Empty changes skip
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 2: Empty changes handling ===${NC}"

assert_contains "Skips tests when no frontend changes" "$hook_entry" 'No frontend source changes, skipping tests'
assert_contains "Has empty CHANGED check" "$hook_entry" 'z.*CHANGED'

# =============================================================================
# Test Suite 3: Config file detection
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 3: Config file change detection ===${NC}"

assert_contains "Checks package.json changes" "$hook_entry" 'package\.json'
assert_contains "Checks package-lock.json changes" "$hook_entry" 'package-lock\.json'
assert_contains "Checks vite.config.ts changes" "$hook_entry" 'vite\.config\.ts'
assert_contains "Checks vitest.config.ts changes" "$hook_entry" 'vitest\.config\.ts'
assert_contains "Checks tsconfig.json changes" "$hook_entry" 'tsconfig\.json'
assert_contains "Checks test utility changes" "$hook_entry" 'src/test/'
assert_contains "Falls back to full suite when config changed" "$hook_entry" 'Config files changed'

# =============================================================================
# Test Suite 4: File count threshold
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 4: File count threshold ===${NC}"

assert_contains "Has file count calculation" "$hook_entry" 'FILE_COUNT'
assert_contains "Threshold is 10 files" "$hook_entry" 'FILE_COUNT.*-gt 10'
assert_contains "Runs full suite above threshold" "$hook_entry" 'many files touched'

# =============================================================================
# Test Suite 5: Related mode for small changesets
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 5: Vitest --related mode ===${NC}"

assert_contains "Uses vitest run --related for small changesets" "$hook_entry" 'vitest run --related'
assert_contains "Reports number of changed files" "$hook_entry" 'changed file'

# =============================================================================
# Test Suite 6: Hook metadata
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 6: Hook metadata ===${NC}"

assert_contains "Hook is at pre-push stage" "$hook_entry" 'pre-push'
assert_contains "Hook does not pass filenames" "$hook_entry" 'pass_filenames: false'
assert_contains "Hook filters to frontend ts/tsx files" "$hook_entry" 'frontend/src/.*\\.\(ts|tsx\)'

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================"
echo -e "Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, $TOTAL total"
echo "============================================"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
exit 0
