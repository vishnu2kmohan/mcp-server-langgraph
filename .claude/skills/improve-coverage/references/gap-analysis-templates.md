# Gap Analysis Templates Reference

Detailed guidance for Steps 7-8 of the improve-coverage skill, plus coverage analysis tools, error handling, and success criteria.

---

## Step 7: Coverage Improvement Plan

Generate a systematic plan:

**Coverage Improvement Plan**:
```markdown
# Coverage Improvement Plan

## Current State
- Overall Coverage: 65%
- Target: 80%
- Gap: 15% (approximately 450 uncovered lines)

## Priority 1: Critical Modules (Week 1)
1. auth/rbac.py (25% -> 80%)
   - Add 8 tests for role validation
   - Add 6 tests for permission checking
   - Estimated time: 2-3 hours
   - Coverage gain: +5%

2. session/distributed.py (38% -> 80%)
   - Add 10 tests for session replication
   - Add 5 tests for failover logic
   - Estimated time: 3-4 hours
   - Coverage gain: +4%

## Priority 2: High-Value Modules (Week 2)
3. tools/filesystem.py (62% -> 80%)
   - Add 6 tests for error handling
   - Add 4 tests for edge cases
   - Estimated time: 1-2 hours
   - Coverage gain: +2%

4. mcp/protocol.py (58% -> 80%)
   - Add 8 tests for protocol error handling
   - Estimated time: 2 hours
   - Coverage gain: +2%

## Priority 3: Polish (Week 3)
5. Remaining 8 files (70-75% -> 80%)
   - Add 15-20 tests total
   - Estimated time: 3-4 hours
   - Coverage gain: +2%

## Timeline
- Week 1: Priority 1 modules -> 65% + 9% = 74%
- Week 2: Priority 2 modules -> 74% + 4% = 78%
- Week 3: Priority 3 modules -> 78% + 2% = 80%

## Success Metrics
- Coverage increases by 2-3% per week
- No regression in existing tests
- All new tests pass
- Coverage trend visible in CI
```

---

## Step 8: Track Progress

**Progress Tracking**:
```
Coverage Progress Tracker
=========================

+-----------------------+----------+----------+----------+----------+
| Module                | Current  | Target   | Gap      | Status   |
+-----------------------+----------+----------+----------+----------+
| auth/rbac.py          | 25%      | 80%      | -55%     | Crit     |
| session/distributed   | 38%      | 80%      | -42%     | Crit     |
| tools/filesystem      | 62%      | 80%      | -18%     | High     |
| mcp/protocol          | 58%      | 80%      | -22%     | High     |
| core/config           | 73%      | 80%      | -7%      | Med      |
+-----------------------+----------+----------+----------+----------+

Overall: 65% -> 80% (15% gap, ~35-40 tests needed)
```

---

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
uv run --frozen python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
for elem in tree.findall('.//class'):
    name = elem.get('filename')
    rate = float(elem.get('line-rate', 0)) * 100
    if rate < 70:
        print(f'{rate:.1f}% {name}')
"
```

---

## Error Handling

- If coverage report doesn't exist, run pytest with coverage
- If threshold invalid, default to 70%
- If module focus invalid, analyze all modules
- If unable to read source file, skip analysis for that file

---

## Success Criteria

- Coverage gaps identified and prioritized
- Specific test recommendations provided
- Test stubs generated (if requested)
- Improvement plan with timeline
- Progress tracking system in place
- Actionable next steps for user
