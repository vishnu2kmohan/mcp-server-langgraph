#!/bin/bash
# =============================================================================
# Tests for scripts/hooks/parallel_security_scan.sh
# =============================================================================
# Validates resource-adaptive concurrency, CI SKIP_* protection,
# signal handling, and cross-platform CPU detection.
# Run: bash tests/scripts/test_parallel_security_scan.sh
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_UNDER_TEST="$REPO_ROOT/scripts/hooks/parallel_security_scan.sh"

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
# Test Suite 1: Script structure
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 1: Script structure ===${NC}"

script_content=$(cat "$SCRIPT_UNDER_TEST")

assert_contains "Has CI detection" "$script_content" 'CI:-'
assert_contains "Has signal handling (trap cleanup)" "$script_content" 'trap cleanup'
assert_contains "Has cross-platform CPU detection (nproc)" "$script_content" 'nproc'
assert_contains "Has cross-platform CPU detection (sysctl fallback)" "$script_content" 'sysctl'
assert_contains "Has SKIP_* env var support" "$script_content" 'SKIP_'
assert_contains "Ignores SKIP_* in CI" "$script_content" 'unset SKIP_'
assert_contains "Has dry-run mode" "$script_content" 'DRY_RUN|dry.run'
assert_contains "Runs tools as background jobs" "$script_content" '&$'
assert_contains "Collects exit codes" "$script_content" 'wait'
assert_contains "Reports per-tool status" "$script_content" 'PASS|FAIL|pass|fail'

# =============================================================================
# Test Suite 2: CI mode protections
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 2: CI mode SKIP_* protection ===${NC}"

# In CI mode, SKIP_* vars should be unset
ci_block=$(echo "$script_content" | sed -n '/CI:-.*true/,/fi$/p' | head -20)
assert_contains "CI block unsets SKIP_ vars" "$ci_block" 'unset SKIP_'

# =============================================================================
# Test Suite 3: Dry-run output
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 3: Dry-run mode ===${NC}"

# CI dry-run should show max_concurrent=2
ci_dry=$(CI=true SECURITY_SCAN_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" 2>&1) || true
assert_contains "CI dry-run shows max_concurrent" "$ci_dry" 'max_concurrent'
assert_contains "CI dry-run concurrency <= 2" "$ci_dry" 'max_concurrent=2'

# Local dry-run should show higher concurrency
local_dry=$(unset CI GITHUB_ACTIONS && SECURITY_SCAN_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" 2>&1) || true
assert_contains "Local dry-run shows max_concurrent" "$local_dry" 'max_concurrent'

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
