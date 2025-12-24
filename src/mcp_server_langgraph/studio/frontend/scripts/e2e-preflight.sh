#!/usr/bin/env bash
#
# E2E Test Preflight
#
# Orchestrates the full E2E test setup:
# 1. Starts docker-compose.test.yml if needed
# 2. Waits for services to become healthy
# 3. Seeds test data
# 4. Runs E2E tests
# 5. Tears down (optional)
#
# Usage:
#   ./scripts/e2e-preflight.sh              # Full workflow
#   ./scripts/e2e-preflight.sh --no-down    # Keep containers running after tests
#   ./scripts/e2e-preflight.sh --skip-seed  # Skip test data seeding
#   ./scripts/e2e-preflight.sh --only-setup # Only setup, don't run tests
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="${FRONTEND_DIR}/../../../.."

# Options
NO_DOWN=false
SKIP_SEED=false
ONLY_SETUP=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-down) NO_DOWN=true ;;
        --skip-seed) SKIP_SEED=true ;;
        --only-setup) ONLY_SETUP=true ;;
        --verbose) VERBOSE=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-down     Keep containers running after tests"
            echo "  --skip-seed   Skip test data seeding"
            echo "  --only-setup  Only setup, don't run tests"
            echo "  --verbose     Show detailed output"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_section() {
    echo ""
    echo -e "${CYAN}=========================================="
    echo -e "  $1"
    echo -e "==========================================${NC}"
    echo ""
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Cleanup function
cleanup() {
    if [[ "$NO_DOWN" == "false" && "$ONLY_SETUP" == "false" ]]; then
        log_section "Cleanup"
        log_info "Stopping docker-compose services..."
        cd "$PROJECT_ROOT"
        docker-compose -f docker-compose.test.yml down --volumes --remove-orphans 2>/dev/null || true
        log_success "Services stopped"
    else
        log_info "Keeping containers running (--no-down or --only-setup)"
    fi
}

# Set up trap for cleanup
trap cleanup EXIT

# Start
log_section "E2E Test Preflight"

START_TIME=$(date +%s)

# Step 1: Start docker-compose
log_section "Step 1: Start Services"

cd "$PROJECT_ROOT"

# Check if services are already running
RUNNING=$(docker-compose -f docker-compose.test.yml ps --services --filter "status=running" 2>/dev/null | wc -l)

if [[ "$RUNNING" -lt 4 ]]; then
    log_info "Starting docker-compose.test.yml..."
    if [[ "$VERBOSE" == "true" ]]; then
        docker-compose -f docker-compose.test.yml up -d
    else
        docker-compose -f docker-compose.test.yml up -d 2>/dev/null
    fi
    log_success "Docker Compose services starting"
else
    log_success "Services already running ($RUNNING services)"
fi

# Step 2: Wait for services
log_section "Step 2: Wait for Services"

cd "$SCRIPT_DIR"
if [[ -x "./wait-for-services.sh" ]]; then
    ./wait-for-services.sh || {
        log_error "Services did not become healthy"
        exit 1
    }
else
    log_warning "wait-for-services.sh not found or not executable"
    log_info "Waiting 30 seconds for services to start..."
    sleep 30
fi

# Step 3: Seed test data
if [[ "$SKIP_SEED" == "false" ]]; then
    log_section "Step 3: Seed Test Data"

    if [[ -x "./seed-test-data.sh" ]]; then
        ./seed-test-data.sh || {
            log_warning "Test data seeding had issues (may be okay if data exists)"
        }
    else
        log_warning "seed-test-data.sh not found or not executable"
    fi
else
    log_section "Step 3: Seed Test Data (Skipped)"
    log_info "Skipping test data seeding (--skip-seed)"
fi

# Step 4: Run E2E tests
if [[ "$ONLY_SETUP" == "false" ]]; then
    log_section "Step 4: Run E2E Tests"

    cd "$FRONTEND_DIR"
    log_info "Running Playwright E2E tests..."

    if [[ "$VERBOSE" == "true" ]]; then
        npm run test:e2e || {
            log_error "E2E tests failed"
            exit 1
        }
    else
        npm run test:e2e 2>&1 | tail -20 || {
            log_error "E2E tests failed"
            exit 1
        }
    fi

    log_success "E2E tests passed!"
else
    log_section "Step 4: Run E2E Tests (Skipped)"
    log_info "Setup complete (--only-setup). Run 'npm run test:e2e' manually."
fi

# Summary
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

log_section "Summary"
echo "Duration: ${DURATION}s"
echo ""

if [[ "$ONLY_SETUP" == "true" ]]; then
    log_success "E2E setup complete! Services are running."
    echo ""
    echo "Next steps:"
    echo "  1. Run tests: npm run test:e2e"
    echo "  2. Stop services: docker-compose -f docker-compose.test.yml down"
else
    log_success "E2E preflight complete!"
fi
