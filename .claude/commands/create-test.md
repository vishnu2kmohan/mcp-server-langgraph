---
description: You are tasked with creating a new test file for the mcp-server-langgraph project. This command auto
---
# Create Test File

You are tasked with creating a new test file for the mcp-server-langgraph project. This command automates test file generation using established testing patterns and common fixtures.

## Project Testing Context

**Test Suite**: 437+ tests across 5 categories
**Coverage**: 60-65% (target: 80%)
**Testing Frameworks**:
- pytest (with pytest-asyncio, pytest-cov, pytest-xdist)
- Hypothesis (property-based testing)
- unittest.mock (AsyncMock, MagicMock, patch)

**Test Categories**:
- Unit Tests (350+) - Fast, no external dependencies
- Integration Tests (50+) - Real infrastructure
- Property Tests (27+) - Hypothesis-based edge case discovery
- Contract Tests (20+) - MCP protocol compliance
- Performance Tests (10+) - Regression tracking

## Your Task

### Step 1: Gather Information

Ask the user using the AskUserQuestion tool:

**Question 1**: What module/file do you want to test?
- Header: "Module"
- Provide text input
- Example: "src/mcp_server_langgraph/tools/calculator_tools.py"
- Or: "mcp_server_langgraph.auth.middleware.AuthMiddleware"

**Question 2**: What type of test?
- Header: "Test Type"
- Options:
  - Unit Test: Fast, mocked dependencies
  - Integration Test: Real infrastructure (Redis, OpenFGA, etc.)
  - Property Test: Hypothesis-based testing
  - Contract Test: Protocol/schema validation

**Question 3**: Does the module use async functions?
- Header: "Async?"
- Options:
  - Yes: Uses async/await (most components)
  - No: Synchronous only

### Step 2: Analyze Module

1. Read the module file to understand:
   - Class names and methods
   - Function names and signatures
   - External dependencies
   - Async vs sync patterns

2. Determine what needs testing:
   - Public methods/functions
   - Edge cases (errors, empty inputs, max values)
   - Dependency interactions

### Step 3: Generate Test File

**File Location**:
- Unit tests: `tests/unit/<category>/test_<module_name>.py`
  - Categories: `auth/`, `core/`, `llm/`, `mcp/`, `observability/`, `tools/`, etc.
  - Example: `tests/unit/auth/test_auth_middleware.py`
- Integration tests: `tests/integration/test_<module_name>.py`
- Property tests: `tests/property/test_<module_name>.py`
- Contract tests: `tests/contract/test_<module_name>.py`

**File Structure**:

```python
"""
Comprehensive tests for <Module Name>

Tests cover:
- <Major functionality 1>
- <Major functionality 2>
- <Major functionality 3>
- Edge cases and error handling
"""

import pytest
<ASYNC_IMPORTS>
<MOCK_IMPORTS>
<MODULE_IMPORTS>

<FIXTURES>

<TEST_CLASSES>
```

### Template Components

#### Async Imports (if module uses async):
```python
from unittest.mock import AsyncMock, MagicMock, patch
```

#### Mock Imports (based on dependencies):
```python
# Common mocks for mcp-server-langgraph:

# For Redis dependencies:
from unittest.mock import AsyncMock, MagicMock

# For LLM dependencies:
from unittest.mock import patch
from langchain_core.messages import AIMessage, HumanMessage

# For OpenFGA dependencies:
from unittest.mock import AsyncMock
```

#### Module Imports:
```python
from mcp_server_langgraph.<path>.<module> import <ClassName>, <function_name>
```

#### Fixtures (based on module type):

**For Session/Store classes**:
```python
@pytest.fixture
def store():
    """Create test instance with default config"""
    return SessionStore(default_ttl=3600, max_sessions=10)
```

**For Auth/Middleware classes**:
```python
@pytest.fixture
def auth_middleware():
    """Create test auth middleware"""
    return AuthMiddleware(
        secret_key="test-secret-key",
        algorithm="HS256"
    )
```

**For Agent/Graph classes**:
```python
@pytest.fixture
def mock_llm():
    """Mock LLM for agent testing"""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(
        return_value=AIMessage(content="Test response")
    )
    return mock
```

#### Test Classes:

**Standard Unit Test Class**:
```python
@pytest.mark.unit
class Test<ClassName><Aspect>:
    """Tests for <specific aspect of functionality>"""

    def test_<method>_<condition>_<expected>(self, fixture_name):
        """Test <what this tests>"""
        # Given
        <setup test data>

        # When
        result = <call method>

        # Then
        assert result == expected
        assert <additional assertions>
```

**Async Test Class**:
```python
@pytest.mark.unit
@pytest.mark.asyncio
class Test<ClassName><Aspect>:
    """Tests for async <functionality>"""

    @pytest.mark.asyncio
    async def test_<method>_<condition>_<expected>(self, fixture_name):
        """Test <what this tests>"""
        # Given
        <setup test data>

        # When
        result = await <call async method>

        # Then
        assert result == expected
```

**Property-Based Test Class**:
```python
from hypothesis import given, settings
from hypothesis import strategies as st

@pytest.mark.property
@pytest.mark.unit
class Test<ClassName>Properties:
    """Property-based tests for <functionality>"""

    @given(
        param1=st.integers(min_value=1, max_value=100),
        param2=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=50, deadline=2000)
    def test_<property_name>(self, param1, param2):
        """Property: <description of invariant>"""
        <test property>
```

### Common Test Patterns to Include

1. **Success Cases**: Test happy path with valid inputs
2. **Error Cases**: Test with invalid inputs, missing data
3. **Edge Cases**: Test with empty, None, max values, min values
4. **Async Cases** (if applicable): Test async operations complete correctly
5. **Mock Verification** (if applicable): Verify mocks called correctly

### Example Test Generation

**For a module like** `src/mcp_server_langgraph/tools/calculator_tools.py`:

Generate:
```python
"""
Comprehensive tests for calculator tools

Tests cover:
- Arithmetic operations (add, subtract, multiply, divide)
- Expression evaluation
- Error handling (division by zero, invalid expressions)
- Edge cases (negative numbers, large values)
"""

import pytest

from mcp_server_langgraph.tools.calculator_tools import (
    add,
    calculator,
    divide,
    multiply,
    subtract,
)


@pytest.mark.unit
class TestCalculatorTool:
    """Test suite for calculator tool"""

    def test_calculator_simple_addition(self):
        """Test simple addition expression"""
        result = calculator.invoke({"expression": "2 + 2"})
        assert result == "4.0"

    def test_calculator_division_by_zero(self):
        """Test division by zero handling"""
        result = calculator.invoke({"expression": "5 / 0"})
        assert "Error" in result

    # ... more tests


@pytest.mark.unit
class TestAddTool:
    """Test suite for add tool"""

    def test_add_positive_numbers(self):
        """Test adding two positive numbers"""
        result = add.invoke({"a": 5, "b": 3})
        assert result == "8.0"

    # ... more tests
```

### Auto-Generate Test Stubs

Based on the module analysis, generate test stubs for:

1. **Each public method/function**:
   - Success case: `test_<method>_success`
   - Error case: `test_<method>_error`
   - Edge case: `test_<method>_edge_case`

2. **Each class**:
   - Separate test class: `Test<ClassName>`
   - Fixture for class instantiation

3. **Dependencies**:
   - Mock imports for external dependencies
   - Fixture for mocked dependencies

### Common Dependencies and Mocks

**Redis** (mcp-server-langgraph uses Redis for sessions):
```python
@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    return mock
```

**OpenFGA** (authorization):
```python
@pytest.fixture
def mock_openfga():
    """Mock OpenFGA client"""
    mock = AsyncMock()
    mock.check = AsyncMock(return_value={"allowed": True})
    mock.write = AsyncMock(return_value=True)
    return mock
```

**LLM** (language model):
```python
@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(
        return_value=AIMessage(content="Test response")
    )
    return mock
```

**Prometheus Metrics**:
```python
from unittest.mock import MagicMock

# No fixture needed, metrics are auto-mocked in tests
```

### Step 4: Inform User

After creating the test file, provide:

1. **File location**: Full path to created test file
2. **Test count**: Number of test stubs generated
3. **Coverage estimate**: Estimated coverage this will add
4. **Next steps**:
   - Fill in test logic
   - Run tests: `pytest <file_path> -v`
   - Run with coverage: `pytest <file_path> --cov=<module>`
   - Run fast: `make test-dev`

5. **Reminders**:
   - Use Given-When-Then pattern in tests
   - Add edge cases and error handling tests
   - Use async fixtures for async tests
   - Mock external dependencies

## Quality Checks

Before completing:

1. ✅ File follows naming convention `test_<module>.py`
2. ✅ Imports are correct and minimal
3. ✅ Test classes use `@pytest.mark.<category>` decorator
4. ✅ Async tests use `@pytest.mark.asyncio`
5. ✅ Fixtures are properly defined
6. ✅ Test names follow `test_<what>_<condition>_<expected>` pattern
7. ✅ Docstrings explain what each test does
8. ✅ Module header describes test coverage

## Example Outputs

**Example 1: Unit test for sync module**
```python
"""
Comprehensive tests for config module

Tests cover:
- Settings initialization
- Environment variable loading
- Validation logic
- Default values
"""

import pytest
from pydantic import ValidationError

from mcp_server_langgraph.core.config import Settings


@pytest.mark.unit
class TestSettings:
    """Tests for Settings configuration"""

    def test_settings_default_values(self):
        """Test default configuration values"""
        # Given/When
        settings = Settings()

        # Then
        assert settings.log_level == "INFO"
        assert settings.max_sessions == 100

    def test_settings_validation_error(self):
        """Test validation with invalid values"""
        # Given/When/Then
        with pytest.raises(ValidationError):
            Settings(max_sessions=-1)
```

**Example 2: Unit test for async module**
```python
"""
Comprehensive tests for session store

Tests cover:
- Session creation and retrieval
- TTL and expiration
- Session deletion
- Error handling
"""

import pytest
from unittest.mock import AsyncMock

from mcp_server_langgraph.session.store import SessionStore


@pytest.mark.unit
class TestSessionStore:
    """Tests for SessionStore"""

    @pytest.fixture
    def store(self):
        """Create test session store"""
        return SessionStore(default_ttl=3600, max_sessions=10)

    @pytest.mark.asyncio
    async def test_create_session_success(self, store):
        """Test successful session creation"""
        # Given
        user_id = "user:alice"

        # When
        session_id = await store.create(user_id=user_id)

        # Then
        assert session_id is not None
        session = await store.get(session_id)
        assert session.user_id == user_id
```

**Example 3: Property-based test**
```python
"""
Property-based tests for JWT encoding

Tests cover:
- Encode/decode round-trip properties
- Expiration invariants
- Signature verification
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mcp_server_langgraph.auth.jwt import encode_jwt, decode_jwt


@pytest.mark.property
@pytest.mark.unit
class TestJWTProperties:
    """Property-based tests for JWT"""

    @given(
        username=st.text(min_size=1, max_size=50),
        expiration=st.integers(min_value=60, max_value=86400)
    )
    @settings(max_examples=50, deadline=2000)
    def test_jwt_roundtrip(self, username, expiration):
        """Property: Encode/decode should be reversible"""
        # Given
        secret = "test-secret"

        # When
        token = encode_jwt(username, expiration, secret)
        decoded = decode_jwt(token, secret)

        # Then
        assert decoded["username"] == username
```

## Notes

- Do NOT run the tests automatically - let user run them
- DO generate comprehensive test stubs
- DO include appropriate mocks for dependencies
- DO follow existing testing patterns
- DO use Given-When-Then structure
- DO add helpful docstrings

---

**Success Criteria**:
- ✅ Test file created in correct location
- ✅ Appropriate test category markers
- ✅ Fixtures for common setup
- ✅ Test stubs for major functionality
- ✅ Mocks for external dependencies
- ✅ Async decorators where needed
- ✅ Clear docstrings and comments
