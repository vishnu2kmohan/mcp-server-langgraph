#!/bin/bash
# =============================================================================
# Test File Size Checker
# =============================================================================
#
# This script checks for test files exceeding the maximum line count to prevent
# OOM issues in Vitest. Large monolithic test files cause excessive memory usage
# due to fixture accumulation and limited worker restart opportunities.
#
# Usage:
#   ./scripts/check-test-file-size.sh [command] [options]
#
# Commands:
#   check     - Check for oversized test files (CI-friendly, default)
#   report    - Generate detailed report of test file sizes
#   list      - List all test files sorted by size
#
# Options:
#   --max-lines N     Maximum allowed lines (default: 1000)
#   --warn-lines N    Warning threshold (default: 800)
#   --fix-suggestions Show suggestions for files over the limit
#
# Exit Codes:
#   0 - All test files within limits
#   1 - One or more test files exceed the limit
#
# Reference: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"

# Default thresholds (based on TESTING_OOM_PREVENTION.md)
MAX_LINES=${MAX_LINES:-1000}
WARN_LINES=${WARN_LINES:-800}
SHOW_SUGGESTIONS=false

# Pre-existing large files that are tracked for future sharding
# These files exceeded the limit before this check was added
# TODO: Shard these files and remove from exception list
KNOWN_LARGE_FILES=(
    "src/conversation/ConnectedChatInputForm.test.tsx"  # 1096 lines - needs sharding
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
# shellcheck disable=SC2034  # BOLD kept for color palette completeness
BOLD='\033[1m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

# =============================================================================
# File Size Analysis
# =============================================================================

get_test_files() {
    find "$SRC_DIR" \
        \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) \
        -not -path "*/node_modules/*" \
        -type f
}

count_lines() {
    wc -l < "$1" | tr -d ' '
}

is_known_large_file() {
    local file_path="$1"
    local relative_path="${file_path#$PROJECT_DIR/}"
    for known_file in "${KNOWN_LARGE_FILES[@]}"; do
        if [ "$relative_path" = "$known_file" ]; then
            return 0
        fi
    done
    return 1
}

# =============================================================================
# Check Command (CI-friendly)
# =============================================================================

check_sizes() {
    local violations=0
    local warnings=0
    local files_checked=0

    while IFS= read -r file; do
        lines=$(count_lines "$file")
        ((files_checked++))

        # Skip known large files (pre-existing issues tracked for future fix)
        if is_known_large_file "$file"; then
            relative_path="${file#$PROJECT_DIR/}"
            print_info "$relative_path: $lines lines (known large file - tracked for sharding)"
            continue
        fi

        if [ "$lines" -gt "$MAX_LINES" ]; then
            ((violations++))
            relative_path="${file#$PROJECT_DIR/}"
            print_error "$relative_path: $lines lines (max: $MAX_LINES)"

            if [ "$SHOW_SUGGESTIONS" = true ]; then
                suggest_split "$file" "$lines"
            fi
        elif [ "$lines" -gt "$WARN_LINES" ]; then
            ((warnings++))
            relative_path="${file#$PROJECT_DIR/}"
            print_warning "$relative_path: $lines lines (warning threshold: $WARN_LINES)"
        fi
    done < <(get_test_files)

    echo ""
    print_info "Checked $files_checked test files (max: $MAX_LINES lines, warn: $WARN_LINES lines)"

    if [ "$violations" -gt 0 ]; then
        echo ""
        print_error "Found $violations test file(s) exceeding the $MAX_LINES line limit"
        echo ""
        echo "To fix: Split these files into smaller shards."
        echo "See: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md"
        echo ""
        echo "Sharding strategy:"
        echo "  1. Create a shared fixtures file: Component.fixtures.ts"
        echo "  2. Split tests by concern: Component.feature1.test.ts, Component.feature2.test.ts"
        echo "  3. Target 400-800 lines per shard"
        exit 1
    elif [ "$warnings" -gt 0 ]; then
        print_warning "Found $warnings test file(s) approaching the limit"
        print_success "No files exceed the $MAX_LINES line limit"
        exit 0
    else
        print_success "All test files are within the $MAX_LINES line limit"
        exit 0
    fi
}

# =============================================================================
# Report Command
# =============================================================================

generate_report() {
    print_header "Test File Size Report"

    echo "Generated: $(date)"
    echo "Project: mcp-server-langgraph/studio/frontend"
    echo "Thresholds: max=$MAX_LINES, warn=$WARN_LINES"
    echo ""

    local total_files=0
    local total_lines=0
    local over_max=0
    local over_warn=0
    # shellcheck disable=SC2034  # Kept for future report expansion
    local under_warn=0

    # Categorize files
    print_header "Files Exceeding Limit (>$MAX_LINES lines)"

    local has_violations=false
    while IFS= read -r file; do
        lines=$(count_lines "$file")
        ((total_files++))
        ((total_lines+=lines))

        if [ "$lines" -gt "$MAX_LINES" ]; then
            has_violations=true
            ((over_max++))
            relative_path="${file#$PROJECT_DIR/}"
            printf "${RED}  %5d  %s${NC}\n" "$lines" "$relative_path"
        fi
    done < <(get_test_files)

    if [ "$has_violations" = false ]; then
        print_success "None"
    fi

    print_header "Files Approaching Limit ($WARN_LINES-$MAX_LINES lines)"

    local has_warnings=false
    while IFS= read -r file; do
        lines=$(count_lines "$file")
        if [ "$lines" -gt "$WARN_LINES" ] && [ "$lines" -le "$MAX_LINES" ]; then
            has_warnings=true
            ((over_warn++))
            relative_path="${file#$PROJECT_DIR/}"
            printf "${YELLOW}  %5d  %s${NC}\n" "$lines" "$relative_path"
        fi
    done < <(get_test_files)

    if [ "$has_warnings" = false ]; then
        print_success "None"
    fi

    print_header "Summary"

    echo "Total test files: $total_files"
    echo "Total lines: $total_lines"
    echo "Average lines per file: $((total_lines / total_files))"
    echo ""
    echo "Distribution:"
    printf "  ${RED}Over limit (>%d):     %d files${NC}\n" "$MAX_LINES" "$over_max"
    printf "  ${YELLOW}Warning (%d-%d):     %d files${NC}\n" "$WARN_LINES" "$MAX_LINES" "$over_warn"
    printf "  ${GREEN}OK (<%d):            %d files${NC}\n" "$WARN_LINES" "$((total_files - over_max - over_warn))"

    if [ "$over_max" -gt 0 ]; then
        echo ""
        print_error "Action required: Split $over_max oversized test file(s)"
        echo "See: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md"
    fi
}

# =============================================================================
# List Command
# =============================================================================

list_files() {
    print_header "Test Files by Size (descending)"

    local count=0
    while IFS= read -r line; do
        lines=$(echo "$line" | awk '{print $1}')
        file=$(echo "$line" | awk '{print $2}')
        relative_path="${file#$PROJECT_DIR/}"
        ((count++))

        if [ "$lines" -gt "$MAX_LINES" ]; then
            printf "${RED}%4d. %5d  %s${NC}\n" "$count" "$lines" "$relative_path"
        elif [ "$lines" -gt "$WARN_LINES" ]; then
            printf "${YELLOW}%4d. %5d  %s${NC}\n" "$count" "$lines" "$relative_path"
        else
            printf "%4d. %5d  %s\n" "$count" "$lines" "$relative_path"
        fi
    done < <(get_test_files | xargs wc -l 2>/dev/null | sort -rn | grep -v "total$" | head -50)

    echo ""
    print_info "Showing top 50 files. Legend: ${RED}Over limit${NC}, ${YELLOW}Warning${NC}"
}

# =============================================================================
# Split Suggestions
# =============================================================================

suggest_split() {
    local file="$1"
    local lines="$2"
    local target_shards=$((lines / 600 + 1))
    local base_name
    base_name=$(basename "$file" | sed 's/\.test\.\(ts\|tsx\)$//')
    local dir_name
    dir_name=$(dirname "$file")

    echo ""
    echo "  Suggested split for $base_name:"
    echo "    Current: $lines lines"
    echo "    Target:  $target_shards shards of ~$((lines / target_shards)) lines each"
    echo ""
    echo "    Steps:"
    echo "      1. Create: $dir_name/__tests__/${base_name}.fixtures.ts"
    echo "      2. Split into:"
    for i in $(seq 1 "$target_shards"); do
        echo "         - ${base_name}.part${i}.test.ts"
    done
    echo "      3. Move shared mocks to fixtures file"
    echo "      4. Delete original after verifying tests pass"
}

# =============================================================================
# Main
# =============================================================================

# Parse arguments
COMMAND="check"
while [[ $# -gt 0 ]]; do
    case $1 in
        check|report|list)
            COMMAND="$1"
            shift
            ;;
        --max-lines)
            MAX_LINES="$2"
            shift 2
            ;;
        --warn-lines)
            WARN_LINES="$2"
            shift 2
            ;;
        --fix-suggestions)
            SHOW_SUGGESTIONS=true
            shift
            ;;
        -h|--help)
            head -40 "$0" | tail -35
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage"
            exit 1
            ;;
    esac
done

case "$COMMAND" in
    check)
        check_sizes
        ;;
    report)
        generate_report
        ;;
    list)
        list_files
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run '$0 --help' for usage"
        exit 1
        ;;
esac
