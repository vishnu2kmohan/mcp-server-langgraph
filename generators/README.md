# API Client Generation

This directory contains configurations for generating production-grade client libraries from OpenAPI specifications with full linting compliance.

## Quick Start

```bash
# Automatic generation (recommended)
./scripts/development/generate_clients.sh

# Or manually generate all clients
openapi-generator-cli batch --clean generators/batch-config.yaml
```

## Configuration Files

### Individual Client Configs
- **`python-config.yaml`** - Python client (flake8 & mypy compliant)
- **`go-config.yaml`** - Go client (golint & go vet compliant)
- **`typescript-config.yaml`** - TypeScript client (ESLint compliant)

### Batch Config
- **`batch-config.yaml`** - Generate all clients at once

## Linting Compliance

All generated clients are configured to adhere to code quality standards:

### Python
- ✅ **flake8** - Code style and quality
- ✅ **black** - Code formatting (127 char line length)
- ✅ **isort** - Import sorting
- ✅ **mypy** - Type checking
- ✅ **bandit** - Security scanning

**Note:** Generated Python client code is excluded from flake8 checks in `.flake8`:
```ini
exclude =
    clients/python/mcp_client,
    clients/python/test,
    clients/python/docs
```

### Go
- ✅ **go fmt** - Standard Go formatting
- ✅ **go vet** - Go static analysis
- ✅ **golint** - Go linting

### TypeScript
- ✅ **ESLint** - JavaScript/TypeScript linting
- ✅ **Prettier** - Code formatting

## Generator Settings

### Python Client
```yaml
generatorName: python
library: urllib3  # Uses urllib3 for HTTP requests
packageName: mcp_client
projectName: mcp-client
packageVersion: "2.8.0"
hideGenerationTimestamp: true
useOneOfDiscriminatorLookup: true
```

### Go Client
```yaml
generatorName: go
packageName: mcpclient
packageVersion: "2.8.0"
generateInterfaces: true
hideGenerationTimestamp: true
isGoSubmodule: true
```

### TypeScript Client
```yaml
generatorName: typescript-axios
npmName: "@mcp/client"
npmVersion: "2.8.0"
supportsES6: true
modelPropertyNaming: camelCase
withNodeImports: true
usePromises: true
```

## Prerequisites

### Option 1: NPM (Recommended for local development)
```bash
npm install @openapitools/openapi-generator-cli -g
```

### Option 2: Homebrew (macOS/Linux)
```bash
brew install openapi-generator
```

### Option 3: Docker (Recommended for CI)
```bash
docker run --rm \
  -v "${PWD}:/local" \
  openapitools/openapi-generator-cli:latest \
  generate -c /local/generators/python-config.yaml
```

## Manual Generation

### Generate Individual Clients

**Python:**
```bash
openapi-generator-cli generate -c generators/python-config.yaml
```

**Go:**
```bash
openapi-generator-cli generate -c generators/go-config.yaml
```

**TypeScript:**
```bash
openapi-generator-cli generate -c generators/typescript-config.yaml
```

### Generate All Clients
```bash
openapi-generator-cli batch generators/batch-config.yaml
```

## Workflow

1. **Update OpenAPI Schema:**
   ```bash
   uv run --frozen python scripts/development/generate_openapi.py
   ```

2. **Generate Clients:**
   ```bash
   ./scripts/development/generate_clients.sh
   ```

3. **Verify Quality:**
   ```bash
   make lint-check  # Check linting (flake8, mypy, bandit)
   make test        # Run tests
   ```

4. **Commit Changes:**
   ```bash
   git add clients/ generators/ .flake8
   git commit -m "chore(clients): regenerate API client bindings"
   ```

## Customization

### Modifying Generation Settings

1. Edit the appropriate config file (`python-config.yaml`, `go-config.yaml`, etc.)
2. Regenerate clients using the generation script
3. Test thoroughly before committing

### Common Customizations

**Change Python package name:**
```yaml
# In python-config.yaml
packageName: my_custom_client
```

**Change TypeScript npm package:**
```yaml
# In typescript-config.yaml
npmName: "@myorg/api-client"
```

**Add custom templates:**
```yaml
# In any config file
templateDir: custom-templates/python
```

## OpenAPI Specifications

- **`../openapi.json`** - Main API spec (auto-generated from FastAPI app)
- **Source:** `mcp_server_langgraph.mcp.server_streamable`

## Troubleshooting

### Linting Errors After Generation

If you see flake8 errors in generated code:

1. Verify `.flake8` excludes generated paths
2. Regenerate with latest configs
3. If issues persist, exclude specific files in `.flake8`:
   ```ini
   per-file-ignores =
       clients/python/mcp_client/api/*.py:F401,F841
   ```

### Version Mismatch

Check generator version:
```bash
openapi-generator-cli version
# Should be 7.x.x or higher
```

Update if needed:
```bash
npm update -g @openapitools/openapi-generator-cli
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/generate-clients.yaml
- name: Generate API clients
  run: |
    npm install -g @openapitools/openapi-generator-cli
    ./scripts/development/generate_clients.sh

- name: Verify linting
  run: make lint-check
```

## Version Information

- **OpenAPI Generator:** 7.18.0-SNAPSHOT
- **Python Client:** 2.8.0
- **Go Client:** 2.8.0
- **TypeScript Client:** 2.8.0
- **OpenAPI Spec:** 3.1.0

## References

- [OpenAPI Generator Documentation](https://openapi-generator.tech/)
- [Python Generator Options](https://openapi-generator.tech/docs/generators/python)
- [Go Generator Options](https://openapi-generator.tech/docs/generators/go)
- [TypeScript Axios Generator Options](https://openapi-generator.tech/docs/generators/typescript-axios)
