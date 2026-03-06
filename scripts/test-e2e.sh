#!/bin/bash
# E2E Test Orchestration Script
# =======================================
# Runs end-to-end tests in isolated Docker environment
#
# This script achieves CI parity by running e2e tests locally in the same
# manner as the e2e-tests.yaml GitHub Actions workflow.
#
# USAGE:
#   ./scripts/test-e2e.sh [options]
#
# OPTIONS:
#   --build        Force rebuild of test runner image
#   --no-cache     Build without Docker cache
#   --keep         Keep containers running after tests (for debugging)
#   --verbose      Show detailed Docker output
#   --services     Only start services (don't run tests)
#
# EXAMPLES:
#   # Run tests (default)
#   ./scripts/test-e2e.sh
#
#   # Rebuild and run
#   ./scripts/test-e2e.sh --build
#
#   # Debug: keep containers for inspection
#   ./scripts/test-e2e.sh --keep
#
#   # Start services only (run tests manually)
#   ./scripts/test-e2e.sh --services
#
#   # Pass custom pytest flags after '--' separator
#   ./scripts/test-e2e.sh -- -v --tb=long
#   ./scripts/test-e2e.sh -- --cov --cov-report=xml
#
# CI PARITY:
#   This script matches e2e-tests.yaml workflow behavior:
#   - Uses docker-compose.test.yml (same as CI)
#   - Waits for Keycloak realm import (7.5 min timeout)
#   - Runs pytest -m e2e with same environment variables

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.test.yml"
BUILD=false
NO_CACHE=false
KEEP=false
VERBOSE=false
SERVICES_ONLY=false

# Parse command line arguments
PYTEST_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --keep)
            KEEP=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --services)
            SERVICES_ONLY=true
            shift
            ;;
        --help)
            grep "^#" "$0" | sed 's/^# //'
            exit 0
            ;;
        --)
            shift
            PYTEST_ARGS+=("$@")
            break
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

# Cleanup function
cleanup() {
    if [ "$KEEP" = false ]; then
        log_info "Cleaning up containers and networks..."
        docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
        log_success "Cleanup complete"
    else
        log_warning "Containers kept running (--keep flag)"
        log_info "To clean up manually: docker compose -f $COMPOSE_FILE down -v"
    fi
}

# Set trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Banner
echo ""
echo "========================================"
echo "  E2E Test Runner (CI Parity)"
echo "========================================"
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker to continue."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    log_error "Docker Compose not found or outdated. Please update Docker."
    exit 1
fi

log_success "Docker and Docker Compose found"

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "Compose file not found: $COMPOSE_FILE"
    log_info "Please run this script from the project root directory."
    exit 1
fi

log_success "Compose file found"
echo ""

# Build options
BUILD_ARGS=()
BUILD_NO_CACHE_ARGS=()
if [ "$BUILD" = true ] || [ "$NO_CACHE" = true ]; then
    BUILD_ARGS+=(--build)
fi

if [ "$NO_CACHE" = true ]; then
    BUILD_NO_CACHE_ARGS+=(--no-cache)
fi

# Verbose options
if [ "$VERBOSE" = true ]; then
    COMPOSE_OPTS="--verbose"
else
    COMPOSE_OPTS=""
fi

# Stop any existing containers
log_info "Stopping any existing test containers..."
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true

# Services only mode
if [ "$SERVICES_ONLY" = true ]; then
    log_info "Starting all services (--services flag)..."
    docker compose $COMPOSE_OPTS -f "$COMPOSE_FILE" up -d "${BUILD_ARGS[@]}"

    log_success "Services started!"
    echo ""
    log_info "Run E2E tests manually:"
    echo "  TESTING=true OTEL_SDK_DISABLED=true pytest -m e2e -v"
    echo ""
    log_info "Stop services:"
    echo "  docker compose -f $COMPOSE_FILE down -v"

    # Don't cleanup in services-only mode
    trap - EXIT INT TERM
    exit 0
fi

# Build images if needed (especially with --no-cache)
if [ "$NO_CACHE" = true ]; then
    log_info "Building images without cache..."
    docker compose -f "$COMPOSE_FILE" build "${BUILD_NO_CACHE_ARGS[@]}"
fi

# Start ALL infrastructure services (E2E tests need the full stack)
log_info "Starting all infrastructure services (full stack for E2E)..."
echo ""

if [ "$BUILD" = true ]; then
    docker compose $COMPOSE_OPTS -f "$COMPOSE_FILE" up -d --build
else
    docker compose $COMPOSE_OPTS -f "$COMPOSE_FILE" up -d
fi

log_success "Services started"

# Wait for services to be healthy
log_info "Waiting for all services to be healthy..."
if bash scripts/utils/wait_for_services.sh "$COMPOSE_FILE"; then
    log_success "All services healthy"
    echo ""

    # CRITICAL: Verify Keycloak realm is actually imported
    # Docker health check passes but realm may not be fully imported yet
    # Timeout: 150 iterations * 3s = 7.5 minutes (matches e2e-tests.yaml)
    log_info "Verifying Keycloak realm is fully imported (may take 3-5 min)..."
    KEYCLOAK_READY=false
    for _ in {1..150}; do
        # Try to get a token using the test user credentials
        TOKEN_RESPONSE=$(curl -sf -X POST \
            "http://localhost:9082/authn/realms/default/protocol/openid-connect/token" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "grant_type=password" \
            -d "client_id=mcp-server" \
            -d "client_secret=test-client-secret-for-e2e-tests" \
            -d "username=alice" \
            -d "password=alice123" 2>&1) || true

        if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
            log_success "Keycloak realm fully imported (user authentication works)"
            KEYCLOAK_READY=true
            break
        fi
        echo -n "."
        sleep 3
    done
    echo ""

    if [ "$KEYCLOAK_READY" = false ]; then
        log_error "Keycloak realm not fully imported after 150 attempts (7.5 min)"
        log_info "E2E tests require authentication - aborting"
        docker compose -f "$COMPOSE_FILE" logs keycloak-test
        TEST_EXIT_CODE=1
        exit $TEST_EXIT_CODE
    fi

    # Verify MCP server is ready (E2E tests interact with the server)
    log_info "Verifying MCP server is ready..."
    MCP_READY=false
    for _ in {1..60}; do
        if curl -sf "http://localhost:8000/health" > /dev/null 2>&1; then
            log_success "MCP server is ready"
            MCP_READY=true
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""

    if [ "$MCP_READY" = false ]; then
        log_warning "MCP server not responding on health endpoint"
        log_info "Some E2E tests may fail - proceeding anyway"
    fi

    # Run E2E tests on host
    log_info "Running E2E tests on host..."
    echo ""

    START_TIME=$(date +%s)

    # Default pytest args for E2E tests (matches e2e-tests.yaml)
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        PYTEST_ARGS=(-m e2e -v --tb=short)
    fi

    # Run pytest with same environment as CI
    if TESTING=true \
       OTEL_SDK_DISABLED=true \
       POSTGRES_HOST=localhost \
       POSTGRES_PORT=9432 \
       POSTGRES_DB=gdpr_test \
       POSTGRES_USER=postgres \
       POSTGRES_PASSWORD=postgres \
       KEYCLOAK_CLIENT_SECRET=test-client-secret-for-e2e-tests \
       KEYCLOAK_ADMIN_PASSWORD=admin \
       JWT_SECRET_KEY=agent-studio-jwt-secret-key-for-e2e-tests \
       uv run --frozen pytest "${PYTEST_ARGS[@]}"; then
        END_TIME=$(date +%s)

        DURATION=$((END_TIME - START_TIME))

        echo ""
        log_success "All E2E tests passed!"
        log_info "Test duration: ${DURATION}s"
        TEST_EXIT_CODE=0
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        echo ""
        log_error "E2E tests failed!"
        log_info "Test duration: ${DURATION}s"
        TEST_EXIT_CODE=1
    fi
else
    # Services failed to become healthy
    log_error "Services failed to become healthy within timeout"
    log_info "Showing service status for debugging:"
    docker compose -f "$COMPOSE_FILE" ps
    TEST_EXIT_CODE=1
fi

echo ""

# Show service status
if [ "$VERBOSE" = true ]; then
    log_info "Service status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
fi

# Cleanup happens automatically via trap
exit $TEST_EXIT_CODE
