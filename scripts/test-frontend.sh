#!/bin/bash
# Frontend Test Script
# =======================================
# Runs frontend lint, typecheck, tests (Vitest + Playwright), and build
#
# This script achieves CI parity by running the same commands as the
# 'frontend-build' job in ci.yaml.
#
# USAGE:
#   ./scripts/test-frontend.sh [options]
#
# OPTIONS:
#   --skip-install    Skip npm ci (use existing node_modules)
#   --skip-build      Skip npm run build (faster for test-only runs)
#   --lint-only       Only run linting
#   --test-only       Only run Vitest tests (skip lint, typecheck, Playwright, build)
#   --verbose         Show detailed output
#
# EXAMPLES:
#   # Run all checks (matches CI exactly)
#   ./scripts/test-frontend.sh
#
#   # Skip install if node_modules is up to date
#   ./scripts/test-frontend.sh --skip-install
#
#   # Quick test run (skip build)
#   ./scripts/test-frontend.sh --skip-build
#
# CI PARITY:
#   This script matches ci.yaml frontend-build job:
#   - npm ci (install dependencies)
#   - npm run lint (ESLint)
#   - npm run typecheck (TypeScript)
#   - npm test -- --run (Vitest unit/integration)
#   - npx playwright install --with-deps chromium
#   - npm run test:e2e (Playwright e2e)
#   - npm run build (build verification)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_DIR="src/mcp_server_langgraph/studio/frontend"
SKIP_INSTALL=false
SKIP_BUILD=false
LINT_ONLY=false
TEST_ONLY=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --lint-only)
            LINT_ONLY=true
            shift
            ;;
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            grep "^#" "$0" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run with --help for usage"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Banner
echo ""
echo "========================================"
echo "  Frontend Test Runner (CI Parity)"
echo "========================================"
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    log_error "Node.js not found. Please install Node.js to continue."
    log_info "Recommended: Node.js 22 LTS (matches CI)"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    log_error "npm not found. Please install npm to continue."
    exit 1
fi

NODE_VERSION=$(node --version)
log_success "Node.js $NODE_VERSION found"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    log_error "Frontend directory not found: $FRONTEND_DIR"
    log_info "Please run this script from the project root directory."
    exit 1
fi

if [ ! -f "$FRONTEND_DIR/package.json" ]; then
    log_error "package.json not found in $FRONTEND_DIR"
    exit 1
fi

log_success "Frontend directory found"
echo ""

# Change to frontend directory
cd "$FRONTEND_DIR"

START_TIME=$(date +%s)

# Step 1: Install dependencies
if [ "$SKIP_INSTALL" = false ]; then
    log_info "Installing dependencies (npm ci)..."
    if [ "$VERBOSE" = true ]; then
        npm ci
    else
        npm ci --silent 2>/dev/null || npm ci
    fi
    log_success "Dependencies installed"
    echo ""
else
    log_warning "Skipping npm ci (--skip-install)"
    echo ""
fi

# Step 2: Lint (ESLint)
if [ "$TEST_ONLY" = false ]; then
    log_info "Running ESLint..."
    if npm run lint; then
        log_success "Linting passed"
    else
        log_error "Linting failed!"
        exit 1
    fi
    echo ""

    if [ "$LINT_ONLY" = true ]; then
        log_success "Lint-only mode complete"
        exit 0
    fi
fi

# Step 3: TypeScript typecheck
if [ "$TEST_ONLY" = false ]; then
    log_info "Running TypeScript typecheck..."
    if npm run typecheck; then
        log_success "Typecheck passed"
    else
        log_error "Typecheck failed!"
        exit 1
    fi
    echo ""
fi

# Step 4: Run tests (Vitest)
log_info "Running Vitest tests..."
if npm test -- --run; then
    log_success "Vitest tests passed"
else
    log_error "Vitest tests failed!"
    exit 1
fi
echo ""

# Step 5: Run Playwright e2e tests
if [ "$TEST_ONLY" = false ]; then
    log_info "Installing Playwright browsers (chromium)..."
    if npx playwright install --with-deps chromium; then
        log_success "Playwright browsers installed"
    else
        log_warning "Playwright browser install failed - continuing anyway"
    fi
    echo ""

    log_info "Running Playwright e2e tests..."
    if npm run test:e2e; then
        log_success "Playwright e2e tests passed"
    else
        log_error "Playwright e2e tests failed!"
        exit 1
    fi
    echo ""
fi

# Step 6: Build verification
if [ "$SKIP_BUILD" = false ] && [ "$TEST_ONLY" = false ]; then
    log_info "Running build verification..."
    if npm run build; then
        log_success "Build succeeded"
    else
        log_error "Build failed!"
        exit 1
    fi
    echo ""
else
    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Skipping build (--skip-build)"
    fi
    echo ""
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "========================================"
log_success "All frontend checks passed!"
log_info "Duration: ${DURATION}s"
echo "========================================"

exit 0
