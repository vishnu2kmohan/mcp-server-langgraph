# Verify All Tests Pass

Run comprehensive test verification to ensure all tests pass before committing or merging.

## Usage

```bash
/verify-tests
```bash
## Test Execution Workflow

### Step 1: Unit Tests (Fast - ~2 minutes)

```bash
make test-unit
```bash
**What it tests**:
- Pure unit tests with mocked dependencies
- No external services required
- Fast execution (< 1s per test ideally)

**Success criteria**: All unit tests PASS

### Step 2: Integration Tests (~5 minutes)

```bash
make test-integration
```bash
**What it tests**:
- Tests with real dependencies (PostgreSQL, Redis, etc.)
- API endpoint tests
- Database query tests
- Authentication flows

**Prerequisites**:
- Infrastructure running: `make setup-infra`
- Services healthy: `docker-compose ps`

**Success criteria**: All integration tests PASS

### Step 3: Property-Based Tests (~2 minutes)

```bash
make test-property
```bash
**What it tests**:
- Edge case discovery using Hypothesis
- Randomized input validation
- Invariant testing

**Success criteria**: All property tests PASS

### Step 4: Contract Tests (~1 minute)

```bash
make test-contract
```bash
**What it tests**:
- MCP protocol compliance
- OpenAPI schema validation
- API contract adherence

**Success criteria**: All contract tests PASS

### Step 5: Security Tests (~1 minute)

```bash
pytest tests/security/ -v
```bash
**What it tests**:
- OWASP Top 10 vulnerabilities
- Authentication/authorization
- Input validation
- SQL injection prevention
- XSS prevention

**Success criteria**: All 34 security tests PASS

### Step 6: Test Coverage Check

```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=64 tests/
```bash
**Success criteria**:
- Coverage ≥ 64% (CI threshold)
- No critical gaps in coverage
- New code has ≥ 80% coverage

## Comprehensive Test Run

Run all tests in one command:

```bash
make test-all-quality
```bash
**Includes**:
- Unit tests
- Integration tests
- Property tests
- Contract tests
- Security tests
- Regression tests

**Duration**: ~10-12 minutes

## Parallel Execution (Faster)

Run tests in parallel using pytest-xdist:

```bash
pytest -n auto tests/
```bash
**Note**: Ensure tests are isolated (no shared state) for parallel execution.

## Test Failure Analysis

If tests fail:

### 1. Identify Failed Tests

```bash
pytest tests/ -v | grep FAILED
```bash
### 2. Run Failed Tests Only

```bash
pytest --lf -xvs
```python
**--lf**: Run last-failed tests first
**-x**: Stop on first failure
**-vs**: Verbose output with print statements

### 3. Debug Specific Test

```bash
pytest tests/path/to/test_file.py::test_function_name -xvs --pdb
```python
**--pdb**: Drop into debugger on failure

### 4. Check for Flaky Tests

```bash
pytest tests/path/to/test_file.py::test_function_name --count=10
```python
Run test 10 times to check for flakiness.

## Common Failure Scenarios

### Scenario: Import Errors

```bash
ModuleNotFoundError: No module named 'module_name'
```bash
**Fix**: Install dependencies
```bash
uv sync
# or
uv sync --extra dev
```python
### Scenario: Fixture Not Found

```python
fixture 'fixture_name' not found
```python
**Fix**: Check fixtures in conftest.py or import from correct location

### Scenario: Database Connection Failed

```bash
could not connect to server: Connection refused
```bash
**Fix**: Start infrastructure
```bash
make setup-infra
docker-compose ps  # Verify services are running
```bash
### Scenario: Async Test Hanging

```bash
Test timeout (hangs indefinitely)
```go
**Fix**: Check for missing `await` or improperly configured AsyncMock

### Scenario: Type Error in Pydantic

```bash
ValidationError: X validation errors
```bash
**Fix**: Check Pydantic model validation, ensure correct types

## Test Quality Checks

### Check for Skipped Tests

```bash
pytest tests/ -v | grep SKIPPED
```bash
**Action**: Investigate why tests are skipped, implement or remove

### Check for Slow Tests

```bash
pytest -m unit --durations=20
```bash
**Action**: Optimize tests taking > 10s

### Check for Test Isolation Issues

```bash
pytest tests/ -n auto  # Parallel
pytest tests/  # Sequential

# If parallel fails but sequential passes, you have isolation issues
```bash
**Action**: Fix shared state, ensure proper fixture teardown

## Pre-Commit Checklist

Before committing:

- [ ] All unit tests pass (`make test-unit`)
- [ ] All integration tests pass (`make test-integration`)
- [ ] Coverage ≥ 64% (`pytest --cov`)
- [ ] No skipped tests (or documented why skipped)
- [ ] No test warnings
- [ ] New code has tests (TDD followed)

## Pre-Push Checklist

Before pushing:

- [ ] All test types pass (`make test-all-quality`)
- [ ] Property tests pass (`make test-property`)
- [ ] Contract tests pass (`make test-contract`)
- [ ] Security tests pass (`pytest tests/security/`)
- [ ] Regression tests pass (`make test-regression`)
- [ ] Performance benchmarks acceptable (`pytest --benchmark-only`)

## CI/CD Validation

Tests in CI should match local execution:

```bash
# What CI runs:
1. make test-unit
2. make test-integration
3. make test-property
4. make test-contract
5. pytest --cov --cov-fail-under=64

# Run locally to match CI:
make test-all-quality
```bash
## Quick Commands Reference

```bash
# Run all tests
make test-all-quality

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run last-failed tests
pytest --lf -xvs

# Run specific test
pytest tests/path/to/test.py::test_name -xvs

# Run tests matching pattern
pytest -k "pattern" tests/

# Run tests with specific marker
pytest -m unit tests/

# Parallel execution
pytest -n auto tests/
```

## Success Criteria

All of the following must be true:

- ✅ All unit tests PASS
- ✅ All integration tests PASS
- ✅ All property tests PASS
- ✅ All contract tests PASS
- ✅ All security tests PASS
- ✅ Test coverage ≥ 64%
- ✅ No test warnings
- ✅ No skipped tests (or documented)

---

**Next Step**: If all tests pass, proceed with commit and push. Otherwise, fix failing tests before continuing.
