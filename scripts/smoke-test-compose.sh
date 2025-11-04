#!/bin/bash
# Docker Compose Smoke Test Script
# ==================================
# Validates that Docker Compose stacks can start successfully
# Addresses OpenAI Codex recommendation for smoke testing
#
# USAGE:
#   ./scripts/smoke-test-compose.sh [options]
#
# OPTIONS:
#   --stack <name>    Which stack to test (main|dev|test) - default: main
#   --timeout <sec>   Timeout in seconds - default: 300
#   --verbose         Show detailed output
#   --keep            Keep containers running after test
#   --config-only     Only validate configuration (don't start services)
#
# EXAMPLES:
#   # Test main production stack
#   ./scripts/smoke-test-compose.sh
#
#   # Test dev environment
#   ./scripts/smoke-test-compose.sh --stack dev
#
#   # Test with custom timeout
#   ./scripts/smoke-test-compose.sh --timeout 600
#
# EXIT CODES:
#   0 - Smoke test passed (all services healthy)
#   1 - Smoke test failed (services didn't start or health checks failed)
#   2 - Invalid arguments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STACK="main"
TIMEOUT=300
VERBOSE=false
KEEP=false
CONFIG_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stack)
            STACK="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --keep)
            KEEP=true
            shift
            ;;
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 2
            ;;
    esac
done

# Determine compose files based on stack
case $STACK in
    main)
        COMPOSE_FILES="-f docker/docker-compose.yml"
        ;;
    dev)
        COMPOSE_FILES="-f docker/docker-compose.yml -f docker/docker-compose.dev.yml"
        ;;
    test)
        COMPOSE_FILES="-f docker/docker-compose.test.yml"
        ;;
    *)
        echo -e "${RED}Invalid stack: $STACK${NC}"
        echo "Valid options: main, dev, test"
        exit 2
        ;;
esac

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

verbose_log() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${NC}  $1${NC}"
    fi
}

cleanup() {
    if [ "$KEEP" = false ]; then
        print_step "Cleaning up containers..."
        cd "$PROJECT_ROOT"
        docker compose $COMPOSE_FILES down --remove-orphans --volumes 2>/dev/null || true
        print_success "Cleanup complete"
    else
        print_info "Keeping containers running (--keep flag set)"
        print_info "To clean up manually, run:"
        echo "  cd $PROJECT_ROOT && docker compose $COMPOSE_FILES down -v"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# ==============================================================================
# Main Smoke Test Logic
# ==============================================================================

main() {
    print_header "Docker Compose Smoke Test - $STACK Stack"

    cd "$PROJECT_ROOT"

    # Step 1: Validate compose configuration
    print_step "Step 1/5: Validating Docker Compose configuration..."
    if docker compose $COMPOSE_FILES config --quiet; then
        print_success "Configuration is valid"
    else
        print_error "Configuration validation failed"
        return 1
    fi

    # If config-only mode, stop here
    if [ "$CONFIG_ONLY" = true ]; then
        print_header "Configuration Validation Complete"
        print_success "Docker Compose configuration is valid"
        print_info "Stack: $STACK"
        print_info "Skipping service startup (--config-only mode)"
        return 0
    fi

    # Step 2: Clean slate - ensure no containers running
    print_step "Step 2/5: Ensuring clean environment..."
    docker compose $COMPOSE_FILES down --remove-orphans --volumes 2>/dev/null || true
    print_success "Environment cleaned"

    # Step 3: Start services
    print_step "Step 3/5: Starting Docker Compose stack..."
    print_info "Timeout: ${TIMEOUT}s"

    if [ "$VERBOSE" = true ]; then
        docker compose $COMPOSE_FILES up -d --wait --wait-timeout $TIMEOUT
    else
        docker compose $COMPOSE_FILES up -d --wait --wait-timeout $TIMEOUT >/dev/null 2>&1
    fi

    if [ $? -eq 0 ]; then
        print_success "All services started successfully"
    else
        print_error "Services failed to start within ${TIMEOUT}s"
        print_info "Check logs:"
        echo "  docker compose $COMPOSE_FILES logs"
        return 1
    fi

    # Step 4: Verify service health
    print_step "Step 4/5: Checking service health..."

    # Get list of services
    SERVICES=$(docker compose $COMPOSE_FILES ps --services)
    HEALTHY_COUNT=0
    TOTAL_COUNT=0

    for service in $SERVICES; do
        ((TOTAL_COUNT++))

        # Check if container is running
        STATUS=$(docker compose $COMPOSE_FILES ps --format json "$service" 2>/dev/null | jq -r '.[0].State // "unknown"' 2>/dev/null || echo "unknown")

        verbose_log "Service: $service - Status: $STATUS"

        if [ "$STATUS" = "running" ]; then
            # Check health status if available
            HEALTH=$(docker compose $COMPOSE_FILES ps --format json "$service" 2>/dev/null | jq -r '.[0].Health // "none"' 2>/dev/null || echo "none")

            if [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "none" ]; then
                ((HEALTHY_COUNT++))
                verbose_log "  ✓ $service is healthy"
            else
                print_error "$service is unhealthy (status: $HEALTH)"
            fi
        else
            print_error "$service is not running (status: $STATUS)"
        fi
    done

    print_info "Services: $HEALTHY_COUNT/$TOTAL_COUNT healthy"

    if [ $HEALTHY_COUNT -eq $TOTAL_COUNT ]; then
        print_success "All services are healthy"
    else
        print_error "Some services are not healthy"
        return 1
    fi

    # Step 5: Basic connectivity test (if applicable)
    print_step "Step 5/5: Testing basic connectivity..."

    # For main/dev stack, check if agent service responds
    if [ "$STACK" = "main" ] || [ "$STACK" = "dev" ]; then
        if docker compose $COMPOSE_FILES exec -T agent python -c "import mcp_server_langgraph.core.agent; print('OK')" 2>/dev/null | grep -q "OK"; then
            print_success "Agent service import test passed"
        else
            print_error "Agent service import test failed"
            return 1
        fi
    fi

    # Summary
    print_header "Smoke Test Results"
    print_success "All smoke tests passed!"
    print_info "Stack: $STACK"
    print_info "Services tested: $TOTAL_COUNT"
    print_info "Elapsed time: ${SECONDS}s"

    return 0
}

# Run main function
main
EXIT_CODE=$?

exit $EXIT_CODE
