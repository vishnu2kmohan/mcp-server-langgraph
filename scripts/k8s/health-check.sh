#!/usr/bin/env bash
# ==============================================================================
# Kubernetes Pod Health Check Script
# ==============================================================================
#
# Performs health checks on deployed MCP server pods in Kubernetes cluster.
#
# Usage:
#   ./health-check.sh <namespace> [pod-name]
#
# Arguments:
#   namespace   - Kubernetes namespace (required)
#   pod-name    - Specific pod name (optional, auto-detects if not provided)
#
# Environment Variables:
#   DEPLOYMENT_NAME - Deployment name to find pods (default: auto-detect)
#   TIMEOUT_SECONDS - Health check timeout (default: 30)
#
# Exit Codes:
#   0 - Health check passed
#   1 - Health check failed
#   2 - Pod not found or configuration error
#
# ==============================================================================

set -euo pipefail

# Configuration
NAMESPACE="${1:-}"
POD_NAME="${2:-}"
TIMEOUT="${TIMEOUT_SECONDS:-30}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==============================================================================
# Helper Functions
# ==============================================================================

log_info() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

# ==============================================================================
# Validation
# ==============================================================================

if [ -z "$NAMESPACE" ]; then
    log_error "Namespace is required"
    echo "Usage: $0 <namespace> [pod-name]"
    exit 2
fi

# Verify kubectl is available
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl."
    exit 2
fi

# Verify namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    log_error "Namespace '$NAMESPACE' does not exist"
    exit 2
fi

# ==============================================================================
# Find Pod
# ==============================================================================

if [ -z "$POD_NAME" ]; then
    log_info "Auto-detecting pod in namespace: $NAMESPACE"

    # Try to find pod from deployment name
    if [ -n "$DEPLOYMENT_NAME" ]; then
        POD_NAME=$(kubectl get pods -n "$NAMESPACE" \
            -l "app.kubernetes.io/name=$DEPLOYMENT_NAME" \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    fi

    # If still not found, find first ready pod with mcp-server label
    if [ -z "$POD_NAME" ]; then
        POD_NAME=$(kubectl get pods -n "$NAMESPACE" \
            -l "app=mcp-server-langgraph" \
            --field-selector=status.phase=Running \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    fi

    # Last resort: find any running pod in namespace
    if [ -z "$POD_NAME" ]; then
        POD_NAME=$(kubectl get pods -n "$NAMESPACE" \
            --field-selector=status.phase=Running \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    fi

    if [ -z "$POD_NAME" ]; then
        log_error "No running pods found in namespace: $NAMESPACE"
        exit 2
    fi

    log_info "Found pod: $POD_NAME"
else
    log_info "Using specified pod: $POD_NAME"
fi

# ==============================================================================
# Wait for Pod to be Ready
# ==============================================================================

log_info "Waiting for pod to be ready (timeout: ${TIMEOUT}s)..."

if ! kubectl wait --for=condition=ready \
    pod/"$POD_NAME" \
    -n "$NAMESPACE" \
    --timeout="${TIMEOUT}s" 2>/dev/null; then
    log_error "Pod did not become ready within ${TIMEOUT}s"
    kubectl describe pod "$POD_NAME" -n "$NAMESPACE" || true
    exit 1
fi

log_info "Pod is ready"

# ==============================================================================
# Health Checks
# ==============================================================================

echo ""
echo "========================================="
echo "Running Health Checks"
echo "========================================="
echo ""

# Check 1: Python import check
log_info "Check 1: Python import verification"
if kubectl exec "$POD_NAME" -n "$NAMESPACE" -- \
    python -c "import mcp_server_langgraph; print('✓ Import successful')" 2>&1; then
    log_info "Python import: PASSED"
else
    log_error "Python import: FAILED"
    exit 1
fi

# Check 2: Module version check
log_info "Check 2: Module version verification"
if kubectl exec "$POD_NAME" -n "$NAMESPACE" -- \
    python -c "import mcp_server_langgraph; print(f'Version: {mcp_server_langgraph.__version__}')" 2>&1; then
    log_info "Version check: PASSED"
else
    log_warn "Version check: FAILED (non-critical)"
fi

# Check 3: Configuration loading
log_info "Check 3: Configuration loading"
if kubectl exec "$POD_NAME" -n "$NAMESPACE" -- \
    python -c "from mcp_server_langgraph.core.config import Settings; s = Settings(); print('✓ Config loaded')" 2>&1; then
    log_info "Configuration: PASSED"
else
    log_warn "Configuration: FAILED (non-critical)"
fi

# Check 4: Container health (if health endpoint exists)
log_info "Check 4: Container resource check"
if kubectl exec "$POD_NAME" -n "$NAMESPACE" -- \
    sh -c "ps aux | grep python | head -n 1" 2>&1; then
    log_info "Container process: PASSED"
else
    log_warn "Container process check: FAILED (non-critical)"
fi

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo "========================================="
echo "Health Check Summary"
echo "========================================="
echo ""
log_info "Pod: $POD_NAME"
log_info "Namespace: $NAMESPACE"
log_info "Status: ALL CRITICAL CHECKS PASSED ✅"
echo ""

exit 0
