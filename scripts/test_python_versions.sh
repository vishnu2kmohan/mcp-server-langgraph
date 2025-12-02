#!/usr/bin/env bash
# Multi-Python Version Smoke Testing Script
# Runs smoke tests on all available Python versions (3.11, 3.12, 3.13)
# to catch version-specific dependency issues before CI
#
# Motivation: PR #121 revealed Click 8.3.x and Hypothesis 6.148.x broke
# on Python 3.11/3.13 while passing on 3.12 (local venv version).
#
# Usage:
#   ./scripts/test_python_versions.sh           # Full suite
#   ./scripts/test_python_versions.sh --quick   # Fast mode (default for pre-push)
#   ./scripts/test_python_versions.sh --ci      # CI mode (fail if version missing)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSIONS=("python3.11" "python3.12" "python3.13")
QUICK_MODE=false
CI_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--quick] [--ci]"
            echo ""
            echo "Options:"
            echo "  --quick  Run minimal smoke tests (faster, uses existing venv)"
            echo "  --ci     CI mode: fail if any Python version is missing"
            echo ""
            echo "Python versions tested: ${PYTHON_VERSIONS[*]}"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Multi-Python Version Smoke Test                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_ROOT"

# Track results (counters only - associative arrays not available in bash 3.x on macOS)
PASSED=0
FAILED=0
SKIPPED=0
# Store results as newline-separated "key:value" pairs for bash 3.x compatibility
RESULTS_STR=""

# Function to check if a Python version is available
check_python_version() {
    local python_cmd="$1"
    if command -v "$python_cmd" &> /dev/null; then
        local version
        version=$("$python_cmd" --version 2>&1 | cut -d' ' -f2)
        echo "$version"
        return 0
    fi
    return 1
}

# Quick mode: Just test the existing venv's pinned dependencies
# This validates that our version pins in pyproject.toml/uv.lock are correct
run_quick_test() {
    echo -e "${BLUE}────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}Quick Mode: Testing pinned dependencies in existing venv${NC}"
    echo -e "${BLUE}────────────────────────────────────────────────────────────${NC}"

    local test_result=0

    # Force development environment to avoid .env production settings triggering validation
    # This smoke test validates imports work, not production config
    export ENVIRONMENT=development

    # Activate existing venv
    if [[ -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
        source "$PROJECT_ROOT/.venv/bin/activate"
    else
        echo -e "  ${YELLOW}⊘ No existing venv found, skipping quick test${NC}"
        return 0
    fi

    # Test Click import
    echo -e "  Testing Click..."
    if python -c "import click; print(f'    click version: {click.__version__}')" 2>&1; then
        echo -e "    ${GREEN}✓ Click import passed${NC}"
    else
        echo -e "    ${RED}✗ Click import failed${NC}"
        test_result=1
    fi

    # Test Hypothesis import (the problematic module)
    echo -e "  Testing Hypothesis..."
    if python -c "import hypothesis; from hypothesis import given, strategies as st; print(f'    hypothesis version: {hypothesis.__version__}')" 2>&1; then
        echo -e "    ${GREEN}✓ Hypothesis import passed${NC}"
    else
        echo -e "    ${RED}✗ Hypothesis import failed${NC}"
        test_result=1
    fi

    # Test core project import
    echo -e "  Testing project import..."
    if python -c "from mcp_server_langgraph.core.config import settings; print(f'    service: {settings.service_name}')" 2>&1; then
        echo -e "    ${GREEN}✓ Project import passed${NC}"
    else
        echo -e "    ${RED}✗ Project import failed${NC}"
        test_result=1
    fi

    deactivate 2>/dev/null || true

    return $test_result
}

# Full mode: Test with temporary venv for each Python version
run_full_test() {
    local python_cmd="$1"

    # Force development environment to avoid .env production settings triggering validation
    export ENVIRONMENT=development
    local version="$2"
    local temp_venv
    temp_venv=$(mktemp -d)
    local test_result=0

    echo -e "${BLUE}────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}Testing with $python_cmd (Python $version)${NC}"
    echo -e "${BLUE}────────────────────────────────────────────────────────────${NC}"

    # Create temporary venv
    echo -e "  Creating temporary venv..."
    if ! "$python_cmd" -m venv "$temp_venv" 2>/dev/null; then
        echo -e "  ${RED}✗ Failed to create venv${NC}"
        rm -rf "$temp_venv"
        return 1
    fi

    # Activate and install
    source "$temp_venv/bin/activate"

    echo -e "  Installing dependencies..."
    if ! pip install --quiet --upgrade pip uv 2>/dev/null; then
        echo -e "  ${RED}✗ Failed to install pip/uv${NC}"
        deactivate
        rm -rf "$temp_venv"
        return 1
    fi

    # Install project with test dependencies
    if ! uv pip install --quiet -e ".[dev]" 2>&1 | grep -v "warning"; then
        echo -e "  ${RED}✗ Failed to install project dependencies${NC}"
        deactivate
        rm -rf "$temp_venv"
        return 1
    fi

    echo -e "  ${GREEN}✓ Dependencies installed successfully${NC}"

    # Run smoke tests
    echo -e "  Running smoke tests..."

    # Verify imports work
    echo -e "    Testing imports..."
    if python -c "from mcp_server_langgraph.core.config import settings; print('  config:', settings.service_name)" 2>&1; then
        echo -e "    ${GREEN}✓ Import test passed${NC}"
    else
        echo -e "    ${RED}✗ Import test failed${NC}"
        test_result=1
    fi

    # Test Click
    echo -e "    Testing CLI..."
    if python -c "import click; print('  click version:', click.__version__)" 2>&1; then
        echo -e "    ${GREEN}✓ Click import passed${NC}"
    else
        echo -e "    ${RED}✗ Click import failed${NC}"
        test_result=1
    fi

    # Test Hypothesis
    echo -e "    Testing hypothesis..."
    if python -c "import hypothesis; from hypothesis import given, strategies as st; print('  hypothesis version:', hypothesis.__version__)" 2>&1; then
        echo -e "    ${GREEN}✓ Hypothesis import passed${NC}"
    else
        echo -e "    ${RED}✗ Hypothesis import failed${NC}"
        test_result=1
    fi

    # Run a subset of tests in full mode
    echo -e "    Running unit tests (subset)..."
    if pytest tests/unit/test_config.py tests/unit/test_feature_flags.py -v --tb=short -q 2>&1 | tail -20; then
        echo -e "    ${GREEN}✓ Unit tests passed${NC}"
    else
        echo -e "    ${RED}✗ Unit tests failed${NC}"
        test_result=1
    fi

    # Cleanup
    deactivate
    rm -rf "$temp_venv"

    return $test_result
}

# Quick mode: just test existing venv dependencies
if $QUICK_MODE; then
    if run_quick_test; then
        echo ""
        echo -e "${GREEN}✓ Quick smoke test passed${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}✗ Quick smoke test failed${NC}"
        exit 1
    fi
fi

# Full mode: test each Python version
for python_cmd in "${PYTHON_VERSIONS[@]}"; do
    version=$(check_python_version "$python_cmd" || echo "")

    if [[ -z "$version" ]]; then
        if $CI_MODE; then
            echo -e "${RED}✗ $python_cmd not found (CI mode - failing)${NC}"
            RESULTS_STR="${RESULTS_STR}${python_cmd}:MISSING\n"
            ((FAILED++))
        else
            echo -e "${YELLOW}⊘ $python_cmd not available (skipping)${NC}"
            RESULTS_STR="${RESULTS_STR}${python_cmd}:SKIPPED\n"
            ((SKIPPED++))
        fi
        continue
    fi

    if run_full_test "$python_cmd" "$version"; then
        echo -e "${GREEN}✓ $python_cmd ($version) - PASSED${NC}"
        RESULTS_STR="${RESULTS_STR}${python_cmd}:PASSED\n"
        ((PASSED++))
    else
        echo -e "${RED}✗ $python_cmd ($version) - FAILED${NC}"
        RESULTS_STR="${RESULTS_STR}${python_cmd}:FAILED\n"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Test Summary                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Helper function to get result for a python version (bash 3.x compatible)
get_result() {
    local key="$1"
    echo -e "$RESULTS_STR" | grep "^${key}:" | cut -d: -f2 | head -1
}

for python_cmd in "${PYTHON_VERSIONS[@]}"; do
    status=$(get_result "$python_cmd")
    status="${status:-UNKNOWN}"
    case $status in
        PASSED)
            echo -e "  $python_cmd: ${GREEN}✓ PASSED${NC}"
            ;;
        FAILED)
            echo -e "  $python_cmd: ${RED}✗ FAILED${NC}"
            ;;
        SKIPPED)
            echo -e "  $python_cmd: ${YELLOW}⊘ SKIPPED${NC}"
            ;;
        MISSING)
            echo -e "  $python_cmd: ${RED}✗ MISSING${NC}"
            ;;
        *)
            echo -e "  $python_cmd: ${YELLOW}? UNKNOWN${NC}"
            ;;
    esac
done

echo ""
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"
echo -e "  Skipped: ${YELLOW}$SKIPPED${NC}"
echo ""

if [[ $FAILED -gt 0 ]]; then
    echo -e "${RED}Some Python versions failed smoke tests!${NC}"
    echo -e "${YELLOW}Check for version-specific dependency issues before pushing.${NC}"
    exit 1
elif [[ $PASSED -eq 0 ]]; then
    echo -e "${YELLOW}Warning: No Python versions were tested.${NC}"
    if $CI_MODE; then
        exit 1
    fi
    exit 0
else
    echo -e "${GREEN}All available Python versions passed smoke tests!${NC}"
    exit 0
fi
