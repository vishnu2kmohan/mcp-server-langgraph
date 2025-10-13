#!/bin/bash
#
# Deployment Configuration Validation Script
# Validates all deployment configurations for consistency
#
# Usage: ./scripts/validate-deployments.sh [--verbose]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VERBOSE=false
ERRORS=0
WARNINGS=0
INFO=0

# Parse arguments
if [[ "$1" == "--verbose" ]]; then
    VERBOSE=true
fi

# Logging functions
log_error() {
    echo -e "${RED}❌ ERROR:${NC} $1"
    ((ERRORS++))
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
    ((WARNINGS++))
}

log_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
    ((INFO++))
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Extract version from file
extract_version() {
    local file=$1
    local pattern=$2
    grep -oP "$pattern" "$file" 2>/dev/null | head -1 || echo ""
}

# Main validation
main() {
    log_section "🔍 Deployment Configuration Validation"
    echo "Started at: $(date)"
    echo ""

    # Check prerequisites
    log_section "📋 Checking Prerequisites"

    if ! command_exists docker; then
        log_warning "Docker not found - skipping Docker Compose validation"
    else
        log_success "Docker found: $(docker --version)"
    fi

    if ! command_exists kubectl; then
        log_warning "kubectl not found - skipping Kubernetes validation"
    else
        log_success "kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    fi

    if ! command_exists helm; then
        log_warning "Helm not found - skipping Helm validation"
    else
        log_success "Helm found: $(helm version --short)"
    fi

    # Validate Python version consistency
    log_section "🐍 Python Version Consistency"

    EXPECTED_PYTHON="3.12"

    # Check Dockerfile
    if [[ -f "Dockerfile" ]]; then
        DOCKERFILE_PYTHON=$(grep -oP 'FROM python:\K[0-9.]+' Dockerfile | head -1 | cut -d'-' -f1)
        if [[ "$DOCKERFILE_PYTHON" == "$EXPECTED_PYTHON" ]]; then
            log_success "Dockerfile uses Python $DOCKERFILE_PYTHON"
        else
            log_error "Dockerfile uses Python $DOCKERFILE_PYTHON, expected $EXPECTED_PYTHON"
        fi
    fi

    # Check GitLab CI
    if [[ -f ".gitlab-ci.yml" ]]; then
        GITLAB_PYTHON=$(grep -oP 'image: python:\K[0-9.]+' .gitlab-ci.yml | head -1 | cut -d'-' -f1)
        if [[ "$GITLAB_PYTHON" == "$EXPECTED_PYTHON" ]]; then
            log_success "GitLab CI uses Python $GITLAB_PYTHON"
        else
            log_error "GitLab CI uses Python $GITLAB_PYTHON, expected $EXPECTED_PYTHON"
        fi
    fi

    # Check langgraph.json
    if [[ -f "langgraph.json" ]]; then
        LANGGRAPH_PYTHON=$(jq -r '.python_version' langgraph.json 2>/dev/null)
        if [[ "$LANGGRAPH_PYTHON" == "$EXPECTED_PYTHON" ]]; then
            log_success "langgraph.json uses Python $LANGGRAPH_PYTHON"
        else
            log_error "langgraph.json uses Python $LANGGRAPH_PYTHON, expected $EXPECTED_PYTHON"
        fi
    fi

    # Validate application version consistency
    log_section "📦 Application Version Consistency"

    # Get version from pyproject.toml
    if [[ -f "pyproject.toml" ]]; then
        APP_VERSION=$(grep -oP 'version = "\K[^"]+' pyproject.toml | head -1)
        log_info "Source version (pyproject.toml): $APP_VERSION"

        # Check Helm Chart
        if [[ -f "deployments/helm/langgraph-agent/Chart.yaml" ]]; then
            HELM_VERSION=$(grep -oP 'version: \K[0-9.]+' deployments/helm/langgraph-agent/Chart.yaml | head -1)
            HELM_APP_VERSION=$(grep -oP 'appVersion: "\K[^"]+' deployments/helm/langgraph-agent/Chart.yaml | head -1)

            if [[ "$HELM_VERSION" == "$APP_VERSION" ]] && [[ "$HELM_APP_VERSION" == "$APP_VERSION" ]]; then
                log_success "Helm Chart version $HELM_VERSION matches"
            else
                log_error "Helm Chart version $HELM_VERSION (app: $HELM_APP_VERSION), expected $APP_VERSION"
            fi
        fi

        # Check package.json
        if [[ -f "package.json" ]]; then
            PKG_VERSION=$(jq -r '.version' package.json 2>/dev/null)
            if [[ "$PKG_VERSION" == "$APP_VERSION" ]]; then
                log_success "package.json version $PKG_VERSION matches"
            else
                log_error "package.json version $PKG_VERSION, expected $APP_VERSION"
            fi
        fi

        # Check .env.example
        if [[ -f ".env.example" ]]; then
            ENV_VERSION=$(grep -oP 'SERVICE_VERSION=\K[0-9.]+' .env.example | head -1)
            if [[ "$ENV_VERSION" == "$APP_VERSION" ]]; then
                log_success ".env.example version $ENV_VERSION matches"
            else
                log_error ".env.example version $ENV_VERSION, expected $APP_VERSION"
            fi
        fi
    fi

    # Validate Docker Compose
    log_section "🐳 Docker Compose Validation"

    if [[ -f "docker-compose.yml" ]] && command_exists docker; then
        # Check for 'latest' tags
        LATEST_COUNT=$(grep -c 'image:.*:latest' docker-compose.yml || echo 0)
        if [[ $LATEST_COUNT -gt 0 ]]; then
            log_error "Found $LATEST_COUNT 'latest' image tags in docker-compose.yml (should use pinned versions)"
            if [[ "$VERBOSE" == "true" ]]; then
                grep -n 'image:.*:latest' docker-compose.yml
            fi
        else
            log_success "No 'latest' image tags found in docker-compose.yml"
        fi

        # Validate syntax
        if docker compose config --quiet 2>/dev/null; then
            log_success "docker-compose.yml syntax is valid"
        else
            log_error "docker-compose.yml syntax validation failed"
        fi
    fi

    # Validate Kubernetes manifests
    log_section "☸️  Kubernetes Manifest Validation"

    if command_exists kubectl; then
        # Validate base deployment
        if [[ -f "deployments/kubernetes/base/deployment.yaml" ]]; then
            if kubectl apply --dry-run=client -f deployments/kubernetes/base/deployment.yaml >/dev/null 2>&1; then
                log_success "Base deployment manifest is valid"
            else
                log_error "Base deployment manifest validation failed"
            fi
        fi

        # Validate Kustomize overlays
        for env in dev staging production; do
            OVERLAY_DIR="deployments/kustomize/overlays/$env"
            if [[ -d "$OVERLAY_DIR" ]]; then
                if kubectl kustomize "$OVERLAY_DIR" >/dev/null 2>&1; then
                    log_success "Kustomize overlay '$env' is valid"
                else
                    log_error "Kustomize overlay '$env' validation failed"
                fi
            fi
        done
    fi

    # Validate Helm chart
    log_section "⎈  Helm Chart Validation"

    if [[ -d "deployments/helm/langgraph-agent" ]] && command_exists helm; then
        # Lint chart
        if helm lint deployments/helm/langgraph-agent 2>/dev/null; then
            log_success "Helm chart linting passed"
        else
            log_error "Helm chart linting failed"
        fi

        # Dry-run template
        if helm template test deployments/helm/langgraph-agent --dry-run >/dev/null 2>&1; then
            log_success "Helm template rendering succeeded"
        else
            log_error "Helm template rendering failed"
        fi

        # Check for required values
        REQUIRED_VALS=("config.serviceName" "config.llmProvider" "config.modelName" "config.authProvider")
        for val in "${REQUIRED_VALS[@]}"; do
            if grep -q "$val" deployments/helm/langgraph-agent/values.yaml; then
                log_success "Required value '$val' found in values.yaml"
            else
                log_warning "Required value '$val' not found in values.yaml"
            fi
        done
    fi

    # Validate environment variable consistency
    log_section "🔧 Environment Variable Consistency"

    # Check critical env vars across configs
    CRITICAL_VARS=(
        "LLM_PROVIDER"
        "MODEL_NAME"
        "AUTH_PROVIDER"
        "SESSION_BACKEND"
        "OPENFGA_API_URL"
    )

    for var in "${CRITICAL_VARS[@]}"; do
        FOUND_IN_COMPOSE=$(grep -c "$var" docker-compose.yml 2>/dev/null || echo 0)
        FOUND_IN_K8S=$(grep -c "$var" deployments/kubernetes/base/deployment.yaml 2>/dev/null || echo 0)
        FOUND_IN_HELM=$(grep -c "$var" deployments/helm/langgraph-agent/templates/deployment.yaml 2>/dev/null || echo 0)

        if [[ $FOUND_IN_COMPOSE -gt 0 ]] && [[ $FOUND_IN_K8S -gt 0 ]] && [[ $FOUND_IN_HELM -gt 0 ]]; then
            log_success "$var present in all deployment configs"
        elif [[ $FOUND_IN_COMPOSE -eq 0 ]] && [[ $FOUND_IN_K8S -eq 0 ]] && [[ $FOUND_IN_HELM -eq 0 ]]; then
            log_warning "$var not found in any deployment config"
        else
            log_error "$var inconsistent across deployments (compose:$FOUND_IN_COMPOSE, k8s:$FOUND_IN_K8S, helm:$FOUND_IN_HELM)"
        fi
    done

    # Validate health check paths
    log_section "🏥 Health Check Consistency"

    HEALTH_PATHS=("/health" "/health/ready" "/health/startup")
    for path in "${HEALTH_PATHS[@]}"; do
        COMPOSE_COUNT=$(grep -c "$path" docker-compose.yml 2>/dev/null || echo 0)
        K8S_COUNT=$(grep -c "$path" deployments/kubernetes/base/deployment.yaml 2>/dev/null || echo 0)
        HELM_COUNT=$(grep -c "$path" deployments/helm/langgraph-agent/templates/deployment.yaml 2>/dev/null || echo 0)

        if [[ $COMPOSE_COUNT -gt 0 ]] || [[ $K8S_COUNT -gt 0 ]] || [[ $HELM_COUNT -gt 0 ]]; then
            log_success "Health check path '$path' found"
        fi
    done

    # Summary
    log_section "📊 Validation Summary"

    echo "Total checks performed: $((ERRORS + WARNINGS + INFO))"
    echo ""

    if [[ $ERRORS -gt 0 ]]; then
        echo -e "${RED}❌ FAILED: $ERRORS error(s) found${NC}"
    else
        echo -e "${GREEN}✅ PASSED: No errors found${NC}"
    fi

    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found${NC}"
    fi

    echo ""
    echo "Validation completed at: $(date)"
    echo ""

    # Exit code
    if [[ $ERRORS -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"
