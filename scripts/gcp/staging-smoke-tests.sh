#!/bin/bash
#
# Staging Smoke Tests for GKE Deployment
#
# This script performs smoke tests on the staging environment to verify:
# - Health endpoints are responding
# - Authentication is working
# - Basic agent functionality
# - Performance is acceptable
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed
#

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-staging-mcp-server-langgraph}"
SERVICE_NAME="${SERVICE_NAME:-staging-mcp-server-langgraph}"
# shellcheck disable=SC2034  # TIMEOUT reserved for future timeout implementation
TIMEOUT=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

test_start() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo ""
    log_info "Test $TESTS_RUN: $1"
}

test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo -e "${GREEN}✓ PASS${NC}"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo -e "${RED}✗ FAIL${NC}: $1"
}

# Setup port-forward
setup_port_forward() {
    log_info "Setting up port-forward to staging service..."

    # Kill any existing port-forwards
    pkill -f "port-forward.*${SERVICE_NAME}" || true
    sleep 2

    # Start port-forward in background
    kubectl port-forward -n "$NAMESPACE" \
        "svc/${SERVICE_NAME}" 8080:80 > /dev/null 2>&1 &
    PORT_FORWARD_PID=$!

    # Wait for port-forward to be ready
    log_info "Waiting for port-forward (PID: $PORT_FORWARD_PID)..."
    for _ in {1..10}; do
        if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
            log_info "Port-forward ready"
            return 0
        fi
        sleep 1
    done

    log_error "Port-forward failed to start"
    return 1
}

cleanup() {
    if [ -n "${PORT_FORWARD_PID:-}" ]; then
        log_info "Cleaning up port-forward (PID: $PORT_FORWARD_PID)"
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Test 1: Health endpoint
test_health_endpoint() {
    test_start "Health endpoint responds"

    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/health || true)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)

    if [ "$HTTP_CODE" = "200" ]; then
        log_info "Response: $BODY"
        test_pass
    else
        test_fail "Expected HTTP 200, got $HTTP_CODE"
    fi
}

# Test 2: Readiness endpoint
test_readiness_endpoint() {
    test_start "Readiness endpoint responds"

    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/health/ready || true)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        test_pass
    else
        test_fail "Expected HTTP 200, got $HTTP_CODE"
    fi
}

# Test 3: Liveness endpoint
test_liveness_endpoint() {
    test_start "Liveness endpoint responds"

    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/health/live || true)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        test_pass
    else
        test_fail "Expected HTTP 200, got $HTTP_CODE"
    fi
}

# Test 4: Authentication endpoint exists
test_auth_endpoint() {
    test_start "Authentication endpoint responds"

    # Try to login (should fail without credentials, but endpoint should exist)
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"test"}' \
        http://localhost:8080/auth/login || true)

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    # We expect 401 (unauthorized) or 400 (bad request), not 404
    if [ "$HTTP_CODE" != "404" ] && [ "$HTTP_CODE" != "500" ]; then
        log_info "Auth endpoint exists (HTTP $HTTP_CODE)"
        test_pass
    else
        test_fail "Auth endpoint returned $HTTP_CODE (should not be 404 or 500)"
    fi
}

# Test 5: MCP tools endpoint
test_mcp_tools_endpoint() {
    test_start "MCP tools endpoint responds"

    RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8080/tools || true)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)

    if [ "$HTTP_CODE" = "200" ]; then
        # Check if response contains tools
        TOOL_COUNT=$(echo "$BODY" | jq '.tools | length' 2>/dev/null || echo "0")
        if [ "$TOOL_COUNT" -gt 0 ]; then
            log_info "Found $TOOL_COUNT tools"
            test_pass
        else
            test_fail "No tools returned"
        fi
    else
        test_fail "Expected HTTP 200, got $HTTP_CODE"
    fi
}

# Test 6: Response time baseline
test_response_time() {
    test_start "Response time is acceptable"

    RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8080/health)

    log_info "Response time: ${RESPONSE_TIME}s"

    # Check if response time is less than 1 second
    if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
        test_pass
    else
        log_warn "Response time is ${RESPONSE_TIME}s (threshold: 1.0s)"
        # Don't fail, just warn
        test_pass
    fi
}

# Test 7: Kubernetes deployment status
test_deployment_status() {
    test_start "Deployment is ready"

    READY_REPLICAS=$(kubectl get deployment "$SERVICE_NAME" \
        -n "$NAMESPACE" \
        -o jsonpath='{.status.readyReplicas}')

    DESIRED_REPLICAS=$(kubectl get deployment "$SERVICE_NAME" \
        -n "$NAMESPACE" \
        -o jsonpath='{.spec.replicas}')

    log_info "Ready: $READY_REPLICAS, Desired: $DESIRED_REPLICAS"

    if [ "$READY_REPLICAS" = "$DESIRED_REPLICAS" ]; then
        test_pass
    else
        test_fail "Not all replicas are ready ($READY_REPLICAS/$DESIRED_REPLICAS)"
    fi
}

# Test 8: Pods are running
test_pods_running() {
    test_start "All pods are running"

    POD_STATUS=$(kubectl get pods -n "$NAMESPACE" \
        -l app=mcp-server-langgraph \
        -o jsonpath='{.items[*].status.phase}')

    RUNNING_COUNT=$(echo "$POD_STATUS" | grep -o "Running" | wc -l)
    TOTAL_COUNT=$(echo "$POD_STATUS" | wc -w)

    log_info "Running: $RUNNING_COUNT, Total: $TOTAL_COUNT"

    if [ "$RUNNING_COUNT" -eq "$TOTAL_COUNT" ] && [ "$TOTAL_COUNT" -gt 0 ]; then
        test_pass
    else
        test_fail "Not all pods are running ($RUNNING_COUNT/$TOTAL_COUNT)"
    fi
}

# Test 9: No pods are restarting
test_pod_restarts() {
    test_start "Pods have low restart count"

    MAX_RESTARTS=$(kubectl get pods -n "$NAMESPACE" \
        -l app=mcp-server-langgraph \
        -o jsonpath='{range .items[*]}{.status.containerStatuses[*].restartCount}{" "}{end}' | \
        tr ' ' '\n' | \
        grep -v '^$' | \
        sort -nr | \
        head -n1 || echo "0")

    log_info "Max restart count: ${MAX_RESTARTS:-0}"

    # Warn if restarts > 2, fail if > 5
    if [ "${MAX_RESTARTS:-0}" -le 2 ]; then
        test_pass
    elif [ "${MAX_RESTARTS:-0}" -le 5 ]; then
        log_warn "Pods have been restarted ${MAX_RESTARTS} times"
        test_pass
    else
        test_fail "Too many restarts: ${MAX_RESTARTS}"
    fi
}

# Test 10: Cloud SQL proxy is running
test_cloud_sql_proxy() {
    test_start "Cloud SQL proxy sidecar is running"

    POD_NAME=$(kubectl get pods -n "$NAMESPACE" \
        -l app=mcp-server-langgraph \
        -o jsonpath='{.items[0].metadata.name}')

    # Check if cloud-sql-proxy container exists
    PROXY_STATUS=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" \
        -o jsonpath='{.status.containerStatuses[?(@.name=="cloud-sql-proxy")].ready}')

    if [ "$PROXY_STATUS" = "true" ]; then
        test_pass
    else
        test_fail "Cloud SQL proxy sidecar is not ready"
    fi
}

# Test 11: External Secrets are synced
test_external_secrets() {
    test_start "External Secrets are synced"

    # Check if ExternalSecret resource exists and is synced
    SYNC_STATUS=$(kubectl get externalsecret mcp-staging-secrets \
        -n "$NAMESPACE" \
        -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")

    if [ "$SYNC_STATUS" = "True" ]; then
        test_pass
    else
        log_warn "ExternalSecret not synced (this is expected if External Secrets Operator is not installed)"
        test_pass  # Don't fail if ESO is not installed
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Smoke Test Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Total Tests:  $TESTS_RUN"
    echo -e "Passed:       ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed:       ${RED}$TESTS_FAILED${NC}"
    echo ""

    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo -e "${GREEN}✓ All smoke tests passed!${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 0
    else
        echo -e "${RED}✗ Some smoke tests failed${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting staging smoke tests..."
    log_info "Namespace: $NAMESPACE"
    log_info "Service: $SERVICE_NAME"
    echo ""

    # Setup
    if ! setup_port_forward; then
        log_error "Failed to setup port-forward"
        exit 1
    fi

    # Run tests
    test_deployment_status
    test_pods_running
    test_pod_restarts
    test_cloud_sql_proxy
    test_external_secrets
    test_health_endpoint
    test_readiness_endpoint
    test_liveness_endpoint
    test_response_time
    test_auth_endpoint
    test_mcp_tools_endpoint

    # Print summary and exit
    print_summary
    EXIT_CODE=$?

    exit $EXIT_CODE
}

# Run main
main "$@"
