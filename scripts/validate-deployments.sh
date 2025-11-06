#!/usr/bin/env bash
#
# Deployment Configuration Validation Script
#
# This script validates all deployment configurations to prevent common issues

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*"; ((PASSED++)); }
log_error() { echo -e "${RED}[FAIL]${NC} $*"; ((FAILED++)); }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*"; ((WARNINGS++)); }

validate_helm_chart() {
    log_info "Validating Helm chart..."
    local chart_path="$PROJECT_ROOT/deployments/helm/mcp-server-langgraph"

    if ! command -v helm &> /dev/null; then
        log_warning "Helm not installed, skipping"
        return 0
    fi

    if helm lint "$chart_path" 2>&1 | grep -v "bad character U+002D" | grep -q "Error:"; then
        log_error "Helm lint failed"
        return 1
    else
        log_success "Helm lint passed"
    fi
}

validate_kustomize_overlays() {
    log_info "Validating Kustomize overlays..."
    local overlays_path="$PROJECT_ROOT/deployments/overlays"

    if ! command -v kustomize &> /dev/null; then
        log_warning "Kustomize not installed, skipping"
        return 0
    fi

    for overlay in "$overlays_path"/*/; do
        [[ -d "$overlay" ]] || continue
        [[ -f "$overlay/kustomization.yaml" ]] || continue

        overlay_name=$(basename "$overlay")
        if kustomize build "$overlay" > /dev/null 2>&1; then
            log_success "Overlay $overlay_name OK"
        else
            log_error "Overlay $overlay_name failed"
            return 1
        fi
    done
}

validate_cors_security() {
    log_info "Validating CORS security..."

    if grep -A 5 "credentials: true" "$PROJECT_ROOT/deployments/kong/kong.yaml" 2>/dev/null | grep -q '"*"'; then
        log_error "Kong: wildcard CORS with credentials"
        return 1
    fi

    log_success "CORS configuration secure"
}

main() {
    log_info "Deployment validation started"

    validate_helm_chart || true
    validate_kustomize_overlays || true
    validate_cors_security || true

    echo "======================================"
    echo -e "${GREEN}Passed:${NC} $PASSED | ${RED}Failed:${NC} $FAILED | ${YELLOW}Warnings:${NC} $WARNINGS"

    [ $FAILED -eq 0 ] && echo -e "${GREEN}✅ PASSED${NC}" && exit 0
    echo -e "${RED}❌ FAILED${NC}" && exit 1
}

main "$@"
