# Monitoring Assets

This directory contains Grafana dashboards, alerting rules, and Helm values for the observability stack.

## Grafana Dashboards

### Golden Signals Dashboard (`golden-signals-dashboard.json`)

The primary operational dashboard following the Google SRE Golden Signals methodology:

- **Latency**: Request duration percentiles (p50, p95, p99)
- **Traffic**: Request rate by endpoint and status code
- **Errors**: Error rates and types
- **Saturation**: Resource utilization metrics

**UID**: `golden-signals`

### Session Lifecycle Dashboard (`session-lifecycle-dashboard.json`)

Tracks user session activity using `session.start` and `session.end` events:

- **Session Overview**: Total sessions started/ended, active session estimates
- **Session Activity Timeline**: Sessions over time with 5-minute granularity
- **User Activity**: Top users by session count, sessions per user
- **Session Health**: Timeout rate, error rate, clean logout rate

**Metrics Used**:
- `session_events_total{event="session.start"}`
- `session_events_total{event="session.end", reason="..."}`

**Labels**:
- `event`: Either `session.start` or `session.end`
- `reason`: End reason (`revoked`, `timeout`, `error`) - only for `session.end`
- `user_id`: Optional user identifier
- `session_id`: Optional session identifier

**UID**: `session-lifecycle`

### LLM Observability Dashboard (`llm-observability-dashboard.json`)

Monitors LLM API usage with bounded cardinality labels:

- **LLM Request Rate**: Requests per second by model family
- **Error Rate**: LLM API errors by type
- **Latency P95**: 95th percentile response time
- **Token Throughput**: Input/output token rates
- **Model Family Breakdown**: Usage by model family (gpt, claude, gemini)
- **Operation Type Breakdown**: Usage by operation (chat, completion, embedding)
- **Status Breakdown**: Success vs error rates

**Bounded Labels** (prevent cardinality explosion):
- `model_family`: Normalized model family (e.g., `gpt`, `claude`, `gemini`)
- `operation`: Operation type (e.g., `chat`, `completion`, `embedding`)
- `status`: Either `success` or `error`

**UID**: `llm-observability`

## SLO Alerts (`slo-alerts.yaml`)

PrometheusRule resources for SLO-based alerting:

- **Availability SLOs**: 99.9% uptime targets
- **Latency SLOs**: P95 latency thresholds
- **Error Budget Alerts**: Burn rate alerts for error budgets

## Helm Values

### Loki Stack (`loki-stack-values.yaml`)

Configuration for the Grafana Loki logging stack.

### Kubecost (`kubecost-values.yaml`)

Configuration for Kubecost cost monitoring.

## Validation

Validate dashboard JSON files:

```bash
make validate-dashboards
```

This checks:
1. Valid JSON syntax
2. Required dashboard fields (panels, title, uid)
3. Panel structure validation

## Importing Dashboards

### Via Grafana UI

1. Open Grafana at `http://localhost:3000`
2. Go to Dashboards > Import
3. Upload the JSON file or paste contents
4. Select the Prometheus data source
5. Click Import

### Via Grafana API

```bash
curl -X POST -H "Content-Type: application/json" \
  -d @deployments/monitoring/session-lifecycle-dashboard.json \
  http://admin:admin@localhost:3000/api/dashboards/db
```

### Via Kubernetes ConfigMap

Dashboards can be auto-provisioned by adding them to a ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  labels:
    grafana_dashboard: "1"
data:
  session-lifecycle.json: |
    <dashboard JSON content>
```

## Metrics Reference

### Session Lifecycle Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `session_events_total` | Counter | `event`, `reason`, `user_id`, `session_id` | Session lifecycle events |
| `auth_sessions_active` | Gauge | `backend` | Current active session count |
| `auth_session_created_total` | Counter | `backend` | Total sessions created |
| `auth_session_revoked_total` | Counter | `backend` | Total sessions revoked |

### LLM Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `llm_requests_total` | Counter | `model_family`, `operation`, `status` | Total LLM API requests |
| `llm_request_duration_seconds` | Histogram | `model_family`, `operation` | Request latency |
| `llm_tokens_total` | Counter | `model_family`, `direction` | Token usage (input/output) |
| `llm_errors_total` | Counter | `model_family`, `error_type` | LLM API errors |

### Golden Signals Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | `method`, `path`, `status` | HTTP request count |
| `http_request_duration_seconds` | Histogram | `method`, `path` | Request latency |
| `http_requests_in_flight` | Gauge | `method`, `path` | Current in-flight requests |
