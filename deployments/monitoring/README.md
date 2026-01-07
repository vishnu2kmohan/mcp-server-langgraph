# Monitoring Assets

This directory contains alerting rules and Helm values for the observability stack.

## Dashboard Location

**Grafana dashboards have been consolidated to `monitoring/grafana/dashboards/`.**

The canonical location for all 36 dashboards is now organized by folder:

| Folder | Dashboards | Description |
|--------|------------|-------------|
| AI/ | 5 | AI/ML observability, suggestions, UX metrics |
| Application/ | 14 | Core application metrics, costs, HITL |
| Auth/ | 4 | Authentication, Keycloak, OpenFGA, security |
| Compliance/ | 3 | SOC2, SLA, audit compliance |
| Infrastructure/ | 5 | PostgreSQL, Redis, Qdrant, Traefik, LGTM |
| Overview/ | 1 | High-level LangGraph agent overview |
| Resilience/ | 2 | Golden signals, resilience patterns |
| WebSocket/ | 2 | LLM streaming, WebSocket telemetry |

**Sync Script**: `./scripts/sync-grafana-dashboards.sh`
**Validation**: `uv run python scripts/validation/validate_grafana_dashboards.py`
**Auto-fix**: `uv run python scripts/validation/fix_grafana_dashboards.py`

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
  -d @monitoring/grafana/dashboards/Application/session-lifecycle-dashboard.json \
  http://admin:admin@localhost:3000/api/dashboards/db
```

### Via Kubernetes ConfigMap

Dashboards are auto-provisioned via Grafana sidecar using ConfigMaps with:
- Label: `grafana_dashboard: "1"`
- Annotation: `grafana_folder: "<FolderName>"`

The Helm chart generates folder-specific ConfigMaps automatically.

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
