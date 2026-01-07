#!/usr/bin/env bash
# sync-mimir-rules.sh - Sync Prometheus/Mimir alerting rules to docker/mimir/rules/
#
# This script ensures all canonical alert rules from monitoring/prometheus/rules/
# are synced to docker/mimir/rules/ for the test environment.
#
# Usage:
#   ./scripts/sync-mimir-rules.sh [OPTIONS]
#
# Options:
#   --check     Exit with error if rules are out of sync (for CI)
#   --dry-run   Show what would be synced without making changes
#   --verbose   Show detailed output
#   --help      Show this help message
#
# The sync adds a 'namespace' field for Mimir ruler compatibility and converts
# .yml extensions to .yaml for consistency.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Directories
CANONICAL_DIR="${PROJECT_ROOT}/monitoring/prometheus/rules"
MIMIR_DIR="${PROJECT_ROOT}/docker/mimir/rules"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Options
CHECK_MODE=false
DRY_RUN=false
VERBOSE=false

# Counters (initialize to 1 to avoid (( )) returning 1 on increment from 0)
SYNCED=0
SKIPPED=0
MISSING=0
OUT_OF_SYNC=0

# Helper to safely increment counters (avoids exit 1 from (( )) when result is 0)
inc() {
    eval "$1=\$(( $1 + 1 ))"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Sync Prometheus/Mimir alerting rules to docker/mimir/rules/ for test environment.

Options:
  --check     Exit with error if rules are out of sync (for CI)
  --dry-run   Show what would be synced without making changes
  --verbose   Show detailed output
  --help      Show this help message

Examples:
  $(basename "$0")              # Sync all rules
  $(basename "$0") --check      # Check if rules are in sync (CI mode)
  $(basename "$0") --dry-run    # Preview changes without syncing
EOF
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*"
    fi
}

# Get namespace from filename (e.g., streaming-sla-alerts -> streaming-sla)
get_namespace() {
    local filename="$1"
    # Remove extension and -alerts/-rules suffix
    echo "$filename" | sed -E 's/\.(yaml|yml)$//' | sed -E 's/-(alerts|rules)$//'
}

# Check if file is a Kubernetes CRD (should be skipped)
is_k8s_crd() {
    local file="$1"
    grep -q "apiVersion:.*monitoring.coreos.com" "$file" 2>/dev/null
}

# Check if file already has namespace field
has_namespace() {
    local file="$1"
    grep -q "^namespace:" "$file" 2>/dev/null
}

# Convert canonical rule file to Mimir format
convert_to_mimir_format() {
    local source_file="$1"
    local dest_file="$2"
    local namespace="$3"

    # Read source content
    local content
    content=$(cat "$source_file")

    # Check if content starts with 'groups:'
    if [[ "$content" == groups:* ]]; then
        # Add namespace header
        cat > "$dest_file" << EOF
# Synced from: ${source_file#$PROJECT_ROOT/}
# Namespace for Mimir ruler compatibility
namespace: ${namespace}

${content}
EOF
    else
        # File might already have namespace or different format, copy as-is
        cp "$source_file" "$dest_file"
    fi
}

# Compare rule files (ignoring comments and namespace header)
files_match() {
    local file1="$1"
    local file2="$2"

    # Extract just the groups section for comparison
    local groups1 groups2
    groups1=$(grep -A 10000 "^groups:" "$file1" 2>/dev/null | head -n -1 || echo "")
    groups2=$(grep -A 10000 "^groups:" "$file2" 2>/dev/null | head -n -1 || echo "")

    # Return 0 if match, 1 if different
    if [[ "$groups1" == "$groups2" ]]; then
        return 0
    else
        return 1
    fi
}

# Main sync function
sync_rules() {
    log_info "Syncing Mimir rules from ${CANONICAL_DIR} to ${MIMIR_DIR}"

    # Ensure destination directory exists
    if [[ ! -d "$MIMIR_DIR" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY-RUN: Would create directory $MIMIR_DIR"
        else
            mkdir -p "$MIMIR_DIR"
            log_info "Created directory $MIMIR_DIR"
        fi
    fi

    # Process each rule file
    for source_file in "$CANONICAL_DIR"/*.y*ml; do
        [[ -f "$source_file" ]] || continue

        local filename
        filename=$(basename "$source_file")

        # Skip Kubernetes CRD files
        if is_k8s_crd "$source_file"; then
            log_verbose "Skipping K8s CRD: $filename"
            inc SKIPPED
            continue
        fi

        # Normalize extension to .yaml (remove .yml or .yaml first, then add .yaml)
        local base_name="${filename%.yml}"
        base_name="${base_name%.yaml}"
        local dest_filename="${base_name}.yaml"
        local dest_file="${MIMIR_DIR}/${dest_filename}"

        # Get namespace from filename
        local namespace
        namespace=$(get_namespace "$filename")

        # Check if destination exists
        if [[ -f "$dest_file" ]]; then
            # Check if files match
            if files_match "$source_file" "$dest_file"; then
                log_verbose "In sync: $filename"
                inc SKIPPED
            else
                inc OUT_OF_SYNC
                if [[ "$CHECK_MODE" == "true" ]]; then
                    log_error "OUT OF SYNC: $filename"
                elif [[ "$DRY_RUN" == "true" ]]; then
                    log_warning "DRY-RUN: Would update $dest_filename"
                else
                    log_info "Updating: $dest_filename"
                    convert_to_mimir_format "$source_file" "$dest_file" "$namespace"
                    inc SYNCED
                fi
            fi
        else
            inc MISSING
            if [[ "$CHECK_MODE" == "true" ]]; then
                log_error "MISSING: $dest_filename"
            elif [[ "$DRY_RUN" == "true" ]]; then
                log_warning "DRY-RUN: Would create $dest_filename"
            else
                log_info "Creating: $dest_filename"
                convert_to_mimir_format "$source_file" "$dest_file" "$namespace"
                inc SYNCED
            fi
        fi
    done
}

# Print summary
print_summary() {
    echo ""
    echo "=========================================="
    echo "Sync Summary"
    echo "=========================================="
    echo "Synced:      $SYNCED"
    echo "Skipped:     $SKIPPED (already in sync or K8s CRD)"
    echo "Missing:     $MISSING"
    echo "Out of sync: $OUT_OF_SYNC"
    echo "=========================================="

    if [[ "$CHECK_MODE" == "true" ]]; then
        if [[ $MISSING -gt 0 || $OUT_OF_SYNC -gt 0 ]]; then
            echo ""
            log_error "Rules are out of sync! Run: ./scripts/sync-mimir-rules.sh"
            return 1
        else
            echo ""
            log_success "All rules are in sync"
            return 0
        fi
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        log_info "DRY-RUN complete. No changes were made."
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)
            CHECK_MODE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
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

# Check if source directory exists
if [[ ! -d "$CANONICAL_DIR" ]]; then
    log_error "Canonical rules directory not found: $CANONICAL_DIR"
    exit 1
fi

# Run sync
sync_rules
print_summary
