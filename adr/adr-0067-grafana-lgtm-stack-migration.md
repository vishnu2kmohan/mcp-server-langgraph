---
title: "67. Grafana LGTM Stack Migration"
description: 'Architecture Decision Record: 67. Grafana LGTM Stack Migration'
icon: 'chart-line'
contentType: "reference"
seoTitle: "67. Grafana LGTM Stack Migration - Architecture Decision Record"
seoDescription: "Architecture Decision Record for 67. Grafana LGTM Stack Migration. Category: Infrastructure. Part of MCP Server with LangGraph documentation."
keywords:
  - "architecture"
  - "decision"
  - "record"
  - "ADR"
  - "MCP Server"
  - "LangGraph"
  - "Grafana"
  - "LGTM"
  - "Observability"
  - "Loki"
  - "Tempo"
  - "Mimir"
  - "Alloy"
---

# 67. Grafana LGTM Stack Migration

Date: 2025-12-07

## Status

Accepted

## Category

Infrastructure

## Context

The test infrastructure used multiple observability tools that were complex to manage:

**Previous Stack (Multi-vendor):**
- **Prometheus** - Metrics collection and storage
- **Alertmanager** - Alert routing and management
- **Jaeger** - Distributed tracing
- **Promtail** - Log collection agent
- **Loki** - Log aggregation

This created operational complexity:
1. Multiple configuration formats (Prometheus YAML, Jaeger YAML, Promtail YAML)
2. Multiple container images to maintain
3. Separate alerting configuration
4. No unified query interface

## Decision

Migrate to **Grafana LGTM Stack** - a unified observability platform:

| Component | Role | Replaces |
|-----------|------|----------|
| **L**oki | Log aggregation | Promtail (collection moved to Alloy) |
| **G**rafana | Dashboards + Unified Alerting | Alertmanager |
| **T**empo | Distributed tracing | Jaeger |
| **M**imir | Metrics storage | Prometheus (storage only, scraping moved to Alloy) |
| **Alloy** | Unified collector | Prometheus (scraping) + Promtail + OTEL Collector |

### Architecture

```
Applications → OpenTelemetry SDK
                    ↓
              Grafana Alloy (OTLP receiver)
                    ↓
         ┌─────────┼─────────┐
         ↓         ↓         ↓
       Tempo     Mimir     Loki
      (traces)  (metrics)  (logs)
         └─────────┼─────────┘
                   ↓
               Grafana
         (Unified Dashboards + Alerting)
```

### Key Changes

**docker-compose.test.yml services:**

| Old Service | New Service | Purpose |
|-------------|-------------|---------|
| `prometheus` | `mimir-test` | Metrics storage |
| `alertmanager` | Removed | Now in Grafana Unified Alerting |
| `jaeger` | `tempo-test` | Distributed tracing |
| `promtail` | Removed | Now in Alloy |
| N/A | `alloy-test` | Unified telemetry collector |

**Configuration files:**

| Old File | New File |
|----------|----------|
| `docker/prometheus/prometheus.yml` | `docker/alloy/alloy-config.alloy` |
| `docker/promtail/promtail-config.yml` | `docker/alloy/alloy-config.alloy` |
| `docker/alertmanager/alertmanager.yml` | `monitoring/grafana/alerting/` |
| `docker/jaeger/jaeger-config.yml` | `docker/tempo/tempo-config.yaml` |
| N/A | `docker/mimir/mimir-config.yaml` |

## Consequences

### Positive

1. **Unified Configuration**: Single Alloy config for all telemetry collection
2. **Single Query Interface**: All telemetry in Grafana (logs, traces, metrics)
3. **Simpler Alerting**: Grafana Unified Alerting replaces separate Alertmanager
4. **Better Trace-Log Correlation**: Native exemplar support between Tempo and Loki
5. **Reduced Container Count**: 4 services instead of 5 (Alloy consolidates collection)
6. **GCP Native Integration**: Mimir/Tempo support GCS backends for production

### Negative

1. **Learning Curve**: New Alloy configuration syntax (River DSL)
2. **Health Check Complexity**: Minimal/distroless images require custom health checks
3. **Initial Setup**: More upfront configuration for Mimir (vs simple Prometheus)

### Lessons Learned

#### Distroless Container Health Checks

Several LGTM images lack common tools like `wget`/`curl`:

| Image | Has wget/curl? | Health Check Pattern |
|-------|----------------|---------------------|
| `grafana/alloy` | No | Bash TCP: `bash -c '</dev/tcp/localhost/PORT'` |
| `grafana/mimir` | No (distroless) | Disable: `healthcheck: { disable: true }` |
| `grafana/tempo` | Yes (wget) | Standard: `wget --spider -q URL` |
| `grafana/loki` | Yes (wget) | Standard: `wget --spider -q URL` |

See `.claude/memory/distroless-container-healthchecks.md` for patterns.

#### Loki Timestamp Rejection

Alloy batches logs before sending, which can cause Loki to reject logs with "timestamp too old" errors in test environments. Fixed by disabling `reject_old_samples` in `docker/loki/loki-config.yaml`.

## Gateway Routes

All services accessible via Traefik gateway at `http://localhost/`:

| Route | Service | Purpose |
|-------|---------|---------|
| `/dashboards` | Grafana | Unified dashboards + alerting |
| `/logs` | Loki | Log API |
| `/tempo` | Tempo | Trace API |
| `/mimir` | Mimir | Metrics API |
| `/alloy` | Alloy | Collector UI |

## Related ADRs

- [ADR-0003: Dual Observability (OpenTelemetry + LangSmith)](/architecture/adr-0003-dual-observability)

## Post-Implementation Enhancements (2026-01-07)

### JSON Structured Logging

All LGTM stack and infrastructure services now output JSON-formatted logs for improved parsing in Loki:

| Service | Configuration | Purpose |
|---------|--------------|---------|
| Loki | `log_format: json` | Internal log parsing |
| Tempo | `log_format: json` | Trace correlator logs |
| Mimir | `log_format: json` | Metrics backend logs |
| Alloy | `format = "json"` | Collector agent logs |
| Traefik | `--log.format=json` | Gateway access logs |
| PostgreSQL | `log_destination=jsonlog` | Database query logs |
| Redis | redis_exporter | Metrics exporter logs |
| OpenFGA | `OPENFGA_LOG_FORMAT=json` | Authorization logs |
| Qdrant | `QDRANT__LOGGER__FORMAT=json` | Vector DB logs |
| Grafana | `GF_LOG_CONSOLE_FORMAT=json` | Dashboard service logs |
| MCP Server | `LOG_FORMAT=json` + uvicorn config | Application logs |

### OTEL Resource Attributes

Services now include OTEL resource attributes for trace correlation:

```yaml
OTEL_SERVICE_NAME: "service-name"
OTEL_RESOURCE_ATTRIBUTES: "service.namespace=agent-studio,deployment.environment=test"
```

### Alert-Runbook Integration

Comprehensive runbook coverage for all alert rules:

| Runbook File | Sections Added | Key Alerts |
|--------------|----------------|------------|
| `authentication-alerts.md` | AuthzProxyDown | Authorization proxy health |
| `langgraph-agent-health.md` | MCPServerDown | MCP service availability |
| `resilience-alerts.md` | 8 sections | Circuit breakers, bulkheads, fallbacks |
| `sla-alerts.md` | URL fix | SLAUptimeBreach typo corrected |

### Runbook Anchor Validation

New test `test_runbook_anchors_exist` in `tests/unit/scripts/test_alert_consolidation.py`:
- Validates all `runbook_url` annotations reference existing sections
- Prevents broken runbook links in alerts
- Enforces 100% runbook anchor coverage

### Alert-Runbook Dashboard

New Grafana dashboard: `Operations/alert-runbook-matrix.json`
- Active alerts table with clickable runbook links
- Runbook quick reference guide
- Alert history by severity
- LGTM stack health overview

## Files Changed

- `docker-compose.test.yml` - New LGTM services + JSON logging + OTEL attributes
- `docker/alloy/alloy-config.alloy` - Unified collector config + authz-proxy scrape
- `docker/tempo/tempo-config.yaml` - Trace storage config + JSON logging
- `docker/mimir/mimir-config.yaml` - Metrics storage config + JSON logging
- `docker/loki/loki-config.yaml` - Log storage config + JSON logging + retention
- `docker/uvicorn-log-config.yaml` - New uvicorn JSON logging config
- `monitoring/grafana/datasources.yml` - Grafana data source config
- `monitoring/grafana/dashboards/Operations/alert-runbook-matrix.json` - New dashboard
- `monitoring/prometheus/rules/lgtm-alerts.yaml` - AuthzProxyDown alert + runbook URLs
- `monitoring/runbooks/authentication-alerts.md` - AuthzProxyDown section
- `monitoring/runbooks/langgraph-agent-health.md` - MCPServerDown section
- `monitoring/runbooks/resilience-alerts.md` - 8 new resilience pattern sections
- `tests/unit/scripts/test_alert_consolidation.py` - Runbook anchor validation test
- `.claude/CLAUDE.md` - Updated observability reference
- `.claude/memory/distroless-container-healthchecks.md` - New lessons learned
