# Performance Optimization Checklist

## Overview

Systematic checklist for identifying, measuring, and resolving performance bottlenecks in the MCP Server LangGraph project.

## Phase 1: Establish Baseline (Day 1)

### Identify Performance Goals
- [ ] Define performance requirements (latency, throughput, resource usage)
- [ ] Identify critical user journeys to optimize
- [ ] Set target metrics (e.g., "API response < 200ms p95")
- [ ] Prioritize optimizations by impact vs. effort

### Measure Current Performance
- [ ] Run benchmarks: `pytest --benchmark-only`
- [ ] Measure test suite duration: `pytest -m unit --durations=20`
- [ ] Record API response times (Grafana/Prometheus)
- [ ] Profile application: `python -m cProfile -o profile.stats app.py`
- [ ] Check memory usage: `memory_profiler` or `tracemalloc`
- [ ] Document baseline metrics in spreadsheet or ADR

### Infrastructure Metrics
- [ ] CPU usage: Current average and peak
- [ ] Memory usage: Current average and peak
- [ ] Disk I/O: Read/write operations per second
- [ ] Network I/O: Bandwidth usage
- [ ] Database query performance: Slow query log analysis
- [ ] Cache hit rate: Redis/L1/L2 cache effectiveness

## Phase 2: Profiling & Analysis (Days 2-3)

### CPU Profiling
```bash
# Profile application
python -m cProfile -o profile.stats src/mcp_server_langgraph/main.py

# Analyze profile
python -m pstats profile.stats
# Commands: sort cumulative, stats 20

# Visual profiling
snakeviz profile.stats
```

- [ ] Identify top 10 CPU-intensive functions
- [ ] Check for unnecessary loops or recursion
- [ ] Look for inefficient algorithms (O(n²) → O(n log n))
- [ ] Identify hot paths in critical code

### Memory Profiling
```bash
# Memory profiler
pip install memory_profiler
python -m memory_profiler script.py

# Track memory allocations
python -m tracemalloc script.py
```

- [ ] Identify memory leaks
- [ ] Check for large object allocations
- [ ] Look for circular references (esp. with AsyncMock in tests)
- [ ] Verify garbage collection is working

### Database Profiling
- [ ] Enable PostgreSQL slow query log (`log_min_duration_statement = 100`)
- [ ] Analyze queries: `EXPLAIN ANALYZE SELECT ...`
- [ ] Check for missing indexes
- [ ] Identify N+1 query problems
- [ ] Review connection pool settings

### API Profiling
- [ ] Use OpenTelemetry traces to identify slow endpoints
- [ ] Check LangSmith for LLM call latency
- [ ] Measure middleware overhead
- [ ] Profile serialization/deserialization (Pydantic)

## Phase 3: Optimization Strategies

### Algorithm Optimization
- [ ] Replace O(n²) algorithms with O(n log n) or O(n)
- [ ] Use appropriate data structures (dict for lookups, set for membership)
- [ ] Implement caching for expensive computations
- [ ] Use generators instead of lists for large datasets
- [ ] Lazy load data when possible

### Database Optimization
- [ ] Add indexes to frequently queried columns
- [ ] Use database connection pooling (SQLAlchemy, psycopg2)
- [ ] Implement read replicas for read-heavy workloads
- [ ] Use database query caching (Redis)
- [ ] Batch insert/update operations
- [ ] Use `select_related()` / `prefetch_related()` (if using ORM)
- [ ] Denormalize data where appropriate

### Caching Strategy
- [ ] Implement L1 (in-memory) cache for frequently accessed data
- [ ] Implement L2 (Redis) cache for shared data
- [ ] Set appropriate TTLs for cache entries
- [ ] Implement cache warming for critical data
- [ ] Use cache-aside pattern for consistency
- [ ] Monitor cache hit rate (target: > 80%)

### API Optimization
- [ ] Enable HTTP/2 or HTTP/3
- [ ] Implement response compression (gzip)
- [ ] Use CDN for static assets
- [ ] Implement pagination for large result sets
- [ ] Use field selection (GraphQL-style) to reduce payload size
- [ ] Implement request batching where applicable

### Async & Concurrency
- [ ] Convert synchronous I/O to async (asyncio)
- [ ] Use asyncio.gather() for parallel async operations
- [ ] Implement background tasks (Celery, RQ)
- [ ] Use thread/process pools for CPU-bound tasks
- [ ] Optimize number of workers (uvicorn --workers N)

### Code-Level Optimization
- [ ] Use list comprehensions instead of for loops (where appropriate)
- [ ] Use `__slots__` for classes with many instances
- [ ] Avoid unnecessary object creation in loops
- [ ] Use `functools.lru_cache` for expensive pure functions
- [ ] Replace string concatenation with f-strings or join()
- [ ] Use built-in functions (they're optimized in C)

## Phase 4: Testing & Validation

### Benchmark Tests
- [ ] Write benchmark tests for critical paths
- [ ] Run benchmarks before optimization (baseline)
- [ ] Run benchmarks after optimization (compare)
- [ ] Ensure improvement meets targets (e.g., 2x faster)
- [ ] Add regression tests: `pytest --benchmark-autosave`

### Load Testing
```bash
# Using locust
locust -f loadtest.py --host=http://localhost:8000

# Using k6
k6 run --vus 100 --duration 30s loadtest.js
```

- [ ] Test with realistic load (number of users, requests/sec)
- [ ] Identify breaking points (max throughput)
- [ ] Check for memory leaks under load
- [ ] Verify error rate < 0.1% under normal load
- [ ] Test with spike traffic (sudden increase)

### Regression Prevention
- [ ] Add performance tests to CI/CD
- [ ] Set performance budgets (max response time, max memory)
- [ ] Monitor trends over time (Grafana dashboards)
- [ ] Alert on performance degradation

## Phase 5: Monitoring & Iteration

### Production Monitoring
- [ ] Set up Prometheus metrics for key operations
- [ ] Create Grafana dashboards for performance KPIs
- [ ] Configure alerts for performance degradation
- [ ] Monitor p50, p95, p99 latencies
- [ ] Track error rates and timeouts

### Continuous Improvement
- [ ] Review performance metrics weekly
- [ ] Prioritize next optimization targets
- [ ] Document optimizations in ADRs
- [ ] Share findings with team

## Performance Targets

### API Response Times
- [ ] p50 latency < 100ms
- [ ] p95 latency < 200ms
- [ ] p99 latency < 500ms

### Test Suite Performance
- [ ] Unit tests < 120s (currently ~220s - needs optimization)
- [ ] Integration tests < 5min
- [ ] Full test suite < 10min

### Resource Usage
- [ ] Memory usage < 2GB per instance
- [ ] CPU usage < 70% average
- [ ] Database connections < 100 per instance

### LLM Performance
- [ ] LLM token processing > 1000 tokens/sec
- [ ] Streaming latency < 50ms TTFB (time to first byte)
- [ ] Tool execution < 2s per tool call

## Common Performance Anti-Patterns

- ❌ **Premature optimization**: Measure first, optimize later
- ❌ **Micro-optimizations**: Focus on algorithmic improvements first
- ❌ **N+1 queries**: Always use joins or prefetch
- ❌ **Synchronous I/O**: Use async for I/O-bound operations
- ❌ **No caching**: Cache expensive computations
- ❌ **Large payloads**: Paginate and compress
- ❌ **No monitoring**: Can't improve what you don't measure

## Validation Commands

```bash
# Run benchmarks
pytest --benchmark-only

# Profile CPU
python -m cProfile -o profile.stats app.py
snakeviz profile.stats

# Profile memory
python -m memory_profiler script.py

# Load testing
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Check slow tests
pytest -m unit --durations=20

# Monitor production
# Open Grafana dashboard: http://localhost:3000
```

## Success Criteria

- [ ] All performance targets met
- [ ] Benchmarks show improvement (≥ 2x for targeted optimizations)
- [ ] No regressions in other areas
- [ ] Load tests pass at target scale
- [ ] Production metrics improved
- [ ] Documentation updated (ADRs, CHANGELOG)
- [ ] Team briefed on optimizations

---

**Created**: 2025-11-15
**Use for**: Performance bottleneck resolution
**Estimated Duration**: 1-2 weeks (depending on scope)
