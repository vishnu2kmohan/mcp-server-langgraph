# Type Safety Migration Checklist

## Goal

Fix 145+ MyPy errors to enable strict type checking across the entire codebase.

## Current Status

- **MyPy Status**: DISABLED in pre-commit (145+ errors)
- **Baseline**: 145+ type errors (as of 2025-11-15)
- **Target**: 0 errors (100% type safety)
- **Estimated Effort**: 20-30 hours (can be broken into smaller sessions)

## Benefits

- **Early bug detection**: Catch type-related bugs at development time
- **Better IDE support**: Improved autocomplete and refactoring
- **Self-documenting code**: Type hints serve as inline documentation
- **Easier refactoring**: Confidence when making changes
- **Production quality**: Industry best practice for Python codebases

## Phase 1: Categorize Errors (Day 1 - 2 hours)

- [ ] Run `mypy src/ --show-error-codes > mypy_errors.txt` to capture baseline
- [ ] Count errors by error code (e.g., `cat mypy_errors.txt | grep error: | cut -d: -f4 | sort | uniq -c | sort -rn`)
- [ ] Identify top 5 error types by frequency
- [ ] Create task list for each category (see categories below)
- [ ] Document baseline in ADR

**Expected Output**: `docs-internal/MYPY_ERROR_ANALYSIS.md` with categorized errors

## Phase 2: Fix Core Modules (Days 2-7 - 10 hours)

### Priority 1: Core Infrastructure
- [ ] Fix `src/mcp_server_langgraph/core/config.py` (settings, dependencies)
- [ ] Fix `src/mcp_server_langgraph/core/agent.py` (main agentic loop)
- [ ] Fix `src/mcp_server_langgraph/core/context.py` (context management)
- [ ] Run unit tests after each fix: `make test-unit`
- [ ] Commit incrementally (one module at a time)

### Priority 2: Authentication & Authorization
- [ ] Fix `src/mcp_server_langgraph/auth/middleware.py`
- [ ] Fix `src/mcp_server_langgraph/auth/keycloak.py`
- [ ] Fix `src/mcp_server_langgraph/auth/openfga.py`
- [ ] Fix `src/mcp_server_langgraph/auth/session.py`
- [ ] Fix `src/mcp_server_langgraph/auth/role_mapper.py`
- [ ] Run auth tests: `pytest tests/auth/ -xvs`

### Priority 3: LLM Integration
- [ ] Fix `src/mcp_server_langgraph/llm/factory.py`
- [ ] Fix `src/mcp_server_langgraph/llm/validator.py`
- [ ] Run LLM tests: `pytest tests/llm/ -xvs`

## Phase 3: Fix Integration Modules (Days 8-12 - 8 hours)

### MCP Servers
- [ ] Fix `src/mcp_server_langgraph/mcp/server_stdio.py`
- [ ] Fix `src/mcp_server_langgraph/mcp/server_streamable.py`
- [ ] Run integration tests: `make test-integration`

### Observability
- [ ] Fix `src/mcp_server_langgraph/observability/opentelemetry.py`
- [ ] Fix `src/mcp_server_langgraph/observability/langsmith.py`
- [ ] Fix `src/mcp_server_langgraph/observability/prometheus.py`

### Secrets Management
- [ ] Fix `src/mcp_server_langgraph/secrets/infisical.py`
- [ ] Fix `src/mcp_server_langgraph/secrets/manager.py`

## Phase 4: Enable MyPy in Pre-commit (Day 13 - 2 hours)

- [ ] Uncomment MyPy hook in `.pre-commit-config.yaml` (lines 53-71)
- [ ] Run MyPy on entire codebase: `mypy src/ --strict`
- [ ] Verify 0 errors
- [ ] Run full test suite: `make test-unit test-integration`
- [ ] Run pre-push validation: `git commit --allow-empty -m "test" && git push --dry-run`
- [ ] Update `CHANGELOG.md` with type safety completion
- [ ] Create ADR-0XXX documenting migration strategy and lessons learned

## Common Error Types & Fixes

### Missing Return Type
```python
# ❌ Before
def get_user(user_id: str):
    return user_service.get(user_id)

# ✅ After
def get_user(user_id: str) -> User | None:
    return user_service.get(user_id)
```

### Argument Type Mismatch
```python
# ❌ Before
def process(data) -> None:
    ...

# ✅ After
def process(data: Dict[str, Any]) -> None:
    ...
```

### Optional Not Handled
```python
# ❌ Before
config = get_config()  # Returns Optional[Config]
config.get("key")  # MyPy error: Item "None" has no attribute "get"

# ✅ After
config = get_config()
if config is not None:
    config.get("key")
```

### Untyped Function Definition
```python
# ❌ Before
def callback(x):
    return x * 2

# ✅ After
def callback(x: int) -> int:
    return x * 2
```

## Progress Tracking

Run the `/type-safety-status` slash command to see current progress:

```bash
# Current command (update as you go)
mypy src/ --show-error-codes 2>&1 | grep "error:" | wc -l
# Target: 0 errors
```

## Validation Commands

```bash
# Check current error count
mypy src/ --show-error-codes 2>&1 | grep "error:" | wc -l

# Check specific module
mypy src/mcp_server_langgraph/core/config.py

# Run with strict mode (target configuration)
mypy src/ --strict

# Check test coverage after fixes
pytest --cov=src --cov-report=term-missing tests/
```

## Success Criteria

- [ ] MyPy runs without errors on `src/` directory
- [ ] All tests pass (`make test-unit test-integration`)
- [ ] Pre-commit hook includes MyPy validation
- [ ] CI/CD includes MyPy in quality checks
- [ ] ADR created documenting migration
- [ ] Team trained on type hint best practices

## Resources

- **MyPy Documentation**: https://mypy.readthedocs.io/
- **PEP 484** (Type Hints): https://peps.python.org/pep-0484/
- **PEP 526** (Variable Annotations): https://peps.python.org/pep-0526/
- **Typing Module**: https://docs.python.org/3/library/typing.html
- **Real Python Guide**: https://realpython.com/python-type-checking/

## Notes

- Commit after each module fix (don't batch all changes)
- Run tests after each commit to catch regressions early
- Use `# type: ignore` sparingly - only for legitimate edge cases
- Document any intentional `# type: ignore` with explanation
- Pair with another developer for complex type annotations
- Consider using `pyright` or `pyre` as alternative type checkers for validation

---

**Created**: 2025-11-15
**Status**: Not Started
**Estimated Completion**: 2-3 weeks (part-time)
