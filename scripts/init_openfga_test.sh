#!/bin/bash
# ==============================================================================
# OpenFGA Test Initialization Script
# ==============================================================================
# This script initializes OpenFGA for integration tests by:
# 1. Waiting for OpenFGA to be healthy
# 2. Creating a test store and authorization model
# 3. Seeding sample test data
# 4. Exporting store/model IDs as environment variables
# ==============================================================================

set -e  # Exit on error

echo "===================================================================="
echo "OpenFGA Test Initialization"
echo "===================================================================="

# Wait for OpenFGA to be ready
echo ""
echo "1. Waiting for OpenFGA service..."
MAX_RETRIES=30
RETRY_COUNT=0

until curl -sf "${OPENFGA_API_URL}/healthz" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "   ✗ OpenFGA failed to become ready after ${MAX_RETRIES} retries"
        exit 1
    fi
    echo "   Waiting for OpenFGA (attempt $RETRY_COUNT/$MAX_RETRIES)..."
    sleep 1
done

echo "   ✓ OpenFGA is ready at ${OPENFGA_API_URL}"

# Initialize OpenFGA store and model
echo ""
echo "2. Initializing OpenFGA store and authorization model..."

# Run Python setup script and capture output
SETUP_OUTPUT=$(python3 scripts/setup/setup_openfga.py 2>&1 || true)

# Extract store and model IDs from output
STORE_ID=$(echo "$SETUP_OUTPUT" | grep -oP 'OPENFGA_STORE_ID=\K[^[:space:]]+' | head -1)
MODEL_ID=$(echo "$SETUP_OUTPUT" | grep -oP 'OPENFGA_MODEL_ID=\K[^[:space:]]+' | head -1)

if [ -z "$STORE_ID" ] || [ -z "$MODEL_ID" ]; then
    echo "   ✗ Failed to extract store/model IDs from setup script"
    echo ""
    echo "Setup script output:"
    echo "$SETUP_OUTPUT"
    exit 1
fi

echo "   ✓ Store ID: $STORE_ID"
echo "   ✓ Model ID: $MODEL_ID"

# Export environment variables for tests
export OPENFGA_STORE_ID="$STORE_ID"
export OPENFGA_MODEL_ID="$MODEL_ID"

echo ""
echo "===================================================================="
echo "✓ OpenFGA initialization complete!"
echo "===================================================================="
echo ""
echo "Environment variables set:"
echo "  OPENFGA_STORE_ID=$OPENFGA_STORE_ID"
echo "  OPENFGA_MODEL_ID=$OPENFGA_MODEL_ID"
echo ""

# Run the command passed as arguments (typically pytest)
exec "$@"
