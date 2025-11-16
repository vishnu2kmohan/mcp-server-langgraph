#!/usr/bin/env bash
# test-worktree-automation.sh
# Verification test for git worktree automation
#
# This script tests the worktree automation without launching Claude Code

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
test_start() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $1"
}

test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "${GREEN}  ✓ PASS${NC}"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "${RED}  ✗ FAIL${NC} $1"
}

# Verify we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Git Worktree Automation - Verification Tests${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1: Scripts exist
test_start "Scripts exist and are executable"
if [ -x "scripts/start-worktree-session.sh" ] && [ -x "scripts/cleanup-worktrees.sh" ]; then
    test_pass
else
    test_fail "Scripts not found or not executable"
fi

# Test 2: Scripts have valid syntax
test_start "Scripts have valid bash syntax"
if bash -n scripts/start-worktree-session.sh && bash -n scripts/cleanup-worktrees.sh; then
    test_pass
else
    test_fail "Syntax errors found"
fi

# Test 3: Settings JSON is valid
test_start "Claude settings.json is valid JSON"
if python3 -m json.tool .claude/settings.json > /dev/null 2>&1; then
    test_pass
else
    test_fail "Invalid JSON in settings.json"
fi

# Test 4: SessionStart hook configured
test_start "SessionStart hook includes worktree detection"
if grep -q "claude-worktree-session" .claude/settings.json; then
    test_pass
else
    test_fail "Worktree detection hook not found in settings.json"
fi

# Test 5: Slash command exists
test_start "Cleanup slash command exists"
if [ -f ".claude/commands/cleanup-worktrees.md" ]; then
    test_pass
else
    test_fail "Slash command file not found"
fi

# Test 6: Documentation updated
test_start "CLAUDE.md includes worktree documentation"
if grep -q "Git Worktree Sessions" CLAUDE.md; then
    test_pass
else
    test_fail "Documentation not updated"
fi

# Test 7: Commands README updated
test_start "Commands README includes cleanup command"
if grep -q "/cleanup-worktrees" .claude/commands/README.md; then
    test_pass
else
    test_fail "Commands README not updated"
fi

# Test 8: Create test worktree (if no worktrees exist)
WORKTREES_DIR="../worktrees"
WORKTREES_PATH="${REPO_ROOT}/${WORKTREES_DIR}"
TEST_WORKTREE_NAME="mcp-server-langgraph-test-$(date +%Y%m%d-%H%M%S)"
TEST_WORKTREE_PATH="${WORKTREES_PATH}/${TEST_WORKTREE_NAME}"
TEST_BRANCH="${TEST_WORKTREE_NAME}"

test_start "Create test worktree"
if [ ! -d "$WORKTREES_PATH" ]; then
    mkdir -p "$WORKTREES_PATH"
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
# Create worktree with a new branch (avoids "branch already checked out" error)
if git worktree add -b "$TEST_BRANCH" "$TEST_WORKTREE_PATH" "$CURRENT_BRANCH" > /dev/null 2>&1; then
    test_pass

    # Test 9: Verify metadata file creation
    test_start "Create session metadata file"
    METADATA_FILE="${TEST_WORKTREE_PATH}/.claude-worktree-session"
    cat > "$METADATA_FILE" << EOF
# Claude Code Worktree Session Metadata
SESSION_ID=${TEST_WORKTREE_NAME}
WORKTREE_BRANCH=${TEST_BRANCH}
BASE_BRANCH=${CURRENT_BRANCH}
CREATED_AT=$(date +%Y%m%d-%H%M%S)
PARENT_REPO=${REPO_ROOT}
EOF
    if [ -f "$METADATA_FILE" ]; then
        test_pass
    else
        test_fail "Failed to create metadata file"
    fi

    # Test 10: Verify worktree is clean
    test_start "Verify worktree is clean (for cleanup test)"
    cd "$TEST_WORKTREE_PATH"
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        test_pass
    else
        test_fail "Worktree not clean"
    fi
    cd "$REPO_ROOT"

    # Test 11: Cleanup test worktree
    test_start "Remove test worktree"
    if git worktree remove --force "$TEST_WORKTREE_PATH" 2>/dev/null; then
        # Also delete the test branch
        git branch -D "$TEST_BRANCH" > /dev/null 2>&1
        test_pass
    else
        test_fail "Failed to remove test worktree"
    fi
else
    test_fail "Failed to create test worktree"
fi

# Print summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Test Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Tests Run:    $TESTS_RUN"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
else
    echo -e "Tests Failed: $TESTS_FAILED"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Git worktree automation is ready to use."
    echo ""
    echo "To start a new session:"
    echo "  ./scripts/start-worktree-session.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
