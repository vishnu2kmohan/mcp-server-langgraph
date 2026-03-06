#!/bin/bash
# =============================================================================
# Tests for scripts/validators/validate_fast_precommit.py
# =============================================================================
# Validates the consolidated pre-commit validator runs all checks in-process.
# Run: bash tests/scripts/test_validate_fast_precommit.sh
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_UNDER_TEST="$REPO_ROOT/scripts/validators/validate_fast_precommit.py"

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

assert_exit_code() {
    local description="$1"
    local expected="$2"
    local actual="$3"
    TOTAL=$((TOTAL + 1))
    if [[ "$actual" -eq "$expected" ]]; then
        echo -e "  ${GREEN}PASS${NC}: $description"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}: $description"
        echo -e "    Expected exit code: $expected, got: $actual"
        FAIL=$((FAIL + 1))
    fi
}

# =============================================================================
# Test Suite 1: Script structure
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 1: Script structure ===${NC}"

script_content=$(cat "$SCRIPT_UNDER_TEST")

assert_contains "Has alembic duplicate check" "$script_content" 'alembic|check_alembic'
assert_contains "Has websocket permissions check" "$script_content" 'websocket|check_websocket'
assert_contains "Has ADR sync check" "$script_content" 'adr|check_adr'
assert_contains "Has main function" "$script_content" 'def main'
assert_contains "Collects results from all checks" "$script_content" 'result|exit_code|errors|failed'
assert_contains "Reports overall status" "$script_content" 'passed|PASS|OK|failed|FAIL|ERROR'

# =============================================================================
# Test Suite 2: Execution (runs without errors on valid repo)
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 2: Execution on valid repo ===${NC}"

set +e
output=$(cd "$REPO_ROOT" && uv run --frozen python -u "$SCRIPT_UNDER_TEST" 2>&1)
exit_code=$?
set -e

# Should succeed on a valid repo (exit 0)
assert_exit_code "Exits 0 on valid repo" 0 "$exit_code"
assert_contains "Shows check names in output" "$output" 'alembic|websocket|adr|ADR'

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
