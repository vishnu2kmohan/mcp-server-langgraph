# 2. Fine-Grained Authorization with OpenFGA

Date: 2025-10-11

## Status

Accepted

## Category

Authentication & Authorization

## Context

The MCP server needs enterprise-grade authorization to control who can:
- Execute specific tools
- Access certain conversations
- View resources
- Manage organizational settings

Requirements:
- **Fine-grained control**: User-level and resource-level permissions
- **Relationship-based**: "Alice can execute tools in Org A"
- **Scalable**: Support thousands of users and resources
- **Auditable**: Track authorization decisions
- **Flexible**: Add new permission models without code changes

Traditional RBAC (Role-Based Access Control) is too coarse-grained. We need to express complex relationships like:
- "Members of Organization X can execute Tool Y"
- "User Alice is a viewer of Conversation Z"
- "Admins of Org A inherit all permissions"

## Decision

We will use **OpenFGA** (Zanzibar-inspired authorization) for fine-grained access control.

OpenFGA provides:
- **Relationship-based authorization**: Model any permission structure
- **Google-proven**: Based on Google's Zanzibar paper
- **Flexible modeling**: Define custom authorization schemas
- **High performance**: Sub-100ms authorization checks
- **Check API**: Simple `check(user, relation, object)` interface
- **Relationship management**: Add/remove permissions dynamically

Implementation in `openfga_client.py`:
- Authorization model with types: user, organization, tool, conversation, role
- Relations: member, admin, executor, viewer, editor, owner
- Integration with AuthMiddleware

## Consequences

### Positive Consequences

- **Fine-Grained Control**: Express complex permissions easily
- **Scalability**: Proven to handle Google-scale workloads
- **Flexibility**: Change permission models without code changes
- **Separation of Concerns**: Authorization logic separate from business logic
- **Audit Trail**: All authorization decisions logged
- **Industry Standard**: Based on proven Zanzibar architecture

### Negative Consequences

- **Complexity**: Requires understanding relationship-based authz
- **Infrastructure**: Needs OpenFGA server running
- **Learning Curve**: Team must learn OpenFGA concepts
- **Debugging**: Relationship chains can be hard to trace
- **Setup Overhead**: Initial model configuration required
- **Latency**: External API call for each check (mitigated with caching)

### Neutral Consequences

- **Fallback Mode**: System works without OpenFGA (degraded permissions)
- **Migration**: Moving from simple to complex permissions is gradual

## Alternatives Considered

### 1. Simple RBAC (Role-Based Access Control)

**Description**: Assign roles to users, roles have permissions

**Example**:
```python
if user.has_role('admin') or user.has_role('premium'):
    allow_tool_execution()
```

**Pros**:
- Simple to understand
- No external dependencies
- Fast permission checks
- Easy to implement

**Cons**:
- Too coarse-grained for enterprise needs
- Can't express "User A can access Resource B"
- Role explosion (need role per combination)
- Hard to model organizational hierarchies

**Why Rejected**: Insufficient for production requirements

### 2. ABAC (Attribute-Based Access Control)

**Description**: Define policies based on attributes (user.department == resource.department)

**Pros**:
- Flexible policy expressions
- Can handle complex scenarios
- No relationship modeling needed

**Cons**:
- Policy evaluation can be slow
- Difficult to reason about combined policies
- No standard implementation
- Hard to audit "why was this allowed?"

**Why Rejected**: More complex without clear benefits over OpenFGA

### 3. Casbin

**Description**: Another relationship-based authorization framework

**Pros**:
- Similar to OpenFGA
- Good documentation
- Active community

**Cons**:
- Less mature than Zanzibar-based solutions
- Not as scalable (no Google proof)
- Policy syntax more complex
- Fewer production deployments

**Why Rejected**: OpenFGA has stronger industry backing

### 4. Cloud Provider IAM (AWS IAM, Google Cloud IAM)

**Description**: Use cloud provider's built-in IAM

**Pros**:
- Highly scalable
- Well-tested
- Integrated with cloud services

**Cons**:
- Vendor lock-in
- Not portable across clouds
- Overkill for application-level authz
- Complex policy syntax

**Why Rejected**: Too cloud-specific, not portable

### 5. Custom Authorization Logic

**Description**: Build permission checks in application code

**Pros**:
- Full control
- No external dependencies
- Fast (in-memory)

**Cons**:
- Reinventing the wheel
- Hard to maintain
- No separation of concerns
- Difficult to audit
- Not declarative

**Why Rejected**: Not sustainable for complex permissions

## Implementation Details

### Authorization Model

The authorization model defines 37 types across multiple domains:

**Core Identity**:
- `user` - Individual users
- `organization` - Multi-tenant organizations with `member`, `admin`, `user_in_context` relations
- `service_principal` - Automated services with `acts_as` for permission inheritance

**Resource Types**:
- `tool` - MCP tools with `owner`, `executor`, `organization` relations
- `conversation` - Chat threads with `owner`, `editor`, `viewer` relations
- `vector_store` - Qdrant collections with RBAC hierarchy
- `artifact` - Files and generated content with project hierarchy
- `workflow`, `session`, `project` - LangGraph execution resources

**Access Control**:
- `authz` - OpenFGA Playground access
- `system` - System-level access (admin → developer → user → viewer monotonic chain)
- `ai` - AI features (admin → user inheritance)
- `skill` - Skills (admin → author → viewer hierarchy)

**Infrastructure**:
- `dashboard`, `logs`, `traces`, `metrics`, `gateway`, `identity` - Observability
- `budget`, `cost`, `compliance` - Financial and compliance
- `mcp`, `mcp_connection`, `connection` - MCP protocol

**Semantic Search** (ADR-0099):
- `tool_index`, `skill_index`, `memory_index` - Vector search indices

**Example Model (schema 1.1)**:
```yaml
model
  schema 1.1

type user

type organization
  relations
    define member: [user]
    define admin: [user] or member
    define user_in_context: [user]  # For contextual tuples (ADR-0068 Phase 3)

type tool
  relations
    define organization: [organization]
    define owner: [user, service_principal]
    define executor: [user, service_principal] or owner or organization.member

type conversation
  relations
    define owner: [user]
    define viewer: [user, user:*] or owner
    define editor: [user] or owner

type system
  relations
    define admin: [user]
    define developer: [user] or admin
    define user: [user] or developer
    define viewer: [user] or user  # Monotonic: admin→developer→user→viewer
```

**Conditions (OpenFGA v1.11.2+)**:
```json
"conditions": {
  "time_bound_share": {"expression": "current_time < expiry_time"},
  "subscription_tier": {"expression": "user_tier == required_tier || user_tier == 'enterprise'"}
}
```

### Usage

```python
# Check permission
authorized = await auth.authorize(
    user_id="user:alice",
    relation="executor",
    resource="tool:chat"
)

# Write relationship
await openfga.write_tuples([
    {"user": "user:alice", "relation": "admin", "object": "organization:acme"}
])
```

### Fallback Strategy

When OpenFGA unavailable:
- Fail-open (default): Allow with warning
- Fail-closed (strict mode): Deny all access
- Configurable via `openfga_strict_mode` feature flag

## References

- [OpenFGA Documentation](https://openfga.dev/)
- [Google Zanzibar Paper](https://research.google/pubs/pub48190/)
- [integrations/openfga-infisical.md](../integrations/openfga-infisical.md)
- Related Files: `openfga_client.py`, `src/mcp_server_langgraph/auth/middleware.py`, `scripts/setup_openfga.py`
