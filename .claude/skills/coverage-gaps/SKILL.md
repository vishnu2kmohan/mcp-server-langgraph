---
name: coverage-gaps
description: Analyzes test coverage gaps and missing test scenarios. Uses cached coverage data when available, falls back to static analysis in Plan mode. Use when the user asks about coverage, test gaps, or untested code paths.
metadata:
  author: mcp-server-langgraph
  version: "2.0"
compatibility: Claude Code 1.0+
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, LS, Bash(uv run --frozen pytest --collect-only *), Bash(uv run --frozen coverage report *)
disable-model-invocation: true
argument-hint: [--module <module> | --all]
---

# Coverage Gaps Dashboard

Generate a visual coverage gaps dashboard for the mcp-server-langgraph project. This command provides an at-a-glance view of coverage health with ASCII heatmaps and prioritization.

## Plan Mode Compatibility

This skill is **Plan mode compatible** because:

1. **Uses `context: fork`** - Runs in isolated Explore subagent
2. **Uses `agent: Explore`** - Read-only tools by default
3. **No edits to codebase** - Only outputs analysis results

**Plan Mode Fallback**: If Bash is blocked in Plan mode, this skill falls back to static analysis of existing `coverage.xml` or `.coverage` files. Full coverage execution requires exiting Plan mode.

## Project Coverage Context

**Current Coverage**: 60-65% combined (unit + integration)
**Target Coverage**: 80%
**Test Suite**: 437+ tests
**Strategy**: Prioritize by risk and criticality

## Workflow

### Step 1: Run Coverage Analysis

Run pytest with coverage:
```bash
uv run --frozen pytest tests/ --cov=src/mcp_server_langgraph --cov-report=term --cov-report=html --quiet
```

Parse coverage output to extract:
- Overall coverage percentage
- Per-module coverage
- Per-file coverage
- Line counts (total, covered, missed)

### Step 2: Generate Visual Coverage Heatmap

Create an ASCII heatmap showing coverage by module:

**Heatmap Legend**:
- Green (80-100%): Good coverage
- Yellow (60-79%): Needs improvement
- Orange (40-59%): Poor coverage
- Red (0-39%): Critical gap

### Step 3: Risk-Based Prioritization

Prioritize coverage gaps based on:

1. **Criticality** (weighted 50%):
   - Auth/Security: Critical
   - Agent/Core: Critical
   - Sessions: High
   - Tools: Medium
   - Utils: Low

2. **Current Coverage** (weighted 30%):
   - 0-39%: Critical
   - 40-59%: High
   - 60-79%: Medium
   - 80-100%: Low

3. **Lines of Code** (weighted 20%):
   - >500 lines: High impact
   - 200-500 lines: Medium impact
   - <200 lines: Low impact

**Risk Score Formula**:
```
Risk Score = (Criticality × 0.5) + ((100 - Coverage) × 0.3) + (LOC/1000 × 0.2)
```

### Step 4: Coverage Trend Analysis

Show coverage trend over recent commits (if available).

### Step 5: Module Health Summary

Provide per-module summary with health indicators.

### Step 6: Quick Wins vs Long-Term Gaps

Identify quick coverage wins vs complex gaps:
- **Quick Wins** (< 2 hours): Small improvements with high impact
- **Long-Term Gaps** (> 4 hours): Complex areas needing comprehensive testing

### Step 7: Actionable Recommendations

Provide specific, actionable next steps organized by phase:
- Phase 1: Quick Wins (Week 1)
- Phase 2: Critical Gaps (Week 2-3)
- Phase 3: Polish (Week 4)

### Step 8: Generate Dashboard

Output final coverage dashboard with:
- Current vs target coverage
- Gap percentage
- Trend indicator
- Critical gaps count
- Quick wins count
- Next action recommendations

## Commands to Run

```bash
# Generate test for highest priority gap
/create-test auth/rbac.py

# Run tests and check coverage improvement
uv run --frozen pytest tests/unit/auth/test_auth_rbac.py --cov=src/mcp_server_langgraph/auth/rbac.py --cov-report=term

# Check overall coverage improvement
make test-coverage-combined

# Track progress
/coverage-gaps  # Run again to see improvement
```

## Integration with Other Commands

- `/improve-coverage` - Detailed analysis with test recommendations
- `/create-test` - Generate test files for gap modules
- `/test-summary` - Overall test health
- `/coverage-trend` - Historical coverage tracking

## Notes

- **Focus on risk**, not just percentages
- **Quick wins** build momentum
- **Critical gaps** should be addressed urgently
- **Trend matters** more than absolute numbers
- Visual representation helps prioritization

## Success Criteria

- Visual ASCII heatmap generated
- Gaps prioritized by risk score
- Quick wins identified
- Actionable plan with timeline
- Specific commands to run next
- Dashboard shows at-a-glance health

---

**Last Updated**: 2026-02-05
