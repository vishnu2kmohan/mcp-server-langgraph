# API Client Generation

This directory contains configurations for generating production-grade client libraries from OpenAPI specifications.

## Available Generators

### Python SDK
```bash
openapi-generator-cli generate \
  -i ../openapi/v1.json \
  -g python \
  -o ../clients/python \
  --additional-properties=packageName=mcp_client,projectName=mcp-client,packageVersion=2.8.0
```

### TypeScript/JavaScript SDK
```bash
openapi-generator-cli generate \
  -i ../openapi/v1.json \
  -g typescript-axios \
  -o ../clients/typescript \
  --additional-properties=npmName=@mcp/client,npmVersion=2.8.0,supportsES6=true
```

### Go SDK
```bash
openapi-generator-cli generate \
  -i ../openapi/v1.json \
  -g go \
  -o ../clients/go \
  --additional-properties=packageName=mcpclient,packageVersion=2.8.0
```

### CLI Tool
```bash
openapi-generator-cli generate \
  -i ../openapi/v1.json \
  -g cli \
  -o ../clients/cli
```

## Installation

```bash
npm install @openapitools/openapi-generator-cli -g
```

## Generated Clients

All clients will include:
- Type-safe request/response models
- Authentication handling (JWT, API keys)
- Automatic retries and error handling
- Pagination support
- Rate limit handling
- Full TypeScript/Python type hints

## OpenAPI Specifications

- **`../openapi/v1.json`** - Complete REST API specification (22 endpoints, 42 schemas)
- **`../openapi/mcp-tools.json`** - MCP tools wrapper specification (3 tools, 6 schemas)
