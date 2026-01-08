#!/usr/bin/env bash
# sync-grafana-dashboards.sh
#
# Synchronizes Grafana dashboards from the canonical location to the Helm chart.
#
# Canonical source: monitoring/grafana/dashboards/
# Helm destination: deployments/helm/mcp-server-langgraph/dashboards/
#
# Usage:
#   ./scripts/sync-grafana-dashboards.sh [--dry-run] [--verbose]
#
# Options:
#   --dry-run   Show what would be synced without making changes
#   --verbose   Show detailed output
#   --check     Exit with error if dashboards are out of sync (for CI)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${PROJECT_ROOT}/monitoring/grafana/dashboards"
DEST_DIR="${PROJECT_ROOT}/deployments/helm/mcp-server-langgraph/dashboards"

# Dashboard folders to sync (must match Helm template folder list)
FOLDERS=(AI Application Auth Compliance HEART Infrastructure Operations Overview Resilience WebSocket)

# Options
DRY_RUN=false
VERBOSE=false
CHECK_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --check)
            CHECK_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--verbose] [--check]"
            echo ""
            echo "Synchronizes Grafana dashboards from canonical location to Helm chart."
            echo ""
            echo "Options:"
            echo "  --dry-run   Show what would be synced without making changes"
            echo "  --verbose   Show detailed output"
            echo "  --check     Exit with error if dashboards are out of sync (for CI)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
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

# Validate paths exist
if [[ ! -d "$SOURCE_DIR" ]]; then
    log_error "Source directory not found: $SOURCE_DIR"
    exit 1
fi

if [[ ! -d "$DEST_DIR" ]]; then
    log_error "Destination directory not found: $DEST_DIR"
    exit 1
fi

log_info "Syncing Grafana dashboards"
log_info "Source: $SOURCE_DIR"
log_info "Destination: $DEST_DIR"
echo ""

# Track sync status
SYNCED_COUNT=0
SKIPPED_COUNT=0
OUT_OF_SYNC=0
MISSING_IN_DEST=0

# Sync each folder
for folder in "${FOLDERS[@]}"; do
    src_folder="${SOURCE_DIR}/${folder}"
    dest_folder="${DEST_DIR}/${folder}"

    if [[ ! -d "$src_folder" ]]; then
        log_warning "Source folder not found: $folder"
        continue
    fi

    # Create destination folder if needed
    if [[ ! -d "$dest_folder" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "[DRY-RUN] Would create folder: $folder/"
        else
            mkdir -p "$dest_folder"
            log_verbose "Created folder: $folder/"
        fi
    fi

    # Sync each dashboard in the folder
    for src_file in "${src_folder}"/*.json; do
        if [[ ! -f "$src_file" ]]; then
            continue
        fi

        filename=$(basename "$src_file")
        dest_file="${dest_folder}/${filename}"

        # Check if file exists in destination
        if [[ ! -f "$dest_file" ]]; then
            MISSING_IN_DEST=$((MISSING_IN_DEST + 1))
            if [[ "$DRY_RUN" == "true" || "$CHECK_MODE" == "true" ]]; then
                log_warning "[MISSING] ${folder}/${filename}"
            else
                cp "$src_file" "$dest_file"
                log_success "Copied: ${folder}/${filename}"
                SYNCED_COUNT=$((SYNCED_COUNT + 1))
            fi
            continue
        fi

        # Compare files using md5sum
        src_hash=$(md5sum "$src_file" | cut -d' ' -f1)
        dest_hash=$(md5sum "$dest_file" | cut -d' ' -f1)

        if [[ "$src_hash" != "$dest_hash" ]]; then
            OUT_OF_SYNC=$((OUT_OF_SYNC + 1))
            if [[ "$DRY_RUN" == "true" || "$CHECK_MODE" == "true" ]]; then
                log_warning "[OUT-OF-SYNC] ${folder}/${filename}"
                log_verbose "  Source: $src_hash"
                log_verbose "  Dest:   $dest_hash"
            else
                cp "$src_file" "$dest_file"
                log_success "Updated: ${folder}/${filename}"
                SYNCED_COUNT=$((SYNCED_COUNT + 1))
            fi
        else
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
            log_verbose "In sync: ${folder}/${filename}"
        fi
    done
done

echo ""
log_info "=== Sync Summary ==="

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "  Mode: ${YELLOW}DRY-RUN${NC}"
elif [[ "$CHECK_MODE" == "true" ]]; then
    echo -e "  Mode: ${YELLOW}CHECK${NC}"
fi

echo -e "  In sync: ${GREEN}${SKIPPED_COUNT}${NC} dashboards"

if [[ "$DRY_RUN" == "true" || "$CHECK_MODE" == "true" ]]; then
    echo -e "  Out of sync: ${YELLOW}${OUT_OF_SYNC}${NC} dashboards"
    echo -e "  Missing: ${YELLOW}${MISSING_IN_DEST}${NC} dashboards"
else
    echo -e "  Synced: ${GREEN}${SYNCED_COUNT}${NC} dashboards"
fi

# Exit with error in check mode if out of sync
if [[ "$CHECK_MODE" == "true" ]]; then
    if [[ $OUT_OF_SYNC -gt 0 || $MISSING_IN_DEST -gt 0 ]]; then
        echo ""
        log_error "Dashboards are out of sync! Run: ./scripts/sync-grafana-dashboards.sh"
        exit 1
    else
        log_success "All dashboards are in sync"
    fi
fi

exit 0
