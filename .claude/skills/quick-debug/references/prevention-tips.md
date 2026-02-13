# Prevention Tips

Debug tips and troubleshooting guides for the `/quick-debug` skill.

---

## Debug Tips

### Tip 1: Read Error Messages Carefully

Most error messages tell you exactly what's wrong:
- **Line number**: Where error occurred
- **Stack trace**: Call sequence leading to error
- **Error type**: Category of problem

### Tip 2: Check Recent Changes

```bash
# What did I just change?
git diff

# What did I stage?
git diff --cached

# Recent commits
git log -5 --oneline
```

### Tip 3: Isolate the Problem

```bash
# Run just the failing test
pytest tests/test_file.py::test_name -v

# Run with print statements
pytest tests/test_file.py::test_name -v -s

# Run with debugger
pytest tests/test_file.py::test_name --pdb
```

### Tip 4: Check the Usual Suspects

1. **Virtual environment**: Using project venv?
2. **Docker services**: All running and healthy?
3. **Git status**: Any uncommitted changes?
4. **Dependencies**: All installed?
5. **Configuration**: Correct .env settings?

### Tip 5: Use Memory Files

Check memory files for known issues:
- `.claude/memory/python-environment-usage.md` - Python env problems
- `~/.claude/memory/task-spawn-error-prevention-strategy.md` - Async/subprocess issues (global)

---

## Troubleshooting

### Issue: Can't find error logs

```bash
# Check recent pytest output
ls -lt ${TMPDIR:-/tmp}/test_*.txt

# Check application logs
find . -name "*.log" -mtime -1
```

### Issue: Too many errors to analyze

```bash
# Focus on first failure
pytest -x  # Stop on first failure

# Or most recent
pytest --lf  # Last failed
```

### Issue: Error is intermittent

```bash
# Run multiple times
for i in {1..10}; do pytest tests/test.py || break; done

# Check for timing issues
pytest tests/test.py --durations=10
```
