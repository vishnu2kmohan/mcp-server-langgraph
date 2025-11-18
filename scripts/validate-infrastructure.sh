#!/bin/bash
# Infrastructure Validation Script
# ==================================
# Validates all infrastructure configurations and version consistency
#
# USAGE:
#   ./scripts/validate-infrastructure.sh [--verbose]
#
# CHECKS:
#   - Version consistency across all deployment files
#   - Symlinks are valid
#   - Required files exist
#   - Docker Compose syntax
#   - Helm chart validity
#   - Kustomize overlay validity
#   - Kubernetes manifests
#
# EXIT CODES:
#   0 - All validations passed
#   1 - One or more validations failed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBOSE=false
FAILED_CHECKS=0
TOTAL_CHECKS=0

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

print_check() {
    echo -e "${CYAN}▶ Checking: $1${NC}"
}

print_success() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
    ((FAILED_CHECKS++))
}

print_warning() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

print_info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${CYAN}    ℹ $1${NC}"
    fi
}

run_check() {
    local description=$1
    shift
    ((TOTAL_CHECKS++))

    print_check "$description"

    if "$@" > /dev/null 2>&1; then
        print_success "Passed"
        return 0
    else
        print_error "Failed"
        if [[ "$VERBOSE" == "true" ]]; then
            "$@" 2>&1 | sed 's/^/    /' || true
        fi
        return 1
    fi
}

# ==============================================================================
# Version Consistency Checks
# ==============================================================================

check_version_consistency() {
    print_header "Version Consistency"

    local pyproject_version=""
    local helm_version=""
    local helm_app_version=""
    local helm_values_tag=""
    local kustomize_base=""
    local kustomize_prod=""
    local kustomize_staging=""

    # Extract versions
    if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        pyproject_version=$(grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | cut -d'"' -f2)
    fi

    if [[ -f "$PROJECT_ROOT/deployments/helm/mcp-server-langgraph/Chart.yaml" ]]; then
        helm_version=$(grep '^version:' "$PROJECT_ROOT/deployments/helm/mcp-server-langgraph/Chart.yaml" | awk '{print $2}')
        helm_app_version=$(grep '^appVersion:' "$PROJECT_ROOT/deployments/helm/mcp-server-langgraph/Chart.yaml" | awk '{print $2}' | tr -d '"')
    fi

    if [[ -f "$PROJECT_ROOT/deployments/helm/mcp-server-langgraph/values.yaml" ]]; then
        helm_values_tag=$(grep 'tag: ' "$PROJECT_ROOT/deployments/helm/mcp-server-langgraph/values.yaml" | head -1 | awk '{print $2}' | tr -d '"')
    fi

    if [[ -f "$PROJECT_ROOT/deployments/kustomize/base/kustomization.yaml" ]]; then
        kustomize_base=$(grep 'newTag:' "$PROJECT_ROOT/deployments/kustomize/base/kustomization.yaml" | awk '{print $2}')
    fi

    if [[ -f "$PROJECT_ROOT/deployments/kustomize/overlays/production/kustomization.yaml" ]]; then
        kustomize_prod=$(grep 'newTag:' "$PROJECT_ROOT/deployments/kustomize/overlays/production/kustomization.yaml" | awk '{print $2}')
    fi

    if [[ -f "$PROJECT_ROOT/deployments/kustomize/overlays/staging/kustomization.yaml" ]]; then
        kustomize_staging=$(grep 'newTag:' "$PROJECT_ROOT/deployments/kustomize/overlays/staging/kustomization.yaml" | awk '{print $2}')
    fi

    print_info "pyproject.toml: $pyproject_version"
    print_info "Helm Chart: $helm_version"
    print_info "Helm appVersion: $helm_app_version"
    print_info "Helm values tag: $helm_values_tag"
    print_info "Kustomize base: $kustomize_base"
    print_info "Kustomize prod: $kustomize_prod"
    print_info "Kustomize staging: $kustomize_staging"

    ((TOTAL_CHECKS++))
    if [[ "$pyproject_version" == "$helm_version" ]] && \
       [[ "$pyproject_version" == "$helm_app_version" ]] && \
       [[ "$pyproject_version" == "$helm_values_tag" ]] && \
       [[ "$pyproject_version" == "$kustomize_base" ]]; then
        print_success "Core versions are consistent: $pyproject_version"
    else
        print_error "Version mismatch detected!"
        echo -e "    pyproject.toml: $pyproject_version"
        echo -e "    Helm Chart: $helm_version"
        echo -e "    Helm appVersion: $helm_app_version"
        echo -e "    Helm values tag: $helm_values_tag"
        echo -e "    Kustomize base: $kustomize_base"
    fi

    # Check overlay versions (allow prefixes)
    ((TOTAL_CHECKS++))
    if [[ "$kustomize_prod" == "v$pyproject_version" ]]; then
        print_success "Production overlay version correct: $kustomize_prod"
    else
        print_error "Production overlay version mismatch: expected v$pyproject_version, got $kustomize_prod"
    fi

    ((TOTAL_CHECKS++))
    if [[ "$kustomize_staging" == "staging-$pyproject_version" ]]; then
        print_success "Staging overlay version correct: $kustomize_staging"
    else
        print_error "Staging overlay version mismatch: expected staging-$pyproject_version, got $kustomize_staging"
    fi
}

# ==============================================================================
# File Existence Checks
# ==============================================================================

check_required_files() {
    print_header "Required Files"

    local required_files=(
        "pyproject.toml"
        "Makefile"
        "docker-compose.yml"
        "docker/docker-compose.yml"
        "docker/docker-compose.dev.yml"
        "docker/docker-compose.test.yml"
        "docker/Dockerfile"
        "docker/prometheus.yml"
        "docker/grafana-datasources.yml"
        "deployments/helm/mcp-server-langgraph/Chart.yaml"
        "deployments/helm/mcp-server-langgraph/values.yaml"
        "deployments/kustomize/base/kustomization.yaml"
        "deployments/kustomize/overlays/dev/kustomization.yaml"
        "deployments/kustomize/overlays/staging/kustomization.yaml"
        "deployments/kustomize/overlays/production/kustomization.yaml"
    )

    for file in "${required_files[@]}"; do
        ((TOTAL_CHECKS++))
        if [[ -f "$PROJECT_ROOT/$file" ]] || [[ -L "$PROJECT_ROOT/$file" ]]; then
            print_success "$file exists"
        else
            print_error "$file is missing"
        fi
    done
}

# ==============================================================================
# Symlink Checks
# ==============================================================================

check_symlinks() {
    print_header "Symlinks"

    ((TOTAL_CHECKS++))
    if [[ -L "$PROJECT_ROOT/docker-compose.yml" ]]; then
        local target
        target=$(readlink "$PROJECT_ROOT/docker-compose.yml")
        if [[ -f "$PROJECT_ROOT/$target" ]]; then
            print_success "docker-compose.yml symlink is valid → $target"
        else
            print_error "docker-compose.yml symlink is broken → $target (target doesn't exist)"
        fi
    else
        print_warning "docker-compose.yml is not a symlink"
    fi
}

# ==============================================================================
# Docker Compose Validation
# ==============================================================================

check_docker_compose() {
    print_header "Docker Compose"

    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found, skipping Docker Compose validation"
        return 0
    fi

    local compose_files=(
        "docker/docker-compose.yml"
        "docker/docker-compose.dev.yml"
        "docker/docker-compose.test.yml"
    )

    for compose_file in "${compose_files[@]}"; do
        ((TOTAL_CHECKS++))
        if [[ -f "$PROJECT_ROOT/$compose_file" ]]; then
            if docker compose -f "$PROJECT_ROOT/$compose_file" config --quiet 2>/dev/null; then
                print_success "$(basename "$compose_file") syntax is valid"
            else
                print_error "$(basename "$compose_file") syntax is invalid"
                if [[ "$VERBOSE" == "true" ]]; then
                    docker compose -f "$PROJECT_ROOT/$compose_file" config 2>&1 | sed 's/^/    /'
                fi
            fi
        fi
    done
}

# ==============================================================================
# Helm Validation
# ==============================================================================

check_helm() {
    print_header "Helm Charts"

    if ! command -v helm &> /dev/null; then
        print_warning "Helm not found, skipping Helm validation"
        return 0
    fi

    local chart_dir="$PROJECT_ROOT/deployments/helm/mcp-server-langgraph"

    ((TOTAL_CHECKS++))
    if helm lint "$chart_dir" &> /dev/null; then
        print_success "Helm chart lint passed"
    else
        print_error "Helm chart lint failed"
        if [[ "$VERBOSE" == "true" ]]; then
            helm lint "$chart_dir" 2>&1 | sed 's/^/    /'
        fi
    fi

    ((TOTAL_CHECKS++))
    if helm template test-release "$chart_dir" --dry-run > /dev/null 2>&1; then
        print_success "Helm template rendering successful"
    else
        print_error "Helm template rendering failed"
        if [[ "$VERBOSE" == "true" ]]; then
            helm template test-release "$chart_dir" --dry-run 2>&1 | sed 's/^/    /'
        fi
    fi
}

# ==============================================================================
# Kustomize Validation
# ==============================================================================

check_kustomize() {
    print_header "Kustomize Overlays"

    if ! command -v kubectl &> /dev/null; then
        print_warning "kubectl not found, skipping Kustomize validation"
        return 0
    fi

    local overlays=("dev" "staging" "production")

    for overlay in "${overlays[@]}"; do
        ((TOTAL_CHECKS++))
        local overlay_path="$PROJECT_ROOT/deployments/kustomize/overlays/$overlay"
        if kubectl kustomize "$overlay_path" > /dev/null 2>&1; then
            print_success "Kustomize $overlay overlay is valid"
        else
            print_error "Kustomize $overlay overlay is invalid"
            if [[ "$VERBOSE" == "true" ]]; then
                kubectl kustomize "$overlay_path" 2>&1 | sed 's/^/    /'
            fi
        fi
    done
}

# ==============================================================================
# Makefile Validation
# ==============================================================================

check_makefile() {
    print_header "Makefile"

    if ! command -v make &> /dev/null; then
        print_warning "Make not found, skipping Makefile validation"
        return 0
    fi

    ((TOTAL_CHECKS++))
    if make -n help > /dev/null 2>&1; then
        print_success "Makefile syntax is valid"
    else
        print_error "Makefile syntax is invalid"
        if [[ "$VERBOSE" == "true" ]]; then
            make -n help 2>&1 | sed 's/^/    /'
        fi
    fi

    # Check key targets exist
    local key_targets=("setup-infra" "test" "validate-all" "clean")
    for target in "${key_targets[@]}"; do
        ((TOTAL_CHECKS++))
        if make -n "$target" > /dev/null 2>&1; then
            print_success "Makefile target '$target' exists"
        else
            print_error "Makefile target '$target' is missing or invalid"
        fi
    done
}

# ==============================================================================
# Main Logic
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--verbose]"
                exit 1
                ;;
        esac
    done

    print_header "Infrastructure Validation"
    echo "Project: $PROJECT_ROOT"
    echo ""

    # Run all checks
    check_version_consistency
    check_required_files
    check_symlinks
    check_docker_compose
    check_helm
    check_kustomize
    check_makefile

    # Summary
    print_header "Validation Summary"

    local passed=$((TOTAL_CHECKS - FAILED_CHECKS))
    echo -e "${GREEN}Passed: $passed${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo -e "Total:  $TOTAL_CHECKS"
    echo ""

    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}✓ All validations passed!${NC}"
        echo ""
        exit 0
    else
        echo -e "${RED}✗ $FAILED_CHECKS validation(s) failed${NC}"
        echo ""
        echo "Run with --verbose for detailed error messages:"
        echo "  ./scripts/validate-infrastructure.sh --verbose"
        echo ""
        exit 1
    fi
}

# Run main function
cd "$PROJECT_ROOT"
main "$@"
