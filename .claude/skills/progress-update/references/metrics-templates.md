# Metrics Templates & Health Assessment

Reference material for sprint health assessment, issue detection, and automated metrics collection.

---

## Sprint Health Assessment (Step 5)

Determine sprint health based on:

**Indicators**:
| Indicator | Status | Criteria |
|-----------|--------|----------|
| On schedule | Green/Yellow/Red | Completion rate vs time elapsed |
| Scope stable | Green/Yellow/Red | No major scope changes |
| Quality maintained | Green/Yellow/Red | Tests passing, coverage maintained |
| Blockers | Green/Yellow/Red | Number of blocked items |

**Overall Health**:
- Green - Healthy: On track, no blockers, quality maintained
- Yellow - At Risk: Behind schedule or quality issues
- Red - Critical: Major blockers or significant delays

---

## Issues and Recommendations (Step 7)

Based on metrics, identify:

**Issues**:
- Behind schedule: If completion rate < (days elapsed / total days)
- Quality degradation: If test pass rate < 95% or coverage dropped
- Scope creep: If total items increased significantly
- Blockers: List any blocked items

**Recommendations**:
- Adjust scope if behind schedule
- Focus on quality if test failures
- Address blockers immediately
- De-prioritize low-value items
- Request help if needed

---

## Automated Metrics Collection

**Metrics to Auto-Collect**:
1. Git commits (count, types, files changed)
2. Test results (pass/fail/skip counts)
3. Code coverage percentage
4. TODO count (source code vs catalog)
5. Lines of code (added/removed)

**Metrics to Manually Track**:
1. Hours spent (from TodoWrite actuals)
2. Blockers and resolutions
3. Quality issues encountered
4. Lessons learned

---

## Example Output

```
=== Sprint Progress Update ===

Sprint: Technical Debt - 2025-10-18
Status: On Track

Progress:
- Completed: 24/27 items (89%)
- In Progress: 0 items
- Blocked: 0 items

Velocity:
- Items per day: 24
- Sprint duration: 1 day
- Efficiency: 8x faster than estimated

Recent Wins:
- CI/CD workflows fixed
- Prometheus monitoring integrated
- Alerting system wired to all modules
- Search tools implemented

Deferred (properly documented):
- Storage backend implementation (3 items)
- Spec created: STORAGE_BACKEND_REQUIREMENTS.md

Metrics:
- Commits: 18
- Files modified: 25+
- Lines added: +2,500
- Tests: 722/727 passing (99.3%)
- Coverage: 69%

Next Steps:
1. Deploy to production
2. Schedule storage backend sprint
3. Fix remaining 5 test assertions

Full Report: docs-internal/SPRINT_PROGRESS_20251018.md
```

---

*Last Updated: 2025-10-20*
