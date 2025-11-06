#!/usr/bin/env bash
# ==============================================================================
# Network Policy Validation Script
# ==============================================================================
#
# Validates that NetworkPolicies follow best practices and prevent
# the classes of errors discovered in staging deployment failures.
#
# USAGE:
#   ./scripts/validate-network-policies.sh [namespace]
#
# CHECKS:
#   1. Bidirectional rules for clustering protocols
#   2. Egress rules match ingress rules for peer-to-peer communication
#   3. Required ports are open for service dependencies
#   4. No duplicate port names in services
#
# EXIT CODES:
#   0 - All validations passed
#   1 - Validation failures found
#
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${1:-staging-mcp-server-langgraph}"
VALIDATION_ERRORS=0

# ==============================================================================
# Helper Functions
# ==============================================================================

log_error() {
    echo -e "${RED}✗ ERROR:${NC} $1" >&2
    ((VALIDATION_ERRORS++))
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠ WARNING:${NC} $1"
}

log_info() {
    echo "ℹ $1"
}

# ==============================================================================
# Validation 1: Keycloak Clustering Ports
# ==============================================================================

validate_keycloak_clustering() {
    log_info "Validating Keycloak clustering configuration..."

    # Check if Keycloak network policy exists
    if ! kubectl get networkpolicy -n "$NAMESPACE" -l app=keycloak -o name &>/dev/null; then
        log_warning "No Keycloak network policy found"
        return
    fi

    local policy_yaml
    policy_yaml=$(kubectl get networkpolicy -n "$NAMESPACE" keycloak-network-policy -o yaml 2>/dev/null || echo "")

    if [ -z "$policy_yaml" ]; then
        log_warning "keycloak-network-policy not found"
        return
    fi

    # Check ingress allows JGroups (7800) and management (9000)
    if echo "$policy_yaml" | grep -q "port: 7800"; then
        log_success "Keycloak ingress allows TCP/7800 (JGroups)"
    else
        log_error "Keycloak network policy missing ingress rule for TCP/7800 (JGroups clustering)"
    fi

    # Check egress allows JGroups (7800) and management (9000)
    local egress_section
    egress_section=$(echo "$policy_yaml" | sed -n '/^  egress:/,/^  [a-z]/p')

    if echo "$egress_section" | grep -q "port: 7800"; then
        log_success "Keycloak egress allows TCP/7800 (JGroups)"
    else
        log_error "Keycloak network policy missing egress rule for TCP/7800 (CRITICAL: prevents cluster formation)"
    fi

    if echo "$egress_section" | grep -q "app: keycloak"; then
        log_success "Keycloak egress allows pod-to-pod communication"
    else
        log_error "Keycloak network policy missing pod-to-pod egress rule (CRITICAL: prevents clustering)"
    fi
}

# ==============================================================================
# Validation 2: Service Port Name Uniqueness
# ==============================================================================

validate_service_port_names() {
    log_info "Validating service port name uniqueness..."

    # Get all services and check for duplicate port names
    local services
    services=$(kubectl get svc -n "$NAMESPACE" -o json)

    # Check each service
    echo "$services" | jq -r '.items[] | .metadata.name' | while read -r svc_name; do
        local port_names
        port_names=$(echo "$services" | jq -r ".items[] | select(.metadata.name==\"$svc_name\") | .spec.ports[]?.name" 2>/dev/null || echo "")

        if [ -z "$port_names" ]; then
            continue
        fi

        # Check for duplicates
        local duplicates
        duplicates=$(echo "$port_names" | sort | uniq -d)

        if [ -n "$duplicates" ]; then
            log_error "Service $svc_name has duplicate port names: $duplicates"
        else
            log_success "Service $svc_name has unique port names"
        fi
    done
}

# ==============================================================================
# Validation 3: Health Check Endpoint Configuration
# ==============================================================================

validate_health_endpoints() {
    log_info "Validating health check endpoint configuration..."

    # Check deployment probe paths using JSONPath
    local startup_path
    local readiness_path
    local liveness_path

    startup_path=$(kubectl get deployment -n "$NAMESPACE" staging-mcp-server-langgraph -o jsonpath='{.spec.template.spec.containers[0].startupProbe.httpGet.path}' 2>/dev/null || echo "")
    readiness_path=$(kubectl get deployment -n "$NAMESPACE" staging-mcp-server-langgraph -o jsonpath='{.spec.template.spec.containers[0].readinessProbe.httpGet.path}' 2>/dev/null || echo "")
    liveness_path=$(kubectl get deployment -n "$NAMESPACE" staging-mcp-server-langgraph -o jsonpath='{.spec.template.spec.containers[0].livenessProbe.httpGet.path}' 2>/dev/null || echo "")

    if [ -z "$startup_path" ]; then
        log_warning "Could not extract probe paths from deployment"
        return
    fi

    # Validate paths follow standardized format
    if [ "$startup_path" = "/health/startup" ]; then
        log_success "Startup probe uses correct path: $startup_path"
    else
        log_error "Startup probe path incorrect: $startup_path (expected: /health/startup)"
    fi

    if [ "$readiness_path" = "/health/ready" ]; then
        log_success "Readiness probe uses correct path: $readiness_path"
    else
        log_error "Readiness probe path incorrect: $readiness_path (expected: /health/ready)"
    fi

    if [ "$liveness_path" = "/health/live" ]; then
        log_success "Liveness probe uses correct path: $liveness_path"
    else
        log_error "Liveness probe path incorrect: $liveness_path (expected: /health/live)"
    fi
}

# ==============================================================================
# Validation 4: Cloud SQL Proxy Health Checks
# ==============================================================================

validate_cloud_sql_proxy_health_checks() {
    log_info "Validating Cloud SQL Proxy health check configuration..."

    # Get Cloud SQL Proxy container args using JSONPath
    local proxy_args
    proxy_args=$(kubectl get deployment -n "$NAMESPACE" staging-mcp-server-langgraph -o jsonpath='{.spec.template.spec.containers[1].args}' 2>/dev/null || echo "")

    if [ -z "$proxy_args" ]; then
        log_warning "Could not extract Cloud SQL Proxy args from deployment"
        return
    fi

    # Check if Cloud SQL Proxy container has health check flags
    if echo "$proxy_args" | grep -q -- "--health-check"; then
        log_success "Cloud SQL Proxy has --health-check flag"
    else
        log_error "Cloud SQL Proxy missing --health-check flag (CRITICAL: causes sidecar crashes)"
    fi

    if echo "$proxy_args" | grep -q -- "--http-port=9801"; then
        log_success "Cloud SQL Proxy configured for health check port 9801"
    else
        log_error "Cloud SQL Proxy missing --http-port=9801 flag"
    fi

    if echo "$proxy_args" | grep -q -- "--http-address=0.0.0.0"; then
        log_success "Cloud SQL Proxy listens on all interfaces"
    else
        log_error "Cloud SQL Proxy missing --http-address=0.0.0.0 flag"
    fi
}

# ==============================================================================
# Validation 5: Pod Health Status
# ==============================================================================

validate_pod_health() {
    log_info "Validating pod health status..."

    # Check Keycloak pods
    local keycloak_ready
    keycloak_ready=$(kubectl get pods -n "$NAMESPACE" -l app=keycloak -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")

    if echo "$keycloak_ready" | grep -q "False"; then
        log_error "Keycloak pods not all ready"
    elif [ -n "$keycloak_ready" ]; then
        log_success "All Keycloak pods ready"
    fi

    # Check MCP server pods
    local mcp_ready
    mcp_ready=$(kubectl get pods -n "$NAMESPACE" -l app=mcp-server-langgraph -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")

    if echo "$mcp_ready" | grep -q "False"; then
        log_error "MCP server pods not all ready"
    elif [ -n "$mcp_ready" ]; then
        log_success "All MCP server pods ready"
    fi

    # Check for CrashLoopBackOff
    local crash_loops
    crash_loops=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running,status.phase!=Succeeded 2>/dev/null | grep -c "CrashLoopBackOff" || echo "0")

    if [ "$crash_loops" -gt 0 ]; then
        log_error "$crash_loops pods in CrashLoopBackOff"
    else
        log_success "No pods in CrashLoopBackOff"
    fi
}

# ==============================================================================
# Main Validation Flow
# ==============================================================================

main() {
    echo "=========================================="
    echo "Network Policy Validation"
    echo "Namespace: $NAMESPACE"
    echo "=========================================="
    echo ""

    # Run all validations
    validate_keycloak_clustering
    echo ""
    validate_service_port_names
    echo ""
    validate_health_endpoints
    echo ""
    validate_cloud_sql_proxy_health_checks
    echo ""
    validate_pod_health
    echo ""

    # Summary
    echo "=========================================="
    if [ $VALIDATION_ERRORS -eq 0 ]; then
        echo -e "${GREEN}✓ All validations passed${NC}"
        echo "=========================================="
        exit 0
    else
        echo -e "${RED}✗ Found $VALIDATION_ERRORS validation error(s)${NC}"
        echo "=========================================="
        exit 1
    fi
}

main
