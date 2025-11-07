#!/usr/bin/env bash
# GitHub Actions Workflow Test Harness
#
# This script runs comprehensive validation tests on GitHub Actions workflows
# following TDD principles. It validates:
# - Workflow syntax (actionlint)
# - Action version consistency
# - Dynamic environment variable usage (no hard-coding)
# - Valid composite action inputs
# - Fork protection on commit/push jobs
# - Context usage correctness
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
#   2 - Setup/infrastructure error

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test results
RESULTS=()

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    RESULTS+=("PASS: $1")
}

log_failure() {
    echo -e "${RED}✗${NC} $1"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    RESULTS+=("FAIL: $1")
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

run_test() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    log_info "Running: $test_name"

    if eval "$test_command"; then
        log_success "$test_name"
        return 0
    else
        log_failure "$test_name"
        return 1
    fi
}

# Main test suite
main() {
    local workflow_dir="${1:-.github/workflows}"
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local project_root
    project_root="$(cd "$script_dir/.." && pwd)"

    echo "═══════════════════════════════════════════════════════════════════════════"
    echo "  GitHub Actions Workflow Test Harness"
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo ""
    log_info "Workflow directory: $workflow_dir"
    log_info "Project root: $project_root"
    echo ""

    # Check prerequisites
    if ! command -v actionlint &> /dev/null; then
        echo -e "${RED}✗ actionlint not found. Please install: https://github.com/rhysd/actionlint${NC}"
        exit 2
    fi

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ python3 not found${NC}"
        exit 2
    fi

    # Test 1: actionlint - Workflow syntax validation
    # Simplified: Let actionlint fail fast on errors (removed || true short-circuit)
    run_test "Workflow syntax validation (actionlint)" \
        "actionlint -color $workflow_dir/*.{yml,yaml}"

    # Test 2: Context usage validation (existing script)
    if [[ -f "$script_dir/validate_github_workflows.py" ]]; then
        run_test "Context usage validation" \
            "cd '$project_root' && python3 '$script_dir/validate_github_workflows.py' --workflow-dir '$workflow_dir'"
    else
        log_warning "Skipping context validation (script not found)"
    fi

    # Test 3: Comprehensive workflow validation (new test suite)
    if [[ -f "$project_root/tests/workflows/test_workflow_validation.py" ]]; then
        run_test "Comprehensive workflow validation" \
            "cd '$project_root' && python3 -m pytest tests/workflows/test_workflow_validation.py -v --tb=short"
    else
        log_warning "Skipping comprehensive validation (test file not found)"
    fi

    # Summary
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo "  Test Results Summary"
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "Total tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    echo ""

    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}✓ All workflow tests passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ $FAILED_TESTS test(s) failed${NC}"
        echo ""
        echo "Failed tests:"
        for result in "${RESULTS[@]}"; do
            if [[ $result == FAIL:* ]]; then
                echo -e "${RED}  - ${result#FAIL: }${NC}"
            fi
        done
        return 1
    fi
}

# Run main function
cd "$(dirname "${BASH_SOURCE[0]}")/.."
main "$@"
