#!/bin/bash
#
# Pre-Deployment Validation Script
# Runs comprehensive validation before deploying to GKE
#
# Usage: ./scripts/validate-deployment.sh [overlay]
# Example: ./scripts/validate-deployment.sh staging-gke

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
OVERLAY="${1:-staging-gke}"
OVERLAY_DIR="deployments/overlays/${OVERLAY}"
TEST_DIR="tests/deployment"

# Helper functions
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

check_dependencies() {
    echo "=================================================="
    echo "Checking Dependencies"
    echo "=================================================="

    local missing_deps=()

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        missing_deps+=("kubectl")
    else
        log_info "kubectl: $(kubectl version --client --short 2>&1 | head -1)"
    fi

    # Check kustomize (via kubectl)
    if ! kubectl kustomize --help &> /dev/null; then
        missing_deps+=("kustomize")
    else
        log_info "kustomize: available via kubectl"
    fi

    # Check python3
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    else
        log_info "python3: $(python3 --version)"
    fi

    # Check pytest
    if ! python3 -m pytest --version &> /dev/null; then
        missing_deps+=("pytest")
    else
        log_info "pytest: $(python3 -m pytest --version)"
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi

    echo ""
}

validate_overlay_exists() {
    echo "=================================================="
    echo "Validating Overlay: ${OVERLAY}"
    echo "=================================================="

    if [ ! -d "${OVERLAY_DIR}" ]; then
        log_error "Overlay directory not found: ${OVERLAY_DIR}"
        exit 1
    fi
    log_info "Overlay directory exists"

    if [ ! -f "${OVERLAY_DIR}/kustomization.yaml" ]; then
        log_error "kustomization.yaml not found in ${OVERLAY_DIR}"
        exit 1
    fi
    log_info "kustomization.yaml found"

    echo ""
}

run_kustomize_build() {
    echo "=================================================="
    echo "Building Kustomize Manifests"
    echo "=================================================="

    local build_output
    if build_output=$(kubectl kustomize "${OVERLAY_DIR}" 2>&1); then
        local manifest_count
        manifest_count=$(echo "$build_output" | grep -c "^---" || true)
        log_info "Kustomize build successful (${manifest_count} manifests)"

        # Save to temp file for inspection
        echo "$build_output" > "/tmp/${OVERLAY}-manifests.yaml"
        log_info "Manifests saved to /tmp/${OVERLAY}-manifests.yaml"
    else
        log_error "Kustomize build failed:"
        echo "$build_output"
        exit 1
    fi

    echo ""
}

run_deployment_tests() {
    echo "=================================================="
    echo "Running Deployment Validation Tests"
    echo "=================================================="

    if [ ! -d "${TEST_DIR}" ]; then
        log_warn "Test directory not found: ${TEST_DIR}"
        log_warn "Skipping tests"
        return 0
    fi

    # Install test dependencies if needed
    if [ -f "${TEST_DIR}/requirements-test.txt" ]; then
        log_info "Installing test dependencies..."
        python3 -m pip install -q -r "${TEST_DIR}/requirements-test.txt" || true
    fi

    # Run pytest with verbose output
    if python3 -m pytest "${TEST_DIR}" -v --tb=short; then
        log_info "All deployment tests passed"
    else
        log_error "Deployment tests failed"
        exit 1
    fi

    echo ""
}

validate_cloud_sql_proxy() {
    echo "=================================================="
    echo "Validating Cloud SQL Proxy Configuration"
    echo "=================================================="

    local manifests="/tmp/${OVERLAY}-manifests.yaml"

    # Check for Cloud SQL Proxy containers
    if grep -q "name: cloud-sql-proxy" "$manifests"; then
        log_info "Cloud SQL Proxy sidecars found"

        # Check for required flags
        if grep -A 10 "name: cloud-sql-proxy" "$manifests" | grep -q -- "--http-port=9801"; then
            log_info "Cloud SQL Proxy has --http-port=9801 flag"
        else
            log_error "Cloud SQL Proxy missing --http-port=9801 flag"
            exit 1
        fi

        if grep -A 10 "name: cloud-sql-proxy" "$manifests" | grep -q -- "--health-check"; then
            log_info "Cloud SQL Proxy has --health-check flag"
        else
            log_error "Cloud SQL Proxy missing --health-check flag"
            exit 1
        fi

        # Check for health probes
        if grep -A 50 "name: cloud-sql-proxy" "$manifests" | grep -q "livenessProbe"; then
            log_info "Cloud SQL Proxy has liveness probe configured"
        else
            log_warn "Cloud SQL Proxy missing liveness probe"
        fi
    else
        log_info "No Cloud SQL Proxy sidecars (may be using different database connection method)"
    fi

    echo ""
}

validate_service_dependencies() {
    echo "=================================================="
    echo "Validating Service Dependencies"
    echo "=================================================="

    local manifests="/tmp/${OVERLAY}-manifests.yaml"

    # Extract all service names
    local services
    services=$(grep -A 5 "^kind: Service" "$manifests" | grep "  name:" | awk '{print $2}' | sort -u)

    log_info "Found services:"
    echo "$services" | while read -r svc; do
        echo "  - $svc"
    done

    # Extract init container service references
    local init_refs
    init_refs=$(grep -A 20 "initContainers:" "$manifests" | grep "nc -z" | awk '{print $4}' | sort -u || true)

    if [ -n "$init_refs" ]; then
        log_info "Checking init container service references..."
        echo "$init_refs" | while read -r ref; do
            if echo "$services" | grep -q "^${ref}$"; then
                log_info "  ✓ Service '$ref' exists"
            else
                log_error "  ✗ Service '$ref' referenced but not found"
                exit 1
            fi
        done
    fi

    echo ""
}

validate_workload_identity() {
    echo "=================================================="
    echo "Validating Workload Identity Configuration"
    echo "=================================================="

    local manifests="/tmp/${OVERLAY}-manifests.yaml"

    # Check for Workload Identity annotations
    if grep -q "iam.gke.io/gcp-service-account" "$manifests"; then
        log_info "Workload Identity annotations found"

        # List all GCP service accounts referenced
        local gcp_sa
        gcp_sa=$(grep "iam.gke.io/gcp-service-account:" "$manifests" | awk '{print $2}' | sort -u)

        log_info "GCP Service Accounts referenced:"
        echo "$gcp_sa" | while read -r sa; do
            echo "  - $sa"
        done
    else
        log_warn "No Workload Identity annotations found"
    fi

    echo ""
}

validate_network_policies() {
    echo "=================================================="
    echo "Validating Network Policy DNS & HTTPS Egress"
    echo "=================================================="

    local manifests="/tmp/${OVERLAY}-manifests.yaml"
    local validation_failed=0

    # Required egress rules
    local required_dns_cidr="169.254.0.0/16"  # GKE Dataplane V2
    local required_https_cidr="0.0.0.0/0"      # sqladmin.googleapis.com

    # Extract all NetworkPolicy resources
    local policies
    policies=$(grep -A 2 "^kind: NetworkPolicy" "$manifests" | grep "  name:" | awk '{print $2}' | sort -u || true)

    if [ -z "$policies" ]; then
        log_warn "No NetworkPolicy resources found in manifests"
        echo ""
        return 0
    fi

    log_info "Validating NetworkPolicy resources:"
    echo "$policies" | while read -r policy; do
        echo "  - $policy"
    done
    echo ""

    # Validate GKE Dataplane V2 DNS egress for critical policies
    log_info "Checking GKE Dataplane V2 DNS egress (169.254.0.0/16)..."
    local dns_policies=("allow-egress" "keycloak-network-policy" "openfga-network-policy")

    for policy in "${dns_policies[@]}"; do
        if echo "$policies" | grep -q "^${policy}$"; then
            # Extract DNS egress CIDR blocks for this policy
            local policy_start
            policy_start=$(grep -n "name: ${policy}" "$manifests" | cut -d: -f1 | head -1)
            if [ -n "$policy_start" ]; then
                local dns_egress
                dns_egress=$(sed -n "${policy_start},/^---/p" "$manifests" | \
                    grep -A 5 "port: 53" | grep -A 2 "ipBlock:" | grep "cidr:" | awk '{print $2}' || true)

                if echo "$dns_egress" | grep -q "$required_dns_cidr"; then
                    log_info "  ✓ ${policy}: Has DNS egress to ${required_dns_cidr}"
                else
                    log_error "  ✗ ${policy}: MISSING DNS egress to ${required_dns_cidr} (GKE Dataplane V2)"
                    log_warn "    This will cause DNS resolution failures for service discovery"
                    validation_failed=1
                fi
            fi
        fi
    done
    echo ""

    # Validate Cloud SQL Auth Proxy HTTPS egress
    log_info "Checking Cloud SQL Auth Proxy HTTPS egress (0.0.0.0/0)..."
    local https_policies=("keycloak-network-policy" "openfga-network-policy")

    for policy in "${https_policies[@]}"; do
        if echo "$policies" | grep -q "^${policy}$"; then
            local policy_start
            policy_start=$(grep -n "name: ${policy}" "$manifests" | cut -d: -f1 | head -1)
            if [ -n "$policy_start" ]; then
                local https_egress
                https_egress=$(sed -n "${policy_start},/^---/p" "$manifests" | \
                    grep -A 5 "port: 443" | grep -A 2 "ipBlock:" | grep "cidr:" | awk '{print $2}' || true)

                if echo "$https_egress" | grep -q "$required_https_cidr"; then
                    log_info "  ✓ ${policy}: Has HTTPS egress to ${required_https_cidr} (allows sqladmin.googleapis.com)"
                else
                    log_error "  ✗ ${policy}: MISSING HTTPS egress to ${required_https_cidr}"
                    log_warn "    Cloud SQL Auth Proxy cannot reach sqladmin.googleapis.com (public Google IPs)"
                    log_warn "    This will cause database connection failures"
                    validation_failed=1
                fi
            fi
        fi
    done
    echo ""

    # Validate --http-address flag for Cloud SQL Proxy
    log_info "Checking Cloud SQL Proxy --http-address flag..."
    if grep -q "name: cloud-sql-proxy" "$manifests"; then
        if grep -A 10 "name: cloud-sql-proxy" "$manifests" | grep -q -- "--http-address=0.0.0.0"; then
            log_info "  ✓ Cloud SQL Proxy has --http-address=0.0.0.0 flag"
        else
            log_error "  ✗ Cloud SQL Proxy MISSING --http-address=0.0.0.0 flag"
            log_warn "    Health endpoints will not be accessible to Kubelet"
            log_warn "    This will cause liveness/readiness probe failures"
            validation_failed=1
        fi
    fi
    echo ""

    if [ $validation_failed -ne 0 ]; then
        log_error "Network policy validation FAILED"
        log_warn "See fixes in: deployments/overlays/staging-gke/network-policy.yaml"
        exit 1
    fi
}

generate_validation_report() {
    echo "=================================================="
    echo "Validation Summary"
    echo "=================================================="

    log_info "Overlay: ${OVERLAY}"
    log_info "Manifests: /tmp/${OVERLAY}-manifests.yaml"
    log_info "All validation checks passed!"

    echo ""
    echo "Next steps:"
    echo "1. Review generated manifests: less /tmp/${OVERLAY}-manifests.yaml"
    echo "2. Apply to cluster: kubectl apply -k ${OVERLAY_DIR}"
    echo "3. Monitor deployment: kubectl get pods -n <namespace> -w"
    echo ""
}

# Main execution
main() {
    echo "=================================================="
    echo "GKE Deployment Pre-Flight Validation"
    echo "=================================================="
    echo ""

    check_dependencies
    validate_overlay_exists
    run_kustomize_build
    run_deployment_tests
    validate_cloud_sql_proxy
    validate_service_dependencies
    validate_workload_identity
    validate_network_policies
    generate_validation_report

    log_info "Pre-deployment validation completed successfully!"
}

# Run main function
main "$@"
