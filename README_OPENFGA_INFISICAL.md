# LangGraph MCP Agent with OpenFGA & Infisical

Complete integration guide for fine-grained authorization and secrets management.

## 🔐 Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    MCP Client                             │
│              (Claude Desktop / Other)                     │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│                  MCP Server                               │
│  ┌────────────────────────────────────────────────┐      │
│  │  Auth Middleware                               │      │
│  │  - JWT Authentication                          │      │
│  │  - OpenFGA Authorization ──────────┐           │      │
│  └────────────────────────────────────┼───────────┘      │
│                                        │                  │
│  ┌────────────────────────────────────┼───────────┐      │
│  │  LangGraph Agent                   │           │      │
│  │  - State Management                │           │      │
│  │  - Tool Execution                  │           │      │
│  │  - Conversation Handling           │           │      │
│  └────────────────────────────────────┼───────────┘      │
└────────────────────┬───────────────────┼──────────────────┘
                     │                   │
        ┌────────────┴──────┐           │
        ▼                   ▼           ▼
┌──────────────┐    ┌──────────────┐   ┌──────────────┐
│  Infisical   │    │ OpenTelemetry│   │   OpenFGA    │
│  (Secrets)   │    │ (Observability)  │(Authorization)│
└──────────────┘    └──────────────┘   └──────────────┘
```

## 🚀 Quick Start

### 1. Start Infrastructure

```bash
# Start observability stack and OpenFGA
docker-compose up -d

# Verify services are running
docker-compose ps
```

Services:
- **OpenFGA**: http://localhost:8080 (API), http://localhost:3000 (Playground)
- **Jaeger**: http://localhost:16686
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

### 2. Setup OpenFGA

```bash
# Initialize OpenFGA with authorization model and sample data
python setup_openfga.py
```

This creates:
- Authorization store
- Authorization model (users, organizations, tools, conversations, roles)
- Sample relationship tuples
- Runs verification tests

**Important**: Save the `OPENFGA_STORE_ID` and `OPENFGA_MODEL_ID` to your `.env` file!

### 3. Setup Infisical (Optional but Recommended)

```bash
# Setup Infisical secrets management
python setup_infisical.py
```

To use Infisical:
1. Sign up at https://app.infisical.com
2. Create a project
3. Generate Universal Auth credentials
4. Add to `.env`:
   ```
   INFISICAL_CLIENT_ID=your-client-id
   INFISICAL_CLIENT_SECRET=your-client-secret
   INFISICAL_PROJECT_ID=your-project-id
   ```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
```env
ANTHROPIC_API_KEY=sk-ant-...
OPENFGA_STORE_ID=01HZXX...  # From setup_openfga.py
OPENFGA_MODEL_ID=01HZXX...  # From setup_openfga.py
```

## 🔑 OpenFGA Authorization Model

### Type Definitions

```
user              - Individual users
organization      - Organizations (multi-tenant)
tool              - AI tools (chat, search, etc.)
conversation      - Conversation threads
role              - User roles (premium, standard, etc.)
```

### Relations

| Resource | Relation | Description |
|----------|----------|-------------|
| organization | member | User is member of organization |
| organization | admin | User is admin of organization |
| tool | executor | User can execute tool |
| tool | owner | User owns tool |
| tool | organization | Tool belongs to organization |
| conversation | owner | User owns conversation |
| conversation | viewer | User can view conversation |
| conversation | editor | User can edit conversation |
| role | assignee | User is assigned role |

### Inheritance Rules

- **Tool Execution**: Users can execute tools if:
  - Directly granted `executor` relation
  - They own the tool (`owner` → `executor`)
  - They're members of the tool's organization

- **Conversation Access**: Users can view conversations if:
  - Directly granted `viewer` relation
  - They own the conversation (`owner` → `viewer`)

### Example Relationships

```python
# Organization membership
user:alice is member of organization:acme
user:alice is admin of organization:acme

# Tool access
user:alice can execute tool:chat
organization:acme organization of tool:chat

# Conversation ownership
user:alice owns conversation:thread_1
user:bob can view conversation:thread_1
```

## 🔒 Infisical Secrets Management

### Configuration

Secrets are loaded with this priority:
1. **Infisical** (if configured)
2. **Environment variables** (fallback)
3. **Default values** (last resort)

### Usage in Code

```python
from secrets_manager import get_secrets_manager

secrets_mgr = get_secrets_manager()

# Get secret with fallback
api_key = secrets_mgr.get_secret("ANTHROPIC_API_KEY", fallback=None)

# Get secret (raises if not found)
jwt_key = secrets_mgr.get_secret("JWT_SECRET_KEY")

# Create/update secrets
secrets_mgr.create_secret("NEW_SECRET", "value", secret_comment="Description")
secrets_mgr.update_secret("EXISTING_SECRET", "new_value")

# List all secrets
all_secrets = secrets_mgr.get_all_secrets()

# Invalidate cache
secrets_mgr.invalidate_cache("SPECIFIC_KEY")
secrets_mgr.invalidate_cache()  # Clear all
```

### Automatic Loading

Secrets are automatically loaded in `config.py`:

```python
from config import settings

# Secrets loaded from Infisical or environment
jwt_secret = settings.jwt_secret_key
anthropic_key = settings.anthropic_api_key
```

## 🛠️ MCP Server Integration

### Running the Server

```bash
python mcp_server.py
```

### Available Tools

#### 1. `chat`
Chat with the AI agent.

**Requirements**:
- User must have `executor` relation on `tool:chat`
- User must have `editor` relation on target conversation

**Input**:
```json
{
  "message": "Your message",
  "username": "alice",
  "thread_id": "thread_1"
}
```

#### 2. `get_conversation`
Retrieve conversation history.

**Requirements**:
- User must have `viewer` relation on target conversation

**Input**:
```json
{
  "thread_id": "thread_1",
  "username": "alice"
}
```

#### 3. `list_conversations`
List all accessible conversations.

**Requirements**:
- Authenticated user

**Input**:
```json
{
  "username": "alice"
}
```

### Authorization Flow

```
1. User calls MCP tool with username
2. Server authenticates user (JWT)
3. Server checks OpenFGA for tool execution permission
4. Server checks OpenFGA for resource access (conversation)
5. If authorized, execute tool
6. Return results with full tracing
```

## 📊 Testing

### Test Authorization Rules

```bash
python example_openfga_usage.py
```

This demonstrates:
- Tool access checks
- Conversation ownership/viewing
- Organization-based permissions
- Listing accessible resources
- Adding/removing relationships
- Expanding relationships

### Test MCP Server

```bash
python example_client.py
```

Tests:
- Authentication (success/failure)
- Tool execution authorization
- Conversation access control
- Listing conversations
- Unauthorized access attempts

## 🔧 Adding Users and Permissions

### Grant User Access to Tool

```python
from openfga_client import OpenFGAClient
from config import settings

client = OpenFGAClient(
    api_url=settings.openfga_api_url,
    store_id=settings.openfga_store_id,
    model_id=settings.openfga_model_id
)

await client.write_tuples([
    {
        "user": "user:charlie",
        "relation": "executor",
        "object": "tool:chat"
    }
])
```

### Grant User Access to Conversation

```python
await client.write_tuples([
    {
        "user": "user:charlie",
        "relation": "viewer",
        "object": "conversation:thread_1"
    }
])
```

### Add User to Organization

```python
await client.write_tuples([
    {
        "user": "user:charlie",
        "relation": "member",
        "object": "organization:acme"
    }
])

# Charlie now has access to all tools owned by organization:acme
```

### Remove Permissions

```python
await client.delete_tuples([
    {
        "user": "user:charlie",
        "relation": "executor",
        "object": "tool:chat"
    }
])
```

## 📈 Observability

All authorization checks are traced and logged:

### Distributed Tracing

Every request creates spans:
- `mcp.call_tool` - Tool invocation
- `auth.authenticate` - User authentication
- `auth.authorize` - OpenFGA check
- `openfga.check` - Permission check
- `agent.chat` - Agent execution

View in Jaeger: http://localhost:16686

### Metrics

- `agent.tool.calls` - Tool invocation count
- `auth.failures` - Authentication failures
- `authz.failures` - Authorization failures (by resource)
- `agent.calls.successful` - Successful operations
- `agent.calls.failed` - Failed operations

Query in Prometheus: http://localhost:9090

### Logs

Structured logs with trace correlation:

```json
{
  "timestamp": "2025-10-10T12:00:00Z",
  "level": "INFO",
  "message": "Authorization check (OpenFGA)",
  "user_id": "user:alice",
  "relation": "executor",
  "resource": "tool:chat",
  "authorized": true,
  "trace_id": "abc123...",
  "span_id": "def456..."
}
```

## 🏗️ Production Deployment

### OpenFGA

Use PostgreSQL backend instead of in-memory:

```yaml
# docker-compose.yml
openfga:
  environment:
    - OPENFGA_DATASTORE_ENGINE=postgres
    - OPENFGA_DATASTORE_URI=postgres://user:pass@postgres:5432/openfga
```

### Infisical

1. Create production project in Infisical
2. Use environment-specific credentials
3. Enable secret versioning
4. Set up secret rotation
5. Use machine identities for service accounts

### Security Checklist

- [ ] Rotate JWT secret keys
- [ ] Use production Infisical project
- [ ] Enable OpenFGA audit logs
- [ ] Set up secret rotation
- [ ] Configure HTTPS for all services
- [ ] Enable rate limiting
- [ ] Set up monitoring alerts
- [ ] Implement backup strategy
- [ ] Review and minimize permissions
- [ ] Enable MFA for admin accounts

## 🎯 Use Cases

### Multi-Tenant SaaS

```python
# Each organization has isolated access
await client.write_tuples([
    {"user": "user:alice", "relation": "member", "object": "organization:acme"},
    {"user": "organization:acme", "relation": "organization", "object": "tool:chat"},
    {"user": "organization:acme", "relation": "organization", "object": "conversation:*"}
])
```

### Role-Based Access Control

```python
# Premium users get extra features
await client.write_tuples([
    {"user": "user:alice", "relation": "assignee", "object": "role:premium"},
    {"user": "role:premium", "relation": "executor", "object": "tool:advanced_search"}
])
```

### Conversation Sharing

```python
# Share conversation with team member
await client.write_tuples([
    {"user": "user:bob", "relation": "viewer", "object": "conversation:thread_1"}
])

# Grant edit access
await client.write_tuples([
    {"user": "user:bob", "relation": "editor", "object": "conversation:thread_1"}
])
```

## 🆘 Troubleshooting

### OpenFGA Not Working

```bash
# Check OpenFGA is running
curl http://localhost:8080/healthz

# Verify store and model IDs in .env
echo $OPENFGA_STORE_ID
echo $OPENFGA_MODEL_ID

# Re-run setup
python setup_openfga.py
```

### Infisical Connection Issues

```bash
# Test credentials
python setup_infisical.py

# Check environment variables
env | grep INFISICAL

# Use environment variable fallback
export ANTHROPIC_API_KEY=sk-ant-...
```

### Authorization Always Fails

1. Check OpenFGA relationships exist
2. Verify user_id format (`user:alice`)
3. Check resource format (`tool:chat`, `conversation:thread_1`)
4. Review logs for specific errors
5. Test with setup script first

## 📚 Additional Resources

- [OpenFGA Documentation](https://openfga.dev/docs)
- [Infisical Documentation](https://infisical.com/docs)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review example scripts
3. Check observability dashboards
4. File an issue with logs and trace IDs
