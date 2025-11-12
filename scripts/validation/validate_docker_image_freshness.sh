#!/bin/bash
# Docker Image Freshness Validation Script
# =========================================
# Validates that Docker test images are up-to-date with the current codebase.
#
# This script prevents the issue where:
# - Local tests pass (using current code)
# - Docker tests fail (using stale cached image)
# - CI/CD fails unexpectedly
#
# USAGE:
#   ./scripts/validation/validate_docker_image_freshness.sh [options]
#
# OPTIONS:
#   --image NAME      Image name to check (default: docker-test-runner:latest)
#   --warn-hours N    Warn if image is N hours old (default: 24)
#   --fail-hours N    Fail if image is N hours old (default: 168, 7 days)
#   --check-commits   Check if image is older than recent commits
#   --verbose         Show detailed information
#   --help            Show this help message
#
# EXIT CODES:
#   0 - Image is fresh
#   1 - Image is stale (warning or error)
#   2 - Image not found
#   3 - Invalid arguments
#
# EXAMPLES:
#   # Check if image exists and is reasonably fresh
#   ./scripts/validation/validate_docker_image_freshness.sh
#
#   # Strict check: fail if older than 1 day
#   ./scripts/validation/validate_docker_image_freshness.sh --fail-hours 24
#
#   # Check against recent commits
#   ./scripts/validation/validate_docker_image_freshness.sh --check-commits
#
# INTEGRATION:
#   # As pre-commit hook
#   - repo: local
#     hooks:
#       - id: validate-docker-image
#         name: Validate Docker Test Image Freshness
#         entry: scripts/validation/validate_docker_image_freshness.sh
#         language: system
#         pass_filenames: false
#
#   # In CI/CD (GitHub Actions)
#   - name: Validate Docker Image Freshness
#     run: ./scripts/validation/validate_docker_image_freshness.sh --fail-hours 24

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
IMAGE_NAME="docker-test-runner:latest"
WARN_HOURS=24
FAIL_HOURS=168  # 7 days
CHECK_COMMITS=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --warn-hours)
            WARN_HOURS="$2"
            shift 2
            ;;
        --fail-hours)
            FAIL_HOURS="$2"
            shift 2
            ;;
        --check-commits)
            CHECK_COMMITS=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            grep "^#" "$0" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run with --help for usage"
            exit 3
            ;;
    esac
done

# Logging functions
log_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}ℹ${NC} $1"
    fi
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

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker to continue."
    exit 2
fi

log_info "Checking Docker image: $IMAGE_NAME"

# Check if image exists
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    log_error "Docker image '$IMAGE_NAME' not found."
    log_info "Build the image with:"
    echo "  ./scripts/test-integration.sh --build"
    exit 2
fi

# Get image creation timestamp
IMAGE_CREATED=$(docker image inspect "$IMAGE_NAME" --format='{{.Created}}')
IMAGE_CREATED_EPOCH=$(date -d "$IMAGE_CREATED" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$IMAGE_CREATED" +%s 2>/dev/null)

if [ -z "$IMAGE_CREATED_EPOCH" ]; then
    log_error "Failed to parse image creation timestamp: $IMAGE_CREATED"
    exit 1
fi

# Get current timestamp
CURRENT_EPOCH=$(date +%s)

# Calculate age in hours
AGE_SECONDS=$((CURRENT_EPOCH - IMAGE_CREATED_EPOCH))
AGE_HOURS=$((AGE_SECONDS / 3600))
AGE_DAYS=$((AGE_HOURS / 24))

log_info "Image created: $IMAGE_CREATED"
log_info "Image age: ${AGE_HOURS} hours (${AGE_DAYS} days)"

# Check against thresholds
EXIT_CODE=0

if [ $AGE_HOURS -ge $FAIL_HOURS ]; then
    log_error "Docker image is ${AGE_HOURS} hours old (threshold: ${FAIL_HOURS} hours)"
    log_error "Image is STALE and should be rebuilt immediately."
    echo ""
    echo "To rebuild:"
    echo "  ./scripts/test-integration.sh --build --no-cache"
    EXIT_CODE=1
elif [ $AGE_HOURS -ge $WARN_HOURS ]; then
    log_warning "Docker image is ${AGE_HOURS} hours old (threshold: ${WARN_HOURS} hours)"
    log_warning "Consider rebuilding the image soon."
    echo ""
    echo "To rebuild:"
    echo "  ./scripts/test-integration.sh --build"
    # Don't set EXIT_CODE here, just warn
else
    log_success "Docker image is ${AGE_HOURS} hours old (within ${WARN_HOURS} hour threshold)"
fi

# Check against recent commits if requested
if [ "$CHECK_COMMITS" = true ]; then
    log_info "Checking recent commits..."

    if [ ! -d ".git" ]; then
        log_warning "Not in a git repository - skipping commit check"
    else
        # Get timestamp of most recent commit
        LATEST_COMMIT_EPOCH=$(git log -1 --format=%ct 2>/dev/null || echo "0")

        if [ "$LATEST_COMMIT_EPOCH" -gt "$IMAGE_CREATED_EPOCH" ]; then
            COMMIT_DELAY_SECONDS=$((LATEST_COMMIT_EPOCH - IMAGE_CREATED_EPOCH))
            COMMIT_DELAY_HOURS=$((COMMIT_DELAY_SECONDS / 3600))

            log_warning "Docker image is older than latest commit by ${COMMIT_DELAY_HOURS} hours"

            # Show recent commits newer than the image
            echo ""
            echo "Recent commits not in Docker image:"
            git log --since="@${IMAGE_CREATED_EPOCH}" --oneline --format="%h %ai %s" | head -10

            echo ""
            log_error "Docker image is OUT OF SYNC with current codebase"
            log_error "Tests may fail unexpectedly due to missing code changes."
            echo ""
            echo "To rebuild and sync:"
            echo "  ./scripts/test-integration.sh --build --no-cache"

            EXIT_CODE=1
        else
            log_success "Docker image is up-to-date with latest commit"
        fi
    fi
fi

# Summary
echo ""
echo "============================================"
if [ $EXIT_CODE -eq 0 ]; then
    log_success "Docker image validation PASSED"
    echo "Image is fresh and up-to-date"
else
    log_error "Docker image validation FAILED"
    echo "Image is stale and needs rebuilding"
fi
echo "============================================"

exit $EXIT_CODE
