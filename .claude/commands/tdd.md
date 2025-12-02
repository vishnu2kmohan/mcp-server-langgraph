---
description: Begin Test-Driven Development (TDD) workflow for a new feature or bug fix.
---
# Start TDD Workflow

Begin Test-Driven Development (TDD) workflow for a new feature or bug fix.

## Usage

```bash
/tdd
```

## Workflow

### 🔴 RED Phase - Write Failing Tests

1. **Understand the requirement**:
   - What behavior needs to be implemented?
   - What are the expected inputs and outputs?
   - What edge cases need to be handled?

2. **Write the test FIRST**:
   ```bash
   # Example: tests/test_feature.py

   def test_feature_handles_valid_input():
       # GIVEN: Valid input
       input_data = {"key": "value"}

       # WHEN: Function is called
       result = my_feature(input_data)

       # THEN: Returns expected output
       assert result == expected_output
   ```

3. **Run the test to verify it FAILS**:
   ```bash
   pytest tests/test_feature.py::test_feature_handles_valid_input -xvs
   ```

   **Expected**: Test should FAIL with clear error message.
   **Why**: Proves the test is actually testing something and isn't a false positive.

4. **Commit the failing test**:
   ```bash
   git add tests/test_feature.py
   git commit -m "test: add failing test for feature X"
   ```

### 🟢 GREEN Phase - Implement Minimal Code

5. **Write the simplest code to make test pass**:
   ```bash
   # src/module/feature.py

   def my_feature(input_data):
       # Minimal implementation
       return expected_output
   ```

6. **Run the test to verify it PASSES**:
   ```bash
   pytest tests/test_feature.py::test_feature_handles_valid_input -xvs
   ```

   **Expected**: Test should PASS.

7. **Run all tests to ensure no regressions**:
   ```bash
   make test-unit
   ```

8. **Commit the implementation**:
   ```bash
   git add src/module/feature.py
   git commit -m "feat: implement feature X

   Adds minimal implementation to make test pass.

   Closes #123"
   ```

### ♻️ REFACTOR Phase - Improve Code Quality

9. **Refactor for better design**:
   - Extract functions for clarity
   - Add type hints
   - Improve variable names
   - Add docstrings
   - Remove duplication

10. **Run tests after EACH refactoring step**:
    ```bash
    pytest tests/test_feature.py -xvs
    ```

    **Important**: Tests must stay GREEN throughout refactoring.

11. **Commit refactoring separately**:
    ```bash
    git add src/module/feature.py
    git commit -m "refactor: improve feature X implementation

    - Add type hints
    - Extract helper function
    - Improve docstrings"
    ```

## Test Coverage

Check coverage after implementation:

```bash
pytest --cov=src/module/feature.py --cov-report=term-missing tests/test_feature.py
```

**Target**: ≥ 80% coverage for new code

## Edge Cases to Test

- [ ] Valid inputs (happy path)
- [ ] Invalid inputs (validation)
- [ ] Empty inputs
- [ ] Null/None values
- [ ] Boundary conditions (min/max values)
- [ ] Error scenarios
- [ ] Concurrent access (if applicable)

## TDD Checklist

- [ ] Requirement clearly defined
- [ ] Test written FIRST
- [ ] Test run and FAILED (RED phase)
- [ ] Test committed separately
- [ ] Minimal implementation written
- [ ] Test run and PASSED (GREEN phase)
- [ ] Implementation committed
- [ ] Code refactored for quality
- [ ] Tests still PASSING after refactoring
- [ ] Coverage checked (≥ 80%)
- [ ] All tests passing (`make test-unit`)

## Common Mistakes to Avoid

- ❌ **Writing implementation before tests**: Always test first
- ❌ **Skipping RED phase**: Must verify test fails before implementing
- ❌ **Testing implementation details**: Test behavior, not internals
- ❌ **One giant test**: Break into small, focused tests
- ❌ **Mixing test and implementation commits**: Commit separately

## Resources

- TDD Best Practices: See `~/.claude/CLAUDE.md` (global TDD standards)
- Testing Patterns: See `.claude/context/testing-patterns.md`
- Test Examples: Browse `tests/` directory for patterns

---

**Remember**: Red → Green → Refactor. Always in this order!
