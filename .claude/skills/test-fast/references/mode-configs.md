# Mode Configs & Workflow Integration

Reference material for the `test-fast` skill. Loaded on demand.

---

## Workflow Integration

### Typical Development Workflow

1. **Make changes to code**
   ```bash
   # Edit src/mcp_server_langgraph/module.py
   ```

2. **Quick sanity check** (3-5s)
   ```bash
   make test-fast-core
   ```

3. **If core tests pass, run dev mode** (15-20s)
   ```bash
   make test-dev
   ```

4. **Before commit, run with coverage** (30-40s)
   ```bash
   make test-unit
   ```

5. **Before PR, run full suite** (45-60s)
   ```bash
   make test
   ```

---

## Additional Fast Test Options

### Re-run Failed Tests Only

```bash
make test-failed
```

Runs only tests that failed in previous run (using pytest `--lf`).

**Speed**: Depends on failure count, typically very fast
**Use case**: Fixing specific test failures

---

### Skip Slow Tests

```bash
make test-slow
```

Runs only slow tests (marked with `@pytest.mark.slow`).

**Use case**: Periodic execution of comprehensive slow tests

---

### Watch Mode (Auto-rerun)

```bash
make test-watch
```

Automatically re-runs tests when files change.

**Requires**: pytest-watch
**Use case**: Continuous testing during development

---

## Advanced Options

### Parallel with Specific Worker Count

```bash
# Use 4 workers
pytest -n 4

# Use all CPU cores
pytest -n auto  # (used by Make targets)
```

### Custom Test Selection

```bash
# Run specific test file
pytest tests/test_auth.py -n auto

# Run specific test
pytest tests/test_auth.py::test_login -n auto

# Run tests matching pattern
pytest -k "auth" -n auto
```

---

*Part of the test-fast skill. See [../SKILL.md](../SKILL.md) for main instructions.*
