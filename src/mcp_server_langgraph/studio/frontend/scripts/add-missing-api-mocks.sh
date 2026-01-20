#!/bin/bash
# Add missing RTK Query hook mocks to test files
# This script adds useGetEmptyStateSuggestionsMutation mock to files that mock ../../api

set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$FRONTEND_DIR"

echo "=== Adding Missing API Mocks ==="
echo "Working directory: $FRONTEND_DIR"

# Find all test files that mock ../../api but don't have useGetEmptyStateSuggestionsMutation
find src/pages/__tests__ -name "*.test.tsx" -exec grep -l 'vi.mock.*api.*=>' {} \; | while read file; do
  if ! grep -q "useGetEmptyStateSuggestionsMutation" "$file"; then
    echo "Adding mock to: $file"

    # Add the mock right after the existing mock opening
    # Pattern: vi.mock("../../api", () => ({
    # We add: useGetEmptyStateSuggestionsMutation: () => [vi.fn(), { isLoading: false }],
    sed -i '' 's/vi.mock("..\/..\/api", () => ({/vi.mock("..\/..\/api", () => ({\
  useGetEmptyStateSuggestionsMutation: () => [vi.fn(), { isLoading: false }],/' "$file"
  fi
done

# Also handle ../api pattern (single parent)
find src/pages -maxdepth 1 -name "*.test.tsx" -exec grep -l 'vi.mock.*api.*=>' {} \; 2>/dev/null | while read file; do
  if ! grep -q "useGetEmptyStateSuggestionsMutation" "$file"; then
    echo "Adding mock to: $file"
    sed -i '' 's/vi.mock("..\/api", () => ({/vi.mock("..\/api", () => ({\
  useGetEmptyStateSuggestionsMutation: () => [vi.fn(), { isLoading: false }],/' "$file"
  fi
done

echo ""
echo "=== Script Complete ==="
echo "Run tests to verify: npm test -- --run 'pages/'"
