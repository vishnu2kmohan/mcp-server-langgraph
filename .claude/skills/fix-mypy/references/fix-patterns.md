# MyPy Fix Patterns

Common type hints, type stubs, ignore patterns, and migration checklist reference.

---

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

---

## Type Stubs for Third-Party Libraries

Install type stubs for libraries without built-in types:

```bash
# Common type stubs
uv add --dev types-PyYAML
uv add --dev types-redis
uv add --dev types-requests
```

---

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

---

## Checklist

See `.github/checklists/TYPE_SAFETY_MIGRATION.md` for the complete migration checklist.
