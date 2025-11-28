#!/bin/bash
#
# Helm Template Security Scanner
#
# This script extracts Helm charts (including subcharts) and scans them with Trivy.
# It addresses the gap where locally-stored .tgz subcharts aren't scanned by default.
#
# Usage: ./scripts/security/scan_helm_templates.sh [--severity LEVEL] [--exit-on-error]
#
# Options:
#   --severity LEVEL    Comma-separated list of severities to scan (default: CRITICAL,HIGH)
#   --exit-on-error     Exit with code 1 if any findings (default: warning only)
#   --help              Show this help message
#
# Prerequisites:
#   - helm (https://helm.sh/docs/intro/install/)
#   - trivy (https://aquasecurity.github.io/trivy/latest/getting-started/installation/)
#
# Example:
#   ./scripts/security/scan_helm_templates.sh --severity CRITICAL --exit-on-error
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HELM_CHART_DIR="${PROJECT_ROOT}/deployments/helm/mcp-server-langgraph"
TRIVYIGNORE_FILE="${HELM_CHART_DIR}/.trivyignore"

# Default values
SEVERITY="${SEVERITY:-CRITICAL,HIGH}"
EXIT_ON_ERROR="${EXIT_ON_ERROR:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    head -27 "$0" | tail -25
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --severity)
            SEVERITY="$2"
            shift 2
            ;;
        --exit-on-error)
            EXIT_ON_ERROR="true"
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Check prerequisites
check_prerequisites() {
    local missing_tools=()

    if ! command -v helm &> /dev/null; then
        missing_tools+=("helm")
    fi

    if ! command -v trivy &> /dev/null; then
        missing_tools+=("trivy")
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Install instructions:"
        for tool in "${missing_tools[@]}"; do
            case $tool in
                helm)
                    log_info "  helm: brew install helm (or see https://helm.sh/docs/intro/install/)"
                    ;;
                trivy)
                    log_info "  trivy: brew install trivy (or see https://aquasecurity.github.io/trivy/)"
                    ;;
            esac
        done

        # In non-strict mode, warn and exit successfully
        if [[ "${EXIT_ON_ERROR}" != "true" ]]; then
            log_warning "Skipping Helm security scan (tools not installed)"
            exit 0
        fi
        exit 1
    fi
}

# Main function
main() {
    log_info "Helm Template Security Scanner"
    log_info "=============================="

    # Check prerequisites
    check_prerequisites

    # Verify Helm chart exists
    if [[ ! -d "${HELM_CHART_DIR}" ]]; then
        log_error "Helm chart directory not found: ${HELM_CHART_DIR}"
        exit 1
    fi

    # Create temporary directory for templated output
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "${TEMP_DIR}"' EXIT

    log_info "Helm chart: ${HELM_CHART_DIR}"
    log_info "Temp directory: ${TEMP_DIR}"
    log_info "Severity filter: ${SEVERITY}"

    # Update Helm dependencies (extracts .tgz subcharts)
    log_info "Updating Helm dependencies..."
    # Capture output but don't fail - dependencies may already be up-to-date
    helm dependency update "${HELM_CHART_DIR}" 2>&1 | grep -E "(Successfully|Saving|Downloading|Error|error)" || true

    # Build dependencies
    log_info "Building Helm dependencies..."
    # Capture output but don't fail - dependencies may already be built
    helm dependency build "${HELM_CHART_DIR}" 2>&1 | grep -E "(Successfully|Saving|Downloading|Error|error)" || true

    # Template the chart (renders all templates including subcharts)
    log_info "Templating Helm chart (including subcharts)..."
    # Note: --generate-name is not compatible with positional release name
    local template_output
    if ! template_output=$(helm template mcp-server-langgraph "${HELM_CHART_DIR}" \
        --output-dir "${TEMP_DIR}" \
        --include-crds 2>&1); then
        log_error "Failed to template Helm chart:"
        echo "${template_output}" | head -20
        exit 1
    fi

    # Count generated files
    FILE_COUNT=$(find "${TEMP_DIR}" -name "*.yaml" | wc -l | tr -d ' ')
    log_info "Generated ${FILE_COUNT} templated YAML files"

    # Build Trivy arguments
    TRIVY_ARGS=(
        config
        "${TEMP_DIR}"
        --severity "${SEVERITY}"
        --format table
    )

    # Add ignorefile if exists
    if [[ -f "${TRIVYIGNORE_FILE}" ]]; then
        TRIVY_ARGS+=(--ignorefile "${TRIVYIGNORE_FILE}")
        log_info "Using ignorefile: ${TRIVYIGNORE_FILE}"
    fi

    # Set exit code behavior
    if [[ "${EXIT_ON_ERROR}" == "true" ]]; then
        TRIVY_ARGS+=(--exit-code 1)
    else
        TRIVY_ARGS+=(--exit-code 0)
    fi

    # Run Trivy scan
    log_info "Running Trivy security scan..."
    echo ""

    if trivy "${TRIVY_ARGS[@]}"; then
        log_success "Security scan completed successfully"
        if [[ "${EXIT_ON_ERROR}" != "true" ]]; then
            log_info "Note: Findings were found but --exit-on-error was not set"
        fi
    else
        log_error "Security scan found issues at ${SEVERITY} severity"
        exit 1
    fi

    # Summary
    echo ""
    log_info "Summary:"
    log_info "  - Chart: ${HELM_CHART_DIR}"
    log_info "  - Files scanned: ${FILE_COUNT}"
    log_info "  - Severity filter: ${SEVERITY}"
    log_info "  - Ignorefile: ${TRIVYIGNORE_FILE}"
}

# Run main function
main "$@"
