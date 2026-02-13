# mypy Error Patterns & Quick Reference

Reference material for type safety analysis. Loaded on demand from SKILL.md.

---

## Error Analysis

**Most Common mypy Errors**:
```
===================================================================
  MYPY ERROR BREAKDOWN
===================================================================

  Error Code          Count   %      Description
  ------------------------------------------------------------------
  type-arg            38      25%    Missing type arguments (Generic[T])
  no-untyped-def      29      19%    Function missing type annotations
  no-untyped-call     24      16%    Calling untyped function
  return-value        18      12%    Return type mismatch
  arg-type            15      10%    Argument type mismatch
  assignment          12      8%     Assignment type mismatch
  var-annotated       9       6%     Variable needs type annotation
  misc                6       4%     Miscellaneous type errors
  union-attr          3       2%     Union attribute access
  ------------------------------------------------------------------
  TOTAL               154     100%
  ------------------------------------------------------------------

  Top 3 Fixes Needed:
  1. Add type parameters to generic classes/functions [type-arg]
  2. Add function signatures with types [no-untyped-def]
  3. Fix calls to untyped functions [no-untyped-call]
```

---

## Quick Reference - Common Type Patterns

```python
# AsyncIO functions
async def fetch_data() -> dict[str, Any]: ...

# Optional parameters
def process(value: str, timeout: Optional[int] = None) -> bool: ...

# Union types
def handle(item: str | int) -> None: ...

# Generic classes
T = TypeVar('T')
class Store(Generic[T]):
    def get(self, key: str) -> Optional[T]: ...

# Protocol compliance
from typing import Protocol
class HasName(Protocol):
    name: str

# Type guards
def is_string(value: Any) -> TypeGuard[str]:
    return isinstance(value, str)

# Callable types
from collections.abc import Callable
def apply(func: Callable[[int], str], value: int) -> str: ...
```

---

## Error Handling

- If mypy not installed, suggest: `uv add --dev mypy`
- If pyproject.toml not found, warn and provide manual config
- If no modules are strict yet, encourage starting with easiest module
- If all modules strict, celebrate completion!
