#!/bin/bash
# Force circuit breaker reset via health endpoint
#
# Usage: ./reset-circuit-breaker.sh <service> [namespace]
#
# Reference: ADR-0026 - Comprehensive Client Resilience Patterns

set -euo pipefail

SERVICE="${1:-}"
NAMESPACE="${2:-default}"
DRY_RUN="${DRY_RUN:-false}"
MCP_SERVER_SVC="${MCP_SERVER_SVC:-mcp-server-langgraph}"
HEALTH_PORT="${HEALTH_PORT:-8080}"
TIMEOUT="${TIMEOUT:-10}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
    fi
}

# Validate input
if [[ -z "$SERVICE" ]]; then
    log_error "Usage: $0 <service> [namespace]"
    log_error "  service: redis, keycloak, openfga, postgres"
    log_error "  namespace: Kubernetes namespace (default: default)"
    exit 1
fi

# Validate service name
case "$SERVICE" in
    redis|keycloak|openfga|postgres)
        log_debug "Valid service: $SERVICE"
        ;;
    *)
        log_error "Unknown service: $SERVICE"
        log_error "Valid services: redis, keycloak, openfga, postgres"
        exit 1
        ;;
esac

log_info "Attempting to reset circuit breaker for service: $SERVICE"

# Get MCP server pod for port-forward
MCP_POD=$(kubectl get pods -n "$NAMESPACE" -l "app=$MCP_SERVER_SVC" \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [[ -z "$MCP_POD" ]]; then
    log_error "No MCP server pods found in namespace $NAMESPACE"
    log_error "Looking for pods with label: app=$MCP_SERVER_SVC"
    exit 1
fi

log_info "Found MCP server pod: $MCP_POD"

# Check current circuit breaker state via metrics
log_info "Checking current circuit breaker state..."

# Create a temporary port-forward
TEMP_PORT=$((RANDOM % 10000 + 30000))

if [[ "$DRY_RUN" == "true" ]]; then
    log_warn "[DRY RUN] Would port-forward to $MCP_POD:$HEALTH_PORT"
    log_warn "[DRY RUN] Would POST to /api/v1/resilience/$SERVICE/reset"
    exit 0
fi

# Start port-forward in background
kubectl port-forward "pod/$MCP_POD" "$TEMP_PORT:$HEALTH_PORT" -n "$NAMESPACE" &
PF_PID=$!

# Give port-forward time to establish
sleep 2

# Cleanup function
cleanup() {
    log_debug "Cleaning up port-forward (PID: $PF_PID)"
    kill $PF_PID 2>/dev/null || true
}
trap cleanup EXIT

# Check if port-forward is working
if ! kill -0 $PF_PID 2>/dev/null; then
    log_error "Port-forward failed to start"
    exit 1
fi

# Get current state from health endpoint
log_info "Fetching current resilience state..."
HEALTH_RESPONSE=$(curl -s --max-time "$TIMEOUT" "http://localhost:$TEMP_PORT/health/ready" || echo "{}")

if echo "$HEALTH_RESPONSE" | grep -q "circuit_breaker"; then
    log_info "Health endpoint responding. Checking circuit breaker state."
    CB_STATE=$(echo "$HEALTH_RESPONSE" | jq -r ".dependencies.$SERVICE.circuit_breaker // \"unknown\"" 2>/dev/null || echo "unknown")
    log_info "Current circuit breaker state for $SERVICE: $CB_STATE"
else
    log_warn "Health endpoint did not return circuit breaker info"
    CB_STATE="unknown"
fi

# Attempt reset via admin endpoint
log_info "Sending reset request to /api/v1/admin/resilience/$SERVICE/reset"

RESET_RESPONSE=$(curl -s --max-time "$TIMEOUT" \
    -X POST \
    -H "Content-Type: application/json" \
    "http://localhost:$TEMP_PORT/api/v1/admin/resilience/$SERVICE/reset" 2>&1 || echo '{"error": "request failed"}')

if echo "$RESET_RESPONSE" | grep -q "error"; then
    log_warn "Reset endpoint returned: $RESET_RESPONSE"
    log_warn "The admin reset endpoint may not be implemented."
    log_info "Alternative: Triggering pod rolling restart to reset circuit breaker state."

    # Fall back to rolling restart of MCP server
    log_info "Initiating rolling restart of $MCP_SERVER_SVC deployment..."

    # Kill port-forward before rolling restart
    kill $PF_PID 2>/dev/null || true
    trap - EXIT

    kubectl rollout restart deployment "$MCP_SERVER_SVC" -n "$NAMESPACE"

    log_info "Waiting for rollout to complete..."
    kubectl rollout status deployment "$MCP_SERVER_SVC" -n "$NAMESPACE" --timeout=300s

    # Create Kubernetes event
    kubectl create event \
        --type=Normal \
        --reason=ResilienceRemediation \
        --message="Reset circuit breaker for $SERVICE via rolling restart" \
        --for="deployment/$MCP_SERVER_SVC" \
        -n "$NAMESPACE" 2>/dev/null || true

    log_info "Rolling restart complete. Circuit breaker state reset."
else
    log_info "Reset response: $RESET_RESPONSE"

    # Verify new state
    sleep 2
    VERIFY_RESPONSE=$(curl -s --max-time "$TIMEOUT" "http://localhost:$TEMP_PORT/health/ready" || echo "{}")
    NEW_CB_STATE=$(echo "$VERIFY_RESPONSE" | jq -r ".dependencies.$SERVICE.circuit_breaker // \"unknown\"" 2>/dev/null || echo "unknown")
    log_info "New circuit breaker state for $SERVICE: $NEW_CB_STATE"

    # Create Kubernetes event
    kubectl create event \
        --type=Normal \
        --reason=ResilienceRemediation \
        --message="Reset circuit breaker for $SERVICE from $CB_STATE to $NEW_CB_STATE" \
        --for="deployment/$MCP_SERVER_SVC" \
        -n "$NAMESPACE" 2>/dev/null || true
fi

log_info "Circuit breaker reset complete for $SERVICE"
