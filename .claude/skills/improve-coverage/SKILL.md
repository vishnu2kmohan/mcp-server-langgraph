---
name: improve-coverage
description: Systematically improve test coverage toward 80% target. Use when you need to identify coverage gaps, generate test recommendations, and create improvement plans.
allowed-tools:
  - Bash(uv:*)
  - Read
  - Glob
  - Grep
  - Write
---
# Improve Test Coverage

**Usage**: `/improve-coverage`

**Purpose**: Analyze coverage gaps and generate targeted test stubs to increase coverage toward the 80% target.

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

---

## Step 1: Gather Information

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

---

## Step 2: Run Coverage Analysis

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

---

## Step 3: Identify Coverage Gaps

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

---

## Steps 4-6: Analyze, Recommend, Generate Stubs

Read [references/test-stub-patterns.md](references/test-stub-patterns.md) for detailed guidance on:
- Analyzing uncovered lines and categorizing them
- Generating test recommendations with coverage estimates
- Generating test stub files with imports, fixtures, and placeholders

---

## Steps 7-8: Improvement Plan and Progress Tracking

Read [references/gap-analysis-templates.md](references/gap-analysis-templates.md) for:
- Coverage improvement plan template (prioritized by week)
- Progress tracking table format
- Coverage analysis tool commands (HTML/XML parsing)
- Error handling guidance

---

## Step 9: Inform User

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
   uv run --frozen pytest tests/unit/<category>/test_<module>.py --cov=src/mcp_server_langgraph/<module> --cov-report=term

   # Run full coverage to see improvement
   make test-coverage-combined
   ```

---

## Integration with Existing Commands

This command works well with:
- `/create-test` - Generate test files for low-coverage modules
- `/test-summary` - View overall test status
- `/coverage-trend` - Track coverage over time

---

## Notes

- Focus on **meaningful** coverage, not just hitting numbers
- Prioritize **critical paths** and **error handling**
- Use **property-based tests** for invariants
- Don't ignore **existing test failures** to increase coverage
