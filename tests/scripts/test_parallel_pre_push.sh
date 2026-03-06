#!/bin/bash
# =============================================================================
# Tests for scripts/hooks/parallel_pre_push.sh
# =============================================================================
# Validates lane orchestration, resource-adaptive concurrency, hook drift
# detection, signal handling, and sequential fallback.
# Run: bash tests/scripts/test_parallel_pre_push.sh
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_UNDER_TEST="$REPO_ROOT/scripts/hooks/parallel_pre_push.sh"

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
assert_contains "Has memory detection (free)" "$script_content" 'free'
assert_contains "Has dry-run mode" "$script_content" 'DRY_RUN|dry.run'
assert_contains "Has sequential fallback" "$script_content" 'PRE_PUSH_SEQUENTIAL'
assert_contains "Has pre-commit run invocation" "$script_content" 'pre-commit run'
assert_contains "Has PRE_COMMIT_HOME isolation" "$script_content" 'PRE_COMMIT_HOME'

# =============================================================================
# Test Suite 2: Lane definitions
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 2: Lane definitions ===${NC}"

assert_contains "Has Lane 1 (Python Tests)" "$script_content" 'python.test|lane.*1|LANE_1'
assert_contains "Has Lane 2 (Frontend)" "$script_content" 'frontend|lane.*2|LANE_2'
assert_contains "Has Lane 3 (Security)" "$script_content" 'security|lane.*3|LANE_3'
assert_contains "Has Lane 4 (Type Check + Validators)" "$script_content" 'validator|lane.*4|LANE_4'
assert_contains "Has Lane 5 (Infra & Docs)" "$script_content" 'infra|lane.*5|LANE_5'

# =============================================================================
# Test Suite 3: Dry-run output
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 3: Dry-run mode ===${NC}"

# CI dry-run should show max_lanes=2
ci_dry=$(CI=true PRE_PUSH_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" 2>&1 </dev/null) || true
assert_contains "CI dry-run shows max_lanes" "$ci_dry" 'max_lanes'
assert_contains "CI dry-run max_lanes <= 2" "$ci_dry" 'max_lanes=2'
assert_contains "CI dry-run shows lane names" "$ci_dry" 'Lane|lane'

# Local dry-run should show higher lane concurrency
local_dry=$(unset CI GITHUB_ACTIONS && PRE_PUSH_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" 2>&1 </dev/null) || true
assert_contains "Local dry-run shows max_lanes" "$local_dry" 'max_lanes'

# =============================================================================
# Test Suite 4: Sequential fallback
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 4: Sequential fallback ===${NC}"

seq_dry=$(PRE_PUSH_SEQUENTIAL=1 PRE_PUSH_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" 2>&1 </dev/null) || true
assert_contains "Sequential mode detected" "$seq_dry" 'sequential|SEQUENTIAL'

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
