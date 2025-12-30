# OpenFGA Authorization Configuration

This directory contains the OpenFGA authorization model and sample relationship tuples for the MCP Server LangGraph project.

## Files

| File | Purpose |
|------|---------|
| `model.json` | Authorization model defining types, relations, and permission inheritance |
| `sample-tuples.json` | Relationship tuples for test users (admin, alice, bob) |

## Authorization Model Overview

The model follows **Relationship-Based Access Control (ReBAC)** principles from [ADR-0068](../../adr/adr-0068-gateway-level-authentication.md).

### Types and Relations

| Type | Relations | Description |
|------|-----------|-------------|
| `user` | (none) | User identity type |
| `organization` | `member`, `admin` | Organization membership |
| `tool` | `owner`, `executor`, `organization` | MCP tool permissions |
| `conversation` | `owner`, `viewer`, `editor` | Chat conversation access |
| `vector_store` | `owner`, `editor`, `viewer`, `organization` | Qdrant vector database |
| `workflow` | `owner`, `editor`, `viewer`, `executor`, `organization`, `project` | LangGraph workflows |
| `session` | `owner`, `viewer`, `organization`, `project` | Workflow execution sessions |
| `project` | `owner`, `editor`, `viewer`, `executor`, `organization` | Unified workspace container |
| `mcp` | `user`, `viewer` | MCP WebSocket protocol access |
| `mcp_connection` | `owner`, `viewer` | MCP connection management |
| `dashboard` | `admin`, `editor`, `viewer`, `organization` | Grafana dashboard access |
| `cost` | `admin`, `viewer`, `organization` | Cost tracking access |
| `observability` | `admin`, `viewer`, `organization` | Traces/metrics/logs access |
| `authz` | `admin`, `viewer` | OpenFGA Playground UI access |
| `ai` | `user`, `viewer` | AI suggestions WebSocket access |
| `budget` | `admin`, `viewer` | Budget alerts WebSocket access |

## Computed Relations (Important!)

Some relations are **computed** from other relations and **cannot be directly assigned** via tuples. Attempting to create tuples with computed relations will fail with `validation_error`.

### Direct vs Computed Relations

| Type | Direct Relations | Computed Relations |
|------|-----------------|-------------------|
| `mcp` | `user` | `viewer` (from `user`) |
| `ai` | `user` | `viewer` (from `user`) |
| `api_key` | `owner` | `viewer`, `revoker` (from `owner`) |
| `service_principal` | `owner`, `acts_as` | `viewer`, `editor` (from `owner`) |

### Example: `mcp` Type

```json
{
  "type": "mcp",
  "relations": {
    "user": { "this": {} },          // Direct - can assign tuples
    "viewer": {                       // Computed - DO NOT assign tuples
      "computedUserset": {"relation": "user"}
    }
  }
}
```

**Correct tuple:**
```json
{"user": "user:alice", "relation": "user", "object": "mcp:websocket"}
```

**Incorrect tuple (will fail):**
```json
{"user": "user:alice", "relation": "viewer", "object": "mcp:websocket"}
```

The `viewer` permission is automatically granted to anyone with the `user` relation.

## Relation Inheritance Patterns

### Owner → Editor → Viewer Chain

Many types implement a permission hierarchy where higher permissions imply lower ones:

```
owner → editor → viewer
```

Example from `vector_store`:
```json
{
  "viewer": {
    "union": {
      "child": [
        {"this": {}},                              // Direct viewer
        {"computedUserset": {"relation": "editor"}} // Editors are viewers
      ]
    }
  },
  "editor": {
    "union": {
      "child": [
        {"this": {}},                             // Direct editor
        {"computedUserset": {"relation": "owner"}} // Owners are editors
      ]
    }
  }
}
```

### Organization Membership

Types with `organization` relation can grant access to all organization members:

```json
{
  "viewer": {
    "union": {
      "child": [
        {"this": {}},
        {"tupleToUserset": {
          "tupleset": {"relation": "organization"},
          "computedUserset": {"relation": "member"}
        }}
      ]
    }
  }
}
```

This means: "Anyone who is a `member` of the related `organization` gets `viewer` access."

## Test Users

The sample tuples configure three test users with different permission levels:

| User | Description | Key Permissions |
|------|-------------|-----------------|
| `admin` | Super user | `owner` on all resources, `admin` on dashboards |
| `alice` | Developer | `editor` on vectors, `viewer` on dashboards |
| `bob` | Basic user | `viewer` on vectors (read-only) |

## Seeding

The `openfga-seed-test` Docker container seeds the authorization data:

1. Creates store `mcp-server-langgraph-test`
2. Uploads `model.json`
3. Writes tuples from `sample-tuples.json`
4. Verifies permissions work correctly

## Validation

Before modifying tuples, ensure:

1. **Check if relation is directly assignable** - Look for `"this": {}` in the relation definition
2. **Use correct relation** - For computed relations, use the source relation instead
3. **No duplicates** - The seed script will fail the batch if any tuple already exists

## References

- [ADR-0068: Gateway-Level Authentication](../../adr/adr-0068-gateway-level-authentication.md)
- [ADR-0070: OpenFGA OIDC Authentication Migration](../../adr/adr-0070-openfga-oidc-authentication.md)
- [OpenFGA Documentation](https://openfga.dev/docs)
