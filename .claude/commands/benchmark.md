---
description: Execute performance benchmarks and analyze results
---
# Run Performance Benchmarks

**Usage**: `/benchmark` or `/benchmark --quick`

**Purpose**: Execute performance benchmarks and analyze results

---

## 🎯 What This Command Does

Runs the project's performance benchmark suite using the existing Makefile command:

```bash
make benchmark
```

This executes benchmarks for:
- Agent response time
- LLM call latency
- Authorization check performance
- Database query performance
- Context loading speed

---

## 📊 Execution Steps

### Step 1: Run Benchmarks

Execute the benchmark suite:

```bash
# Full benchmark suite
make benchmark

# View benchmark configuration
cat tests/benchmark/config.yaml
```

### Step 2: Parse Results

Analyze benchmark output:

```bash
# Benchmark results are typically in:
# - pytest output (console)
# - .benchmark/ directory (if configured)

# Look for metrics like:
# - ops/sec (operations per second)
# - mean, median, p95, p99 latencies
# - memory usage
# - CPU usage
```

### Step 3: Compare with Baselines

```bash
# If baseline metrics exist
if [ -f "tests/regression/baseline_metrics.json" ]; then
    echo "Comparing with baseline..."
    # Check for regressions (>20% slower)
fi
```

### Step 4: Generate Summary

Provide user with formatted summary:

```
=== Performance Benchmark Results ===

Benchmark Suite: Agent Performance
Executed: YYYY-MM-DD HH:MM:SS

Results:
┌─────────────────────────────┬──────────┬─────────┬─────────┐
│ Benchmark                   │ Mean     │ P95     │ Status  │
├─────────────────────────────┼──────────┼─────────┼─────────┤
│ agent_response              │ 2.3s     │ 4.5s    │ ✅ PASS │
│ llm_call                    │ 1.8s     │ 3.2s    │ ✅ PASS │
│ authorization_check         │ 25ms     │ 45ms    │ ✅ PASS │
│ database_query              │ 15ms     │ 30ms    │ ✅ PASS │
│ context_loading             │ 120ms    │ 200ms   │ ✅ PASS │
└─────────────────────────────┴──────────┴─────────┴─────────┘

Baseline Comparison:
- No regressions detected ✅
- 2/5 benchmarks improved (context_loading: -15ms)

Memory Usage:
- Peak: 256 MB
- Average: 180 MB

Overall Status: ✅ ALL BENCHMARKS PASSING
```

---

## 📈 Benchmark Categories

### Agent Performance
- Full request/response cycle
- Including LLM calls
- With real auth checks
- Target: p95 < 5s

### LLM Performance
- API call latency
- Streaming response time
- Fallback mechanism
- Target: p95 < 10s

### Authorization Performance
- OpenFGA check latency
- Cache hit rate
- Session validation
- Target: p95 < 50ms

### Database Performance
- Query execution time
- Connection pool usage
- Transaction overhead
- Target: p95 < 100ms

---

## 🎯 Performance Targets

From `tests/regression/baseline_metrics.json`:

```json
{
  "agent_response": {
    "p95_ms": 5000,
    "max_regression": 0.2
  },
  "llm_call": {
    "p95_ms": 10000,
    "max_regression": 0.2
  },
  "authorization": {
    "p95_ms": 50,
    "max_regression": 0.2
  }
}
```

**Regression threshold**: 20% slower than baseline = FAIL

---

## 🔧 Options

### Quick Benchmark

Run subset of benchmarks (fast, ~30 seconds):

```bash
# Run only critical path benchmarks
pytest tests/benchmark/ -k "agent_response or authorization" -v
```

### Full Benchmark

Complete suite with memory profiling (~5 minutes):

```bash
make benchmark

# Or with memory profiling
pytest tests/benchmark/ --benchmark-enable --benchmark-autosave
```

### Comparison Mode

Compare against previous run:

```bash
pytest tests/benchmark/ --benchmark-compare=0001 --benchmark-compare-fail=mean:20%
```

---

## 📊 Output Formats

### Console Output

```
tests/benchmark/test_performance.py::test_agent_response
  Mean: 2.3s, StdDev: 0.3s, Min: 1.8s, Max: 3.1s, Ops/sec: 0.43

tests/benchmark/test_performance.py::test_llm_call
  Mean: 1.8s, StdDev: 0.2s, Min: 1.5s, Max: 2.3s, Ops/sec: 0.56
```

### JSON Report

```json
{
  "machine_info": {...},
  "benchmarks": [
    {
      "name": "test_agent_response",
      "stats": {
        "mean": 2.3,
        "stddev": 0.3,
        "min": 1.8,
        "max": 3.1,
        "ops": 0.43
      }
    }
  ]
}
```

---

## 💡 When to Run

**Required**:
- Before releases
- After performance optimizations
- When adding expensive operations
- After dependency upgrades

**Optional**:
- Weekly (trending)
- After major refactoring
- When investigating slowness

---

## 🚨 Regression Handling

If benchmarks fail:

1. **Identify** which benchmark regressed
2. **Analyze** recent changes (git log)
3. **Profile** the slow component
4. **Optimize** or accept new baseline
5. **Re-run** to verify fix

**Acceptable reasons for regression**:
- Added functionality (more work)
- Security hardening (trade-off)
- Dependency update (temporary)

**Unacceptable**:
- Accidental O(n²) algorithm
- Missing cache
- Unnecessary computation

---

## 📈 NEW: Trend Analysis

### Step 5: Historical Trend Analysis

After running benchmarks, analyze historical performance trends:

**Load Historical Data**:
```bash
# Find all benchmark results
find .benchmark/ -name "*.json" -type f | sort -r | head -10

# Or use git commits with benchmark data
git log --all --oneline --grep="benchmark" | head -20
```

**Trend Visualization**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PERFORMANCE TREND ANALYSIS (Last 10 Runs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Agent Response Time (P95)
  ─────────────────────────────────────────────────────────────────
  6.0s ┤
  5.5s ┤                                    Target: 5.0s
  5.0s ┤ ════════════════════════════════════════════════════════
  4.5s ┤                               ╭────╮
  4.0s ┤                         ╭─────╯    ╰────╮
  3.5s ┤                   ╭─────╯                ╰──╮
  3.0s ┤             ╭─────╯                         ╰────╮
  2.5s ┤       ╭─────╯                                    │
  2.0s ┤ ╭─────╯                                          ╰────●
       └─┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──────────────────────────→
         10  9  8  7  6  5  4  3  2  1  now          runs

  Trend: 📉 IMPROVING (-18% over last 10 runs)
  Velocity: -0.3s per run
  Status: ✅ Below target (2.0s < 5.0s)

  ─────────────────────────────────────────────────────────────────
  LLM Call Latency (P95)
  ─────────────────────────────────────────────────────────────────
  4.0s ┤                                    ●
  3.5s ┤                          ╭────●────╯
  3.0s ┤                    ╭─────╯              Target: 10.0s
  2.5s ┤              ╭─────╯
  2.0s ┤        ╭─────╯
  1.5s ┤  ╭─────╯
       └─┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──────────────────────────→
         10  9  8  7  6  5  4  3  2  1  now          runs

  Trend: 📈 DEGRADING (+12% over last 10 runs) ⚠️
  Velocity: +0.15s per run
  Status: ⚠️ Degrading but within target
  Root Cause: Likely LLM provider latency increase

  ─────────────────────────────────────────────────────────────────
  Authorization Check (P95)
  ─────────────────────────────────────────────────────────────────
  60ms ┤
  50ms ┤ ════════════════════════════════════════════════════════ Target
  40ms ┤                     ●────●────●────●────●────●────●
  30ms ┤       ●────●────●────╯
  20ms ┤ ●────●╯
       └─┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──────────────────────────→
         10  9  8  7  6  5  4  3  2  1  now          runs

  Trend: 📊 STABLE (±2% variation)
  Velocity: +0.5ms per run (negligible)
  Status: ✅ Consistently below target
```

**Trend Statistics**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TREND STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Benchmark            Trend      Change    Status    Concern
  ──────────────────────────────────────────────────────────────────
  agent_response       📉 Down    -18%      ✅ Good   None
  llm_call             📈 Up      +12%      ⚠️ Watch  Provider latency
  authorization        📊 Stable  ±2%       ✅ Good   None
  database_query       📉 Down    -8%       ✅ Good   None
  context_loading      📉 Down    -22%      ✅ Great  Recent optimization
  ──────────────────────────────────────────────────────────────────

  Overall Health: 🟢 HEALTHY
  Improving: 3/5 benchmarks
  Degrading: 1/5 benchmarks (under investigation)
  Stable: 1/5 benchmarks
```

### Step 6: Automated Regression Detection

**Regression Detection Algorithm**:
```
For each benchmark:
  1. Calculate mean of last 5 runs
  2. Calculate current deviation from mean
  3. Check if deviation > threshold (20%)
  4. Check if trend is consistently worsening (3+ runs)
  5. Flag as regression if both conditions met
```

**Regression Alert**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🚨 REGRESSION DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Benchmark: llm_call (P95 latency)
  Severity: ⚠️ MEDIUM

  Current:  4.2s
  Baseline: 3.2s
  Change:   +31% (EXCEEDS 20% threshold)

  Trend: Degrading for last 3 consecutive runs
    Run -3: 3.5s (+9%)
    Run -2: 3.8s (+19%)
    Run -1: 4.2s (+31%) ← Current

  Likely Causes:
  1. LLM provider latency increase (external)
  2. Increased prompt size (check recent changes)
  3. Network latency to LLM API
  4. Rate limiting kicking in

  Recommended Actions:
  1. Check LLM provider status page
  2. Review recent prompt changes (git log)
  3. Monitor for next 2 runs to confirm trend
  4. Consider fallback model if persistent
  5. Add timeout/circuit breaker if needed

  Auto-Generated Issue:
  Title: "Performance Regression: llm_call latency +31%"
  Labels: performance, regression, p2
  Link: [Create Issue] (if GitHub CLI available)
```

### Step 7: Performance Recommendations

Based on trend analysis, provide actionable recommendations:

**Recommendation Engine**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PERFORMANCE RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Based on trend analysis:

  ✅ Celebrate Success:
     - context_loading improved 22% (great optimization!)
     - agent_response improved 18% (excellent work!)
     - database_query improved 8% (good progress!)

  ⚠️ Monitor Closely:
     - llm_call degrading +12% over 10 runs
       Action: Investigate LLM provider latency
       Timeline: Review in next 2 benchmark runs

  🔥 Optimize Now:
     None currently (all within targets)

  📊 Maintain:
     - authorization stable at 40ms (keep it up!)

  🎯 Next Targets:
     1. Investigate llm_call latency increase
     2. Continue optimizing context_loading (already great!)
     3. Consider setting stricter targets (current: generous)

  💡 Pro Tips:
     - Run benchmarks weekly to catch trends early
     - Update baselines after confirmed optimizations
     - Document optimization wins in ADRs
     - Share performance improvements with team
```

### Step 8: Benchmark History Storage

**Store benchmark results for trend analysis**:
```bash
# Create benchmark history directory
mkdir -p .benchmark/history/

# Save current benchmark with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp .benchmark/latest.json .benchmark/history/$TIMESTAMP.json

# Store in git (optional, for CI/CD tracking)
git add .benchmark/history/$TIMESTAMP.json
git commit -m "chore(benchmark): performance results $TIMESTAMP"

# Prune old results (keep last 30, cross-platform, handles filenames safely)
uv run --frozen python3 -c "
from pathlib import Path
import os
files = sorted(Path('.benchmark/history').glob('*.json'), key=os.path.getmtime, reverse=True)
for f in files[30:]:  # Keep 30 newest
    f.unlink()
"
```

**Integrate with CI/CD**:
```yaml
# .github/workflows/benchmark.yaml
name: Performance Benchmarks

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run benchmarks
        run: make benchmark

      - name: Save results
        run: |
          mkdir -p .benchmark/history
          cp .benchmark/latest.json .benchmark/history/$(date +%Y%m%d).json

      - name: Detect regressions
        run: |
          uv run --frozen python scripts/detect_benchmark_regressions.py \
            --threshold 20 \
            --consecutive 3

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: .benchmark/history/
```

---

## 🔗 Related Commands

- `/coverage-trend` - Check test coverage trends
- `/security-scan-report` - Security performance
- `/test-summary regression` - Run regression tests
- `/ci-status` - Check CI pipeline status including benchmarks

---

## 🛠️ Troubleshooting

### Issue: Benchmarks fail with timeouts

```bash
# Increase timeout
pytest tests/benchmark/ --timeout=300
```

### Issue: High variance in results

```bash
# Run more iterations
pytest tests/benchmark/ --benchmark-warmup=on --benchmark-min-rounds=10
```

### Issue: No baseline to compare

```bash
# Create initial baseline
pytest tests/benchmark/ --benchmark-autosave

# Use as baseline for future runs
pytest tests/benchmark/ --benchmark-compare=0001
```

---

## 📝 Example Session

```
User: /benchmark

Claude:
Running performance benchmarks...

Executing: make benchmark

🔄 Running benchmark suite (this may take 2-3 minutes)...

- ✅ Benchmark Results:

Agent Performance:
- agent_response: Mean 2.3s, P95 4.5s ✅ (target: <5s)
- Context: 120ms ✅ (15ms faster than baseline)

LLM Performance:
- llm_call: Mean 1.8s, P95 3.2s ✅ (target: <10s)

Authorization:
- openfga_check: Mean 25ms, P95 45ms ✅ (target: <50ms)

Comparison with Baseline:
- No regressions detected ✅
- 2 improvements found
- Overall: 5% faster than baseline

Memory Usage: 256 MB peak (within limits)

Recommendation: Performance is healthy. Safe to deploy.

Full report: .benchmark/0001_YYYYMMDD_HHMMSS.json
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Benchmark Tool**: pytest-benchmark
