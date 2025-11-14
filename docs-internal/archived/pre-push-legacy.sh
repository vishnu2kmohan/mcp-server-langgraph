#!/bin/bash
# shellcheck disable=SC2034  # Unused variables are fine in archived/obsolete files
# ⚠️ OBSOLETE: This template is no longer used - kept for historical reference only
#
# The actual pre-push hook at .git/hooks/pre-push is now installed via pre-commit
# and includes comprehensive 4-phase validation (lockfile, type checking, tests, hooks)
# that exactly matches CI/CD configuration.
#
# DO NOT USE THIS FILE. It is a legacy lint-only version.
#
# To install the current pre-push hook, run: make git-hooks
# Or manually: pre-commit install --hook-type pre-push
#
# See: .git/hooks/pre-push for the current comprehensive validation hook
# See: tests/meta/test_hook_sync_validation.py for hook configuration tests
# See: tests/meta/test_local_ci_parity.py for CI parity tests
#
# This file is retained for historical reference and should not be executed.
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEGACY LINT-ONLY VERSION (OBSOLETE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Pre-push hook to ensure code quality before pushing upstream
# This prevents CI/CD failures by running comprehensive lint checks locally

set -e  # Exit on first error

echo "🔍 Running pre-push lint checks..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
LINT_FAILED=0

# Get the remote branch being pushed to
while read local_ref local_sha remote_ref remote_sha
do
    # Determine comparison branch (default to origin/main)
    if [ "$remote_ref" = "refs/heads/main" ] || [ "$remote_ref" = "refs/heads/develop" ]; then
        COMPARE_BRANCH="$remote_ref"
    else
        COMPARE_BRANCH="refs/heads/main"
    fi
done

# Get list of changed Python files
echo "📝 Finding changed Python files..."
CHANGED_FILES=$(git diff --name-only --diff-filter=ACMR origin/main...HEAD | grep -E '\.py$' || true)

if [ -z "$CHANGED_FILES" ]; then
    echo -e "${GREEN}✓ No Python files changed, skipping lint checks${NC}"
    exit 0
fi

echo "Found $(echo "$CHANGED_FILES" | wc -l) changed Python file(s)"
echo ""

# Function to run a linter
run_linter() {
    local name=$1
    local command=$2

    echo -e "${YELLOW}Running $name...${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}"
        echo ""
        LINT_FAILED=1
        return 1
    fi
}

# Change to repo root
cd "$(git rev-parse --show-toplevel)"

# Ensure we're using the virtual environment
if [ ! -f ".venv/bin/activate" ]; then
    echo -e "${RED}✗ Virtual environment not found at .venv${NC}"
    echo "Run 'make install-dev' first"
    exit 1
fi

# Run linters only on changed files
echo "🔧 Running lint checks on changed files..."
echo ""

# 1. flake8 (syntax errors and critical issues)
run_linter "flake8" \
    "echo '$CHANGED_FILES' | xargs -r uv run flake8 --count --select=E9,F63,F7,F82 --show-source --statistics"

# 2. Black format check
run_linter "black" \
    "echo '$CHANGED_FILES' | xargs -r uv run black --check --line-length=127"

# 3. isort import order check
run_linter "isort" \
    "echo '$CHANGED_FILES' | xargs -r uv run isort --check --profile=black --line-length=127"

# 4. mypy type checking (warning only - matches CI continue-on-error behavior)
# TODO: Make this blocking once CI removes continue-on-error flag
echo -e "${YELLOW}Running mypy (warning only)...${NC}"
if uv run mypy --ignore-missing-imports --show-error-codes src/ 2>&1; then
    echo -e "${GREEN}✓ mypy passed${NC}"
else
    echo -e "${YELLOW}⚠ mypy found issues (non-blocking during gradual rollout)${NC}"
fi
echo ""

# 5. bandit security scan
run_linter "bandit" \
    "echo '$CHANGED_FILES' | xargs -r uv run bandit -ll --skip B608"

# Final status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $LINT_FAILED -eq 1 ]; then
    echo -e "${RED}✗ Lint checks failed! Push blocked.${NC}"
    echo ""
    echo "To fix:"
    echo "  1. Run 'make lint-fix' to auto-fix black/isort issues"
    echo "  2. Run 'make lint-check' to see detailed errors"
    echo "  3. Fix remaining issues manually"
    echo ""
    echo "To bypass (not recommended):"
    echo "  git push --no-verify"
    echo ""
    exit 1
else
    echo -e "${GREEN}✓ All lint checks passed!${NC}"
    echo ""
    exit 0
fi
