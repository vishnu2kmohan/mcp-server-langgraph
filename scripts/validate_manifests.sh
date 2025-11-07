#!/usr/bin/env bash
#
# Manifest Validation Script
#
# Validates Kubernetes manifests, Kustomize overlays, and Helm charts
# to ensure they are syntactically correct and can be built/rendered.
#
# Usage:
#   ./scripts/validate_manifests.sh [--verbose] [--fail-fast]
#
# Options:
#   --verbose     Show detailed output from each validation step
#   --fail-fast   Stop on first error (default: run all validations)
#
# Exit codes:
#   0 - All validations passed
#   1 - One or more validations failed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSE=0
FAIL_FAST=0
ERRORS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=1
            shift
            ;;
        --fail-fast)
            FAIL_FAST=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ERRORS=$((ERRORS + 1))
}

check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        log_error "Required command not found: $cmd"
        exit 1
    fi
}

run_validation() {
    local description=$1
    shift
    local cmd=("$@")

    log_info "Validating: $description"

    local output
    local exit_code=0

    if [[ $VERBOSE -eq 1 ]]; then
        if "${cmd[@]}"; then
            log_success "$description"
        else
            exit_code=$?
            log_error "$description (exit code: $exit_code)"
            if [[ $FAIL_FAST -eq 1 ]]; then
                exit 1
            fi
        fi
    else
        if output=$("${cmd[@]}" 2>&1); then
            log_success "$description"
        else
            exit_code=$?
            log_error "$description (exit code: $exit_code)"
            echo "$output"
            if [[ $FAIL_FAST -eq 1 ]]; then
                exit 1
            fi
        fi
    fi
}

# Main validation steps

main() {
    log_info "Starting manifest validation..."
    log_info "Project root: $PROJECT_ROOT"
    echo ""

    # Check required commands
    log_info "Checking required tools..."
    check_command kubectl
    check_command kustomize
    check_command helm
    check_command yamllint
    echo ""

    # Validate base manifests with yamllint
    log_info "=== YAML Syntax Validation ==="
    if [[ -d "$PROJECT_ROOT/deployments/base" ]]; then
        run_validation "Base manifests YAML syntax" \
            yamllint -d '{extends: relaxed, rules: {line-length: {max: 200}}}' \
            "$PROJECT_ROOT/deployments/base"
    fi
    echo ""

    # Validate Kustomize overlays
    log_info "=== Kustomize Overlay Validation ==="

    local overlays=(dev staging production)
    for overlay in "${overlays[@]}"; do
        local overlay_dir="$PROJECT_ROOT/deployments/overlays/$overlay"
        if [[ -d "$overlay_dir" ]]; then
            run_validation "Kustomize overlay: $overlay" \
                kustomize build "$overlay_dir"
        else
            log_warning "Overlay not found: $overlay"
        fi
    done
    echo ""

    # Validate cloud provider overlays
    log_info "=== Cloud Provider Overlay Validation ==="

    local cloud_overlays=(aws gcp azure)
    for overlay in "${cloud_overlays[@]}"; do
        local overlay_dir="$PROJECT_ROOT/deployments/kubernetes/overlays/$overlay"
        if [[ -d "$overlay_dir" ]]; then
            run_validation "Cloud provider overlay: $overlay" \
                kustomize build "$overlay_dir"
        else
            log_warning "Cloud provider overlay not found: $overlay"
        fi
    done
    echo ""

    # Validate Helm chart
    log_info "=== Helm Chart Validation ==="

    local helm_chart="$PROJECT_ROOT/deployments/helm/mcp-server-langgraph"
    if [[ -d "$helm_chart" ]]; then
        run_validation "Helm chart lint" \
            helm lint "$helm_chart"

        run_validation "Helm chart template (default values)" \
            helm template test-release "$helm_chart"

        # Test with Istio disabled
        run_validation "Helm chart template (Istio disabled)" \
            helm template test-release "$helm_chart" \
            --set serviceMesh.enabled=false

        # Test with NetworkPolicy disabled
        run_validation "Helm chart template (NetworkPolicy disabled)" \
            helm template test-release "$helm_chart" \
            --set networkPolicy.enabled=false
    else
        log_warning "Helm chart not found: $helm_chart"
    fi
    echo ""

    # Validate base kustomization resources
    log_info "=== Base Kustomization Resource Check ==="

    local base_kustomization="$PROJECT_ROOT/deployments/base/kustomization.yaml"
    if [[ -f "$base_kustomization" ]]; then
        # Check that all referenced resources exist
        local resources
        resources=$(yq eval '.resources[]' "$base_kustomization" 2>/dev/null || echo "")

        local missing=0
        while IFS= read -r resource; do
            if [[ -n "$resource" && ! "$resource" =~ ^http ]]; then
                local resource_file="$PROJECT_ROOT/deployments/base/$resource"
                if [[ ! -f "$resource_file" ]]; then
                    log_error "Referenced resource not found: $resource"
                    missing=$((missing + 1))
                fi
            fi
        done <<< "$resources"

        if [[ $missing -eq 0 ]]; then
            log_success "All kustomization resources exist"
        fi
    fi
    echo ""

    # Validate kubectl dry-run on built manifests
    log_info "=== Kubernetes API Validation ==="

    local temp_manifest
    temp_manifest=$(mktemp)

    if kustomize build "$PROJECT_ROOT/deployments/overlays/dev" > "$temp_manifest" 2>/dev/null; then
        run_validation "Kubectl dry-run validation (dev overlay)" \
            kubectl apply --dry-run=server -f "$temp_manifest"
    else
        log_warning "Could not build dev overlay for kubectl validation"
    fi

    rm -f "$temp_manifest"
    echo ""

    # Summary
    echo "======================================"
    if [[ $ERRORS -eq 0 ]]; then
        log_success "All validations passed!"
        exit 0
    else
        log_error "Validation failed with $ERRORS error(s)"
        exit 1
    fi
}

main "$@"
