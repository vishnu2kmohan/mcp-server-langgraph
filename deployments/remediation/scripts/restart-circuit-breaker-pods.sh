#!/bin/bash
# Restart pods when circuit breaker is open for extended period
#
# Usage: ./restart-circuit-breaker-pods.sh <service> [namespace]
#
# Reference: ADR-0026 - Comprehensive Client Resilience Patterns

set -euo pipefail

SERVICE="${1:-}"
NAMESPACE="${2:-default}"
DRY_RUN="${DRY_RUN:-false}"
COOLDOWN_FILE="/tmp/remediation-cooldown-${SERVICE}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-300}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Validate input
if [[ -z "$SERVICE" ]]; then
    log_error "Usage: $0 <service> [namespace]"
    log_error "  service: redis, keycloak, openfga, postgres"
    exit 1
fi

# Check cooldown
if [[ -f "$COOLDOWN_FILE" ]]; then
    LAST_RUN=$(cat "$COOLDOWN_FILE")
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - LAST_RUN))

    if [[ $ELAPSED -lt $COOLDOWN_SECONDS ]]; then
        REMAINING=$((COOLDOWN_SECONDS - ELAPSED))
        log_warn "Cooldown active for $SERVICE. ${REMAINING}s remaining. Skipping."
        exit 0
    fi
fi

log_info "Starting circuit breaker remediation for service: $SERVICE"

# Map service to deployment/statefulset
case "$SERVICE" in
    redis)
        WORKLOAD_TYPE="statefulset"
        WORKLOAD_NAME="redis"
        ;;
    keycloak)
        WORKLOAD_TYPE="deployment"
        WORKLOAD_NAME="keycloak"
        ;;
    openfga)
        WORKLOAD_TYPE="deployment"
        WORKLOAD_NAME="openfga"
        ;;
    postgres)
        WORKLOAD_TYPE="statefulset"
        WORKLOAD_NAME="postgres"
        ;;
    *)
        log_error "Unknown service: $SERVICE"
        exit 1
        ;;
esac

# Check if workload exists
if ! kubectl get "$WORKLOAD_TYPE" "$WORKLOAD_NAME" -n "$NAMESPACE" &>/dev/null; then
    log_error "Workload $WORKLOAD_TYPE/$WORKLOAD_NAME not found in namespace $NAMESPACE"
    exit 1
fi

# Check for skip annotation on MCP server deployment
SKIP_ANNOTATION=$(kubectl get deployment mcp-server-langgraph -n "$NAMESPACE" \
    -o jsonpath='{.metadata.annotations.remediation\.skip}' 2>/dev/null || echo "")

if [[ "$SKIP_ANNOTATION" == "true" ]]; then
    log_warn "Remediation skip annotation found. Skipping."
    exit 0
fi

# Get current pod status
log_info "Checking pod status for $WORKLOAD_TYPE/$WORKLOAD_NAME"
PODS=$(kubectl get pods -n "$NAMESPACE" -l "app=$WORKLOAD_NAME" -o jsonpath='{.items[*].metadata.name}')

if [[ -z "$PODS" ]]; then
    log_warn "No pods found for $WORKLOAD_NAME"
    exit 0
fi

# Check pod health
UNHEALTHY_PODS=0
for POD in $PODS; do
    READY=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
    if [[ "$READY" != "True" ]]; then
        ((UNHEALTHY_PODS++))
        log_warn "Pod $POD is not ready"
    fi
done

if [[ $UNHEALTHY_PODS -eq 0 ]]; then
    log_info "All pods are healthy. Circuit breaker may close naturally."
    log_info "Consider investigating why circuit breaker opened despite healthy pods."
    exit 0
fi

# Perform rolling restart
log_info "Found $UNHEALTHY_PODS unhealthy pod(s). Triggering rolling restart."

if [[ "$DRY_RUN" == "true" ]]; then
    log_warn "[DRY RUN] Would execute: kubectl rollout restart $WORKLOAD_TYPE/$WORKLOAD_NAME -n $NAMESPACE"
else
    kubectl rollout restart "$WORKLOAD_TYPE/$WORKLOAD_NAME" -n "$NAMESPACE"

    # Wait for rollout to complete
    log_info "Waiting for rollout to complete..."
    kubectl rollout status "$WORKLOAD_TYPE/$WORKLOAD_NAME" -n "$NAMESPACE" --timeout=300s

    # Update cooldown file
    date +%s > "$COOLDOWN_FILE"

    # Create Kubernetes event
    kubectl create event \
        --type=Normal \
        --reason=ResilienceRemediation \
        --message="Triggered rolling restart of $WORKLOAD_TYPE/$WORKLOAD_NAME due to circuit breaker open" \
        --for="$WORKLOAD_TYPE/$WORKLOAD_NAME" \
        -n "$NAMESPACE" 2>/dev/null || true

    log_info "Rolling restart completed for $WORKLOAD_TYPE/$WORKLOAD_NAME"
fi

log_info "Remediation complete for $SERVICE"
