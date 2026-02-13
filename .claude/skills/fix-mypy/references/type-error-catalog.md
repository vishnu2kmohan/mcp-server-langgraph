# MyPy Common Error Types & Fixes

Reference catalog of the 8 most common MyPy error types with before/after examples.

---

## 1. Missing Return Type Annotation

**Error**: `error: Function is missing a return type annotation`

```python
# Before
def get_user(user_id: str):
    return user_service.get(user_id)

# After
def get_user(user_id: str) -> User | None:
    return user_service.get(user_id)
```

---

## 2. Missing Type Hints for Function Arguments

**Error**: `error: Function is missing a type annotation for one or more arguments`

```python
# Before
def process_data(data):
    return data.upper()

# After
def process_data(data: str) -> str:
    return data.upper()
```

---

## 3. Incompatible Types in Assignment

**Error**: `error: Incompatible types in assignment (expression has type "X", variable has type "Y")`

```python
# Before
result: int = get_value()  # get_value() returns str

# After - Option 1: Fix type hint
result: str = get_value()

# After - Option 2: Convert type
result: int = int(get_value())
```

---

## 4. Optional Not Handled

**Error**: `error: Item "None" of "Optional[X]" has no attribute "Y"`

```python
# Before
config = get_config()  # Returns Optional[Config]
value = config.get("key")  # MyPy error

# After
config = get_config()
if config is not None:
    value = config.get("key")
```

---

## 5. Argument Type Mismatch

**Error**: `error: Argument 1 has incompatible type "X"; expected "Y"`

```python
# Before
def process(data: dict) -> None:
    ...

process([1, 2, 3])  # Passing list instead of dict

# After
process({"key": "value"})  # Pass correct type
```

---

## 6. Missing Type Annotation for Variable

**Error**: `error: Need type annotation for variable`

```python
# Before
data = []  # MyPy can't infer type

# After
data: List[str] = []
```

---

## 7. Untyped Function Definition

**Error**: `error: Function is missing a type annotation`

```python
# Before
def callback(x):
    return x * 2

# After
def callback(x: int) -> int:
    return x * 2
```

---

## 8. Any Type Used

**Error**: `error: Returning Any from function declared to return "X"`

```python
# Before
def get_data() -> dict:
    return json.loads(text)  # json.loads returns Any

# After
def get_data() -> Dict[str, Any]:
    return json.loads(text)
```
