# MCP Server Client Libraries

Production-grade client libraries auto-generated from OpenAPI 3.1.0 specifications.

## Available SDKs

| Language | Package | Status | Directory |
|----------|---------|--------|-----------|
| **Python** | `mcp-client` | ✅ Generated | `./python/` |
| **TypeScript** | `mcp-client` | ✅ Generated | `./typescript/` |
| **Go** | `mcpclient` | ✅ Generated | `./go/` |

## Quick Start

### Python SDK

```bash
cd clients/python
pip install -e .
```

**Usage:**
```python
from mcp_client import ApiClient, Configuration
from mcp_client.api import APIKeysApi, GDPRComplianceApi, AuthApi

# Configure API client
config = Configuration(
    host="https://api.example.com"
)

# Authenticate
with ApiClient(config) as client:
    auth_api = AuthApi(client)

    # Login to get JWT token
    login_response = auth_api.login_auth_login_post(
        login_request={
            "username": "alice",
            "password": "secret"
        }
    )

    token = login_response.access_token

    # Configure authenticated client
    config.access_token = token

    # Use API Keys endpoint
    api_keys_api = APIKeysApi(client)
    keys = api_keys_api.list_api_keys_api_v1_api_keys_get()

    print(f"Found {len(keys)} API keys")

    # GDPR: Export user data
    gdpr_api = GDPRComplianceApi(client)
    user_data = gdpr_api.export_user_data_api_v1_users_me_data_get()

    print(f"Exported data for user: {user_data.username}")
```

---

### TypeScript SDK

```bash
cd clients/typescript
npm install
npm run build
```

**Usage:**
```typescript
import {
  Configuration,
  APIKeysApi,
  GDPRComplianceApi,
  AuthApi,
  LoginRequest
} from 'mcp-client';

// Configure API client
const config = new Configuration({
  basePath: 'https://api.example.com'
});

const authApi = new AuthApi(config);
const apiKeysApi = new APIKeysApi(config);
const gdprApi = new GDPRComplianceApi(config);

// Authenticate
const loginRequest: LoginRequest = {
  username: 'alice',
  password: 'secret'
};

const loginResponse = await authApi.loginAuthLoginPost(loginRequest);
const token = loginResponse.data.access_token;

// Configure authenticated client
config.accessToken = token;

// List API keys
const keys = await apiKeysApi.listApiKeysApiV1ApiKeysGet();
console.log(`Found ${keys.data.length} API keys`);

// GDPR: Export user data
const userData = await gdprApi.exportUserDataApiV1UsersMeDataGet();
console.log(`Exported data for user: ${userData.data.username}`);
```

---

### Go SDK

```bash
cd clients/go
go mod init github.com/yourorg/mcp-client
go mod tidy
```

**Usage:**
```go
package main

import (
    "context"
    "fmt"
    "github.com/yourorg/mcp-client"
)

func main() {
    // Configure API client
    config := mcpclient.NewConfiguration()
    config.Host = "api.example.com"
    config.Scheme = "https"

    client := mcpclient.NewAPIClient(config)
    ctx := context.Background()

    // Authenticate
    loginReq := mcpclient.LoginRequest{
        Username: "alice",
        Password: "secret",
    }

    loginResp, _, err := client.AuthApi.LoginAuthLoginPost(ctx).
        LoginRequest(loginReq).
        Execute()
    if err != nil {
        panic(err)
    }

    token := loginResp.GetAccessToken()

    // Configure authenticated context
    authCtx := context.WithValue(ctx, mcpclient.ContextAccessToken, token)

    // List API keys
    keys, _, err := client.APIKeysApi.ListApiKeysApiV1ApiKeysGet(authCtx).
        Execute()
    if err != nil {
        panic(err)
    }

    fmt.Printf("Found %d API keys\n", len(keys))

    // GDPR: Export user data
    userData, _, err := client.GDPRComplianceApi.ExportUserDataApiV1UsersMeDataGet(authCtx).
        Execute()
    if err != nil {
        panic(err)
    }

    fmt.Printf("Exported data for user: %s\n", userData.GetUsername())
}
```

---

## API Endpoints

### Authentication
- `POST /auth/login` - JWT authentication
- `POST /auth/refresh` - Refresh token

### API Keys
- `POST /api/v1/api-keys/` - Create API key
- `GET /api/v1/api-keys/` - List API keys
- `POST /api/v1/api-keys/{id}/rotate` - Rotate key
- `DELETE /api/v1/api-keys/{id}` - Revoke key

### Service Principals
- `POST /api/v1/service-principals/` - Create service principal
- `GET /api/v1/service-principals/` - List service principals
- `POST /api/v1/service-principals/{id}/rotate-secret` - Rotate secret
- `DELETE /api/v1/service-principals/{id}` - Delete service principal

### GDPR Compliance
- `GET /api/v1/users/me/data` - Export user data (Article 15)
- `GET /api/v1/users/me/export` - Portable export (Article 20)
- `PATCH /api/v1/users/me` - Update profile (Article 16)
- `DELETE /api/v1/users/me` - Delete account (Article 17)
- `POST /api/v1/users/me/consent` - Update consent (Article 21)
- `GET /api/v1/users/me/consent` - Get consent status

### SCIM 2.0
- `POST /scim/v2/Users` - Create user
- `GET /scim/v2/Users/{id}` - Get user
- `PUT /scim/v2/Users/{id}` - Replace user
- `PATCH /scim/v2/Users/{id}` - Update user
- `DELETE /scim/v2/Users/{id}` - Deactivate user
- `GET /scim/v2/Users?filter=...` - Search users
- `POST /scim/v2/Groups` - Create group
- `GET /scim/v2/Groups/{id}` - Get group
- `PATCH /scim/v2/Groups/{id}` - Update group

### API Metadata
- `GET /api/version` - Version information

---

## Features

All generated SDKs include:

- ✅ **Type Safety** - Full type hints/annotations
- ✅ **Authentication** - JWT, API keys, service principals
- ✅ **Error Handling** - Structured exceptions
- ✅ **Rate Limiting** - Automatic retry with backoff
- ✅ **Pagination** - Built-in pagination support
- ✅ **Async Support** - Async/await patterns (where applicable)
- ✅ **Documentation** - Generated markdown docs
- ✅ **Unit Tests** - Auto-generated test templates

---

## OpenAPI Specifications

- **`../openapi/v1.json`** - Main API spec (22 endpoints, 42 schemas)
- **`../openapi/mcp-tools.json`** - MCP tools spec (3 tools, 6 schemas)

---

## Regenerating SDKs

To regenerate after API changes:

```bash
# Update OpenAPI spec
python -c "
import json
from mcp_server_langgraph.mcp.server_streamable import app
schema = app.openapi()
with open('openapi/v1.json', 'w') as f:
    json.dump(schema, f, indent=2)
"

# Regenerate all SDKs
docker run --rm \
  -v "$(pwd):/local" \
  openapitools/openapi-generator-cli:latest batch \
  --clean /local/generators/batch-config.yaml
```

---

## Publishing

### Python (PyPI)
```bash
cd clients/python
python -m build
twine upload dist/*
```

### TypeScript (npm)
```bash
cd clients/typescript
npm publish
```

### Go (GitHub)
```bash
cd clients/go
git tag v2.8.0
git push origin v2.8.0
```

---

**Generated from:** OpenAPI 3.1.0 specification
**Version:** 2.8.0
**Last Updated:** 2025-11-02
