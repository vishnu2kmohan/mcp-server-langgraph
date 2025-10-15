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
COMPOSE_FILE="docker/docker-compose.test.yml"
BUILD=false
NO_CACHE=false
KEEP=false
VERBOSE=false
SERVICES_ONLY=false

# Parse command line arguments
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
if [ "$BUILD" = true ] || [ "$NO_CACHE" = true ]; then
    BUILD_ARGS+=(--build)
fi

if [ "$NO_CACHE" = true ]; then
    BUILD_ARGS+=(--no-cache)
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

# Start services and run tests
log_info "Starting services and running integration tests..."
echo ""

START_TIME=$(date +%s)

# Run docker compose with appropriate options
if docker compose $COMPOSE_OPTS -f "$COMPOSE_FILE" up \
    "${BUILD_ARGS[@]}" \
    --abort-on-container-exit \
    --exit-code-from test-runner; then

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

    # Show test runner logs
    log_info "Test runner logs:"
    docker compose -f "$COMPOSE_FILE" logs test-runner

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
