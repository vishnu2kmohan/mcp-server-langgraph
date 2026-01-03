# Chat-to-Workflow API Documentation

**Date**: 2026-01-03
**Status**: Implemented
**Plan**: ~/.claude/plans/greedy-wiggling-marshmallow.md
**ADR**: adr-0089-prompt-architecture-centralization.md

---

## Executive Summary

This document describes the API endpoints for the Chat-to-Workflow feature, which enables generating durable, versioned workflows from chat session history. The feature implements a full draft/publish lifecycle with validation, version history, and telemetry linkage.

### Key Principles

1. **Centralized Validation** - All validation logic resides in `WorkflowValidator` service. NO JavaScript duplication.
2. **Version Immutability** - `workflow_versions` table is append-only for auditability.
3. **Telemetry Linkage** - Each version stores `prompt_version` and `prompt_model` for optimization analytics.
4. **Sanitization First** - All session content is sanitized via `security/prompt_injection.py` before LLM exposure.

---

## API Endpoints

### 1. Generate Workflow from Chat

Generate a workflow from chat session history. Persists as a draft with version 1.

**Endpoint**: `POST /api/v1/workflows/from-chat`

**Feature Flag**: `FF_ENABLE_WORKFLOW_FROM_CHAT`

#### Request

```typescript
interface GenerateWorkflowFromChatRequest {
  session_id: string;           // Required: Session ID to generate from
  refinement_mode?: "auto" | "plan";  // Optional: Generation mode
  template_id?: string;         // Optional: Template to base workflow on
}
```

#### Response

```typescript
interface GenerateWorkflowFromChatResponse {
  workflow: Workflow;           // Persisted workflow (status='draft', version=1)
  confidence: number;           // Confidence score (0.0-1.0)
  suggestions: string[];        // Improvement suggestions
  prompt_metadata: {
    name: string;               // Prompt name ("workflow_generator")
    version: string;            // Prompt version ("v1")
    hash: string;               // SHA-256 hash of prompt content
    model: string;              // LLM model used
  };
  plan?: Record<string, unknown>;  // Execution plan (if refinement_mode="plan")
}
```

#### Example

```bash
curl -X POST http://localhost/api/v1/workflows/from-chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-abc123",
    "refinement_mode": "auto"
  }'
```

#### Errors

| Status | Code | Description |
|--------|------|-------------|
| 400 | `INVALID_SESSION` | Session ID not found or empty |
| 400 | `GENERATION_FAILED` | LLM failed to generate valid workflow |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | User doesn't have access to session |
| 404 | `SESSION_NOT_FOUND` | Session with given ID doesn't exist |
| 503 | `LLM_UNAVAILABLE` | LLM provider temporarily unavailable |

---

### 2. Validate Workflow

Validate a workflow's graph structure using the centralized `WorkflowValidator` service.

**Endpoint**: `POST /api/v1/workflows/{workflow_id}/validate`

**No feature flag required** - Always available when workflows feature is enabled.

#### Request

URL parameter:
- `workflow_id` (string): ID of the workflow to validate

#### Response

```typescript
interface ValidateWorkflowResponse {
  valid: boolean;               // Whether workflow passed validation
  errors: string[];             // Blocking validation errors
  warnings: string[];           // Non-blocking warnings
}
```

#### Example

```bash
curl -X POST http://localhost/api/v1/workflows/wf-123/validate \
  -H "Authorization: Bearer $TOKEN"
```

#### Response Example

```json
{
  "valid": false,
  "errors": [
    "Missing start node",
    "Orphan node detected: 'node-xyz'"
  ],
  "warnings": [
    "Consider adding error handling for node 'llm-call'"
  ]
}
```

#### Validation Rules

| Rule | Type | Description |
|------|------|-------------|
| Single Start | Error | Exactly one start node required |
| Reachable End | Error | All paths must reach an end node |
| Acyclic Graph | Error | No circular dependencies |
| No Orphans | Error | All nodes must be connected |
| Edge Targets Exist | Error | All edge targets must exist |
| Tool Availability | Warning | Referenced tools should be available |

---

### 3. Get Workflow Versions

Retrieve version history for a workflow.

**Endpoint**: `GET /api/v1/workflows/{workflow_id}/versions`

#### Request

URL parameter:
- `workflow_id` (string): ID of the workflow

#### Response

```typescript
interface WorkflowVersion {
  id: string;
  workflow_id: string;
  version_number: number;
  graph_json: {
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  };
  source_text?: string;         // Python/YAML representation
  commit_message?: string;      // Description of changes
  created_by: string;           // User who created version
  created_at: string;           // ISO 8601 timestamp
  prompt_version?: string;      // Prompt version used
  prompt_model?: string;        // LLM model used
}

// Response is array of versions, newest first
type GetWorkflowVersionsResponse = WorkflowVersion[];
```

#### Example

```bash
curl http://localhost/api/v1/workflows/wf-123/versions \
  -H "Authorization: Bearer $TOKEN"
```

---

### 4. Restore Workflow Version

Restore a workflow to a previous version. Creates a new version with the restored state.

**Endpoint**: `POST /api/v1/workflows/{workflow_id}/versions/{version_id}/restore`

#### Request

URL parameters:
- `workflow_id` (string): ID of the workflow
- `version_id` (string): ID of the version to restore

#### Response

Returns the updated `Workflow` object with incremented version number.

#### Example

```bash
curl -X POST http://localhost/api/v1/workflows/wf-123/versions/v-456/restore \
  -H "Authorization: Bearer $TOKEN"
```

---

## Frontend Integration

### RTK Query Hooks

The frontend provides these RTK Query hooks for the API:

```typescript
// Generate workflow from chat
useGenerateWorkflowFromChatMutation()

// Validate workflow
useValidateWorkflowMutation()

// Get workflow versions
useGetWorkflowVersionsQuery(workflowId)

// Restore a version
useRestoreWorkflowVersionMutation()
```

### Custom Hooks

For higher-level abstractions:

```typescript
// Full generation flow with navigation
useGenerateWorkflowFromChat(sessionId: string)

// Debounced validation with status
useWorkflowValidation({ debounceMs: 300 })

// WebSocket real-time validation events
useWorkflowValidationWebSocket({ workflowId, onValidationFailed })
```

### Components

| Component | Purpose |
|-----------|---------|
| `GenerateWorkflowButton` | Button in chat panel to trigger generation |
| `WorkflowEditor` | Main editor with visual/code tabs |
| `WorkflowVersionHistory` | Version history panel with restore |

---

## WebSocket Events

Real-time validation events are broadcast via the `orchestrator_status` WebSocket endpoint.

**Endpoint**: `ws://localhost/api/v1/ws/orchestrator/status`

### Event Types

```typescript
interface WorkflowValidationEvent {
  type:
    | "workflow_validation_started"
    | "workflow_validation_passed"
    | "workflow_validation_failed"
    | "workflow_draft_saved"
    | "workflow_published";
  workflow_id: string;
  user_id?: string;
  errors?: string[];
  warnings?: string[];
  timestamp?: string;
}
```

---

## Data Model

### Workflow Table (Extended)

```sql
ALTER TABLE workflows ADD COLUMN head_version_id VARCHAR(36);
ALTER TABLE workflows ADD COLUMN source_text TEXT;
ALTER TABLE workflows ADD COLUMN status VARCHAR(20) DEFAULT 'draft';
ALTER TABLE workflows ADD COLUMN version INT DEFAULT 1;
```

### Workflow Versions Table

```sql
CREATE TABLE workflow_versions (
    id VARCHAR(36) PRIMARY KEY,
    workflow_id VARCHAR(36) NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    graph_json JSONB NOT NULL,
    source_text TEXT,
    commit_message TEXT,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prompt_version VARCHAR(50),
    prompt_model VARCHAR(100),

    UNIQUE (workflow_id, version_number),
    CHECK (version_number > 0)
);
```

---

## Security Considerations

1. **Sanitization**: All session messages are sanitized via `sanitize_content()` before LLM exposure
2. **Authorization**: OpenFGA checks ensure user has access to the session
3. **Rate Limiting**: Generation endpoint is rate-limited to prevent abuse
4. **Audit Logging**: All workflow operations are logged to audit trail

---

## Telemetry

Each workflow version stores telemetry metadata for optimization:

```sql
-- Which prompt version produces the most published workflows?
SELECT prompt_version, COUNT(*) as published_count
FROM workflow_versions wv
JOIN workflows w ON wv.workflow_id = w.id
WHERE w.status = 'published'
GROUP BY prompt_version
ORDER BY published_count DESC;
```

Prometheus metrics:
- `workflow_generation_total{status="success|failure"}`
- `workflow_generation_duration_seconds`
- `workflow_validation_total{valid="true|false"}`
- `workflow_version_created_total`

---

## Feature Flag

```python
# In feature_flags.py
FF_ENABLE_WORKFLOW_FROM_CHAT = Field(
    default=False,
    description="Enable chat-to-workflow generation with versioning. "
    "Requires workflow_versions table migration."
)
```

Enable in environment:
```bash
FF_ENABLE_WORKFLOW_FROM_CHAT=true
```
