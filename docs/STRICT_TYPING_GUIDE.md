# Strict Typing Guide

## Overview

This project uses **gradual strict typing** with mypy to improve type safety incrementally. Not all modules have strict typing enabled yet, but we're working towards 100% strict coverage.

## Current Status

### Phase 1: Fully Strict Modules ✅

These modules have `strict = true` and `disallow_untyped_calls = true`:

- `config.py` - Configuration management
- `feature_flags.py` - Feature flag system
- `observability.py` - Observability setup

**Why these first?**
- New code (easier to start strict)
- Well-defined interfaces
- Minimal external dependencies

### Phase 2: Planned (Future)

Modules scheduled for strict typing:

- `auth.py` - Authentication/authorization
- `llm_factory.py` - LLM abstraction
- `agent.py` - LangGraph agent

### Not Strict (Intentional)

- `tests/` - Test code excluded from strict checks
- Third-party integrations - May have untyped dependencies

## Mypy Configuration

### pyproject.toml

```toml
[tool.mypy]
# Base settings (all files)
python_version = "3.11"
disallow_untyped_defs = true  # Functions must have type hints
warn_return_any = true
strict_equality = true

# Gradual rollout - allow some flexibility
disallow_untyped_calls = false  # Will enable per-module

# Phase 1: Strict modules
[[tool.mypy.overrides]]
module = ["config", "feature_flags", "observability"]
disallow_untyped_calls = true
strict = true
```

## What is Strict Mode?

### `strict = true` enables:

1. **disallow_untyped_calls**
   - Can't call untyped functions
   - Forces external libs to have stubs

2. **disallow_untyped_defs**
   - All functions must have type hints
   - No `def foo(x):` without types

3. **disallow_incomplete_defs**
   - All parameters must be typed
   - Return type must be specified

4. **check_untyped_defs**
   - Checks function bodies even without annotations

5. **disallow_subclassing_any**
   - Can't subclass `Any` typed classes

6. **disallow_untyped_decorators**
   - Decorators must be typed

7. **warn_redundant_casts**
   - Catches unnecessary `cast()` calls

8. **warn_unused_ignores**
   - Catches unnecessary `# type: ignore`

9. **no_implicit_optional**
   - `def foo(x: int = None)` is error
   - Must be `x: Optional[int] = None`

10. **warn_return_any**
    - Functions returning `Any` trigger warning

## Running Mypy

### Check All Code

```bash
# Check everything
mypy .

# Check specific file
mypy agent.py
```

### Check Only Strict Modules

```bash
mypy config.py feature_flags.py observability.py
```

### CI Integration

Mypy runs in CI:

```yaml
# .github/workflows/ci.yaml
- name: Run mypy
  run: mypy *.py --ignore-missing-imports || true
```

## Common Errors & Fixes

### Error: Call to untyped function

```python
# Error
def untyped_helper(x):  # No types!
    return x * 2

def typed_caller(value: int) -> int:
    return untyped_helper(value)  # Error in strict mode
```

**Fix**: Add types to helper

```python
def untyped_helper(x: int) -> int:
    return x * 2
```

### Error: Missing return type

```python
# Error
def process_data(data: dict):  # Missing return type
    return data["key"]
```

**Fix**: Add return type

```python
def process_data(data: dict) -> str:
    return data["key"]
```

### Error: Implicit Optional

```python
# Error
def greet(name: str = None):  # None not in type
    if name:
        return f"Hello, {name}"
    return "Hello"
```

**Fix**: Use Optional

```python
from typing import Optional

def greet(name: Optional[str] = None) -> str:
    if name:
        return f"Hello, {name}"
    return "Hello"
```

### Error: Returning Any

```python
# Warning
def get_value(config: dict) -> Any:  # Too permissive
    return config.get("value")
```

**Fix**: Be more specific

```python
def get_value(config: dict) -> Optional[str]:
    value = config.get("value")
    if isinstance(value, str):
        return value
    return None
```

### Error: Untyped third-party library

```python
# Error
from some_lib import some_function  # No type stubs

def use_it(x: int) -> int:
    return some_function(x)  # Error if some_lib untyped
```

**Fix Options**:

1. Install type stubs: `pip install types-some-lib`
2. Add to pyproject.toml overrides
3. Use `# type: ignore` sparingly

```python
return some_function(x)  # type: ignore[no-untyped-call]
```

## Best Practices

### 1. Type All Public APIs

```python
# Good
def authenticate(username: str, password: str) -> AuthResult:
    ...

# Bad
def authenticate(username, password):
    ...
```

### 2. Use Type Aliases

```python
from typing import TypeAlias

UserId: TypeAlias = str
ResourceId: TypeAlias = str

def authorize(user: UserId, resource: ResourceId) -> bool:
    ...
```

### 3. Use TypedDict for Structured Dicts

```python
from typing import TypedDict

class UserDict(TypedDict):
    username: str
    email: str
    roles: list[str]

def get_user(user_id: str) -> UserDict:
    ...
```

### 4. Use Literal for Fixed Values

```python
from typing import Literal

Action = Literal["use_tools", "respond", "end"]

def route(message: str) -> Action:
    if "search" in message:
        return "use_tools"
    return "respond"
```

### 5. Generic Types

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Response(Generic[T]):
    data: T
    status: int

def get_data() -> Response[dict]:
    return Response(data={}, status=200)
```

## Migration Strategy

### Step 1: Add Basic Types

```python
# Before
def process(data):
    return data["key"]

# After
def process(data: dict) -> str:
    return data["key"]
```

### Step 2: Strengthen Types

```python
# Before
def process(data: dict) -> str:
    return data["key"]

# After
class InputData(TypedDict):
    key: str

def process(data: InputData) -> str:
    return data["key"]
```

### Step 3: Enable Strict Mode

```toml
[[tool.mypy.overrides]]
module = ["my_module"]
strict = true
```

### Step 4: Fix All Errors

Run mypy, fix errors one by one.

## Gradual Rollout Timeline

| Phase | Modules | Timeline | Status |
|-------|---------|----------|--------|
| 1 | config, feature_flags, observability | ✅ Complete | Done |
| 2 | auth, llm_factory | Sprint 2 | Planned |
| 3 | agent, openfga_client | Sprint 3 | Planned |
| 4 | All remaining | Sprint 4 | Planned |

## Measuring Progress

### Type Coverage

```bash
# Count typed vs untyped functions
grep -r "def " *.py | wc -l  # Total
mypy --html-report mypy-report .  # Generates report
```

### Mypy Report

```bash
mypy --html-report mypy-report .
open mypy-report/index.html
```

## Benefits of Strict Typing

1. **Catch Bugs Early**: Type errors found before runtime
2. **Better IDE Support**: Autocomplete, refactoring
3. **Documentation**: Types are self-documenting
4. **Refactoring Safety**: Changes break tests, not production
5. **Team Onboarding**: New developers understand interfaces faster

## Common Questions

### Q: Why not enable strict mode everywhere immediately?

**A**: Legacy code has many type violations. Gradual rollout:
- Prevents blocking development
- Allows learning mypy
- Focuses effort on critical modules first

### Q: What about tests?

**A**: Tests are excluded from strict checking (`exclude = ["tests/"]`) because:
- Tests use mocking (inherently untyped)
- Test code is less critical
- Too many false positives

### Q: How strict is too strict?

**A**: Balance pragmatism with safety:
- Critical modules: Very strict
- Utilities: Moderately strict
- Scripts: Basic types only

### Q: What if third-party library has no stubs?

**A**: Options:
1. Create stubs yourself (contribute to typeshed)
2. Use `# type: ignore` with comment
3. Wait for library to add types

## Resources

- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Python Type Hints PEP 484](https://peps.python.org/pep-0484/)
- [typing Module](https://docs.python.org/3/library/typing.html)
- [Type Stubs](https://github.com/python/typeshed)

## Contributing

When adding new code:

1. **Always add type hints** to new functions
2. **Use TypedDict** for structured dicts
3. **Run mypy** before committing
4. **Fix mypy errors** don't just ignore them

**Goal**: All new code should pass strict mypy checks from day one.
