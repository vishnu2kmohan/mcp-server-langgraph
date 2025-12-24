#!/bin/bash
#
# Validate Generated TypeScript Types
#
# Checks that generated-api.ts is in sync with api/openapi.json.
# Used by pre-commit hook and CI to ensure type generation is up-to-date.
#
# Usage:
#   ./scripts/validate-generated-types.sh
#
# Exit codes:
#   0 - Types are in sync
#   1 - Types are out of sync (regeneration needed)
#   2 - Error during validation
#

set -e

# Determine script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(cd "$FRONTEND_DIR/../../../.." && pwd)"

GENERATED_FILE="$FRONTEND_DIR/src/types/generated-api.ts"
OPENAPI_FILE="$PROJECT_ROOT/api/openapi.json"

# Verify source files exist
if [[ ! -f "$OPENAPI_FILE" ]]; then
  echo "ERROR: OpenAPI spec not found at $OPENAPI_FILE"
  exit 2
fi

if [[ ! -f "$GENERATED_FILE" ]]; then
  echo "ERROR: Generated types not found at $GENERATED_FILE"
  echo "Run: cd $FRONTEND_DIR && npm run generate-types"
  exit 1
fi

# Create temp file for comparison
TEMP_FILE=$(mktemp)
# shellcheck disable=SC2064
# Note: We want TEMP_FILE to expand now, not at trap time
trap "rm -f $TEMP_FILE" EXIT

# Generate types to temp file
echo "Generating types from OpenAPI spec..."
cd "$FRONTEND_DIR"
npx openapi-typescript "$OPENAPI_FILE" -o "$TEMP_FILE" 2>/dev/null

# Compare files (skip first few lines which may contain timestamps)
# We compare from line 5 onwards to ignore header differences
echo "Comparing generated types..."
if ! diff -q <(tail -n +5 "$GENERATED_FILE") <(tail -n +5 "$TEMP_FILE") > /dev/null 2>&1; then
  echo ""
  echo "ERROR: generated-api.ts is out of sync with api/openapi.json"
  echo ""
  echo "The generated TypeScript types do not match the OpenAPI specification."
  echo "This can happen when:"
  echo "  - Backend API schemas were modified"
  echo "  - OpenAPI spec was regenerated"
  echo "  - Types were manually edited (don't do this!)"
  echo ""
  echo "To fix, run:"
  echo "  cd $FRONTEND_DIR && npm run generate-types"
  echo ""
  exit 1
fi

echo "SUCCESS: generated-api.ts is in sync with api/openapi.json"
exit 0
