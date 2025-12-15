# MCP Connections Feature Documentation

**Version**: 1.0.0
**Last Updated**: 2025-12-14
**Status**: Production Ready

## Overview

The MCP Connections feature provides a comprehensive interface for managing Model Context Protocol (MCP) server connections. It enables users to register, configure, and monitor external MCP servers that provide tools, resources, and prompts to the LangGraph agent.

## Architecture

### Backend Components

```
src/mcp_server_langgraph/
├── api/v1/
│   ├── connections.py          # Main connections API router
│   ├── connections_bulk.py     # Bulk operations API
│   ├── connection_templates.py # Connection templates
│   ├── connection_audit.py     # Audit logging API
│   └── connection_health_ws.py # WebSocket health monitoring
├── repositories/
│   ├── connections.py          # PostgreSQL repository
│   └── cached_connections.py   # Caching wrapper (L1/L2)
├── models/
│   └── connection.py           # SQLAlchemy models
└── core/
    └── secrets.py              # Secure credential storage
```

### Frontend Components

```
src/mcp_server_langgraph/studio/frontend/src/
├── pages/
│   ├── ConnectionsPage.tsx     # Main connections list page
│   └── OAuth2CallbackPage.tsx  # OAuth2 callback handler
├── components/Connection/
│   ├── index.ts                # Barrel export
│   ├── ConnectionDialog.tsx    # Create/Edit dialog
│   ├── ConnectionBulkActions.tsx # Bulk operations bar
│   ├── ConnectionTemplateSelector.tsx # Template picker
│   └── ConnectionAuditLog.tsx  # Audit log viewer
├── hooks/
│   ├── useConnectionHealth.ts  # Real-time health hook
│   └── useKeyboardShortcuts.ts # Keyboard navigation
└── types/
    └── connection.ts           # TypeScript types
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/connections` | List connections with filtering/sorting |
| POST | `/api/v1/connections` | Create new connection |
| GET | `/api/v1/connections/{id}` | Get connection details |
| PUT | `/api/v1/connections/{id}` | Update connection |
| DELETE | `/api/v1/connections/{id}` | Delete connection |
| POST | `/api/v1/connections/{id}/test` | Test connection health |
| GET | `/api/v1/connections/{id}/audit-logs` | Get audit logs |
| GET | `/api/v1/connections/{id}/audit-logs/export` | Export audit logs |
| POST | `/api/v1/connections/bulk/delete` | Bulk delete connections |
| POST | `/api/v1/connections/bulk/test` | Bulk test connections |
| GET | `/api/v1/connections/templates` | List available templates |
| POST | `/api/v1/connections/{id}/oauth2/authorize` | Start OAuth2 flow |
| POST | `/api/v1/connections/{id}/oauth2/callback` | Complete OAuth2 flow |

### Query Parameters (List)

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Full-text search on name, description, URL |
| `status` | string | Filter by status: connected, disconnected, error, auth_required |
| `auth_type` | string | Filter by auth: none, api_key, oauth2 |
| `project_id` | string | Filter by project |
| `sort_by` | string | Sort field: name, created_at, updated_at, status |
| `sort_order` | string | Sort direction: asc, desc |
| `limit` | int | Page size (default: 20, max: 100) |
| `cursor` | string | Pagination cursor |

### Response Models

#### MCPConnection
```typescript
interface MCPConnection {
  id: string;
  name: string;
  description?: string;
  url: string;
  auth_type: 'none' | 'api_key' | 'oauth2';
  status: 'connected' | 'disconnected' | 'connecting' | 'error' | 'auth_required';
  owner_id: string;
  project_id?: string;
  server_name?: string;
  server_version?: string;
  tool_count?: number;
  resource_count?: number;
  prompt_count?: number;
  last_error?: string;
  created_at: string;
  updated_at: string;
}
```

#### MCPConnectionCreate
```typescript
interface MCPConnectionCreate {
  name: string;
  description?: string;
  url: string;
  auth_type: 'none' | 'api_key' | 'oauth2';
  api_key?: string;
  oauth2_client_id?: string;
  oauth2_client_secret?: string;
  project_id?: string;
}
```

## Features

### 1. Connection Management

- **Create**: Add new MCP server connections with various auth types
- **Edit**: Update connection details and reconfigure authentication
- **Delete**: Remove connections with cascade deletion of related data
- **Test**: Validate connection health and retrieve server capabilities

### 2. Authentication Types

| Type | Description | Flow |
|------|-------------|------|
| None | No authentication | Direct connection |
| API Key | Static API key | Key stored encrypted in PostgreSQL |
| OAuth2 | OAuth2 with PKCE | Authorization code flow with PKCE |

### 3. Real-time Status Monitoring

- WebSocket-based health updates
- Configurable polling intervals (5s, 10s, 30s, or off)
- Visual status indicators with color coding

### 4. Bulk Operations

- Select multiple connections with checkboxes
- Bulk delete with confirmation
- Bulk test with parallel execution

### 5. Connection Templates

Predefined templates for popular MCP servers:
- GitHub MCP Server
- Slack MCP Server
- Google Drive MCP Server
- Notion MCP Server
- Custom template option

### 6. Audit Logging

Every connection operation is logged with:
- Action type (create, update, delete, test)
- Actor (user ID and email)
- Timestamp
- Before/after state (for updates)
- Result status

Export formats: JSON, CSV

### 7. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New connection |
| Ctrl+F | Focus search |
| Ctrl+R | Refresh list |
| Ctrl+A | Select all |
| Delete | Delete selected |
| Escape | Close modal |

## Caching Strategy

### L1 Cache (In-Memory LRU)
- Scope: Per-instance
- TTL: 5 minutes (connections), 1 minute (health)
- Size: 1000 entries max
- Latency: < 1ms

### L2 Cache (Redis)
- Scope: Distributed
- TTL: 5 minutes (connections), 1 minute (health)
- Latency: < 10ms

### Cache Invalidation
- Automatic on write operations (create, update, delete)
- Manual via `invalidate_connection()` method
- Pattern-based clearing for list caches

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OAUTH2_REDIRECT_URI` | `http://localhost:5173/studio/oauth/callback` | OAuth2 callback URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection for L2 cache |
| `REDIS_PASSWORD` | (none) | Redis authentication password |
| `REDIS_SSL` | `false` | Enable SSL for Redis |

### Database Schema

```sql
-- Main connections table
CREATE TABLE mcp_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(1024) NOT NULL,
    auth_type VARCHAR(50) NOT NULL DEFAULT 'none',
    status VARCHAR(50) NOT NULL DEFAULT 'disconnected',
    owner_id VARCHAR(255) NOT NULL,
    project_id UUID REFERENCES projects(id),
    server_name VARCHAR(255),
    server_version VARCHAR(100),
    tool_count INTEGER DEFAULT 0,
    resource_count INTEGER DEFAULT 0,
    prompt_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit logs table
CREATE TABLE connection_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    actor_id VARCHAR(255) NOT NULL,
    actor_email VARCHAR(255),
    details JSONB,
    status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_connections_owner ON mcp_connections(owner_id);
CREATE INDEX idx_connections_status ON mcp_connections(status);
CREATE INDEX idx_connections_fts ON mcp_connections USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));
CREATE INDEX idx_audit_logs_connection ON connection_audit_logs(connection_id);
CREATE INDEX idx_audit_logs_created ON connection_audit_logs(created_at DESC);
```

## Testing

### Unit Tests
- `tests/unit/repositories/test_cached_connections.py` - Cache behavior
- `frontend/src/hooks/useKeyboardShortcuts.test.ts` - Keyboard shortcuts
- `frontend/src/pages/ConnectionsPage.test.tsx` - UI components

### Integration Tests
- `tests/integration/test_connections_repository.py` - Database operations
- `tests/api/test_connections_api.py` - API endpoints

### E2E Tests
- `tests/e2e/journeys/test_connections_journey.py` - Complete user flows

## Security Considerations

### Credential Storage
- API keys encrypted at rest using AES-256
- OAuth2 tokens stored in PostgreSQL with expiry tracking
- PKCE used for OAuth2 to prevent authorization code interception

### Authorization
- OpenFGA-based fine-grained access control
- Connection ownership enforced at repository level
- Audit logs for compliance and forensics

### Rate Limiting
- 100 requests/minute per user for list operations
- 10 requests/minute per connection for test operations

## Troubleshooting

### Connection Stuck in "Connecting"
1. Check MCP server is accessible from backend
2. Verify network/firewall rules allow outbound connections
3. Check server logs for SSL/TLS errors

### OAuth2 Flow Fails
1. Verify `OAUTH2_REDIRECT_URI` matches Keycloak configuration
2. Check OAuth2 client credentials are correct
3. Ensure PKCE is enabled on the OAuth2 server

### Cache Inconsistency
1. Clear cache manually: `cache.clear("connection:*")`
2. Check Redis connectivity
3. Verify TTL settings match expected freshness

## Changelog

### v1.0.0 (2025-12-14)
- Initial release with full CRUD operations
- OAuth2 PKCE authentication support
- Bulk operations (delete, test)
- Connection templates
- Audit logging with export
- L1/L2 caching for performance
- Keyboard shortcuts for power users
- Real-time status monitoring via polling
