# Create Architecture Decision Record

You are tasked with creating a new Architecture Decision Record (ADR) for the mcp-server-langgraph project. This command automates ADR creation with intelligent auto-filling and dual format generation.

## Project Context

**Project**: MCP Server LangGraph
**Version**: 2.8.0
**Technology Stack**:
- Python 3.10+ with LangGraph
- Multi-provider LLM via LiteLLM (Anthropic, OpenAI, Google, Azure, AWS, Ollama)
- Authentication: JWT + Keycloak SSO
- Authorization: OpenFGA (Zanzibar-style RBAC)
- Observability: OpenTelemetry + LangSmith
- Session Storage: Redis + PostgreSQL
- Deployment: Kubernetes, GKE, Cloud Run, Helm

## Your Task

### Step 1: Gather Information

Ask the user for the following information using the AskUserQuestion tool:

**Question 1**: What is the title of the ADR?
- Header: "ADR Title"
- Provide text input for the title
- Example: "GraphQL API Design for Agent Interactions"

**Question 2**: What category does this ADR fall under?
- Header: "Category"
- Options:
  - Architecture: Core architectural patterns
  - Infrastructure: Deployment, scaling, infrastructure
  - Security: Authentication, authorization, secrets
  - Observability: Monitoring, logging, tracing
  - Testing: Testing strategies and patterns
  - Data: Data storage, caching, persistence
  - Integration: External service integration
  - Performance: Performance optimization, caching

**Question 3** (Optional): Are there related ADRs? (comma-separated numbers, e.g., "1,3,15")
- Header: "Related ADRs"
- Allow text input for comma-separated ADR numbers

### Step 2: Determine Next ADR Number

1. Use `Bash` to find the highest numbered ADR:
   ```bash
   ls adr/adr-*.md | sed 's/.*adr-0*\([0-9]*\)-.*/\1/' | sort -n | tail -1
   ```

2. Add 1 to get the next ADR number
3. Format as 4-digit zero-padded number (e.g., 0040)

### Step 3: Auto-Link Related ADRs

If the user didn't specify related ADRs, search for them automatically based on keywords in the title:

**Common keyword mappings**:
- "auth" / "authentication" → ADR-0007 (Authentication Provider Pattern), ADR-0031 (Keycloak), ADR-0034 (API Key JWT)
- "authorization" / "permissions" → ADR-0002 (OpenFGA), ADR-0039 (Permission Inheritance)
- "observability" / "monitoring" / "logging" → ADR-0003 (Dual Observability), ADR-0026 (Lazy Initialization)
- "LLM" / "model" / "provider" → ADR-0001 (Multi-Provider LLM)
- "session" / "state" → ADR-0006 (Session Storage), ADR-0036 (Hybrid Session)
- "deployment" / "kubernetes" / "k8s" → ADR-0013 (Multi-Deployment Strategy)
- "testing" / "test" → ADR-0016 (Property-Based Testing)
- "cache" / "caching" → ADR-0028 (Caching Strategy)
- "rate limit" / "throttle" → ADR-0027 (Rate Limiting)
- "resilience" / "retry" / "circuit breaker" → ADR-0030 (Resilience Patterns)
- "error" / "exception" → ADR-0017 (Error Handling), ADR-0029 (Exception Hierarchy)
- "API" / "MCP" → ADR-0004 (MCP Streamable HTTP), ADR-0020 (Dual Transport)
- "secrets" / "credentials" → ADR-0008 (Infisical Secrets Management)

### Step 4: Generate ADR Files

Create **TWO** files:

#### File 1: Markdown version (adr/adr-XXXX-title-kebab-case.md)

Use the template from `.claude/templates/adr-template.md` with these auto-fills:

**Auto-Fill Values**:
- `[NUMBER]`: The determined ADR number (without leading zeros in title)
- `[Title]`: User-provided title in Title Case
- `Date`: Today's date (YYYY-MM-DD format: 2025-10-31)
- `Status`: Set to "Proposed" for new ADRs
- `[Language]`: Auto-select based on category:
  - Architecture/Integration → "python"
  - Infrastructure → "yaml" or "bash"
  - Security → "python"
  - Data → "sql" or "python"

**Context Section - Auto-Fill Background**:
Add project-specific context based on category:
- **Architecture**: "This decision affects the core architecture of mcp-server-langgraph, a production-ready MCP server template built with LangGraph..."
- **Security**: "Security is critical for mcp-server-langgraph's enterprise authentication (JWT + Keycloak) and authorization (OpenFGA) systems..."
- **Infrastructure**: "This decision impacts deployment across multiple targets: Kubernetes, GKE, Cloud Run, and Helm..."
- **Observability**: "This decision affects our dual observability stack (OpenTelemetry + LangSmith) and production monitoring..."

**Add Related ADRs Section** (if any related ADRs identified):
```markdown
## Related Decisions

This decision is related to:
- [ADR-0001: Multi-Provider LLM Support](/architecture/adr-0001-llm-multi-provider) - LLM abstraction layer
- [ADR-0003: Dual Observability Strategy](/architecture/adr-0003-dual-observability) - Monitoring integration
```

#### File 2: MDX version (docs/architecture/adr-XXXX-title-kebab-case.mdx)

**Frontmatter** (MUST be first thing in file):
```yaml
---
title: XXXX. [Title in Title Case]
description: 'Architecture Decision Record: XXXX. [Title in Title Case]'
icon: 'file-lines'
---
```

**Content**: Copy the EXACT same content from the .md file (without frontmatter)

### Step 5: Inform User

After creating both files, provide:
1. Confirmation message with file locations
2. Next ADR number used
3. List of auto-linked related ADRs (if any)
4. Reminder to:
   - Fill in the template sections
   - Run `/validate` before committing
   - Update docs/mint.json to include the new ADR in navigation (if needed)

## Filename Convention

- **Format**: `adr-XXXX-title-in-kebab-case.md` and `.mdx`
- **Number**: 4-digit zero-padded (0001, 0040, etc.)
- **Title**: Lowercase kebab-case, derived from user title
- **Example**: User title "GraphQL API Design" → `adr-0040-graphql-api-design.md`

## Example Execution

**User Input**:
- Title: "Distributed Tracing with OpenTelemetry"
- Category: Observability

**Auto-Generated**:
- Number: 0040 (if last ADR was 0039)
- Related ADRs: ADR-0003 (Dual Observability), ADR-0026 (Lazy Initialization)
- Files:
  - `adr/adr-0040-distributed-tracing-opentelemetry.md`
  - `docs/architecture/adr-0040-distributed-tracing-opentelemetry.mdx`

**Auto-Filled Context**:
```markdown
## Context

This decision affects our dual observability stack (OpenTelemetry + LangSmith) and production monitoring.

**Background**:
- mcp-server-langgraph uses OpenTelemetry for distributed tracing across agent workflows
- Current observability stack includes LangSmith for LLM-specific tracing
- Need to decide on distributed tracing strategy for production deployments
```

## Error Handling

- If unable to determine next ADR number, default to prompting the user
- If related ADR files don't exist, warn but continue
- If adr/ or docs/architecture/ directories don't exist, create them
- Validate generated filenames follow kebab-case convention

## Quality Checks

Before completing:
1. Verify both .md and .mdx files created
2. Verify .mdx frontmatter is valid YAML
3. Verify icon is 'file-lines' (standard for ADRs)
4. Verify related ADR links use correct paths
5. Suggest running `python3 scripts/validate_mintlify_docs.py` to validate

## Notes

- Do NOT commit the files automatically - let the user review first
- Do NOT open editor - just create the files
- DO provide the file paths so user can review
- DO suggest related ADRs even if user doesn't specify
- DO maintain consistent formatting with existing ADRs

---

**Success Criteria**:
- ✅ Two files created (.md and .mdx)
- ✅ Valid frontmatter in .mdx
- ✅ Auto-filled with project context
- ✅ Related ADRs linked (if applicable)
- ✅ Ready for user to fill in details
- ✅ Validation-ready (passes MDX validator)
