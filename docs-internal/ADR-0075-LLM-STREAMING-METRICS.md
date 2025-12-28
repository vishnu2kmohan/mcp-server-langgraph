# ADR-0075: LLM Streaming Metrics Architecture

**Status**: Implemented
**Date**: 2025-12-28
**Authors**: Claude Code (AI-assisted)
**Total Tests**: 65 (unit: 30, integration: 21, e2e: 13, feature-flag: 12)

## Context

LLM streaming is a critical user experience feature. When streaming degrades, users experience:
- Long waits before first token appears (Time To First Chunk / TTFC)
- Choppy, uneven text flow (high inter-chunk latency)
- Failed or incomplete responses (errors/timeouts)

Without observability into streaming performance, we cannot:
- Detect SLA breaches before user complaints
- Compare provider performance
- Identify regression patterns
- Make data-driven capacity decisions

## Decision

We implement a comprehensive streaming metrics observability layer with four Prometheus metrics:

### Metrics Defined

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `llm_streaming_ttfc_seconds` | Histogram | model, provider | Time to first chunk |
| `llm_streaming_inter_chunk_latency_seconds` | Histogram | model, provider | Gap between chunks |
| `llm_streaming_duration_seconds` | Histogram | model, provider, status | Total streaming time |
| `llm_streaming_chunks_total` | Counter | model, provider | Total chunks emitted |

### Histogram Bucket Design

**TTFC Buckets** (optimized for user-perceived latency):
```python
(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
```
- SLA threshold: 2 seconds (p95)
- Critical threshold: 5 seconds

**Inter-Chunk Latency Buckets** (millisecond precision):
```python
(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
```
- SLA threshold: 250ms (p95)
- Smooth streaming: <50ms

**Duration Buckets** (end-to-end streaming):
```python
(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LLMFactory.astream()                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              StreamingMetricsContext                        │   │
│  │  ┌─────────┐  ┌──────────────┐  ┌────────────┐             │   │
│  │  │ start() │──│record_first_ │──│record_chunk│──┐          │   │
│  │  │         │  │chunk()       │  │()          │  │          │   │
│  │  └────┬────┘  └──────┬───────┘  └──────┬─────┘  │          │   │
│  │       │              │                 │        │          │   │
│  │       │              ▼                 ▼        │          │   │
│  │       │    ┌─────────────────┐  ┌───────────┐   │          │   │
│  │       │    │ record_ttfc()   │  │ record_   │   │          │   │
│  │       │    │ → Prometheus    │  │ inter_    │   │          │   │
│  │       │    └─────────────────┘  │ chunk_    │   │          │   │
│  │       │                         │ latency() │   │          │   │
│  │       │                         └───────────┘   │          │   │
│  │       │                                         │          │   │
│  │       └────────────────────────┬────────────────┘          │   │
│  │                                ▼                           │   │
│  │                      ┌──────────────────┐                  │   │
│  │                      │    finalize()    │                  │   │
│  │                      │  → duration      │                  │   │
│  │                      │  → chunk_count   │                  │   │
│  │                      └──────────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Prometheus Registry                          │
│                                                                     │
│  llm_streaming_ttfc_seconds{model="gpt-4o", provider="openai"}     │
│  llm_streaming_inter_chunk_latency_seconds{...}                     │
│  llm_streaming_duration_seconds{..., status="success"}             │
│  llm_streaming_chunks_total{...}                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Grafana Alloy Scraper                            │
│                    (Every 15s)                                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Grafana Mimir (Storage)                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 LLM Streaming Dashboard (Grafana)                   │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   TTFC p95      │  │  Inter-Chunk    │  │  Success Rate   │     │
│  │   Heatmap       │  │  Latency        │  │  by Provider    │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Chunks/sec    │  │  Duration by    │  │  Error Rate     │     │
│  │   by Model      │  │  Status         │  │  Timeline       │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Feature Flag

**Flag**: `FF_ENABLE_STREAMING_METRICS`
**Default**: `true`
**Description**: Enable Prometheus metrics for LLM streaming operations.

When disabled:
- All `record_*` functions become no-ops
- `StreamingMetricsContext` still tracks values internally (for debugging)
- No metrics emitted to Prometheus
- Useful for low-overhead environments or during testing

### SLA Alert Rules

```yaml
# TTFC p95 exceeds 2 seconds
- alert: StreamingTTFCBreached
  expr: |
    histogram_quantile(0.95, sum(rate(llm_streaming_ttfc_seconds_bucket[5m])) by (le, provider)) > 2
  for: 5m
  labels:
    severity: warning
    component: streaming
    sla_metric: ttfc

# Inter-chunk latency p95 exceeds 250ms
- alert: StreamingLatencyBreached
  expr: |
    histogram_quantile(0.95, sum(rate(llm_streaming_inter_chunk_latency_seconds_bucket[5m])) by (le, provider)) > 0.25
  for: 5m
  labels:
    severity: warning
    component: streaming
    sla_metric: inter_chunk_latency

# Error rate exceeds 5%
- alert: StreamingErrorRateHigh
  expr: |
    sum(rate(llm_streaming_duration_seconds_count{status!="success"}[5m])) by (provider)
    / sum(rate(llm_streaming_duration_seconds_count[5m])) by (provider) > 0.05
  for: 5m
  labels:
    severity: critical
    component: streaming
    sla_metric: error_rate
```

### Alertmanager Routing

Streaming SLA alerts route to:
1. **Critical**: PagerDuty + `#llm-streaming-alerts` Slack
2. **Warning**: `#llm-streaming-alerts` Slack only

## Key Implementation Details

### Lazy Initialization

Metrics are initialized lazily on first use to:
- Avoid startup overhead if never used
- Allow graceful degradation if `prometheus_client` not installed

```python
_metrics_available: bool | None = None

def _init_metrics() -> bool:
    global _metrics_available
    if _metrics_available is not None:
        return _metrics_available
    try:
        from prometheus_client import Counter, Histogram
        # Initialize metrics...
        _metrics_available = True
    except ImportError:
        _metrics_available = False
    return _metrics_available
```

### Model Family Normalization

Models are normalized to families for cardinality control:
- `gpt-4-turbo-preview` → `gpt-4`
- `claude-3-opus-20241022` → `claude-3-opus`
- `gemini-2.0-flash-exp` → `gemini-2.0-flash`

### Integration Points

| Component | Integration | Notes |
|-----------|-------------|-------|
| `LLMFactory.astream()` | Full instrumentation | Lines 774-909 |
| `/metrics` endpoint | Auto-exposed | via prometheus_client |
| Grafana Alloy | Scrapes every 15s | config.alloy |
| Grafana Mimir | Long-term storage | 13 months retention |

## Alternatives Considered

### 1. OpenTelemetry Metrics Only

**Rejected**: OpenTelemetry histogram support in Grafana is less mature than Prometheus native histograms.

### 2. Application-Level Logging Only

**Rejected**: Logs don't provide quantile calculations, time-series queries, or alerting integration.

### 3. Third-Party APM (Datadog, New Relic)

**Rejected**: Vendor lock-in, higher cost, and our stack already uses Prometheus/Grafana.

## Consequences

### Positive

- **Visibility**: Real-time streaming health monitoring
- **Alerting**: Proactive SLA breach detection
- **Comparison**: Provider/model performance comparison
- **Optimization**: Data-driven capacity planning

### Negative

- **Overhead**: ~0.1ms per metric recording (acceptable)
- **Cardinality**: Model label adds cardinality (mitigated by normalization)
- **Storage**: Histogram data consumes more storage than counters

### Neutral

- **Feature Flag**: Operators can disable in overhead-sensitive environments

## Files Changed

| File | Change |
|------|--------|
| `src/mcp_server_langgraph/llm/streaming_metrics.py` | New module |
| `src/mcp_server_langgraph/llm/llm_factory.py` | Instrumentation in `astream()` |
| `src/mcp_server_langgraph/core/feature_flags.py` | Add `enable_streaming_metrics` |
| `monitoring/grafana/dashboards/Application/llm-streaming.json` | Dashboard |
| `monitoring/prometheus/rules/streaming-sla-alerts.yml` | Alert rules |
| `deployments/monitoring/alertmanager/alertmanager-config.yaml` | Routing |

## Test Coverage

| Category | Count | File |
|----------|-------|------|
| Unit | 19 | `tests/unit/llm/test_streaming_metrics.py` |
| Feature Flag | 12 | `tests/unit/llm/test_streaming_metrics_feature_flag.py` |
| Integration | 21 | `tests/integration/observability/test_streaming_metrics_integration.py` |
| E2E | 13 | `tests/e2e/test_streaming_metrics_e2e.py` |
| **Total** | **65** | |

## References

- [Prometheus Histogram Best Practices](https://prometheus.io/docs/practices/histograms/)
- [Grafana LGTM Stack](https://grafana.com/docs/lgtm/)
- [LLM Observability Patterns](https://www.langchain.com/blog/llm-observability)
