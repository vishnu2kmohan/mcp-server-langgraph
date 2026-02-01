# GitHub Copilot Instructions

Read: AGENTS.md, .ai/CORE.md

Key points:
- Python: Always use .venv (uv run --frozen)
- TDD: Write tests first
- Stack: React 18 + Tailwind 4 + Radix + Motion.dev

**Shared instructions**: `.ai/CORE.md` (Python env, commands, TDD, style)

---

## Copilot-Specific Patterns

### Inline Comments for Guidance
Use comments to guide Copilot suggestions:
```python
# Create async Redis client with connection pool
client = ...

# Validate JWT token and extract user_id
payload = ...
```

### VSCode Integration
- Works with `.vscode/settings.json`
- Respects `.vscode/extensions.json`
- Debug configs in `.vscode/launch.json`

---

## Quick Reference

| Task | Command |
|------|---------|
| Unit tests | `uv run --frozen pytest -m unit` |
| All tests | `uv run --frozen pytest` |
| Format | `uv run --frozen ruff format src/` |
| Lint | `uv run --frozen ruff check src/` |
| Type check | `uv run --frozen mypy src/` |

---

## Code Patterns

### Async Request Handler
```python
@app.post("/api/endpoint")
async def handler(request: RequestModel) -> ResponseModel:
    """Handler docstring."""
    with tracer.start_as_current_span("handler"):
        # Validate, authorize, process, return
        pass
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

### Health Checks
```python
@app.get("/health/live")
async def liveness():
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness():
    # Check dependencies
    return {"status": "ready"}
```

---

## Testing Pattern

```python
@pytest.mark.unit
def test_function_success():
    """Test normal operation."""
    # Arrange
    input_data = "test"

    # Act
    result = function(input_data)

    # Assert
    assert result == "expected"
```

---

## What to Avoid

- Never hardcode secrets
- Never skip authorization
- Never use sync I/O in async handlers
- Never commit without tests

---

## Architecture

Production LangGraph agent with:
- Multi-LLM (100+ providers via LiteLLM)
- OpenFGA authorization
- OpenTelemetry observability
- Kubernetes deployment

---

## Resources

| Resource | Path |
|----------|------|
| Shared Core | `.ai/CORE.md` |
| Testing | `docs-internal/testing/TESTING.md` |
| Architecture | `adr/` |
| API Docs | Start server, visit `/docs` |

---

**See `.ai/CORE.md` for complete instructions.**
