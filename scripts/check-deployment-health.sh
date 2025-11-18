#!/usr/bin/env bash
#
# Deployment Health Check Script
#
# This script validates a deployed MCP server instance to ensure:
# - All required secrets are accessible
# - Services are reachable
# - Network policies allow required traffic
# - Configuration is correct
#
# Usage:
#   ./scripts/check-deployment-health.sh [namespace] [release-name]
#
# Examples:
#   ./scripts/check-deployment-health.sh production-mcp-server-langgraph mcp
#   ./scripts/check-deployment-health.sh dev-mcp-server-langgraph dev-mcp

set -euo pipefail

# Default values
NAMESPACE="${1:-mcp-server-langgraph}"
RELEASE_NAME="${2:-mcp-server-langgraph}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*"; ((CHECKS_PASSED++)); }
log_error() { echo -e "${RED}[FAIL]${NC} $*"; ((CHECKS_FAILED++)); }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*"; ((CHECKS_WARNED++)); }

check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not installed"
        exit 2
    fi
}

check_namespace_exists() {
    log_info "Checking namespace: $NAMESPACE"

    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_success "Namespace exists"
    else
        log_error "Namespace not found: $NAMESPACE"
        return 1
    fi
}

check_deployment_ready() {
    log_info "Checking deployment status..."

    local deployment="${RELEASE_NAME}"

    if ! kubectl get deployment "$deployment" -n "$NAMESPACE" &> /dev/null; then
        log_error "Deployment not found: $deployment"
        return 1
    fi

    local ready
    ready=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
    local desired
    desired=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.replicas}')

    if [[ "$ready" == "$desired" ]] && [[ "$ready" -gt 0 ]]; then
        log_success "Deployment ready: $ready/$desired replicas"
    else
        log_error "Deployment not ready: $ready/$desired replicas"
        return 1
    fi
}

check_secrets_exist() {
    log_info "Checking required secrets..."

    local secret_name="${RELEASE_NAME}-secrets"

    if ! kubectl get secret "$secret_name" -n "$NAMESPACE" &> /dev/null; then
        log_warning "Secret not found: $secret_name (might use existingSecret)"
        return 0
    fi

    # Check required secret keys
    local required_keys=(
        "anthropic-api-key"
        "jwt-secret-key"
        "redis-password"
    )

    local missing_keys=()

    for key in "${required_keys[@]}"; do
        if ! kubectl get secret "$secret_name" -n "$NAMESPACE" -o jsonpath="{.data.$key}" &> /dev/null; then
            missing_keys+=("$key")
        fi
    done

    if [[ ${#missing_keys[@]} -eq 0 ]]; then
        log_success "All required secret keys present"
    else
        log_error "Missing secret keys: ${missing_keys[*]}"
        return 1
    fi
}

check_pods_running() {
    log_info "Checking pod status..."

    local pods
    pods=$(kubectl get pods -n "$NAMESPACE" -l app=mcp-server-langgraph -o jsonpath='{.items[*].metadata.name}')

    if [[ -z "$pods" ]]; then
        log_error "No pods found with label app=mcp-server-langgraph"
        return 1
    fi

    local all_running=true

    for pod in $pods; do
        local status
        status=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.phase}')

        if [[ "$status" != "Running" ]]; then
            log_error "Pod $pod is in $status state"
            all_running=false
        fi
    done

    if [[ "$all_running" == "true" ]]; then
        log_success "All pods running"
    else
        return 1
    fi
}

check_service_endpoints() {
    log_info "Checking service endpoints..."

    local service="${RELEASE_NAME}"

    if ! kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
        log_error "Service not found: $service"
        return 1
    fi

    local endpoints
    endpoints=$(kubectl get endpoints "$service" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}')

    if [[ -n "$endpoints" ]]; then
        local count
        count=$(echo "$endpoints" | wc -w)
        log_success "Service has $count endpoint(s)"
    else
        log_error "Service has no endpoints (no ready pods)"
        return 1
    fi
}

check_configmap_exists() {
    log_info "Checking ConfigMap..."

    local configmap="${RELEASE_NAME}-config"

    if kubectl get configmap "$configmap" -n "$NAMESPACE" &> /dev/null; then
        log_success "ConfigMap exists"
    else
        log_warning "ConfigMap not found: $configmap (might use different name)"
    fi
}

check_ingress_configured() {
    log_info "Checking Ingress configuration..."

    local ingresses
    ingresses=$(kubectl get ingress -n "$NAMESPACE" -o name 2>/dev/null)

    if [[ -z "$ingresses" ]]; then
        log_warning "No ingress resources found (might use LoadBalancer service)"
        return 0
    fi

    for ingress in $ingresses; do
        local ingress_name
        ingress_name=$(basename "$ingress")
        local hosts
        hosts=$(kubectl get "$ingress" -n "$NAMESPACE" -o jsonpath='{.spec.rules[*].host}')

        if [[ -n "$hosts" ]]; then
            log_success "Ingress $ingress_name configured with hosts: $hosts"
        else
            log_warning "Ingress $ingress_name has no hosts configured"
        fi
    done
}

check_network_policy() {
    log_info "Checking NetworkPolicy..."

    if ! kubectl get networkpolicy -n "$NAMESPACE" &> /dev/null; then
        log_warning "No NetworkPolicy found (might use CNI defaults)"
        return 0
    fi

    local policies
    policies=$(kubectl get networkpolicy -n "$NAMESPACE" -o name)
    local count
    count=$(echo "$policies" | wc -l)

    log_success "Found $count NetworkPolicy resource(s)"
}

check_external_secrets() {
    log_info "Checking ExternalSecrets..."

    if ! kubectl get externalsecret -n "$NAMESPACE" &> /dev/null 2>&1; then
        log_info "ExternalSecrets not used (using static secrets)"
        return 0
    fi

    local external_secrets
    external_secrets=$(kubectl get externalsecret -n "$NAMESPACE" -o name 2>/dev/null)

    for es in $external_secrets; do
        local es_name
        es_name=$(basename "$es")
        local status
        status=$(kubectl get "$es" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)

        if [[ "$status" == "True" ]]; then
            log_success "ExternalSecret $es_name is synced"
        else
            log_error "ExternalSecret $es_name not ready"
            return 1
        fi
    done
}

# Main execution
main() {
    log_info "====================================="
    log_info "Deployment Health Check"
    log_info "Namespace: $NAMESPACE"
    log_info "Release: $RELEASE_NAME"
    log_info "====================================="
    echo

    check_kubectl
    check_namespace_exists || true
    check_deployment_ready || true
    check_secrets_exist || true
    check_pods_running || true
    check_service_endpoints || true
    check_configmap_exists || true
    check_ingress_configured || true
    check_network_policy || true
    check_external_secrets || true

    echo
    echo "====================================="
    echo "Health Check Summary"
    echo "====================================="
    echo -e "${GREEN}Passed:${NC}   $CHECKS_PASSED"
    echo -e "${RED}Failed:${NC}   $CHECKS_FAILED"
    echo -e "${YELLOW}Warnings:${NC} $CHECKS_WARNED"
    echo "====================================="

    if [[ $CHECKS_FAILED -gt 0 ]]; then
        echo -e "${RED}❌ Deployment health check FAILED${NC}"
        exit 1
    elif [[ $CHECKS_WARNED -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  Deployment healthy with warnings${NC}"
        exit 0
    else
        echo -e "${GREEN}✅ Deployment is HEALTHY${NC}"
        exit 0
    fi
}

main "$@"
