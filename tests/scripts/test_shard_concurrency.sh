#!/bin/bash
# =============================================================================
# Tests for run-tests-sharded.sh resource-adaptive concurrency
# =============================================================================
# Validates that shard concurrency adapts to CI vs local environments.
# Run: bash tests/scripts/test_shard_concurrency.sh
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_UNDER_TEST="$REPO_ROOT/src/mcp_server_langgraph/studio/frontend/scripts/run-tests-sharded.sh"

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

assert_equals() {
    local description="$1"
    local expected="$2"
    local actual="$3"
    TOTAL=$((TOTAL + 1))
    if [[ "$actual" == "$expected" ]]; then
        echo -e "  ${GREEN}PASS${NC}: $description"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}: $description"
        echo -e "    Expected: '$expected', got: '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

# =============================================================================
# Test Suite 1: Script structure — resource-adaptive hard cap
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 1: Script has resource-adaptive concurrency ===${NC}"

script_content=$(cat "$SCRIPT_UNDER_TEST")

assert_contains "Script has CI detection in get_optimal_concurrency" "$script_content" 'CI:-'
assert_contains "Script has VITEST_SHARD_CONCURRENCY_MAX env override" "$script_content" 'VITEST_SHARD_CONCURRENCY_MAX'
assert_contains "Script uses 3/4 CPU formula" "$script_content" 'cpu_count \* 3 / 4'

# =============================================================================
# Test Suite 2: CI mode dry-run outputs low concurrency
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 2: CI mode concurrency ===${NC}"

# Create temp dir with vitest stub
TEST_DIR=$(mktemp -d)
mkdir -p "$TEST_DIR/node_modules/.bin"
cat > "$TEST_DIR/node_modules/.bin/vitest" << 'STUB'
#!/bin/bash
exit 0
STUB
chmod +x "$TEST_DIR/node_modules/.bin/vitest"

# CI mode with parallel should give low concurrency (<=2)
ci_output=$(cd "$TEST_DIR" && CI=true SHARDED_TEST_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" --parallel 2>&1) || true

# Extract concurrency value from dry-run output
ci_concurrency=$(echo "$ci_output" | grep -oE 'concurrency=[0-9]+' | grep -oE '[0-9]+' || echo "NOT_FOUND")
assert_contains "CI dry-run shows concurrency" "$ci_output" "concurrency="

if [[ "$ci_concurrency" != "NOT_FOUND" ]]; then
    if [[ "$ci_concurrency" -le 3 ]]; then
        echo -e "  ${GREEN}PASS${NC}: CI concurrency is conservative (${ci_concurrency} <= 3)"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}: CI concurrency too high (${ci_concurrency} > 3)"
        FAIL=$((FAIL + 1))
    fi
    TOTAL=$((TOTAL + 1))
fi

# =============================================================================
# Test Suite 3: Local mode dry-run allows higher concurrency
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 3: Local mode concurrency ===${NC}"

# Local mode (no CI env var) should allow higher concurrency
local_output=$(cd "$TEST_DIR" && unset CI GITHUB_ACTIONS && SHARDED_TEST_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" --parallel 2>&1) || true

local_concurrency=$(echo "$local_output" | grep -oE 'concurrency=[0-9]+' | grep -oE '[0-9]+' || echo "NOT_FOUND")
assert_contains "Local dry-run shows concurrency" "$local_output" "concurrency="

if [[ "$local_concurrency" != "NOT_FOUND" ]]; then
    if [[ "$local_concurrency" -ge 2 ]]; then
        echo -e "  ${GREEN}PASS${NC}: Local concurrency is reasonable (${local_concurrency} >= 2)"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}: Local concurrency too low (${local_concurrency} < 2)"
        FAIL=$((FAIL + 1))
    fi
    TOTAL=$((TOTAL + 1))
fi

# =============================================================================
# Test Suite 4: VITEST_SHARD_CONCURRENCY_MAX override
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 4: Env var override ===${NC}"

override_output=$(cd "$TEST_DIR" && unset CI GITHUB_ACTIONS && VITEST_SHARD_CONCURRENCY_MAX=3 SHARDED_TEST_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" --parallel 2>&1) || true

override_concurrency=$(echo "$override_output" | grep -oE 'concurrency=[0-9]+' | grep -oE '[0-9]+' || echo "NOT_FOUND")

if [[ "$override_concurrency" != "NOT_FOUND" ]]; then
    if [[ "$override_concurrency" -le 3 ]]; then
        echo -e "  ${GREEN}PASS${NC}: Override caps concurrency (${override_concurrency} <= 3)"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}: Override not respected (${override_concurrency} > 3)"
        FAIL=$((FAIL + 1))
    fi
    TOTAL=$((TOTAL + 1))
fi

# Cleanup
rm -rf "$TEST_DIR"

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
