#!/bin/bash
# Integration Test Orchestration Script
# =======================================
# Runs integration tests in isolated Docker environment
#
# USAGE:
#   ./scripts/test-integration.sh [options]
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
#   ./scripts/test-integration.sh
#
#   # Rebuild and run
#   ./scripts/test-integration.sh --build
#
#   # Debug: keep containers for inspection
#   ./scripts/test-integration.sh --keep
#
#   # Start services only (run tests manually)
#   ./scripts/test-integration.sh --services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# Use root docker-compose.test.yml for local/CI parity (OpenAI Codex Finding #1)
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
echo "  Integration Test Runner"
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
    log_info "Starting services only (--services flag)..."
    docker compose $COMPOSE_OPTS -f "$COMPOSE_FILE" up -d postgres-test openfga-test redis-test "${BUILD_ARGS[@]}"

    log_success "Services started!"
    echo ""
    log_info "Service URLs:"
    echo "  PostgreSQL: localhost:$(docker compose -f "$COMPOSE_FILE" port postgres-test 5432 2>/dev/null | cut -d: -f2 || echo "not exposed")"
    echo "  OpenFGA:    localhost:$(docker compose -f "$COMPOSE_FILE" port openfga-test 8080 2>/dev/null | cut -d: -f2 || echo "not exposed")"
    echo "  Redis:      localhost:$(docker compose -f "$COMPOSE_FILE" port redis-test 6379 2>/dev/null | cut -d: -f2 || echo "not exposed")"
    echo ""
    log_info "Run tests manually:"
    echo "  pytest -m integration -v"
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

# Start infrastructure services
log_info "Starting infrastructure services..."
echo ""

# Start services in background
# CODEX FINDING FIX (2025-11-21): Add mcp-server-test for E2E Tests
# ====================================================================
# Added mcp-server-test service to enable end-to-end testing of:
# - MCP protocol initialization
# - Full user journey workflows
# - API endpoint integration
#
# The MCP server depends on all infrastructure services being healthy
# before it starts, ensuring proper initialization order.
docker compose $COMPOSE_OPTS -f "$COMPOSE_FILE" up -d \
    "${BUILD_ARGS[@]}" \
    postgres-test \
    openfga-migrate-test \
    openfga-test \
    keycloak-test \
    redis-test \
    redis-sessions-test \
    qdrant-test \
    mcp-server-test

log_success "Services started"

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
# Use smart wait utility instead of hardcoded sleep loops
# Only wait for critical services to prevent optional services (observability) from blocking tests
if bash scripts/utils/wait_for_services.sh "$COMPOSE_FILE" postgres-test keycloak-test openfga-test redis-test redis-sessions-test qdrant-test mcp-server-test; then
    log_success "All services healthy"
    echo ""

    # Verify PostgreSQL actually accepts connections (not just reports healthy)
    # This matches CI workflow behavior (integration-tests.yaml lines 203-220)
    log_info "Verifying PostgreSQL accepts connections..."
    PG_CONNECTED=false
    # shellcheck disable=SC2034
    for i in {1..30}; do
        if docker compose -f "$COMPOSE_FILE" exec -T postgres-test \
            psql -U postgres -d gdpr_test -c "SELECT 1" > /dev/null 2>&1; then
            log_success "PostgreSQL accepting connections on gdpr_test database"
            PG_CONNECTED=true
            break
        fi
        echo -n "."
        sleep 1  # Reduced from 2s since health check already passed
    done
    echo ""

    if [ "$PG_CONNECTED" = false ]; then
        log_error "PostgreSQL not accepting connections after 30 attempts"
        docker compose -f "$COMPOSE_FILE" logs postgres-test
        TEST_EXIT_CODE=1
        exit $TEST_EXIT_CODE
    fi

    # Verify PostgreSQL is accessible from HOST on port 9432
    # This is critical because tests run on host, not in container
    log_info "Verifying PostgreSQL accessible from host on port 9432..."
    if command -v nc &> /dev/null && nc -z localhost 9432 2>/dev/null; then
        log_success "PostgreSQL port 9432 accessible from host"
    elif command -v psql &> /dev/null; then
        if PGPASSWORD=postgres psql -h localhost -p 9432 -U postgres -d gdpr_test -c "SELECT 1" > /dev/null 2>&1; then
            log_success "PostgreSQL accessible from host (verified with psql)"
        else
            log_warning "PostgreSQL container healthy but not accessible from host on port 9432"
            log_info "This may cause test failures. Check port mapping and firewall rules."
        fi
    else
        log_warning "Cannot verify host connectivity (nc and psql not available)"
        log_info "Proceeding with tests - errors may occur if port not accessible"
    fi
    echo ""

    # Run integration tests on host (CI parity - OpenAI Codex Finding #1)
    log_info "Running integration tests on host..."
    echo ""

    START_TIME=$(date +%s)

    # Run pytest directly on host (same as CI)
    # Set PostgreSQL connection parameters inline (MUST match docker-compose.test.yml and CI)
    # This ensures local/CI parity and prevents connection failures
    # Use uv run to ensure correct Python environment (fixes bad interpreter issue)
    #
    # NOTE: Default to "-m integration -v --tb=short" if no args provided
    if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
        PYTEST_ARGS=(-m integration -v --tb=short)
    fi

    if TESTING=true \
       OTEL_SDK_DISABLED=true \
       POSTGRES_HOST=localhost \
       POSTGRES_PORT=9432 \
       POSTGRES_DB=gdpr_test \
       POSTGRES_USER=postgres \
       POSTGRES_PASSWORD=postgres \
       KEYCLOAK_CLIENT_SECRET=test-client-secret-for-e2e-tests \
       uv run pytest -m integration -v --tb=short; then
        END_TIME=$(date +%s)

        DURATION=$((END_TIME - START_TIME))

        echo ""
        log_success "All integration tests passed!"
        log_info "Test duration: ${DURATION}s"
        TEST_EXIT_CODE=0
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        echo ""
        log_error "Integration tests failed!"
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
