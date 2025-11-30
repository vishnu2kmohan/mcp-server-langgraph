#!/bin/bash
# Generate OpenAPI client SDKs for Python, Go, and TypeScript
# Uses OpenAPI Generator with configuration files that ensure linting compliance

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# GENERATORS_DIR reserved for future generator configuration logic
# shellcheck disable=SC2034
GENERATORS_DIR="$PROJECT_ROOT/generators"

echo "======================================================================"
echo "Generating OpenAPI Client SDKs"
echo "======================================================================"
echo ""

# Check if openapi-generator-cli is available
if ! command -v openapi-generator-cli &> /dev/null; then
    echo "⚠️  openapi-generator-cli not found."
    echo ""
    echo "Installation options:"
    echo "  1. npm install @openapitools/openapi-generator-cli -g"
    echo "  2. brew install openapi-generator"
    echo "  3. Use Docker (recommended for CI):"
    echo "     docker run --rm -v \"\${PWD}:/local\" openapitools/openapi-generator-cli:latest"
    echo ""
    read -p "Use Docker? (y/n): " use_docker

    if [[ "$use_docker" =~ ^[Yy]$ ]]; then
        GENERATOR_CMD="docker run --rm -v \"$PROJECT_ROOT:/local\" -w /local openapitools/openapi-generator-cli:latest"
    else
        echo "❌ Exiting. Please install openapi-generator-cli first."
        exit 1
    fi
else
    GENERATOR_CMD="openapi-generator-cli"
fi

echo "Using generator: $GENERATOR_CMD"
echo ""

# Step 1: Generate/update OpenAPI schema
echo "Step 1: Generating OpenAPI schema..."
cd "$PROJECT_ROOT"
uv run python scripts/development/generate_openapi.py
echo ""

# Step 2: Generate Python client
echo "Step 2: Generating Python client..."
eval "$GENERATOR_CMD generate -c generators/python-config.yaml"
echo "✓ Python client generated"
echo ""

# Step 3: Generate Go client
echo "Step 3: Generating Go client..."
eval "$GENERATOR_CMD generate -c generators/go-config.yaml"
echo "✓ Go client generated"
echo ""

# Step 4: Generate TypeScript client
echo "Step 4: Generating TypeScript client..."
eval "$GENERATOR_CMD generate -c generators/typescript-config.yaml"
echo "✓ TypeScript client generated"
echo ""

echo "======================================================================"
echo "✓ All clients generated successfully!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Review generated code"
echo "  2. Run tests: make test"
echo "  3. Run linting: make lint-check"
echo "  4. Commit changes: git add clients/ generators/ && git commit"
echo ""
