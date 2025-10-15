#!/bin/bash
# Wait for Docker Services to be Healthy
# ========================================
# Ensures all required services are healthy before running tests
#
# USAGE:
#   ./scripts/wait-for-services.sh [compose-file]
#
# EXAMPLES:
#   # Wait for test services
#   ./scripts/wait-for-services.sh docker/docker-compose.test.yml
#
#   # Wait for dev services
#   ./scripts/wait-for-services.sh docker/docker-compose.yml

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="${1:-docker/docker-compose.test.yml}"
TIMEOUT=120  # Maximum wait time in seconds
CHECK_INTERVAL=2  # Seconds between health checks

# Service list (from compose file)
SERVICES=(
    "postgres-test"
    "openfga-test"
    "redis-test"
)

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_waiting() {
    echo -e "${YELLOW}⏳${NC} $1"
}

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Error: Compose file not found: $COMPOSE_FILE"
    exit 1
fi

echo ""
log_info "Waiting for services to be healthy..."
echo "Timeout: ${TIMEOUT}s, Check interval: ${CHECK_INTERVAL}s"
echo ""

# Wait for each service
for service in "${SERVICES[@]}"; do
    log_waiting "Waiting for $service..."

    elapsed=0
    while [ $elapsed -lt $TIMEOUT ]; do
        # Check if service is healthy
        if docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | grep -q "healthy"; then
            log_success "$service is healthy (${elapsed}s)"
            break
        fi

        # Check if service failed to start
        if docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | grep -qE "Exited|Dead"; then
            echo "Error: $service failed to start"
            docker compose -f "$COMPOSE_FILE" logs "$service"
            exit 1
        fi

        # Wait and retry
        sleep $CHECK_INTERVAL
        elapsed=$((elapsed + CHECK_INTERVAL))
    done

    # Timeout check
    if [ $elapsed -ge $TIMEOUT ]; then
        echo "Error: $service did not become healthy within ${TIMEOUT}s"
        docker compose -f "$COMPOSE_FILE" logs "$service"
        exit 1
    fi
done

echo ""
log_success "All services are healthy and ready!"
echo ""

# Show service status
log_info "Service status:"
docker compose -f "$COMPOSE_FILE" ps

exit 0
