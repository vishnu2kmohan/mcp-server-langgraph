---
description: Systematic workflow for fixing MyPy type checking errors in the codebase.
---
# Fix MyPy Type Errors

Systematic workflow for fixing MyPy type checking errors in the codebase.

## Usage

```bash
/fix-mypy
```

## Current Status

- **MyPy**: Currently DISABLED in pre-commit due to 145+ errors
- **Goal**: Fix all errors to enable strict type checking
- **Target**: 0 errors (100% type safety)
- **Checklist**: See `.github/checklists/TYPE_SAFETY_MIGRATION.md`

## Quick Start

### Run MyPy to See Errors

```bash
mypy src/ --show-error-codes
```

### Run on Specific Module

```bash
mypy src/mcp_server_langgraph/core/config.py
```

### Save Errors to File

```bash
mypy src/ --show-error-codes > mypy_errors.txt
```

## Common Error Types & Fixes

### 1. Missing Return Type Annotation

**Error**: `error: Function is missing a return type annotation`

```python
# ❌ Before
def get_user(user_id: str):
    return user_service.get(user_id)

# ✅ After
def get_user(user_id: str) -> User | None:
    return user_service.get(user_id)
```

### 2. Missing Type Hints for Function Arguments

**Error**: `error: Function is missing a type annotation for one or more arguments`

```python
# ❌ Before
def process_data(data):
    return data.upper()

# ✅ After
def process_data(data: str) -> str:
    return data.upper()
```

### 3. Incompatible Types in Assignment

**Error**: `error: Incompatible types in assignment (expression has type "X", variable has type "Y")`

```python
# ❌ Before
result: int = get_value()  # get_value() returns str

# ✅ After - Option 1: Fix type hint
result: str = get_value()

# ✅ After - Option 2: Convert type
result: int = int(get_value())
```

### 4. Optional Not Handled

**Error**: `error: Item "None" of "Optional[X]" has no attribute "Y"`

```python
# ❌ Before
config = get_config()  # Returns Optional[Config]
value = config.get("key")  # MyPy error

# ✅ After
config = get_config()
if config is not None:
    value = config.get("key")
```

### 5. Argument Type Mismatch

**Error**: `error: Argument 1 has incompatible type "X"; expected "Y"`

```python
# ❌ Before
def process(data: dict) -> None:
    ...

process([1, 2, 3])  # Passing list instead of dict

# ✅ After
process({"key": "value"})  # Pass correct type
```

### 6. Missing Type Annotation for Variable

**Error**: `error: Need type annotation for variable`

```python
# ❌ Before
data = []  # MyPy can't infer type

# ✅ After
data: List[str] = []
```

### 7. Untyped Function Definition

**Error**: `error: Function is missing a type annotation`

```python
# ❌ Before
def callback(x):
    return x * 2

# ✅ After
def callback(x: int) -> int:
    return x * 2
```

### 8. Any Type Used

**Error**: `error: Returning Any from function declared to return "X"`

```python
# ❌ Before
def get_data() -> dict:
    return json.loads(text)  # json.loads returns Any

# ✅ After
def get_data() -> Dict[str, Any]:
    return json.loads(text)
```

## Systematic Fix Workflow

### Phase 1: Categorize Errors

```bash
# Generate error report
mypy src/ --show-error-codes > mypy_errors.txt

# Count errors by type
cat mypy_errors.txt | grep "error:" | cut -d: -f4 | cut -d'[' -f2 | cut -d']' -f1 | sort | uniq -c | sort -rn

# Example output:
#   45 arg-type
#   32 return-value
#   28 no-untyped-def
#   15 var-annotated
#   ...
```

### Phase 2: Fix by Module (Incremental)

**Fix ONE module at a time**:

```bash
# 1. Pick a module
mypy src/mcp_server_langgraph/core/config.py

# 2. Fix errors one by one
# 3. Run tests after each fix
pytest tests/test_config.py -xvs

# 4. Commit when module is clean
git add src/mcp_server_langgraph/core/config.py
git commit -m "fix(types): add type hints to core/config.py

Fixes MyPy errors:
- Add return type annotations
- Add parameter type hints
- Handle Optional types properly

MyPy errors fixed: 12"
```

### Phase 3: Validate Progress

```bash
# Count remaining errors
mypy src/ --show-error-codes 2>&1 | grep "error:" | wc -l

# Track progress
echo "Baseline: 145 errors"
echo "Current: $(mypy src/ --show-error-codes 2>&1 | grep 'error:' | wc -l) errors"
echo "Progress: $(python -c 'print(f"{(145 - $(mypy src/ --show-error-codes 2>&1 | grep error: | wc -l)) / 145 * 100:.1f}%")')"
```

## MyPy Configuration

Current config in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # TODO: Enable after fixing errors
ignore_missing_imports = true  # TODO: Add type stubs for libraries
```

**Target config** (after fixes):

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true  # ✅ Enable strict mode
ignore_missing_imports = false  # ✅ Require type stubs
strict = true  # ✅ Maximum strictness
```

## Common Type Hints Reference

```python
# Basic types
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Simple types
name: str = "value"
count: int = 10
price: float = 9.99
is_active: bool = True

# Collections
items: List[str] = ["a", "b", "c"]
mapping: Dict[str, int] = {"a": 1, "b": 2}
unique: Set[int] = {1, 2, 3}
pair: Tuple[str, int] = ("name", 42)

# Optional (can be None)
user: Optional[User] = get_user()  # Same as: User | None
value: str | None = None  # Python 3.10+ syntax

# Union (multiple types)
result: Union[str, int] = get_result()
result: str | int = get_result()  # Python 3.10+ syntax

# Any (avoid if possible)
data: Any = json.loads(text)

# Callable
from typing import Callable
callback: Callable[[int, str], bool] = my_function

# TypedDict
from typing import TypedDict

class UserDict(TypedDict):
    name: str
    age: int

user: UserDict = {"name": "Alice", "age": 30}

# Generics
from typing import Generic, TypeVar

T = TypeVar('T')

class Box(Generic[T]):
    def __init__(self, content: T) -> None:
        self.content = content
```

## Type Stubs for Third-Party Libraries

Install type stubs for libraries without built-in types:

```bash
# Common type stubs
uv add --dev types-PyYAML
uv add --dev types-redis
uv add --dev types-requests
```

## Ignoring Errors (Use Sparingly)

When a type error is legitimately unfixable:

```python
# Option 1: Ignore specific line
result = legacy_function()  # type: ignore[return-value]

# Option 2: Ignore entire file
# mypy: ignore-errors

# Option 3: Skip file in config
# pyproject.toml:
# [[tool.mypy.overrides]]
# module = "problematic_module"
# ignore_errors = true
```

**Important**: Always add a comment explaining WHY you're ignoring.

## Validation Commands

```bash
# Run MyPy
mypy src/

# Run with error codes
mypy src/ --show-error-codes

# Run strict mode
mypy src/ --strict

# Generate HTML report
mypy src/ --html-report mypy-report

# Check specific module
mypy src/mcp_server_langgraph/core/config.py
```

## Progress Tracking

Use this slash command to check status:

```bash
/type-safety-status
```

Or manually:

```bash
# Current error count
mypy src/ --show-error-codes 2>&1 | grep "error:" | wc -l

# Errors by category
mypy src/ --show-error-codes 2>&1 | grep "error:" | cut -d'[' -f2 | cut -d']' -f1 | sort | uniq -c | sort -rn
```

## Checklist

See `.github/checklists/TYPE_SAFETY_MIGRATION.md` for complete migration checklist.

## Resources

- **MyPy Documentation**: https://mypy.readthedocs.io/
- **PEP 484** (Type Hints): https://peps.python.org/pep-0484/
- **Python Typing Module**: https://docs.python.org/3/library/typing.html

---

**Goal**: Enable MyPy in pre-commit hooks after fixing all 145+ errors.
