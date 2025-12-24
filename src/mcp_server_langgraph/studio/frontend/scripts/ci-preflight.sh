#!/usr/bin/env bash
#
# CI Preflight Checks
#
# Runs before deployment to validate contracts, migrations, and code quality.
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#
# Usage:
#   ./scripts/ci-preflight.sh
#   ./scripts/ci-preflight.sh --skip-types  # Skip TypeScript validation
#   ./scripts/ci-preflight.sh --verbose     # Show detailed output
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="${FRONTEND_DIR}/../../../.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_TYPES=false
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-types) SKIP_TYPES=true ;;
        --verbose) VERBOSE=true ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Track failures
FAILURES=0
CHECKS_RUN=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

run_check() {
    local name="$1"
    local cmd="$2"

    CHECKS_RUN=$((CHECKS_RUN + 1))
    log_info "Running: $name"

    if $VERBOSE; then
        if eval "$cmd"; then
            log_success "$name"
            return 0
        else
            log_error "$name"
            FAILURES=$((FAILURES + 1))
            return 1
        fi
    else
        if eval "$cmd" > /dev/null 2>&1; then
            log_success "$name"
            return 0
        else
            log_error "$name"
            FAILURES=$((FAILURES + 1))
            return 1
        fi
    fi
}

echo ""
echo "=========================================="
echo "  CI Preflight Checks"
echo "=========================================="
echo ""

cd "$FRONTEND_DIR"

# 1. Contract Validation - TypeScript types match OpenAPI
if [[ "$SKIP_TYPES" != "true" ]]; then
    run_check "TypeScript generated types validation" \
        "./scripts/validate-generated-types.sh" || true
fi

# 2. Contract Tests - Pagination, API, HITL
run_check "Contract tests (pagination, API, HITL)" \
    "npm test -- src/api/transforms.test.ts src/api/agentRequestContract.test.ts src/api/artifactsContract.test.ts src/types/hitl.test.ts --reporter=dot" || true

# 3. OpenAPI Diff Check (detect unintentional drift)
if [[ -f "$PROJECT_ROOT/openapi.baseline.json" ]]; then
    run_check "OpenAPI spec drift check" \
        "diff -q '$PROJECT_ROOT/openapi.baseline.json' '$PROJECT_ROOT/openapi.json'" || {
            log_warning "OpenAPI spec has changed. Verify changes are intentional."
        }
else
    log_warning "No openapi.baseline.json found. Skipping drift check."
fi

# 4. TypeScript Compilation Check
run_check "TypeScript compilation" \
    "npx tsc --noEmit" || true

# 5. Lint Check
run_check "ESLint" \
    "npm run lint -- --max-warnings=0" || true

# 6. Migration Dry-Run (if alembic is available)
cd "$PROJECT_ROOT"
if command -v uv &> /dev/null; then
    run_check "Alembic migration dry-run" \
        "uv run alembic upgrade head --sql > /dev/null" || true
else
    log_warning "uv not available. Skipping migration dry-run."
fi

# 7. WebSocket Ping Test (if backend is running)
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
if curl -s --max-time 2 "$BACKEND_URL/api/v1/health" > /dev/null 2>&1; then
    run_check "Backend health check" \
        "curl -s '$BACKEND_URL/api/v1/health' | grep -q 'ok'" || true
else
    log_warning "Backend not running at $BACKEND_URL. Skipping health check."
fi

# Summary
echo ""
echo "=========================================="
echo "  Preflight Results"
echo "=========================================="
echo ""
echo "Checks run: $CHECKS_RUN"
echo "Failures: $FAILURES"
echo ""

if [[ "$FAILURES" -gt 0 ]]; then
    log_error "Preflight checks failed. Fix issues before deployment."
    exit 1
else
    log_success "All preflight checks passed!"
    exit 0
fi
