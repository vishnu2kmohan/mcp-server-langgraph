#!/usr/bin/env bash
#
# Wait for Services
#
# Waits for required services to become healthy before running E2E tests.
# Uses exponential backoff with configurable timeout.
#
# Usage:
#   ./scripts/wait-for-services.sh
#   TIMEOUT=120 ./scripts/wait-for-services.sh  # Custom timeout (seconds)
#

set -euo pipefail

# Configuration (can be overridden via environment)
TIMEOUT="${TIMEOUT:-90}"                              # Total timeout in seconds
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:9082}"
OPENFGA_URL="${OPENFGA_URL:-http://localhost:9080}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-9432}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-9379}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WAIT]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Wait for HTTP endpoint to return 2xx
wait_for_http() {
    local name="$1"
    local url="$2"
    local path="${3:-/}"
    local timeout="$TIMEOUT"
    local start_time
    start_time=$(date +%s)
    local delay=1

    log_info "Waiting for $name at $url$path..."

    while true; do
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ $elapsed -ge $timeout ]]; then
            log_error "$name did not become healthy within ${timeout}s"
            return 1
        fi

        if curl -sf --max-time 5 "$url$path" > /dev/null 2>&1; then
            log_success "$name is healthy (${elapsed}s)"
            return 0
        fi

        log_warning "$name not ready, retrying in ${delay}s... (${elapsed}s/${timeout}s)"
        sleep "$delay"
        delay=$((delay < 8 ? delay * 2 : 8))  # Max 8 seconds between retries
    done
}

# Wait for TCP port to accept connections
wait_for_tcp() {
    local name="$1"
    local host="$2"
    local port="$3"
    local timeout="$TIMEOUT"
    local start_time
    start_time=$(date +%s)
    local delay=1

    log_info "Waiting for $name at $host:$port..."

    while true; do
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ $elapsed -ge $timeout ]]; then
            log_error "$name did not become available within ${timeout}s"
            return 1
        fi

        # Try nc if available, otherwise use bash's /dev/tcp
        if command -v nc &> /dev/null; then
            if nc -z "$host" "$port" 2>/dev/null; then
                log_success "$name is available (${elapsed}s)"
                return 0
            fi
        elif [[ -e /dev/tcp ]]; then
            if (echo > "/dev/tcp/$host/$port") 2>/dev/null; then
                log_success "$name is available (${elapsed}s)"
                return 0
            fi
        else
            # Fallback: try timeout with bash
            if timeout 1 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
                log_success "$name is available (${elapsed}s)"
                return 0
            fi
        fi

        log_warning "$name not ready, retrying in ${delay}s... (${elapsed}s/${timeout}s)"
        sleep "$delay"
        delay=$((delay < 8 ? delay * 2 : 8))
    done
}

echo ""
echo "=========================================="
echo "  Waiting for Services"
echo "=========================================="
echo ""
echo "Timeout: ${TIMEOUT}s"
echo ""

FAILED=0

# Wait for PostgreSQL
wait_for_tcp "PostgreSQL" "$POSTGRES_HOST" "$POSTGRES_PORT" || FAILED=$((FAILED + 1))

# Wait for Redis
wait_for_tcp "Redis" "$REDIS_HOST" "$REDIS_PORT" || FAILED=$((FAILED + 1))

# Wait for Keycloak
wait_for_http "Keycloak" "$KEYCLOAK_URL" "/health/ready" || FAILED=$((FAILED + 1))

# Wait for OpenFGA
wait_for_http "OpenFGA" "$OPENFGA_URL" "/healthz" || FAILED=$((FAILED + 1))

# Wait for Backend (optional, may not be running in CI)
if [[ "${WAIT_FOR_BACKEND:-true}" == "true" ]]; then
    wait_for_http "Backend" "$BACKEND_URL" "/api/v1/health" || {
        log_warning "Backend not available (may be intentional in CI)"
        # Don't fail on backend - it might be started separately
    }
fi

echo ""

if [[ $FAILED -gt 0 ]]; then
    log_error "Some services failed to become healthy"
    exit 1
else
    log_success "All required services are healthy!"
    exit 0
fi
