# Test Stub Patterns Reference

Detailed guidance for Steps 4-6 of the improve-coverage skill.

---

## Step 4: Analyze Uncovered Lines

For each file below threshold:

1. **Read the file** to understand uncovered code
2. **Categorize uncovered lines**:
   - Error handling paths
   - Edge cases (None, empty, max values)
   - Async exception handling
   - Conditional branches
   - Exception catch blocks

3. **Determine test type needed**:
   - Unit test (mocked dependencies)
   - Integration test (real dependencies)
   - Property test (invariants)
   - Error/exception test

---

## Step 5: Generate Test Recommendations

For each uncovered section, provide:

**Test Recommendation Format**:
```python
# File: src/mcp_server_langgraph/auth/rbac.py
# Lines 45-67: Role validation logic
# Current Coverage: 25% | Target: 80%

# Recommended Test 1: test_validate_role_success
"""Test successful role validation"""
# Location: tests/unit/auth/test_auth_rbac.py
# Test should cover:
# - Lines 45-52: Role format validation
# - Lines 53-60: Permission lookup
# - Lines 61-67: Return validated role

@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_role_success(self, mock_openfga):
    """Test successful role validation"""
    # Given
    rbac = RBACManager(openfga_client=mock_openfga)
    role = "admin"
    mock_openfga.check.return_value = {"allowed": True}

    # When
    result = await rbac.validate_role(role)

    # Then
    assert result.is_valid is True
    assert result.role == "admin"
    mock_openfga.check.assert_called_once()

# Estimated coverage increase: +15% (to 40%)


# Recommended Test 2: test_validate_role_invalid_format
"""Test role validation with invalid format"""
# Location: tests/unit/auth/test_auth_rbac.py
# Test should cover:
# - Lines 45-48: Format validation failure
# - Lines 89-92: Error handling

@pytest.mark.unit
async def test_validate_role_invalid_format(self, mock_openfga):
    """Test role validation with invalid format"""
    # Given
    rbac = RBACManager(openfga_client=mock_openfga)
    invalid_role = "admin@invalid!"

    # When/Then
    with pytest.raises(ValueError, match="Invalid role format"):
        await rbac.validate_role(invalid_role)

# Estimated coverage increase: +8% (to 48%)
```

---

## Step 6: Generate Test Stubs (Optional)

If user wants test stubs generated, create test files with:

1. **Imports** based on module dependencies
2. **Fixtures** for common setup
3. **Test stubs** for each uncovered section
4. **Placeholders** for assertions

**Example Generated Test Stub**:
```python
"""
Tests for RBAC manager - Coverage improvement

This test file was generated to improve coverage from 25% to 80%.
Focus areas:
- Role validation (lines 45-67)
- Permission checking (lines 89-103)
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp_server_langgraph.auth.rbac import RBACManager


@pytest.mark.unit
class TestRBACManagerRoleValidation:
    """Tests for role validation - currently 25% coverage"""

    @pytest.fixture
    def mock_openfga(self):
        """Mock OpenFGA client"""
        mock = AsyncMock()
        mock.check = AsyncMock(return_value={"allowed": True})
        return mock

    @pytest.fixture
    def rbac_manager(self, mock_openfga):
        """Create RBAC manager with mocked OpenFGA"""
        return RBACManager(openfga_client=mock_openfga)

    @pytest.mark.asyncio
    async def test_validate_role_success(self, rbac_manager, mock_openfga):
        """Test successful role validation [Lines 45-67]"""
        # TODO: Implement test
        # Covers: Role format validation, permission lookup, return
        pass

    @pytest.mark.asyncio
    async def test_validate_role_invalid_format(self, rbac_manager):
        """Test role validation with invalid format [Lines 45-48, 89-92]"""
        # TODO: Implement test
        # Covers: Format validation failure, error handling
        pass

    @pytest.mark.asyncio
    async def test_validate_role_openfga_error(self, rbac_manager, mock_openfga):
        """Test role validation when OpenFGA fails [Lines 95-103]"""
        # TODO: Implement test
        # Covers: OpenFGA connection error, retry logic
        mock_openfga.check.side_effect = ConnectionError("OpenFGA unavailable")
        pass
```
