# Improve Test Coverage

You are tasked with systematically improving test coverage for the mcp-server-langgraph project. This command analyzes coverage gaps and generates targeted test stubs to increase coverage toward the 80% target.

## Project Coverage Context

**Current Coverage**: 60-65% combined (unit + integration)
**Target Coverage**: 80%
**Test Suite**: 437+ tests across 5 categories
**Coverage Tools**: pytest-cov with HTML/XML reports

**Coverage Gap Strategy**:
- Identify files below threshold (default: 70%)
- Prioritize critical modules (auth, agent, sessions)
- Generate test stubs for uncovered lines
- Track progress toward 80% target

## Your Task

### Step 1: Gather Information

Ask the user using the AskUserQuestion tool:

**Question 1**: What coverage threshold to use?
- Header: "Threshold"
- Options:
  - 50%: Show all files below 50% (high-priority gaps)
  - 60%: Show files below 60% (medium-priority)
  - 70%: Show files below 70% (standard threshold)
  - 80%: Show files below 80% (target coverage)

**Question 2** (Optional): Focus on specific module?
- Header: "Module Focus"
- Options:
  - All modules: Analyze entire codebase
  - Auth: Focus on authentication/authorization
  - Agent: Focus on LangGraph agent
  - Sessions: Focus on session storage
  - Tools: Focus on MCP tools
  - Observability: Focus on telemetry/logging
  - Specific file: User-provided file path

### Step 2: Run Coverage Analysis

1. **Run pytest with coverage** (if coverage report doesn't exist):
   ```bash
   uv run --frozen pytest tests/ --cov=src/mcp_server_langgraph --cov-report=html --cov-report=xml --cov-report=term -v
   ```

2. **Parse coverage report**:
   - Read `htmlcov/index.html` for summary
   - Read `.coverage` database (if available)
   - Parse terminal output for quick overview

3. **Extract coverage data**:
   - File-level coverage percentages
   - Uncovered line ranges
   - Missing branches (if branch coverage enabled)

### Step 3: Identify Coverage Gaps

**Priority Ranking** (for files below threshold):

1. **Critical** (0-50% coverage):
   - Core agent modules
   - Authentication/authorization
   - Session management
   - Security-sensitive code

2. **High** (50-70% coverage):
   - MCP protocol implementation
   - Tools and integrations
   - Configuration management

3. **Medium** (70-80% coverage):
   - Utility functions
   - Helper classes
   - Less critical paths

**Output Format**:
```
Coverage Gap Analysis
=====================
Target: 80% | Current: 65% | Gap: 15%

Critical Gaps (0-50% coverage):
  [25%] src/mcp_server_langgraph/auth/rbac.py
        - Missing: Lines 45-67, 89-103
        - Uncovered: Role validation, permission checking

  [38%] src/mcp_server_langgraph/session/distributed.py
        - Missing: Lines 23-45, 78-92
        - Uncovered: Session replication, failover logic

High Priority (50-70% coverage):
  [62%] src/mcp_server_langgraph/tools/filesystem.py
        - Missing: Lines 156-178
        - Uncovered: Error handling, edge cases

  [58%] src/mcp_server_langgraph/mcp/protocol.py
        - Missing: Lines 234-256
        - Uncovered: Protocol error handling

Medium Priority (70-80% coverage):
  [73%] src/mcp_server_langgraph/core/config.py
        - Missing: Lines 89-94
        - Uncovered: Edge case validation

Total Files Below Threshold: 12
Estimated Tests Needed: ~35-40 tests
```

### Step 4: Analyze Uncovered Lines

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

### Step 5: Generate Test Recommendations

For each uncovered section, provide:

**Test Recommendation Format**:
```python
# File: src/mcp_server_langgraph/auth/rbac.py
# Lines 45-67: Role validation logic
# Current Coverage: 25% | Target: 80%

# Recommended Test 1: test_validate_role_success
"""Test successful role validation"""
# Location: tests/unit/test_auth_rbac.py
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
# Location: tests/unit/test_auth_rbac.py
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

### Step 6: Generate Test Stubs (Optional)

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

### Step 7: Coverage Improvement Plan

Generate a systematic plan:

**Coverage Improvement Plan**:
```markdown
# Coverage Improvement Plan

## Current State
- Overall Coverage: 65%
- Target: 80%
- Gap: 15% (approximately 450 uncovered lines)

## Priority 1: Critical Modules (Week 1)
1. auth/rbac.py (25% → 80%)
   - Add 8 tests for role validation
   - Add 6 tests for permission checking
   - Estimated time: 2-3 hours
   - Coverage gain: +5%

2. session/distributed.py (38% → 80%)
   - Add 10 tests for session replication
   - Add 5 tests for failover logic
   - Estimated time: 3-4 hours
   - Coverage gain: +4%

## Priority 2: High-Value Modules (Week 2)
3. tools/filesystem.py (62% → 80%)
   - Add 6 tests for error handling
   - Add 4 tests for edge cases
   - Estimated time: 1-2 hours
   - Coverage gain: +2%

4. mcp/protocol.py (58% → 80%)
   - Add 8 tests for protocol error handling
   - Estimated time: 2 hours
   - Coverage gain: +2%

## Priority 3: Polish (Week 3)
5. Remaining 8 files (70-75% → 80%)
   - Add 15-20 tests total
   - Estimated time: 3-4 hours
   - Coverage gain: +2%

## Timeline
- Week 1: Priority 1 modules → 65% + 9% = 74%
- Week 2: Priority 2 modules → 74% + 4% = 78%
- Week 3: Priority 3 modules → 78% + 2% = 80% ✓

## Success Metrics
- Coverage increases by 2-3% per week
- No regression in existing tests
- All new tests pass
- Coverage trend visible in CI
```

### Step 8: Track Progress

**Progress Tracking**:
```
Coverage Progress Tracker
=========================

┌─────────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Module              │ Current  │ Target   │ Gap      │ Status   │
├─────────────────────┼──────────┼──────────┼──────────┼──────────┤
│ auth/rbac.py        │ 25%      │ 80%      │ -55%     │ 🔴 Crit  │
│ session/distributed │ 38%      │ 80%      │ -42%     │ 🔴 Crit  │
│ tools/filesystem    │ 62%      │ 80%      │ -18%     │ 🟡 High  │
│ mcp/protocol        │ 58%      │ 80%      │ -22%     │ 🟡 High  │
│ core/config         │ 73%      │ 80%      │ -7%      │ 🟢 Med   │
└─────────────────────┴──────────┴──────────┴──────────┴──────────┘

Overall: 65% → 80% (15% gap, ~35-40 tests needed)
```

### Step 9: Inform User

After analysis, provide:

1. **Summary**:
   - Current vs target coverage
   - Number of files below threshold
   - Estimated tests needed
   - Time estimate

2. **Top Priority Files**: List 3-5 files that need immediate attention

3. **Actionable Next Steps**:
   - Which file to start with
   - Specific test recommendations
   - Link to `/create-test` command for generation
   - Run command to verify coverage increase

4. **Commands to Run**:
   ```bash
   # Generate test stub
   /create-test <priority-file>

   # Run tests and check coverage
   uv run --frozen pytest tests/unit/test_<module>.py --cov=src/mcp_server_langgraph/<module> --cov-report=term

   # Run full coverage to see improvement
   make test-coverage-combined
   ```

## Coverage Analysis Tools

**Parse HTML Coverage Report**:
```bash
# Extract coverage summary
grep -A 5 '<div class="summary"' htmlcov/index.html

# Find files below threshold
grep -E '<span class="pc_cov">([0-6][0-9]|[0-9])%</span>' htmlcov/index.html
```

**Parse XML Coverage Report**:
```bash
# Extract file-level coverage (if XML report exists)
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
for elem in tree.findall('.//class'):
    name = elem.get('filename')
    rate = float(elem.get('line-rate', 0)) * 100
    if rate < 70:
        print(f'{rate:.1f}% {name}')
"
```

## Error Handling

- If coverage report doesn't exist, run pytest with coverage
- If threshold invalid, default to 70%
- If module focus invalid, analyze all modules
- If unable to read source file, skip analysis for that file

## Integration with Existing Commands

This command works well with:
- `/create-test` - Generate test files for low-coverage modules
- `/test-summary` - View overall test status
- `/coverage-trend` - Track coverage over time

## Notes

- Focus on **meaningful** coverage, not just hitting numbers
- Prioritize **critical paths** and **error handling**
- Use **property-based tests** for invariants
- Don't ignore **existing test failures** to increase coverage

---

**Success Criteria**:
- ✅ Coverage gaps identified and prioritized
- ✅ Specific test recommendations provided
- ✅ Test stubs generated (if requested)
- ✅ Improvement plan with timeline
- ✅ Progress tracking system in place
- ✅ Actionable next steps for user
