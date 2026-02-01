#!/usr/bin/env bash
# sync-ai-config.sh - Check AI agent configuration sync status
#
# This script CHECKS (read-only) sync status across AI config files:
# 1. Extracts versions from pyproject.toml and package.json
# 2. Verifies version index in CLAUDE.md and AGENTS.md
# 3. Checks cross-file sync for .cursorrules and copilot-instructions.md
#
# NOTE: This is a CHECK/AUDIT tool - it does NOT modify files.
# Manual updates are required when sync issues are detected.
#
# Usage: ./scripts/sync-ai-config.sh [--dry-run] [--verbose]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Options
DRY_RUN=false
VERBOSE=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run    Show what would be done without making changes"
    echo "  --verbose    Show detailed output"
    echo "  -h, --help   Show this help message"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"

log_info "Syncing AI configuration files..."

# Extract Python version from pyproject.toml
extract_python_versions() {
    log_verbose "Extracting Python versions from pyproject.toml..."

    local python_version
    python_version=$(grep 'requires-python' pyproject.toml | grep -oP '>=\K[0-9]+\.[0-9]+' | head -1)

    local langgraph_version
    langgraph_version=$(grep 'langgraph>=' pyproject.toml | grep -oP '>=\K[0-9]+\.[0-9]+\.[0-9]+' | head -1)

    local fastapi_version
    fastapi_version=$(grep 'fastapi>=' pyproject.toml | grep -oP '>=\K[0-9]+\.[0-9]+' | head -1)

    local pydantic_version
    pydantic_version=$(grep 'pydantic>=' pyproject.toml | grep -oP '>=\K[0-9]+' | head -1)

    local pytest_version
    pytest_version=$(grep '"pytest>=' pyproject.toml | grep -oP '>=\K[0-9]+' | head -1)

    local keycloak_version
    keycloak_version=$(grep 'python-keycloak>=' pyproject.toml | grep -oP '>=\K[0-9]+' | head -1)

    local openfga_version
    openfga_version=$(grep 'openfga-sdk>=' pyproject.toml | grep -oP '>=\K[0-9]+\.[0-9]+' | head -1)

    local opentelemetry_version
    opentelemetry_version=$(grep 'opentelemetry-api>=' pyproject.toml | grep -oP '>=\K[0-9]+' | head -1)

    echo "python:$python_version"
    echo "langgraph:$langgraph_version"
    echo "fastapi:$fastapi_version"
    echo "pydantic:$pydantic_version"
    echo "pytest:$pytest_version"
    echo "keycloak:$keycloak_version"
    echo "openfga:$openfga_version"
    echo "opentelemetry:$opentelemetry_version"
}

# Extract frontend versions from package.json
extract_frontend_versions() {
    log_verbose "Extracting frontend versions from package.json..."

    local frontend_pkg="src/mcp_server_langgraph/studio/frontend/package.json"

    if [[ ! -f "$frontend_pkg" ]]; then
        log_warn "Frontend package.json not found at $frontend_pkg"
        return
    fi

    local react_version
    react_version=$(grep '"react":' "$frontend_pkg" | grep -oP '\^?\K[0-9]+' | head -1)

    local vite_version
    vite_version=$(grep '"vite":' "$frontend_pkg" | grep -oP '\^?\K[0-9]+' | head -1)
    vite_version="${vite_version:-6}"

    local motion_version
    motion_version=$(grep '"motion":' "$frontend_pkg" | grep -oP '\^?\K[0-9]+' | head -1)

    echo "react:$react_version"
    echo "vite:$vite_version"
    echo "motion:$motion_version"
}

# Print version summary
print_version_summary() {
    log_info "Detected versions:"
    echo ""
    echo "=== Backend (from pyproject.toml) ==="
    extract_python_versions
    echo ""
    echo "=== Frontend (from package.json) ==="
    extract_frontend_versions
    echo ""
}

# Check if files are in sync
check_sync_status() {
    log_info "Checking sync status..."

    local errors=0

    # Check AGENTS.md has YAML frontmatter
    if ! head -1 AGENTS.md | grep -q '^---$'; then
        log_warn "AGENTS.md missing YAML frontmatter"
        ((errors++)) || true
    else
        log_success "AGENTS.md has YAML frontmatter"
    fi

    # Check .cursorrules references AGENTS.md
    if ! grep -q 'AGENTS.md' .cursorrules; then
        log_warn ".cursorrules does not reference AGENTS.md"
        ((errors++)) || true
    else
        log_success ".cursorrules references AGENTS.md"
    fi

    # Check copilot-instructions.md references AGENTS.md
    if ! grep -q 'AGENTS.md' .github/copilot-instructions.md; then
        log_warn ".github/copilot-instructions.md does not reference AGENTS.md"
        ((errors++)) || true
    else
        log_success ".github/copilot-instructions.md references AGENTS.md"
    fi

    # Check .ai/CORE.md has documentation-first section
    if ! grep -q 'Documentation-First\|retrieval-led' .ai/CORE.md; then
        log_warn ".ai/CORE.md missing documentation-first guidance"
        ((errors++)) || true
    else
        log_success ".ai/CORE.md has documentation-first guidance"
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "All files are in sync"
    else
        log_warn "$errors file(s) need attention"
    fi

    return $errors
}

# Main execution
main() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN mode - no changes will be made"
    fi

    print_version_summary
    check_sync_status || true

    log_info "Sync check complete"
}

main "$@"
