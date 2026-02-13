# Error Categories

Reference for categorizing test failures by error pattern. Used during Step 3 of the test failure analysis workflow.

---

## Categories

Group failures by matching error output against these known patterns:

### Assertion Failures (Logic Errors)

```
AssertionError: assert X == Y
AssertionError: assert result is not None
```

### Import/Module Errors

```
ImportError: cannot import name
ModuleNotFoundError: No module named
```

### Async/Event Loop Errors

```
RuntimeError: Event loop is closed
asyncio.TimeoutError
RuntimeError: This event loop is already running
```

### Mock/Fixture Errors

```
AttributeError: Mock object has no attribute
TypeError: object MagicMock can't be used in 'await'
```

### Database/Connection Errors

```
ConnectionError
sqlalchemy.exc.OperationalError
redis.exceptions.ConnectionError
```

### Type Errors

```
TypeError: X() takes N arguments but M were given
TypeError: unsupported operand type(s)
```

### Configuration Errors

```
KeyError: environment variable not set
FileNotFoundError: config file missing
```
