#!/bin/bash
# Publish LangGraph Agent to MCP Registry

set -e

echo "=========================================="
echo "MCP Registry Publication Script"
echo "=========================================="
echo ""

# Configuration
REGISTRY_URL="${MCP_REGISTRY_URL:-https://registry.modelcontextprotocol.io}"
REGISTRY_TOKEN="${MCP_REGISTRY_TOKEN}"
MANIFEST_PATH=".mcp/manifest.json"
REGISTRY_INFO_PATH=".mcp/registry.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "1. Checking prerequisites..."

if [ ! -f "$MANIFEST_PATH" ]; then
    echo -e "${RED}✗ Manifest file not found: $MANIFEST_PATH${NC}"
    exit 1
fi

if [ ! -f "$REGISTRY_INFO_PATH" ]; then
    echo -e "${RED}✗ Registry info not found: $REGISTRY_INFO_PATH${NC}"
    exit 1
fi

if [ -z "$REGISTRY_TOKEN" ]; then
    echo -e "${YELLOW}⚠ Warning: MCP_REGISTRY_TOKEN not set${NC}"
    echo "Set it with: export MCP_REGISTRY_TOKEN=your-token"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"
echo ""

# Validate manifest
echo "2. Validating manifest..."

if ! jq empty "$MANIFEST_PATH" 2>/dev/null; then
    echo -e "${RED}✗ Invalid JSON in manifest${NC}"
    exit 1
fi

NAME=$(jq -r '.name' "$MANIFEST_PATH")
VERSION=$(jq -r '.version' "$MANIFEST_PATH")

if [ "$NAME" == "null" ] || [ "$VERSION" == "null" ]; then
    echo -e "${RED}✗ Manifest missing name or version${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Manifest valid${NC}"
echo "  Name: $NAME"
echo "  Version: $VERSION"
echo ""

# Build package
echo "3. Building package..."

PACKAGE_DIR="dist/mcp-package"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

# Copy manifest and registry info
cp "$MANIFEST_PATH" "$PACKAGE_DIR/"
cp "$REGISTRY_INFO_PATH" "$PACKAGE_DIR/"

# Copy source code
echo "  Copying source files..."
cp *.py "$PACKAGE_DIR/" 2>/dev/null || true
cp requirements.txt "$PACKAGE_DIR/"
cp README.md "$PACKAGE_DIR/"

# Copy configuration
mkdir -p "$PACKAGE_DIR/helm"
mkdir -p "$PACKAGE_DIR/kubernetes"
cp -r helm/langgraph-agent "$PACKAGE_DIR/helm/" 2>/dev/null || true
cp -r kubernetes/base "$PACKAGE_DIR/kubernetes/" 2>/dev/null || true

# Create package tarball
echo "  Creating tarball..."
cd dist
tar -czf "${NAME}-${VERSION}.tar.gz" mcp-package/
cd ..

echo -e "${GREEN}✓ Package built: dist/${NAME}-${VERSION}.tar.gz${NC}"
echo ""

# Upload to registry
echo "4. Uploading to registry..."

if [ -n "$REGISTRY_TOKEN" ]; then
    echo "  Registry URL: $REGISTRY_URL"

    # Upload package
    UPLOAD_URL="${REGISTRY_URL}/api/v1/packages"

    curl -X POST "$UPLOAD_URL" \
        -H "Authorization: Bearer $REGISTRY_TOKEN" \
        -H "Content-Type: multipart/form-data" \
        -F "package=@dist/${NAME}-${VERSION}.tar.gz" \
        -F "manifest=@$MANIFEST_PATH" \
        -F "registry_info=@$REGISTRY_INFO_PATH" \
        --fail-with-body || {
            echo -e "${RED}✗ Upload failed${NC}"
            exit 1
        }

    echo -e "${GREEN}✓ Package uploaded successfully${NC}"
else
    echo -e "${YELLOW}⚠ Skipping upload (no registry token)${NC}"
    echo "  Package ready at: dist/${NAME}-${VERSION}.tar.gz"
    echo ""
    echo "  To upload manually:"
    echo "  1. Get registry token from: $REGISTRY_URL"
    echo "  2. Upload package: curl -X POST $REGISTRY_URL/api/v1/packages \\"
    echo "       -H 'Authorization: Bearer YOUR_TOKEN' \\"
    echo "       -F 'package=@dist/${NAME}-${VERSION}.tar.gz'"
fi

echo ""

# Generate registry card
echo "5. Generating registry card..."

cat > "dist/REGISTRY_CARD.md" << EOF
# $NAME

**Version:** $VERSION

## Installation

### HTTP/SSE Transport

\`\`\`bash
# Connect to hosted instance
export MCP_SERVER_URL=https://langgraph-agent.example.com
\`\`\`

### stdio Transport (Local)

\`\`\`bash
# Clone repository
git clone https://github.com/your-org/mcp-server-langgraph.git
cd mcp-server-langgraph

# Install dependencies
pip install -r requirements.txt

# Run server
python mcp_server.py
\`\`\`

### Kubernetes Deployment

\`\`\`bash
# Deploy with Helm
helm install langgraph-agent ./helm/langgraph-agent \\
  --namespace langgraph-agent \\
  --create-namespace

# Or with kubectl
kubectl apply -k kubernetes/base/
\`\`\`

## Configuration

Required environment variables:
- \`ANTHROPIC_API_KEY\`: Your Anthropic API key

Optional:
- \`OPENFGA_STORE_ID\`: OpenFGA store ID for fine-grained auth
- \`OPENFGA_MODEL_ID\`: OpenFGA authorization model ID

## Features

- **AI Agent**: Powered by Claude (Anthropic)
- **Authorization**: Fine-grained, relationship-based (OpenFGA)
- **Observability**: Full tracing, metrics, logging (OpenTelemetry)
- **Rate Limiting**: Kong API Gateway integration
- **Kubernetes**: Production-ready deployment (GKE, EKS, AKS, Rancher, Tanzu)

## Documentation

- [README](https://github.com/your-org/mcp-server-langgraph/blob/main/README.md)
- [Kubernetes Deployment](https://github.com/your-org/mcp-server-langgraph/blob/main/KUBERNETES_DEPLOYMENT.md)
- [OpenFGA Integration](https://github.com/your-org/mcp-server-langgraph/blob/main/README_OPENFGA_INFISICAL.md)
- [Kong Integration](https://github.com/your-org/mcp-server-langgraph/blob/main/KONG_INTEGRATION.md)

## Support

- GitHub Issues: https://github.com/your-org/mcp-server-langgraph/issues
- Email: support@example.com

## License

MIT
EOF

echo -e "${GREEN}✓ Registry card generated: dist/REGISTRY_CARD.md${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}Publication complete!${NC}"
echo "=========================================="
echo ""
echo "Package: dist/${NAME}-${VERSION}.tar.gz"
echo "Registry card: dist/REGISTRY_CARD.md"
echo ""
echo "Next steps:"
echo "1. Review the package contents"
echo "2. Test the package locally"
echo "3. Submit for registry review (if applicable)"
echo ""
