# AI Assistant Instructions

This directory contains instructions and configurations for various AI coding assistants to work effectively with this codebase.

## Supported AI Assistants

- ✅ **GitHub Copilot** (VSCode, Cursor, Neovim)
- ✅ **Cursor AI**
- ✅ **Claude Code** (Anthropic)
- ✅ **Gemini Code Assist** (Google)
- ✅ **OpenAI GPT-4** (via extensions)

## Quick Start for AI Assistants

When working with this codebase, please:

1. **Read these files first**:
   - `README.md` - Project overview
   - `CONTRIBUTING.md` - Contribution guidelines
   - `DEVELOPMENT.md` - Development setup
   - `.cursorrules` - Code style and patterns

2. **Understand the architecture**:
   - LangGraph agent with MCP protocol
   - Multi-LLM support (LiteLLM)
   - OpenFGA authorization
   - OpenTelemetry observability

3. **Follow code standards**:
   - Black formatting (127 char lines)
   - Type hints required
   - Google-style docstrings
   - Comprehensive testing

## Configuration Files by Tool

### VSCode (with Copilot, extensions)
- `.vscode/settings.json` - Editor and Python settings
- `.vscode/extensions.json` - Recommended extensions
- `.vscode/launch.json` - Debug configurations
- `.vscode/tasks.json` - Build and test tasks
- `.github/copilot-instructions.md` - Copilot-specific rules

### Cursor
- `.cursorrules` - Cursor AI rules and patterns
- `.cursor/mcp.json` - MCP server configuration
- `.vscode/*` - Inherits VSCode settings

### Claude Code (Anthropic)
- `.claude/` - Claude-specific configurations (if needed)
- Follows `.cursorrules` and general guidelines

### Gemini Code Assist (Google)
- `.gemini/` - Gemini-specific configurations (if needed)
- Follows general AI instructions

### Universal Settings
- `.editorconfig` - Editor-agnostic formatting
- `.pre-commit-config.yaml` - Git hooks for quality
- `pyproject.toml` - Python tool configurations

## Project Structure

```
mcp_server_langgraph/
├── agent.py                    # LangGraph agent implementation
├── mcp_server*.py              # MCP protocol servers (3 transports)
├── auth.py                     # JWT authentication
├── openfga_client.py          # Authorization client
├── secrets_manager.py         # Infisical integration
├── observability.py           # OpenTelemetry setup
├── config.py                  # Configuration management
├── tests/                     # Test suite
│   ├── unit/
│   ├── integration/
│   └── performance/
├── .vscode/                   # VSCode configuration
├── .cursor/                   # Cursor configuration
├── .github/                   # GitHub workflows & Copilot
└── docs/                      # Documentation
```

## Common AI Assistant Queries

### "How do I add a new tool to the agent?"

1. Define tool in `agent.py`:
```python
@agent_graph.tool
async def my_tool(param: str, user_id: str) -> str:
    """Tool description."""
    # Authorization check
    # Implementation
    # Return result
```

2. Add Pydantic schema for inputs
3. Add telemetry (spans, metrics)
4. Write tests
5. Update docs

### "How do I run the tests?"

```bash
# All tests
pytest -v

# Unit tests only
pytest -m unit -v

# Integration tests
pytest -m integration -v

# With coverage
pytest --cov=. --cov-report=html
```

### "How do I start the development server?"

```bash
# Option 1: Start infrastructure
docker-compose up -d

# Option 2: Run MCP server
python mcp_server_streamable.py

# Option 3: Use VSCode debugger
# Press F5 and select "Python: MCP Server (StreamableHTTP)"
```

### "What are the security requirements?"

- **Authentication**: JWT tokens with 256-bit secrets
- **Authorization**: OpenFGA checks before protected operations
- **Secrets**: Never hardcode, use Infisical or env vars
- **Logging**: Structured with trace context, no sensitive data
- **Validation**: Pydantic models for all inputs

### "How do I add observability?"

```python
# Tracing
with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("key", "value")
    result = await perform_operation()

# Logging
logger.info("Event occurred", extra={"context": "data"})

# Metrics
metrics.counter_name.add(1, {"label": "value"})
```

## Code Quality Checklist

Before submitting code, ensure:

- [ ] Code formatted with `black`
- [ ] Imports sorted with `isort`
- [ ] Type hints on all public functions
- [ ] Docstrings in Google style
- [ ] Tests written and passing
- [ ] No hardcoded secrets
- [ ] Observability added (traces, logs, metrics)
- [ ] Error handling implemented
- [ ] Security checks in place

## Common Patterns

### Async Request Handler
```python
@app.post("/api/endpoint")
async def handler(request: RequestModel) -> ResponseModel:
    """Handler docstring."""
    with tracer.start_as_current_span("handler_name"):
        # Validate
        # Authorize
        # Process
        # Return
```

### Authorization Check
```python
allowed = await openfga_client.check(
    user=f"user:{user_id}",
    relation="viewer",
    object=f"resource:{resource_id}"
)
if not allowed:
    raise PermissionError("Not authorized")
```

### LLM Call with Telemetry
```python
with tracer.start_as_current_span("llm_call") as span:
    span.set_attribute("model", model_name)
    span.set_attribute("provider", provider)

    start_time = time.time()
    response = await llm_client.complete(prompt)
    duration = (time.time() - start_time) * 1000

    metrics.llm_duration.record(duration, {"model": model_name})
```

## Performance Targets

| Operation | Target (p95) |
|-----------|--------------|
| Agent response | < 5s |
| LLM call | < 10s |
| Authorization check | < 50ms |
| JWT validation | < 2ms |

Add benchmarks for critical paths:
```python
@pytest.mark.benchmark
def test_operation_performance(benchmark):
    result = benchmark(operation)
    assert benchmark.stats["mean"] < 0.050  # 50ms
```

## Testing Strategy

### Unit Tests
- Test individual functions in isolation
- Mock external dependencies
- Fast execution (< 1s total)

### Integration Tests
- Test component interactions
- Use real services in Docker
- Slower but more realistic

### Benchmarks
- Measure performance of critical paths
- Track over time
- Alert on regressions

## Debugging Tips

### Enable Debug Logging
```python
# In .env
LOG_LEVEL=DEBUG
```

### View Traces
```bash
# Open Jaeger UI
open http://localhost:16686
```

### Check Metrics
```bash
# Open Prometheus
open http://localhost:9090
```

### View Dashboards
```bash
# Open Grafana
open http://localhost:3000
```

## Documentation

- **API Docs**: Start server, visit http://localhost:8000/docs
- **Architecture**: See `README.md`
- **Deployment**: See `KUBERNETES_DEPLOYMENT.md`
- **Security**: See `SECURITY_AUDIT.md`
- **Testing**: See `TESTING.md`
- **Contributing**: See `CONTRIBUTING.md`

## Getting Help

- **Issues**: https://github.com/vishnu2kmohan/mcp_server_langgraph/issues
- **Discussions**: https://github.com/vishnu2kmohan/mcp_server_langgraph/discussions
- **Docs**: See `docs/` directory

## AI Assistant Best Practices

### For Code Generation
1. Read existing code patterns first
2. Follow established conventions
3. Add comprehensive tests
4. Include error handling
5. Add observability

### For Refactoring
1. Maintain backward compatibility
2. Update tests
3. Update documentation
4. Keep changes focused

### For Bug Fixes
1. Write failing test first
2. Fix minimal code
3. Verify test passes
4. Update CHANGELOG.md

### For Documentation
1. Use clear, concise language
2. Provide code examples
3. Keep up to date
4. Link to related docs

## Tool-Specific Notes

### GitHub Copilot
- Reads `.github/copilot-instructions.md`
- Works in VSCode, Cursor, Neovim
- Use inline comments to guide suggestions

### Cursor
- Reads `.cursorrules`
- Can connect to MCP server (`.cursor/mcp.json`)
- Use @-mentions to reference docs

### Claude Code
- Reads project structure automatically
- Follow conversation with context
- Ask for clarification when needed

### Gemini Code Assist
- Integrates with Google Cloud
- Reads workspace configuration
- Provides inline suggestions

## Version Compatibility

| Tool | Minimum Version | Tested Version |
|------|----------------|----------------|
| VSCode | 1.85.0 | 1.95.0 |
| Cursor | 0.30.0 | 0.42.0 |
| Python | 3.10 | 3.11 |
| Node.js (docs) | 18.0 | 20.0 |

## Contributing to AI Configs

If you improve AI assistant configurations:

1. Test with multiple tools
2. Document changes
3. Update this README
4. Submit PR with description

## License

Same as project: MIT License
