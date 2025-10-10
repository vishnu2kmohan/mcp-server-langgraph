# AI Assistant Prompt Templates

Common prompts for working with this codebase across different AI assistants.

## Getting Started

### Understanding the Codebase
```
Can you explain the overall architecture of this LangGraph MCP agent?
Please focus on:
1. How the agent processes requests
2. The authentication and authorization flow
3. How observability is implemented
4. The MCP protocol implementation
```

### Setting Up Development Environment
```
I'm setting up my development environment for this project.
Can you guide me through:
1. Installing dependencies
2. Starting the infrastructure (Docker)
3. Configuring environment variables
4. Running the first test
```

## Code Generation

### Adding a New Tool
```
I want to add a new tool to the agent called "summarize_document" that:
- Takes a document ID as input
- Checks if the user has permission to view the document (via OpenFGA)
- Fetches the document content
- Uses an LLM to generate a summary
- Returns the summary

Please generate the complete implementation with:
- Tool definition in agent.py
- Pydantic input schema
- Authorization check
- Telemetry (tracing, logging, metrics)
- Error handling
- Unit tests
```

### Creating API Endpoint
```
Create a new FastAPI endpoint at POST /api/v1/analyze that:
- Accepts JSON with: {"text": str, "analysis_type": str}
- Validates input with Pydantic
- Requires JWT authentication
- Checks OpenFGA authorization for "analyst" role
- Calls the agent with the text
- Returns structured response
- Includes OpenAPI documentation
- Has proper error handling

Follow the existing patterns in mcp_server_streamable.py
```

### Writing Tests
```
Write comprehensive tests for the search_documents function including:
- Happy path test (authorized user, valid query)
- Unauthorized user test
- Invalid query test (empty, too long)
- Service unavailable test (OpenFGA down)
- Performance benchmark test (p95 < 100ms)

Use existing test patterns from tests/
Mark appropriately with pytest markers
Mock external dependencies
```

## Refactoring

### Improving Code Quality
```
Review this function and suggest improvements for:
- Type safety (add missing type hints)
- Error handling (specific exceptions)
- Performance (async/await patterns)
- Observability (add tracing/logging)
- Documentation (docstring)

[Paste code here]
```

### Adding Observability
```
Add comprehensive observability to this function:
- OpenTelemetry span with attributes
- Structured logging with context
- Metrics (duration, success/failure counts)
- Error tracking

Current code:
[Paste code here]
```

### Security Hardening
```
Review this authentication/authorization code for security issues:
- Are there any security vulnerabilities?
- Is input properly validated?
- Are secrets handled correctly?
- Is logging appropriate (not leaking sensitive data)?
- Are there missing authorization checks?

[Paste code here]
```

## Debugging

### Understanding Errors
```
I'm getting this error when running the agent:
[Paste error message and stack trace]

Can you help me:
1. Understand what's causing it
2. Identify the root cause
3. Suggest a fix
4. Recommend how to prevent similar issues
```

### Performance Issues
```
The agent is responding slowly (>10s). Can you help me:
1. Identify potential bottlenecks
2. Suggest profiling approaches
3. Recommend optimizations
4. Update benchmarks to catch regressions
```

### Tracing Problems
```
Help me debug this authorization issue:
- User: user-123
- Resource: document-456
- Expected: allowed
- Actual: denied

What should I check in:
1. OpenFGA model
2. Relationships
3. Authorization code
4. Logs
```

## Documentation

### Generating API Documentation
```
Generate comprehensive API documentation for this endpoint including:
- Description and purpose
- Authentication requirements
- Request schema with examples
- Response schema with examples
- Error codes and meanings
- Usage examples in curl and Python

Endpoint: [describe or paste code]
```

### Writing User Guide
```
Create a user guide for developers who want to:
1. Add a new LLM provider via LiteLLM
2. Configure provider credentials
3. Test the integration
4. Monitor usage and costs
5. Handle errors

Format as markdown suitable for docs/guides/
```

### Creating Runbook
```
Create an operational runbook for this alert:
Alert: HighErrorRate (error rate > 10%)

Include:
1. What this alert means
2. Immediate actions to take
3. How to investigate (logs, traces, metrics)
4. Common causes and solutions
5. When to escalate
6. How to prevent recurrence
```

## Configuration

### Environment Setup
```
I'm deploying to [staging/production]. Help me configure:
1. Required environment variables
2. Kubernetes secrets
3. Resource limits (CPU, memory)
4. Scaling parameters (min/max replicas)
5. Health check settings
6. Monitoring and alerts

Use existing configurations as templates
```

### Adding New Configuration
```
Add a new configuration option for:
- Name: max_llm_tokens
- Type: int
- Default: 1000
- Validation: 1-10000
- Description: Maximum tokens for LLM responses

Update:
1. config.py with validation
2. .env.example with documentation
3. README with usage
4. Tests for validation
```

## Deployment

### Kubernetes Manifest
```
Create Kubernetes manifests for deploying this service to [GKE/EKS/AKS]:
- Deployment with 3 replicas
- Service (LoadBalancer)
- Secrets for sensitive config
- ConfigMap for non-sensitive config
- HPA (autoscaling 3-10 replicas)
- PodDisruptionBudget
- NetworkPolicy
- ServiceMonitor (Prometheus)

Follow existing patterns in kubernetes/
```

### Helm Values
```
Create Helm values for [dev/staging/production] environment:
- Appropriate resource limits
- Replicas and autoscaling
- Secrets configuration
- Ingress settings
- Monitoring configuration

Base on existing values.yaml
```

## Monitoring

### Creating Dashboards
```
Create a Grafana dashboard for monitoring:
- Request rate and latency (p50, p95, p99)
- Error rate
- LLM usage and costs
- Authorization metrics
- Resource usage (CPU, memory)

Export as JSON following existing dashboards in grafana/
```

### Alert Rules
```
Create Prometheus alert rules for:
- High error rate (>5% for 5min)
- Slow responses (p95 > 10s for 5min)
- High LLM costs (>$100/hour)
- Memory pressure (>85% for 10min)

Follow patterns in monitoring/alerts/
```

## Testing

### Integration Test
```
Create an integration test that:
1. Starts the MCP server
2. Authenticates a user
3. Sends a chat message
4. Verifies the response
5. Checks authorization was enforced
6. Validates telemetry was recorded

Use fixtures from conftest.py
```

### Load Testing
```
Create a load test that:
- Simulates 100 concurrent users
- Sends chat requests for 5 minutes
- Measures response times
- Tracks error rates
- Generates report

Use locust or similar
```

## Migration

### Upgrading Dependencies
```
I want to upgrade [dependency] from version X to Y.
Help me:
1. Identify breaking changes
2. Update code for compatibility
3. Update tests
4. Validate functionality
5. Update documentation
```

### Database Migration
```
Create a migration for adding document storage:
- Schema design
- Migration script
- Rollback procedure
- Testing strategy
- Documentation
```

## AI Assistant Meta-Prompts

### For Better Suggestions
```
When suggesting code changes:
1. Follow black formatting (127 char lines)
2. Add type hints
3. Include docstrings
4. Add error handling
5. Include tests
6. Consider security
7. Add observability
```

### For Code Reviews
```
Review this code as if you were a senior engineer:
- Architecture and design
- Code quality and style
- Performance implications
- Security considerations
- Testing coverage
- Documentation quality
- Maintainability

[Paste code]
```

### For Learning
```
Explain [concept/pattern/feature] in this codebase:
- What is it?
- Why is it used this way?
- How does it work?
- When should I use it?
- What are common pitfalls?
- Where can I learn more?
```

## Common Workflows

### Feature Development
```
I'm implementing a new feature: [describe feature]

Guide me through:
1. Planning the implementation
2. Updating the agent
3. Adding API endpoints
4. Writing tests
5. Adding documentation
6. Submitting PR
```

### Bug Fix
```
I found a bug: [describe bug]

Help me:
1. Reproduce it reliably
2. Write a failing test
3. Identify root cause
4. Implement fix
5. Verify fix works
6. Add regression test
```

### Performance Optimization
```
I need to optimize [component] because [reason]

Help me:
1. Profile current performance
2. Identify bottlenecks
3. Design improvements
4. Implement changes
5. Benchmark results
6. Document optimization
```

## Tool-Specific Prompts

### For Cursor
```
@codebase How is authentication implemented?
@docs What are the deployment options?
@git Show me recent changes to agent.py
@terminal Run the unit tests
```

### For GitHub Copilot
```
// Generate a function that validates JWT tokens
// It should check: signature, expiration, issuer, subject
// Return user_id if valid, raise error if not
// Add proper error handling and logging
```

### For Claude Code
```
Please analyze the authentication flow in this codebase
and create a sequence diagram showing how a request
is authenticated and authorized from start to finish.
```

## Tips for AI Assistants

1. **Be Specific**: Include context, constraints, and requirements
2. **Reference Examples**: Point to existing code patterns
3. **Request Tests**: Always ask for tests with code
4. **Consider Security**: Explicitly ask about security implications
5. **Think Performance**: Request benchmarks for critical code
6. **Document Intent**: Ask for clear documentation
7. **Follow Standards**: Reference .cursorrules and style guides
8. **Iterate**: Refine prompts based on results

## Example Iteration

### First Attempt
```
Create a function to search documents
```

### Improved Prompt
```
Create an async function `search_documents` that:
- Input: query (str), user_id (str), limit (int, default 10)
- Checks OpenFGA authorization (user needs "searcher" role)
- Queries document index with user's accessible docs filter
- Returns List[DocumentResult] with Pydantic models
- Adds OpenTelemetry span with query and result attributes
- Logs search with structured logging
- Handles errors gracefully
- Includes comprehensive unit tests
- Follows existing patterns in agent.py
```

The improved prompt provides context, constraints, and examples, leading to better results.
