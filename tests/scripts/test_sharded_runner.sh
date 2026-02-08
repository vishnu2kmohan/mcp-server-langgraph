#!/bin/bash
# =============================================================================
# Tests for run-tests-sharded.sh
# =============================================================================
# Lightweight bash assertions — no external test framework required.
# Run: bash tests/scripts/test_sharded_runner.sh
# Or:  make test-frontend-scripts
#
# These tests exercise argument parsing, help text, flag precedence,
# and dry-run output WITHOUT launching actual vitest processes.
# =============================================================================

set -euo pipefail

# Paths (relative to repo root)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_UNDER_TEST="$REPO_ROOT/src/mcp_server_langgraph/studio/frontend/scripts/run-tests-sharded.sh"
TEST_UTILS="$REPO_ROOT/.claude/lib/test_utils.sh"

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

# -----------------------------------------------------------------------------
# Test setup: create a temporary directory with a vitest stub
# -----------------------------------------------------------------------------
setup_test_env() {
    TEST_DIR=$(mktemp -d)
    # Create node_modules/.bin/vitest stub that exits 0
    mkdir -p "$TEST_DIR/node_modules/.bin"
    cat > "$TEST_DIR/node_modules/.bin/vitest" << 'STUB'
#!/bin/bash
# Stub vitest for testing — records invocations and exits 0
echo "VITEST_STUB_CALLED: $*" >> "${VITEST_STUB_LOG:-/dev/null}"
echo "VITEST_STUB: args=$*"
exit 0
STUB
    chmod +x "$TEST_DIR/node_modules/.bin/vitest"

    # Create npm stub that records calls
    mkdir -p "$TEST_DIR/bin"
    cat > "$TEST_DIR/bin/npm" << 'STUB'
#!/bin/bash
echo "NPM_STUB_CALLED: $*" >> "${NPM_STUB_LOG:-/dev/null}"
echo "NPM_STUB: args=$*"
exit 0
STUB
    chmod +x "$TEST_DIR/bin/npm"
}

teardown_test_env() {
    [[ -n "${TEST_DIR:-}" ]] && rm -rf "$TEST_DIR"
}
trap teardown_test_env EXIT

# =============================================================================
# Test Suite 1: --help output
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 1: Help text ===${NC}"

help_output=$(bash "$SCRIPT_UNDER_TEST" --help 2>&1) || true

assert_contains "--help includes --ci flag" "$help_output" "ci"
assert_contains "--help includes --parallel flag" "$help_output" "parallel"
assert_contains "--help includes --fast flag" "$help_output" "fast"
assert_contains "--help includes --shard flag" "$help_output" "shard"
assert_contains "--help mentions heap escalation for CI" "$help_output" "[Hh]eap"

# =============================================================================
# Test Suite 2: --ci flag dry-run output
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 2: --ci flag (dry-run) ===${NC}"

setup_test_env

# Run with --ci and SHARDED_TEST_DRY_RUN=1 to get config output without running shards
ci_output=$(cd "$TEST_DIR" && SHARDED_TEST_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" --ci 2>&1) || true

assert_contains "--ci sets 50 shards" "$ci_output" "50 shards"
assert_contains "--ci enables CI mode" "$ci_output" "[Cc][Ii]"

# =============================================================================
# Test Suite 3: Flag precedence
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 3: Flag precedence ===${NC}"

# --parallel --ci → sequential (--ci overrides --parallel, last flag wins)
pc_output=$(cd "$TEST_DIR" && SHARDED_TEST_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" --parallel --ci 2>&1) || true
assert_not_contains "--parallel --ci → sequential (no concurrency)" "$pc_output" "concurrency"

# --ci --parallel → parallel with 50 shards (--parallel overrides --ci's sequential)
cp_output=$(cd "$TEST_DIR" && SHARDED_TEST_DRY_RUN=1 bash "$SCRIPT_UNDER_TEST" --ci --parallel 2>&1) || true
assert_contains "--ci --parallel → parallel (concurrency shown)" "$cp_output" "concurrency"
assert_contains "--ci --parallel → still 50 shards" "$cp_output" "50 shards"

teardown_test_env

# =============================================================================
# Test Suite 4: run_npm_test_parallel() behavior
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 4: run_npm_test_parallel() delegation ===${NC}"

setup_test_env

# Create a mock frontend directory structure for test_utils.sh
FRONTEND_DIR="$TEST_DIR/src/mcp_server_langgraph/studio/frontend"
mkdir -p "$FRONTEND_DIR/scripts"
mkdir -p "$FRONTEND_DIR/node_modules/.bin"

# Copy the sharded runner script to the mock frontend dir
cp "$SCRIPT_UNDER_TEST" "$FRONTEND_DIR/scripts/run-tests-sharded.sh"

# Create vitest stub in the mock frontend dir
cp "$TEST_DIR/node_modules/.bin/vitest" "$FRONTEND_DIR/node_modules/.bin/vitest"

# Test: no args → should invoke sharded runner
NPM_LOG="$TEST_DIR/npm_calls.log"

# Create a wrapper script that tests run_npm_test_parallel
cat > "$TEST_DIR/test_no_args.sh" << WRAPPER
#!/bin/bash
set -euo pipefail
export PATH="$TEST_DIR/bin:\$PATH"
export NPM_STUB_LOG="$NPM_LOG"
export SHARDED_TEST_DRY_RUN=1

cd "$TEST_DIR"
source "$TEST_UTILS"

# Override frontend_dir to our test location
run_npm_test_parallel 2>&1
WRAPPER
chmod +x "$TEST_DIR/test_no_args.sh"

no_args_output=$(bash "$TEST_DIR/test_no_args.sh" 2>&1) || true
assert_contains "No args → invokes sharded runner" "$no_args_output" "sharded|Sharded|shard"

# Test: with file args → should use direct vitest (npm test)
cat > "$TEST_DIR/test_with_args.sh" << WRAPPER
#!/bin/bash
set -euo pipefail
export PATH="$TEST_DIR/bin:\$PATH"
export NPM_STUB_LOG="$NPM_LOG"

cd "$TEST_DIR"
source "$TEST_UTILS"

run_npm_test_parallel "src/path/to/file.test.tsx" 2>&1
WRAPPER
chmod +x "$TEST_DIR/test_with_args.sh"

with_args_output=$(bash "$TEST_DIR/test_with_args.sh" 2>&1) || true
assert_contains "With args → uses npm test (direct vitest)" "$with_args_output" "NPM_STUB|npm|pool"

teardown_test_env

# =============================================================================
# Test Suite 5: NODE_OPTIONS conflict fix — vitest called directly
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 5: run_shard() uses vitest directly (not npm run test:single) ===${NC}"

# Verify the script calls ./node_modules/.bin/vitest, not npm run test:single
script_content=$(cat "$SCRIPT_UNDER_TEST")
assert_contains "run_shard() calls vitest directly" "$script_content" "node_modules/.bin/vitest"
# Check that no non-comment line invokes npm run test:single
# (comments explaining the change are allowed)
non_comment_lines=$(echo "$script_content" | grep -Ev '^[[:space:]]*#' | grep -Ev '^[[:space:]]*echo')
assert_not_contains "run_shard() does NOT call npm run test:single (non-comment)" "$non_comment_lines" "npm run test:single"

# =============================================================================
# Test Suite 6: CI heap cap
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 6: CI mode caps heap escalation ===${NC}"

# The script should reference CI_MODE and cap at 6144
assert_contains "Script references CI_MODE for heap cap" "$script_content" "CI_MODE"
assert_contains "Script caps heap at 6144 (6GB) in CI" "$script_content" "6144"

# =============================================================================
# Test Suite 7: wait -n optimization (bash version gated)
# =============================================================================
echo ""
echo -e "${YELLOW}=== Suite 7: wait -n optimization ===${NC}"

assert_contains "Script has bash version check for wait -n" "$script_content" "BASH_VERSINFO"
assert_contains "Script uses wait -n -p for bash 5.1+" "$script_content" "wait -n"
assert_contains "Script has fallback for older bash" "$script_content" "kill -0"

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
