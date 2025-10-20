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

## 🔗 Related Commands

- `/coverage-trend` - Check test coverage trends
- `/security-scan-report` - Security performance
- `/test-summary regression` - Run regression tests

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

✅ Benchmark Results:

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
