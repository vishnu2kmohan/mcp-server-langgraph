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
#   ./scripts/test_python_versions.sh --quick   # Fast mode
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
            echo "  --quick  Run minimal smoke tests (faster)"
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

# Track results
declare -A RESULTS
PASSED=0
FAILED=0
SKIPPED=0

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

# Function to run smoke tests for a specific Python version
run_smoke_test() {
    local python_cmd="$1"
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

    if $QUICK_MODE; then
        # Quick mode: just verify imports work
        echo -e "    Testing imports..."
        if python -c "from mcp_server_langgraph.core.config import settings; print('  config:', settings.service_name)" 2>&1; then
            echo -e "    ${GREEN}✓ Import test passed${NC}"
        else
            echo -e "    ${RED}✗ Import test failed${NC}"
            test_result=1
        fi

        # Quick CLI test
        echo -e "    Testing CLI..."
        if python -c "import click; print('  click version:', click.__version__)" 2>&1; then
            echo -e "    ${GREEN}✓ Click import passed${NC}"
        else
            echo -e "    ${RED}✗ Click import failed${NC}"
            test_result=1
        fi

        # Quick hypothesis test
        echo -e "    Testing hypothesis..."
        if python -c "import hypothesis; from hypothesis import given, strategies as st; print('  hypothesis version:', hypothesis.__version__)" 2>&1; then
            echo -e "    ${GREEN}✓ Hypothesis import passed${NC}"
        else
            echo -e "    ${RED}✗ Hypothesis import failed${NC}"
            test_result=1
        fi
    else
        # Full mode: run a subset of tests
        echo -e "    Running unit tests (subset)..."
        if pytest tests/unit/test_config.py tests/unit/test_feature_flags.py -v --tb=short -q 2>&1 | tail -20; then
            echo -e "    ${GREEN}✓ Unit tests passed${NC}"
        else
            echo -e "    ${RED}✗ Unit tests failed${NC}"
            test_result=1
        fi

        # Run a property test to verify hypothesis
        echo -e "    Running property tests..."
        if pytest tests/property/ -v --tb=short -q --hypothesis-seed=12345 -x 2>&1 | tail -10; then
            echo -e "    ${GREEN}✓ Property tests passed${NC}"
        else
            echo -e "    ${RED}✗ Property tests failed${NC}"
            test_result=1
        fi
    fi

    # Cleanup
    deactivate
    rm -rf "$temp_venv"

    return $test_result
}

# Main test loop
for python_cmd in "${PYTHON_VERSIONS[@]}"; do
    version=$(check_python_version "$python_cmd" || echo "")

    if [[ -z "$version" ]]; then
        if $CI_MODE; then
            echo -e "${RED}✗ $python_cmd not found (CI mode - failing)${NC}"
            RESULTS[$python_cmd]="MISSING"
            ((FAILED++))
        else
            echo -e "${YELLOW}⊘ $python_cmd not available (skipping)${NC}"
            RESULTS[$python_cmd]="SKIPPED"
            ((SKIPPED++))
        fi
        continue
    fi

    if run_smoke_test "$python_cmd" "$version"; then
        echo -e "${GREEN}✓ $python_cmd ($version) - PASSED${NC}"
        RESULTS[$python_cmd]="PASSED"
        ((PASSED++))
    else
        echo -e "${RED}✗ $python_cmd ($version) - FAILED${NC}"
        RESULTS[$python_cmd]="FAILED"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Test Summary                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

for python_cmd in "${PYTHON_VERSIONS[@]}"; do
    status="${RESULTS[$python_cmd]:-UNKNOWN}"
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
