#!/bin/bash
# Scale deployment horizontally when HTTP pool saturation is detected
#
# Usage: ./scale-deployment.sh <deployment> [target-replicas] [namespace]
#
# Reference: ADR-0026 - Comprehensive Client Resilience Patterns

set -euo pipefail

DEPLOYMENT="${1:-}"
TARGET_REPLICAS="${2:-}"
NAMESPACE="${3:-default}"
DRY_RUN="${DRY_RUN:-false}"
MAX_REPLICAS="${MAX_REPLICAS:-10}"
MIN_REPLICAS="${MIN_REPLICAS:-1}"
COOLDOWN_FILE="/tmp/scale-cooldown-${DEPLOYMENT}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-300}"

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
if [[ -z "$DEPLOYMENT" ]]; then
    log_error "Usage: $0 <deployment> [target-replicas] [namespace]"
    log_error "  deployment: Name of the deployment to scale"
    log_error "  target-replicas: Target replica count (optional, defaults to +50%)"
    log_error "  namespace: Kubernetes namespace (default: default)"
    exit 1
fi

# Check cooldown
if [[ -f "$COOLDOWN_FILE" ]]; then
    LAST_RUN=$(cat "$COOLDOWN_FILE")
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - LAST_RUN))

    if [[ $ELAPSED -lt $COOLDOWN_SECONDS ]]; then
        REMAINING=$((COOLDOWN_SECONDS - ELAPSED))
        log_warn "Cooldown active for $DEPLOYMENT. ${REMAINING}s remaining. Skipping."
        exit 0
    fi
fi

log_info "Starting scale remediation for deployment: $DEPLOYMENT"

# Check if deployment exists
if ! kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" &>/dev/null; then
    log_error "Deployment $DEPLOYMENT not found in namespace $NAMESPACE"
    exit 1
fi

# Check for skip annotation
SKIP_ANNOTATION=$(kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" \
    -o jsonpath='{.metadata.annotations.remediation\.skip}' 2>/dev/null || echo "")

if [[ "$SKIP_ANNOTATION" == "true" ]]; then
    log_warn "Remediation skip annotation found on $DEPLOYMENT. Skipping."
    exit 0
fi

# Get current replica count
CURRENT_REPLICAS=$(kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" \
    -o jsonpath='{.spec.replicas}')

log_info "Current replicas: $CURRENT_REPLICAS"

# Calculate target if not specified
if [[ -z "$TARGET_REPLICAS" ]]; then
    # Scale up by 50%, minimum +1
    INCREASE=$((CURRENT_REPLICAS / 2))
    if [[ $INCREASE -lt 1 ]]; then
        INCREASE=1
    fi
    TARGET_REPLICAS=$((CURRENT_REPLICAS + INCREASE))
    log_info "Auto-calculated target: $TARGET_REPLICAS (+50%)"
fi

# Enforce min/max bounds
if [[ $TARGET_REPLICAS -lt $MIN_REPLICAS ]]; then
    log_warn "Target $TARGET_REPLICAS below minimum. Using $MIN_REPLICAS"
    TARGET_REPLICAS=$MIN_REPLICAS
fi

if [[ $TARGET_REPLICAS -gt $MAX_REPLICAS ]]; then
    log_warn "Target $TARGET_REPLICAS exceeds maximum. Capping at $MAX_REPLICAS"
    TARGET_REPLICAS=$MAX_REPLICAS
fi

# Check if scaling is needed
if [[ $TARGET_REPLICAS -eq $CURRENT_REPLICAS ]]; then
    log_info "Already at target replica count ($TARGET_REPLICAS). No action needed."
    exit 0
fi

if [[ $TARGET_REPLICAS -lt $CURRENT_REPLICAS ]]; then
    log_warn "Target ($TARGET_REPLICAS) is less than current ($CURRENT_REPLICAS). Skipping scale-down."
    log_info "Use 'kubectl scale' directly for intentional scale-down."
    exit 0
fi

# Perform scaling
log_info "Scaling $DEPLOYMENT from $CURRENT_REPLICAS to $TARGET_REPLICAS replicas"

if [[ "$DRY_RUN" == "true" ]]; then
    log_warn "[DRY RUN] Would execute: kubectl scale deployment $DEPLOYMENT --replicas=$TARGET_REPLICAS -n $NAMESPACE"
else
    kubectl scale deployment "$DEPLOYMENT" --replicas="$TARGET_REPLICAS" -n "$NAMESPACE"

    # Wait for rollout to complete
    log_info "Waiting for deployment to stabilize..."
    kubectl rollout status deployment "$DEPLOYMENT" -n "$NAMESPACE" --timeout=300s

    # Update cooldown file
    date +%s > "$COOLDOWN_FILE"

    # Create Kubernetes event
    kubectl create event \
        --type=Normal \
        --reason=ResilienceRemediation \
        --message="Scaled deployment from $CURRENT_REPLICAS to $TARGET_REPLICAS replicas due to HTTP pool saturation" \
        --for="deployment/$DEPLOYMENT" \
        -n "$NAMESPACE" 2>/dev/null || true

    # Verify new replica count
    NEW_REPLICAS=$(kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" \
        -o jsonpath='{.spec.replicas}')
    log_info "Scale complete. New replica count: $NEW_REPLICAS"
fi

log_info "Scale remediation complete for $DEPLOYMENT"
