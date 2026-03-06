#!/bin/bash
# =============================================================================
# Tests for scripts/hooks/dmypy_check.sh
# =============================================================================
# Lightweight bash assertions — no external test framework required.
# Run: bash tests/scripts/test_dmypy_check.sh
#
# Tests exercise CI/local mode selection, stale lockfile recovery,
# and argument passing WITHOUT launching actual mypy/dmypy processes.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_UNDER_TEST="$REPO_ROOT/scripts/hooks/dmypy_check.sh"

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
# Test Suite 1: Script structure validation
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 1: Script structure ===${NC}"

script_content=$(cat "$SCRIPT_UNDER_TEST")

assert_contains "Script has CI detection" "$script_content" 'CI:-'
assert_contains "Script has GITHUB_ACTIONS detection" "$script_content" 'GITHUB_ACTIONS:-'
assert_contains "Script uses standard mypy in CI" "$script_content" 'uv run --frozen mypy'
assert_contains "Script uses dmypy for local" "$script_content" 'dmypy check'
assert_contains "Script has stale lockfile recovery" "$script_content" 'dmypy kill'
assert_contains "Script passes config-file flag" "$script_content" 'config-file=pyproject.toml'
assert_contains "Script passes show-error-codes flag" "$script_content" 'show-error-codes'
assert_contains "Script passes pretty flag" "$script_content" 'pretty'
assert_contains "Script has set -e for strict mode" "$script_content" 'set -e'

# =============================================================================
# Test Suite 2: CI mode uses standard mypy (not dmypy)
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 2: CI mode path ===${NC}"

# Extract the CI branch of the script (between CI detection and the exit/fi)
ci_block=$(echo "$script_content" | sed -n '/CI:-.*true/,/exit \$\?/p')
assert_contains "CI block runs standard mypy" "$ci_block" 'uv run --frozen mypy src/mcp_server_langgraph'
assert_not_contains "CI block does NOT use dmypy" "$ci_block" 'dmypy'

# =============================================================================
# Test Suite 3: Local mode uses dmypy with recovery
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 3: Local mode path ===${NC}"

# The local path should have daemon status check, start with recovery, and check
local_block=$(echo "$script_content" | sed -n '/dmypy status/,/dmypy check/p')
assert_contains "Local mode checks dmypy status" "$local_block" 'dmypy status'
assert_contains "Local mode has kill fallback" "$script_content" 'dmypy kill'
assert_contains "Local mode starts daemon if needed" "$script_content" 'dmypy start'

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
