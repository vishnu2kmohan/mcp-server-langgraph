#!/usr/bin/env bash
# cleanup-worktrees.sh
# Manages and cleans up git worktrees created for Claude Code sessions
#
# Usage:
#   ./scripts/cleanup-worktrees.sh [--auto] [--dry-run] [--all]
#
# Options:
#   --auto      Automatically delete clean worktrees without prompting
#   --dry-run   Show what would be deleted without actually deleting
#   --all       Delete all worktrees (even with uncommitted changes) - DANGEROUS!

set -euo pipefail

# Configuration
REPO_NAME="mcp-server-langgraph"
WORKTREES_DIR="../worktrees"

# Flags
AUTO_DELETE=false
DRY_RUN=false
DELETE_ALL=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_dry_run() {
    echo -e "${CYAN}[DRY RUN]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_DELETE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --all)
            DELETE_ALL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--auto] [--dry-run] [--all]"
            echo ""
            echo "Options:"
            echo "  --auto      Automatically delete clean worktrees without prompting"
            echo "  --dry-run   Show what would be deleted without actually deleting"
            echo "  --all       Delete all worktrees (even with changes) - DANGEROUS!"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Verify we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
fi

# Get the repository root
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Check if worktrees directory exists
WORKTREES_PATH="${REPO_ROOT}/${WORKTREES_DIR}"
if [ ! -d "$WORKTREES_PATH" ]; then
    log_info "No worktrees directory found at: $WORKTREES_PATH"
    exit 0
fi

# Print header
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${CYAN}Git Worktree Cleanup${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${CYAN}[DRY RUN MODE - No changes will be made]${NC}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get list of all worktrees
WORKTREES=$(git worktree list --porcelain | grep -E '^worktree ' | cut -d' ' -f2)

# Count worktrees
TOTAL_COUNT=0
CLEAN_COUNT=0
DIRTY_COUNT=0
DELETED_COUNT=0
KEPT_COUNT=0

# Arrays to store worktrees
declare -a CLEAN_WORKTREES
declare -a DIRTY_WORKTREES

# Analyze each worktree
for worktree in $WORKTREES; do
    # Skip the main repository
    if [ "$worktree" = "$REPO_ROOT" ]; then
        continue
    fi

    # Only process worktrees in our managed directory
    if [[ ! "$worktree" =~ ${WORKTREES_DIR}/${REPO_NAME}-session- ]]; then
        continue
    fi

    TOTAL_COUNT=$((TOTAL_COUNT + 1))

    # Get worktree name
    WORKTREE_NAME=$(basename "$worktree")

    # Check if worktree has uncommitted changes
    cd "$worktree"

    # Check for uncommitted changes (staged, unstaged, or untracked files)
    if git diff-index --quiet HEAD -- 2>/dev/null && \
       [ -z "$(git ls-files --others --exclude-standard)" ]; then
        CLEAN_WORKTREES+=("$worktree")
        CLEAN_COUNT=$((CLEAN_COUNT + 1))
        STATUS="${GREEN}CLEAN${NC}"
    else
        DIRTY_WORKTREES+=("$worktree")
        DIRTY_COUNT=$((DIRTY_COUNT + 1))
        STATUS="${YELLOW}DIRTY${NC}"
    fi

    # Get branch and commit info
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

    # Read session metadata if available
    CREATED=""
    if [ -f "$worktree/.claude-worktree-session" ]; then
        CREATED=$(grep '^CREATED_AT=' "$worktree/.claude-worktree-session" | cut -d'=' -f2)
    fi

    # Print worktree info
    echo -e "${BLUE}Worktree:${NC} $WORKTREE_NAME"
    echo -e "  Status:  $STATUS"
    echo -e "  Branch:  $BRANCH @ $COMMIT"
    if [ -n "$CREATED" ]; then
        echo -e "  Created: $CREATED"
    fi
    echo -e "  Path:    $worktree"
    echo ""
done

# Print summary
cd "$REPO_ROOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total worktrees:  $TOTAL_COUNT"
echo -e "Clean worktrees:  ${GREEN}$CLEAN_COUNT${NC}"
echo -e "Dirty worktrees:  ${YELLOW}$DIRTY_COUNT${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Exit if no worktrees found
if [ $TOTAL_COUNT -eq 0 ]; then
    log_info "No managed worktrees found"
    exit 0
fi

# Determine which worktrees to delete
if [ "$DELETE_ALL" = true ]; then
    WORKTREES_TO_DELETE=("${CLEAN_WORKTREES[@]}" "${DIRTY_WORKTREES[@]}")
    log_warning "DELETE ALL mode: Will delete all worktrees (clean and dirty)"
else
    WORKTREES_TO_DELETE=("${CLEAN_WORKTREES[@]}")
    if [ $CLEAN_COUNT -eq 0 ]; then
        log_info "No clean worktrees to delete"
        exit 0
    fi
fi

# Delete worktrees
if [ ${#WORKTREES_TO_DELETE[@]} -gt 0 ]; then
    echo -e "${BLUE}Deleting ${#WORKTREES_TO_DELETE[@]} worktree(s)...${NC}"
    echo ""

    for worktree in "${WORKTREES_TO_DELETE[@]}"; do
        WORKTREE_NAME=$(basename "$worktree")

        if [ "$DRY_RUN" = true ]; then
            log_dry_run "Would delete: $WORKTREE_NAME"
        elif [ "$AUTO_DELETE" = true ]; then
            if git worktree remove "$worktree" --force 2>/dev/null; then
                log_success "Deleted: $WORKTREE_NAME"
                DELETED_COUNT=$((DELETED_COUNT + 1))
            else
                log_error "Failed to delete: $WORKTREE_NAME"
            fi
        else
            # Interactive mode - prompt for each
            read -p "Delete $WORKTREE_NAME? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                if git worktree remove "$worktree" --force 2>/dev/null; then
                    log_success "Deleted: $WORKTREE_NAME"
                    DELETED_COUNT=$((DELETED_COUNT + 1))
                else
                    log_error "Failed to delete: $WORKTREE_NAME"
                fi
            else
                log_info "Kept: $WORKTREE_NAME"
                KEPT_COUNT=$((KEPT_COUNT + 1))
            fi
        fi
    done

    # Final summary
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Cleanup Complete${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ "$DRY_RUN" = true ]; then
        log_dry_run "No changes were made (dry run mode)"
    else
        log_success "Deleted: $DELETED_COUNT worktree(s)"
        if [ $KEPT_COUNT -gt 0 ]; then
            log_info "Kept: $KEPT_COUNT worktree(s)"
        fi
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi
