# LGTM Stack Alert Runbook

This runbook provides troubleshooting guidance for LGTM (Loki, Grafana, Tempo, Mimir) observability stack alerts.

## Overview

LGTM alerts monitor the health and performance of the observability infrastructure itself. These alerts are critical for ensuring visibility into system behavior.

## Symptoms

When these alerts fire, you may observe:
- Missing or delayed logs in Grafana
- Trace queries timing out or returning incomplete data
- Metrics dashboards showing gaps
- Slow or unresponsive Grafana dashboards

---

## LGTMStackDegraded

### Description
Less than 80% of LGTM stack components are healthy.

### Impact
**Warning** - Observability capabilities are degraded.

### Resolution
1. Check individual component status: `docker compose ps`
2. Review unhealthy component logs
3. Restart unhealthy components
4. Verify resource availability (CPU, memory, disk)

### Escalation
Notify platform team if multiple components are down.

---

## LokiHighRequestLatency

### Description
Loki p99 request latency exceeds 5 seconds.

### Impact
**Warning** - Log queries are slow, affecting troubleshooting.

### Resolution
1. Check Loki resource utilization
2. Review query complexity (wide time ranges, complex regex)
3. Check ingester and querier health
4. Consider scaling Loki horizontally

### Escalation
Create performance optimization ticket.

---

## LokiHighIngestionRate

### Description
Loki is receiving more than 10MB/s of logs.

### Impact
**Warning** - High log volume may impact performance and storage.

### Resolution
1. Identify high-volume log sources: check by job/namespace labels
2. Review log verbosity settings in applications
3. Consider sampling or filtering less critical logs
4. Verify storage capacity

### Escalation
Review logging policy with application teams.

---

## LokiTooManyActiveStreams

### Description
Loki has more than 10,000 active log streams.

### Impact
**Warning** - High stream cardinality impacts memory and query performance.

### Resolution
1. Identify streams with high cardinality labels
2. Review label usage in log pipelines
3. Consider relabeling to reduce cardinality
4. Check for label explosion from dynamic values

### Escalation
Create cardinality optimization ticket.

---

## TempoHighSpanRate

### Description
Tempo is receiving more than 10,000 spans per second.

### Impact
**Warning** - High trace volume may impact storage and query performance.

### Resolution
1. Identify high-volume trace sources
2. Review sampling configuration
3. Consider implementing tail-based sampling
4. Verify storage capacity

### Escalation
Review tracing policy with application teams.

---

## TempoHighQueryLatency

### Description
Tempo p95 query latency exceeds 10 seconds.

### Impact
**Warning** - Trace queries are slow, affecting troubleshooting.

### Resolution
1. Check Tempo resource utilization
2. Review query complexity (wide time ranges)
3. Check compactor health
4. Consider scaling Tempo

### Escalation
Create performance optimization ticket.

---

## MimirHighActiveSeries

### Description
Mimir has more than 500,000 active time series.

### Impact
**Warning** - High cardinality impacts memory and query performance.

### Resolution
1. Identify high-cardinality metrics: `topk(10, count by (__name__) ({__name__=~".+"}))`
2. Review metric label usage
3. Consider dropping unused labels
4. Check for label explosion from dynamic values

### Escalation
Create cardinality optimization ticket.

---

## MimirHighQueryLatency

### Description
Mimir p99 query latency exceeds 30 seconds.

### Impact
**Warning** - Metric queries are slow, affecting dashboards.

### Resolution
1. Check Mimir resource utilization
2. Review dashboard query complexity
3. Optimize PromQL queries (add filters, reduce time ranges)
4. Consider recording rules for expensive queries

### Escalation
Create performance optimization ticket.

---

## MimirIngestionRateHigh

### Description
Mimir sample ingestion rate exceeds 80,000 samples/second.

### Impact
**Warning** - Approaching ingestion rate limits (100,000/s).

### Resolution
1. Identify high-volume metric sources
2. Review scrape intervals (increase if too frequent)
3. Drop unused metrics at collection time
4. Consider metric aggregation

### Escalation
Review metrics collection policy.

---

## AlloyDataRefused

### Description
Alloy OTLP receiver is refusing more than 100 data points per second.

### Impact
**Warning** - Telemetry data is being dropped.

### Resolution
1. Check Alloy resource utilization
2. Review receiver buffer configuration
3. Check downstream exporters (Loki, Tempo, Mimir) health
4. Consider scaling Alloy

### Escalation
Investigate telemetry pipeline bottlenecks.

---

## AlloyExporterFailures

### Description
Alloy is failing to export more than 10 data points per second.

### Impact
**Warning** - Telemetry data may be lost.

### Resolution
1. Check exporter target health (Loki, Tempo, Mimir)
2. Review network connectivity
3. Check exporter configuration
4. Review retry queue settings

### Escalation
Check observability backend health.

---

## TraefikHighErrorRate

### Description
Traefik 5xx error rate exceeds 5%.

### Impact
**Warning** - Users are experiencing errors.

### Resolution
1. Identify affected routes/services
2. Check backend service health
3. Review error logs for root cause
4. Check for deployment issues

### Escalation
Page on-call if error rate continues to increase.

---

## TraefikHighLatency

### Description
Traefik p95 request latency exceeds 2 seconds.

### Impact
**Warning** - Users are experiencing slow responses.

### Resolution
1. Identify slow routes/services
2. Check backend service latency
3. Review resource utilization
4. Check for network issues

### Escalation
Create performance investigation ticket.

---

## TraefikBackendDown

### Description
A backend service is not reachable through Traefik.

### Impact
**Critical** - Service is unavailable to users.

### Resolution
1. Check backend service health: `docker compose ps`
2. Verify service is running and healthy
3. Check network connectivity between Traefik and service
4. Review Traefik router configuration

### Escalation
Page on-call immediately for critical services.
