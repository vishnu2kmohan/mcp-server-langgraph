# Coverage Gaps Dashboard

You are tasked with generating a visual coverage gaps dashboard for the mcp-server-langgraph project. This command provides an at-a-glance view of coverage health with ASCII heatmaps and prioritization.

## Project Coverage Context

**Current Coverage**: 60-65% combined (unit + integration)
**Target Coverage**: 80%
**Test Suite**: 437+ tests
**Strategy**: Prioritize by risk and criticality

## Your Task

### Step 1: Run Coverage Analysis

1. **Run pytest with coverage**:
   ```bash
   uv run --frozen pytest tests/ --cov=src/mcp_server_langgraph --cov-report=term --cov-report=html --quiet
   ```

2. **Parse coverage output** to extract:
   - Overall coverage percentage
   - Per-module coverage
   - Per-file coverage
   - Line counts (total, covered, missed)

### Step 2: Generate Visual Coverage Heatmap

Create an ASCII heatmap showing coverage by module:

**Heatmap Legend**:
- 🟢 Green (80-100%): Good coverage
- 🟡 Yellow (60-79%): Needs improvement
- 🟠 Orange (40-59%): Poor coverage
- 🔴 Red (0-39%): Critical gap

**Example Heatmap Output**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  COVERAGE HEATMAP - mcp-server-langgraph
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Module                     Coverage  Status  Lines    Missing
  ──────────────────────────────────────────────────────────────
  📦 core/
    ├─ agent.py              ████████  82%   🟢  456     82
    ├─ config.py             ██████░░  73%   🟡  234     63
    └─ feature_flags.py      ████████  91%   🟢  127     11

  🔐 auth/
    ├─ middleware.py         ███████░  78%   🟡  312     69
    ├─ jwt.py                ████████  88%   🟢  198     24
    ├─ rbac.py               ██░░░░░░  25%   🔴  267    200  ⚠️
    └─ keycloak.py           ███░░░░░  35%   🔴  189    123  ⚠️

  💾 session/
    ├─ store.py              ███████░  76%   🟡  345     83
    ├─ distributed.py        ███░░░░░  38%   🔴  402    249  ⚠️
    └─ checkpointing.py      ████████  84%   🟢  278     44

  🔧 tools/
    ├─ calculator_tools.py   ████████  95%   🟢  156     8
    ├─ filesystem.py         ██████░░  62%   🟡  289    110
    └─ search_tools.py       ███████░  72%   🟡  201     56

  🌐 mcp/
    ├─ stdio_server.py       ███████░  77%   🟡  423    97
    ├─ protocol.py           █████░░░  58%   🟠  378    159  ⚠️
    └─ handlers.py           ████████  81%   🟢  234     44

  📊 observability/
    ├─ telemetry.py          ████████  86%   🟢  412     58
    ├─ logging.py            ███████░  79%   🟡  267     56
    └─ metrics.py            ████████  89%   🟢  334     37

  ──────────────────────────────────────────────────────────────
  TOTAL                      ██████░░  65%   🟡  6,302  1,573
  ──────────────────────────────────────────────────────────────

  Legend: ████ = covered | ░░░░ = missing | ⚠️ = critical gap
```

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
   - Greater than 500 lines: High impact
   - 200-500 lines: Medium impact
   - Less than 200 lines: Low impact

**Risk Score Formula**:
```text
Risk Score = (Criticality × 0.5) + ((100 - Coverage) × 0.3) + (LOC/1000 × 0.2)
```

**Prioritized Gap List**:
```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PRIORITY COVERAGE GAPS (by Risk Score)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Rank  File                        Cov   Risk   Category  Action
  ───────────────────────────────────────────────────────────────────
  🔥 1  auth/rbac.py                25%   8.9    Critical  URGENT
         Lines: 267 | Missing: 200
         Impact: Security vulnerability if untested
         Tests needed: ~12-15 tests
         Estimated time: 3-4 hours
         Command: /create-test auth/rbac.py

  🔥 2  session/distributed.py      38%   7.2    Critical  URGENT
         Lines: 402 | Missing: 249
         Impact: Session data loss/corruption risk
         Tests needed: ~15-18 tests
         Estimated time: 4-5 hours
         Command: /create-test session/distributed.py

  ⚠️ 3  auth/keycloak.py            35%   7.0    Critical  HIGH
         Lines: 189 | Missing: 123
         Impact: Authentication failures
         Tests needed: ~8-10 tests
         Estimated time: 2-3 hours
         Command: /create-test auth/keycloak.py

  ⚠️ 4  mcp/protocol.py             58%   5.1    High      HIGH
         Lines: 378 | Missing: 159
         Impact: Protocol compatibility issues
         Tests needed: ~10-12 tests
         Estimated time: 2-3 hours
         Command: /create-test mcp/protocol.py

  ℹ️ 5  tools/filesystem.py         62%   3.8    Medium    MEDIUM
         Lines: 289 | Missing: 110
         Impact: Tool reliability
         Tests needed: ~6-8 tests
         Estimated time: 1-2 hours
         Command: /create-test tools/filesystem.py

  ───────────────────────────────────────────────────────────────────
  Total Priority Files: 5
  Total Tests Needed: ~51-63 tests
  Estimated Coverage Gain: +12-15%
  Estimated Time: 12-17 hours
  ───────────────────────────────────────────────────────────────────
```

### Step 4: Coverage Trend Analysis

Show coverage trend over recent commits (if available):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  COVERAGE TREND (Last 10 Commits)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  70% ┤
  68% ┤                                             ╭──
  66% ┤                                       ╭─────╯
  64% ┤                                 ╭─────╯        Target: 80%
  62% ┤                           ╭─────╯              ════════
  60% ┤                     ╭─────╯                    Current: 65%
  58% ┤               ╭─────╯                          ────────
  56% ┤         ╭─────╯                                Gap: -15%
  54% ┤   ╭─────╯
  52% ┼───╯
      └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──→ commits
        10  9  8  7  6  5  4  3  2  1  now

  Trend: 📈 IMPROVING (+2.1%/week)
  Velocity: +1.3% per 5 commits
  ETA to 80%: ~6-8 weeks at current pace
```

### Step 5: Module Health Summary

**Per-Module Summary**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODULE HEALTH SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Module            Coverage  Health  Files  Gap to 80%  Priority
  ──────────────────────────────────────────────────────────────────
  📦 core/           82%      🟢      3      +2%         ✓ Good
  🔐 auth/           57%      🔴      4      -23%        🔥 URGENT
  💾 session/        66%      🟡      3      -14%        ⚠️ HIGH
  🔧 tools/          76%      🟡      3      -4%         ✓ Good
  🌐 mcp/            72%      🟡      3      -8%         ℹ️ MEDIUM
  📊 observability/  85%      🟢      3      +5%         ✓ Excellent
  ──────────────────────────────────────────────────────────────────

  Status Summary:
    🟢 Excellent (≥80%): 2 modules (33%)
    🟡 Needs Work (60-79%): 3 modules (50%)
    🔴 Critical (< 60%): 1 module (17%)

  Overall Assessment: MODERATE - Focus on auth module urgently
```

### Step 6: Quick Wins vs Long-Term Gaps

Identify quick coverage wins vs complex gaps:

**Quick Wins** (< 2 hours):
```
Quick Coverage Wins (< 2 hours each)
════════════════════════════════════════════════════════════════

1. tools/calculator_tools.py (95% → 98%)
   - Add 2 tests for edge cases
   - Estimated time: 20 minutes
   - Coverage gain: +3%

2. core/feature_flags.py (91% → 96%)
   - Add 3 tests for flag combinations
   - Estimated time: 30 minutes
   - Coverage gain: +5%

3. observability/metrics.py (89% → 94%)
   - Add 4 tests for metric edge cases
   - Estimated time: 45 minutes
   - Coverage gain: +5%

Total Quick Win Potential: +13% in ~2 hours
```

**Long-Term Gaps** (> 4 hours):
```
Complex Coverage Gaps (> 4 hours each)
════════════════════════════════════════════════════════════════

1. auth/rbac.py (25% → 80%)
   - Complex OpenFGA integration
   - Requires comprehensive mocking
   - 12-15 tests needed
   - Estimated time: 3-4 hours
   - Coverage gain: +55%

2. session/distributed.py (38% → 80%)
   - Distributed session logic
   - Requires Redis integration tests
   - 15-18 tests needed
   - Estimated time: 4-5 hours
   - Coverage gain: +42%
```

### Step 7: Actionable Recommendations

Provide specific, actionable next steps:

**Recommended Action Plan**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RECOMMENDED ACTION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Phase 1: Quick Wins (Week 1)
  ════════════════════════════════════════════════════════════════
  Goal: Increase coverage from 65% → 70% (+5%)
  Time: 2-3 hours

  1. ✓ Add edge case tests to tools/calculator_tools.py
     Command: /create-test tools/calculator_tools.py

  2. ✓ Add flag combination tests to core/feature_flags.py
     Command: /create-test core/feature_flags.py

  3. ✓ Add metric tests to observability/metrics.py
     Command: /create-test observability/metrics.py

  Phase 2: Critical Gaps (Week 2-3)
  ════════════════════════════════════════════════════════════════
  Goal: Increase coverage from 70% → 78% (+8%)
  Time: 8-10 hours

  1. 🔥 URGENT: Fix auth/rbac.py (25% → 80%)
     Command: /create-test auth/rbac.py
     Priority: Security-critical, start immediately

  2. ⚠️ HIGH: Fix session/distributed.py (38% → 80%)
     Command: /create-test session/distributed.py
     Priority: Data integrity risk

  Phase 3: Polish (Week 4)
  ════════════════════════════════════════════════════════════════
  Goal: Increase coverage from 78% → 80% (+2%)
  Time: 2-3 hours

  1. ℹ️ Fill remaining gaps in mcp/protocol.py
  2. ℹ️ Fill remaining gaps in tools/filesystem.py

  ────────────────────────────────────────────────────────────────
  Timeline: 4 weeks
  Total Time: 12-16 hours
  Coverage Gain: +15% (65% → 80%)
  Success Rate: High (incremental approach)
  ────────────────────────────────────────────────────────────────
```

### Step 8: Generate Dashboard

Output final coverage dashboard:

```
╔══════════════════════════════════════════════════════════════════╗
║              COVERAGE GAPS DASHBOARD                             ║
║              mcp-server-langgraph                                ║
╠══════════════════════════════════════════════════════════════════╣
║  Current Coverage:    65%  [████████████████████░░░░░░░░]        ║
║  Target Coverage:     80%  [████████████████████████████░░]      ║
║  Gap:                -15%  [⚠️  Needs improvement]               ║
║  Trend:               📈   [+2.1%/week - Improving]              ║
║  Test Count:         437   [Unit: 350 | Integration: 50+]       ║
║  ETA to 80%:       6-8wk   [At current pace]                    ║
╠══════════════════════════════════════════════════════════════════╣
║  Critical Gaps:        1   [🔴 auth/ module @ 57%]               ║
║  High Priority:        2   [🟠 session/, mcp/]                   ║
║  Medium Priority:      3   [🟡 tools/, core/]                    ║
╠══════════════════════════════════════════════════════════════════╣
║  Quick Wins:          3    [+13% gain in ~2 hours]               ║
║  Long-Term Gaps:      2    [+97% gain in ~8 hours]               ║
╠══════════════════════════════════════════════════════════════════╣
║  Next Action:  🔥 /create-test auth/rbac.py                      ║
║  After That:   ⚠️ /create-test session/distributed.py            ║
╚══════════════════════════════════════════════════════════════════╝
```

### Commands to Run

Provide specific commands for next steps:

```bash
# 1. Generate test for highest priority gap
/create-test auth/rbac.py

# 2. Run tests and check coverage improvement
uv run --frozen pytest tests/unit/test_auth_rbac.py --cov=src/mcp_server_langgraph/auth/rbac.py --cov-report=term

# 3. Check overall coverage improvement
make test-coverage-combined

# 4. Track progress
/coverage-gaps  # Run again to see improvement
```

## Error Handling

- If coverage report missing, run pytest with coverage first
- If unable to parse coverage data, show manual instructions
- If no gaps found (100% coverage), congratulate and exit
- If coverage data is stale, warn and suggest re-running

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

---

**Success Criteria**:
- ✅ Visual ASCII heatmap generated
- ✅ Gaps prioritized by risk score
- ✅ Quick wins identified
- ✅ Actionable plan with timeline
- ✅ Specific commands to run next
- ✅ Dashboard shows at-a-glance health
