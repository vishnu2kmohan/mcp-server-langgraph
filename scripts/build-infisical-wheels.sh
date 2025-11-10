#!/bin/bash
# Build Infisical Python Wheels using Docker
# ===========================================
# Builds pre-compiled wheels for infisical-python across multiple Python versions
#
# USAGE:
#   ./scripts/build-infisical-wheels.sh [output-dir]
#
# EXAMPLES:
#   # Build all wheels (default: ./wheels)
#   ./scripts/build-infisical-wheels.sh
#
#   # Build to custom directory
#   ./scripts/build-infisical-wheels.sh ./dist/wheels
#
#   # Build for specific Python version
#   PYTHON_VERSIONS="3.12" ./scripts/build-infisical-wheels.sh
#
# ENVIRONMENT VARIABLES:
#   PYTHON_VERSIONS - Space-separated Python versions (default: "3.10 3.11 3.12")
#   OUTPUT_DIR      - Output directory (default: ./wheels)
#   CLEAN           - Clean output directory before build (default: false)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSIONS="${PYTHON_VERSIONS:-3.10 3.11 3.12}"
OUTPUT_DIR="${1:-./wheels}"
CLEAN="${CLEAN:-false}"
DOCKERFILE="docker/Dockerfile.infisical-builder"

# Logging functions
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

# Banner
echo ""
echo "========================================"
echo "  Infisical Python Wheel Builder"
echo "========================================"
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker to continue."
    exit 1
fi

if ! docker buildx version &> /dev/null; then
    log_warning "Docker BuildKit not available. Using standard build (slower)."
    BUILDX=""
else
    log_success "Docker BuildKit available"
    BUILDX="buildx"
fi

if [ ! -f "$DOCKERFILE" ]; then
    log_error "Dockerfile not found: $DOCKERFILE"
    log_info "Please run this script from the project root directory."
    exit 1
fi

if [ ! -f "requirements-infisical.txt" ]; then
    log_error "requirements-infisical.txt not found"
    log_info "Please ensure requirements-infisical.txt exists in project root."
    exit 1
fi

log_success "All prerequisites met"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Clean if requested
if [ "$CLEAN" = "true" ]; then
    # Safety check: validate OUTPUT_DIR before rm -rf (Codex Security Fix)
    if [ -z "$OUTPUT_DIR" ] || [ "$OUTPUT_DIR" = "/" ] || [ "$OUTPUT_DIR" = "/tmp" ]; then
        log_error "Invalid OUTPUT_DIR for cleanup: '$OUTPUT_DIR'"
        log_error "OUTPUT_DIR must be set to a specific, non-system directory"
        exit 1
    fi

    log_info "Cleaning output directory: $OUTPUT_DIR"
    # shellcheck disable=SC2115  # OUTPUT_DIR validated above
    rm -rf "$OUTPUT_DIR"/*
fi

# Build wheels for each Python version
log_info "Building wheels for Python versions: $PYTHON_VERSIONS"
echo ""

BUILD_COUNT=0
SUCCESS_COUNT=0
FAILED_VERSIONS=""

for PY_VERSION in $PYTHON_VERSIONS; do
    BUILD_COUNT=$((BUILD_COUNT + 1))
    VERSION_OUTPUT="$OUTPUT_DIR/py${PY_VERSION}"

    log_info "[$BUILD_COUNT] Building for Python $PY_VERSION..."

    # Create version-specific output directory
    mkdir -p "$VERSION_OUTPUT"

    # Build command
    BUILD_CMD="docker"
    if [ -n "$BUILDX" ]; then
        BUILD_CMD="docker buildx"
    fi

    # Build the wheels
    if $BUILD_CMD build \
        --build-arg PYTHON_VERSION="$PY_VERSION" \
        --target wheels-export \
        --output type=local,dest="$VERSION_OUTPUT" \
        -f "$DOCKERFILE" \
        . 2>&1 | tee "$OUTPUT_DIR/build-py${PY_VERSION}.log"; then

        # Check if wheels were created
        WHEEL_COUNT=$(find "$VERSION_OUTPUT" -name "*.whl" | wc -l)

        if [ "$WHEEL_COUNT" -gt 0 ]; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            log_success "Python $PY_VERSION: Built $WHEEL_COUNT wheel(s)"

            # List created wheels
            find "$VERSION_OUTPUT" -name "*.whl" -exec basename {} \; | while read -r wheel; do
                echo "    → $wheel"
            done
        else
            log_warning "Python $PY_VERSION: Build succeeded but no wheels found"
            FAILED_VERSIONS="$FAILED_VERSIONS $PY_VERSION"
        fi
    else
        log_error "Python $PY_VERSION: Build failed"
        FAILED_VERSIONS="$FAILED_VERSIONS $PY_VERSION"

        # Show last 20 lines of error log
        echo ""
        log_warning "Last 20 lines of build log:"
        tail -n 20 "$OUTPUT_DIR/build-py${PY_VERSION}.log" || true
    fi

    echo ""
done

# Summary
echo "========================================"
echo "  Build Summary"
echo "========================================"
echo ""
log_info "Total builds:      $BUILD_COUNT"
log_success "Successful builds: $SUCCESS_COUNT"

if [ $SUCCESS_COUNT -lt $BUILD_COUNT ]; then
    FAILED_COUNT=$((BUILD_COUNT - SUCCESS_COUNT))
    log_error "Failed builds:     $FAILED_COUNT"
    echo ""
    log_warning "Failed versions:$FAILED_VERSIONS"
fi

echo ""
log_info "Output directory:  $OUTPUT_DIR"

# Show directory structure
if [ $SUCCESS_COUNT -gt 0 ]; then
    echo ""
    log_info "Built wheels:"
    tree "$OUTPUT_DIR" -L 2 2>/dev/null || find "$OUTPUT_DIR" -name "*.whl" | sort
fi

# Show total size
TOTAL_SIZE=$(du -sh "$OUTPUT_DIR" 2>/dev/null | cut -f1)
echo ""
log_info "Total size: $TOTAL_SIZE"

# Instructions
echo ""
echo "========================================"
echo "  Usage Instructions"
echo "========================================"
echo ""
echo "To install from built wheels:"
echo ""
echo "  # For Python 3.12:"
echo "  pip install --no-index --find-links=$OUTPUT_DIR/py3.12 infisical-python"
echo ""
echo "  # For all versions:"
echo "  pip install --no-index --find-links=$OUTPUT_DIR/py\$(python3 -c 'import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")') infisical-python"
echo ""

# Exit code
if [ $SUCCESS_COUNT -eq $BUILD_COUNT ]; then
    log_success "All builds completed successfully!"
    exit 0
else
    log_warning "Some builds failed. See logs in $OUTPUT_DIR/*.log"
    exit 1
fi
