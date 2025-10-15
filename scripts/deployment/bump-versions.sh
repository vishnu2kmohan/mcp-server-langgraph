#!/bin/bash
set -euo pipefail

# bump-versions.sh - Update version references in deployment files
#
# Usage:
#   ./scripts/deployment/bump-versions.sh <version>
#   ./scripts/deployment/bump-versions.sh v2.4.0
#   ./scripts/deployment/bump-versions.sh 2.4.0
#
# Environment Variables:
#   DRY_RUN=1 - Show changes without modifying files

VERSION="${1:-}"
DRY_RUN="${DRY_RUN:-0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Validate version format
validate_version() {
    local version="$1"

    # Remove 'v' prefix if present
    version="${version#v}"

    # Validate semantic versioning (X.Y.Z, optionally with -prerelease)
    if ! echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?$'; then
        log_error "Invalid version format: $version"
        log_error "Expected: X.Y.Z or X.Y.Z-prerelease (e.g., 2.4.0 or 2.4.0-beta.1)"
        return 1
    fi

    echo "$version"
}

# Show diff if in dry run mode
show_diff() {
    local file="$1"
    local temp_file="$2"

    if [[ "$DRY_RUN" == "1" ]]; then
        log_info "Changes in $file:"
        diff -u "$file" "$temp_file" || true
        echo ""
    fi
}

# Update file with version
update_file() {
    local file="$1"
    local pattern="$2"
    local replacement="$3"
    local description="$4"

    if [[ ! -f "$file" ]]; then
        log_warning "File not found: $file"
        return 0
    fi

    local temp_file="${file}.tmp"

    # Perform replacement
    sed -E "s|${pattern}|${replacement}|g" "$file" > "$temp_file"

    # Check if file changed
    if ! diff -q "$file" "$temp_file" >/dev/null 2>&1; then
        log_success "Updated: $description"
        show_diff "$file" "$temp_file"

        if [[ "$DRY_RUN" != "1" ]]; then
            mv "$temp_file" "$file"
        else
            rm "$temp_file"
        fi
    else
        log_info "No changes: $description"
        rm "$temp_file"
    fi
}

# Main function
main() {
    cd "$REPO_ROOT"

    # Validate input
    if [[ -z "$VERSION" ]]; then
        log_error "Usage: $0 <version>"
        log_error "Example: $0 v2.4.0"
        exit 1
    fi

    # Validate and normalize version
    VERSION=$(validate_version "$VERSION") || exit 1

    log_info "Bumping versions to: $VERSION"

    if [[ "$DRY_RUN" == "1" ]]; then
        log_warning "DRY RUN MODE - No files will be modified"
        echo ""
    fi

    # Update pyproject.toml
    update_file \
        "pyproject.toml" \
        '^version = "[^"]+"' \
        "version = \"$VERSION\"" \
        "pyproject.toml version"

    # Update Kubernetes deployment
    update_file \
        "deployments/kubernetes/base/deployment.yaml" \
        'image: mcp-server-langgraph:[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?' \
        "image: mcp-server-langgraph:$VERSION" \
        "Kubernetes deployment image tag"

    # Update Helm Chart.yaml (both version and appVersion)
    update_file \
        "deployments/helm/mcp-server-langgraph/Chart.yaml" \
        '^version: [0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?' \
        "version: $VERSION" \
        "Helm chart version"

    update_file \
        "deployments/helm/mcp-server-langgraph/Chart.yaml" \
        '^appVersion: "[^"]+"' \
        "appVersion: \"$VERSION\"" \
        "Helm chart appVersion"

    # Update Helm values.yaml
    update_file \
        "deployments/helm/mcp-server-langgraph/values.yaml" \
        'tag: "[^"]+"' \
        "tag: \"$VERSION\"" \
        "Helm values image tag"

    # Update Kustomize base
    update_file \
        "deployments/kustomize/base/kustomization.yaml" \
        'newTag: [0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?' \
        "newTag: $VERSION" \
        "Kustomize image tag"

    # Update docker-compose.yml (add version comment if not present)
    if grep -q "# Version:" docker-compose.yml; then
        update_file \
            "docker-compose.yml" \
            '# Version: [0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?' \
            "# Version: $VERSION" \
            "docker-compose.yml version comment"
    else
        log_info "Adding version comment to docker-compose.yml"
        if [[ "$DRY_RUN" != "1" ]]; then
            sed -i "1s|^|# Version: $VERSION\n|" docker-compose.yml
            log_success "Added version comment to docker-compose.yml"
        else
            log_info "Would add: # Version: $VERSION"
        fi
    fi

    # Update package.json
    update_file \
        "package.json" \
        '"version": "[^"]+"' \
        "\"version\": \"$VERSION\"" \
        "package.json version"

    # Update config.py service_version
    update_file \
        "src/mcp_server_langgraph/core/config.py" \
        'service_version: str = "[^"]+"' \
        "service_version: str = \"$VERSION\"" \
        "config.py service_version"

    # Update MCP manifest.json
    update_file \
        ".mcp/manifest.json" \
        '"version": "[^"]+"' \
        "\"version\": \"$VERSION\"" \
        "MCP manifest version"

    echo ""

    if [[ "$DRY_RUN" == "1" ]]; then
        log_warning "DRY RUN COMPLETE - Run without DRY_RUN=1 to apply changes"
    else
        log_success "Version bump to $VERSION complete!"
        log_info "Modified files:"
        log_info "  - pyproject.toml"
        log_info "  - package.json"
        log_info "  - src/mcp_server_langgraph/core/config.py"
        log_info "  - .mcp/manifest.json"
        log_info "  - docker-compose.yml"
        log_info "  - deployments/kubernetes/base/deployment.yaml"
        log_info "  - deployments/helm/mcp-server-langgraph/Chart.yaml"
        log_info "  - deployments/helm/mcp-server-langgraph/values.yaml"
        log_info "  - deployments/kustomize/base/kustomization.yaml"
        echo ""
        log_info "Next steps:"
        log_info "  1. Review changes: git diff"
        log_info "  2. Commit changes: git commit -am 'chore: bump version to $VERSION'"
        log_info "  3. Push changes: git push origin main"
    fi
}

main "$@"
