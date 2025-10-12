# Mutation Testing Guide

## What is Mutation Testing?

Mutation testing evaluates the **quality of your tests** by introducing small changes (mutations) to your code and checking if your tests catch them. If a mutation doesn't break any tests, it indicates a gap in test coverage.

## Why Mutation Testing?

- **Test Effectiveness**: 87% code coverage doesn't mean your tests are good
- **Find Weak Tests**: Tests that pass but don't actually verify behavior
- **Improve Quality**: Forces you to write better assertions
- **Catch Edge Cases**: Reveals untested code paths

## Mutation Score

**Target**: 80%+ mutation score on critical modules

**Interpretation**:
- **90-100%**: Excellent test quality
- **80-89%**: Good test quality (our target)
- **70-79%**: Acceptable test quality
- **Below 70%**: Weak tests, needs improvement

## Running Mutation Tests

### Quick Start

```bash
# Run mutation tests on all configured files
make test-mutation

# Or directly with mutmut
mutmut run

# View results
mutmut results

# Generate HTML report
mutmut html
```

### Targeting Specific Files

```bash
# Test only one file
mutmut run --paths-to-mutate=src/mcp_server_langgraph/core/agent.py

# Test multiple files
mutmut run --paths-to-mutate=src/mcp_server_langgraph/core/agent.py,src/mcp_server_langgraph/auth/middleware.py,src/mcp_server_langgraph/core/config.py
```

### Understanding Results

```bash
# Show summary
mutmut results

# Show survived mutations (tests didn't catch them)
mutmut show

# Show specific mutation
mutmut show 42
```

## Configured Modules

See `pyproject.toml` for the list of modules being tested:

```toml
[tool.mutmut]
paths_to_mutate = [
    "src/mcp_server_langgraph/core/agent.py",
    "src/mcp_server_langgraph/auth/middleware.py",
    "src/mcp_server_langgraph/core/config.py",
    "feature_flags.py",
    "llm_factory.py",
    "observability.py",
    "openfga_client.py",
]
```

These are our most critical modules that need strong test coverage.

## Types of Mutations

Mutmut applies various mutations:

### 1. Boolean Mutations
```python
# Original
if enabled:
    do_something()

# Mutated
if not enabled:  # Flipped boolean
    do_something()
```

### 2. Comparison Mutations
```python
# Original
if x > 5:
    return True

# Mutated
if x >= 5:  # Changed comparison
    return True
```

### 3. Return Value Mutations
```python
# Original
def get_value():
    return 42

# Mutated
def get_value():
    return 43  # Changed return value
```

### 4. Removal Mutations
```python
# Original
def process(data):
    validate(data)
    return data

# Mutated
def process(data):
    # validate(data) removed
    return data
```

## Interpreting Results

### Killed Mutations ✅
```
KILLED (tests caught the mutation)
```
Your tests successfully detected the change. Good!

### Survived Mutations ⚠️
```
SURVIVED (tests passed despite mutation)
```
Your tests didn't catch this change. This indicates:
- Missing test case
- Weak assertion
- Unreachable code

### Timeout Mutations ⏱️
```
TIMEOUT (tests took too long)
```
Mutation caused infinite loop or very slow execution.

### Example: Survived Mutation

```python
# Original code (src/mcp_server_langgraph/core/agent.py:42)
def route_input(message):
    if "search" in message.lower():
        return "use_tools"
    return "respond"

# Mutated to:
def route_input(message):
    if "search" in message.upper():  # Changed to upper()
        return "use_tools"
    return "respond"
```

If tests still pass, you need a test that verifies case-insensitive matching:

```python
def test_routing_is_case_insensitive():
    # This test would catch the mutation
    assert route_input("SEARCH for Python") == "use_tools"
    assert route_input("SeArCh for Python") == "use_tools"
```

## Improving Mutation Score

### 1. Add Edge Case Tests

```python
# Survived mutation: boundary condition not tested
def test_empty_string():
    assert route_input("") == "respond"

def test_only_whitespace():
    assert route_input("   ") == "respond"
```

### 2. Strengthen Assertions

```python
# Weak test
def test_format_messages():
    result = format_messages(messages)
    assert result is not None  # Too weak!

# Strong test
def test_format_messages():
    result = format_messages(messages)
    assert len(result) == len(messages)  # Better
    assert result[0]["role"] == "user"  # Even better
    assert result[0]["content"] == messages[0].content  # Best
```

### 3. Test Return Values

```python
# Test doesn't verify return value
def test_create_token():
    token = auth.create_token("alice")
    # No assertions! Mutation survives

# Fixed
def test_create_token():
    token = auth.create_token("alice")
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
    # Even better: verify it can be decoded
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    assert payload["username"] == "alice"
```

### 4. Test Error Paths

```python
# Only tests happy path
def test_authorize_success():
    result = await auth.authorize("user:alice", "executor", "tool:chat")
    assert result is True

# Add error path
def test_authorize_with_invalid_user():
    result = await auth.authorize("", "executor", "tool:chat")
    assert result is False

def test_authorize_with_invalid_resource():
    result = await auth.authorize("user:alice", "executor", "")
    assert result is False
```

## CI/CD Integration

Mutation tests run on a schedule (weekly) due to their runtime:

```yaml
# .github/workflows/mutation-tests.yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday
```

**Why not on every commit?**
- Mutation testing is slow (minutes to hours)
- Better suited for periodic quality checks
- Prevents blocking rapid development

## Performance Tips

### 1. Limit Scope

```bash
# Only test changed files
git diff --name-only main | grep "\.py$" | xargs mutmut run --paths-to-mutate
```

### 2. Use Fast Tests

```toml
[tool.mutmut]
runner = "pytest -x -m unit"  # Only unit tests, stop on first failure
```

### 3. Parallel Execution

```bash
# Run with multiple workers (requires mutmut-pro)
mutmut run --runner="pytest -x" --use-coverage --processes=4
```

## Common Issues

### Issue: All Mutations Timeout
**Cause**: Tests are slow or have infinite loops
**Solution**: Use `pytest -x -m unit` for faster tests

### Issue: Low Mutation Score
**Cause**: Tests exist but don't assert enough
**Solution**: Add more specific assertions, test edge cases

### Issue: Mutations in Unreachable Code
**Cause**: Dead code or defensive programming
**Solution**: Either remove code or add tests for those paths

## Best Practices

1. **Start Small**: Focus on critical modules first
2. **Set Realistic Goals**: 80% is excellent, 100% is overkill
3. **Review Survived Mutations**: Each one is a potential bug
4. **Update Baselines**: As you improve, raise the bar
5. **Don't Game the System**: Adding assertions without thought defeats the purpose

## Resources

- [Mutmut Documentation](https://mutmut.readthedocs.io/)
- [Mutation Testing Wikipedia](https://en.wikipedia.org/wiki/Mutation_testing)
- [PyCon Talk: Mutation Testing](https://www.youtube.com/watch?v=jwB3Nn4hR1o)

## Next Steps

1. Run initial mutation test: `make test-mutation`
2. Review survived mutations: `mutmut show`
3. Add tests to kill survived mutations
4. Track improvement over time
5. Integrate into CI/CD

**Goal**: Achieve 80%+ mutation score on all critical modules within 2 sprints.
