# Grafana Dashboard Metrics Audit - Final Report

**Project**: mcp-server-langgraph
**Date**: 2025-12-10
**Auditor**: Claude Code Analysis
**Mimir Endpoint**: http://localhost:19009/prometheus

---

## Executive Summary

### Metrics Status
- **Total Dashboards Audited**: 15
- **Available Metrics in Mimir**: 2,605 metrics
- **Unique Missing Metrics**: 67 metrics
- **Dashboards with Issues**: 15 (100%)
- **Total Panel Issues**: 193 panels

### Key Findings

✅ **Good News**:
- Alloy (OpenTelemetry Collector) IS exposing metrics (found `otelcol_*` metrics)
- Tempo IS exposing comprehensive metrics (found 300+ `tempo_*` metrics)
- Traefik IS exposing metrics (found 21 `traefik_*` metrics)
- Playground has basic metrics (`playground_active_sessions`, `playground_chat_latency_seconds_*`)

❌ **Issues Found**:
1. **Application instrumentation incomplete** - Most auth, builder, and advanced playground metrics missing
2. **Qdrant metrics not being scraped** - No `collection_*` or `rest_responses_*` metrics found
3. **Metric naming mismatches** - Dashboards use old/expected names that don't match reality
4. **Container metrics missing** - Docker Compose doesn't expose `container_*` metrics (need cAdvisor)

---

## Critical Issues (Priority Order)

### 1. Application Code Instrumentation Missing (CRITICAL)

**Impact**: 45+ application metrics not exposed, breaking 12 dashboards

**Missing Categories**:

#### Authentication Metrics (5 metrics, 11 panels affected)
```
auth_login_attempts_total
auth_login_failures_total
auth_login_duration_milliseconds_bucket
auth_token_verifications_total
auth_jwks_cache_operations_total
```

**Location to Fix**: `src/mcp_server_langgraph/auth/`

**Example Implementation**:
```python
from prometheus_client import Counter, Histogram

# In auth/session.py or auth/token.py
auth_login_attempts = Counter(
    'auth_login_attempts_total',
    'Total login attempts',
    ['result']  # success, failure
)

auth_login_duration = Histogram(
    'auth_login_duration_milliseconds',
    'Login duration in milliseconds',
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

# In auth/token.py
auth_token_verifications = Counter(
    'auth_token_verifications_total',
    'Token verification attempts',
    ['result']
)
```

#### Authorization Metrics (1 metric, 4 panels affected)
```
auth_authorization_checks_total
```

**Location to Fix**: `src/mcp_server_langgraph/auth/openfga_client.py`

**Example Implementation**:
```python
auth_authorization_checks = Counter(
    'auth_authorization_checks_total',
    'Authorization check calls to OpenFGA',
    ['result', 'resource_type']  # allowed, denied
)
```

#### Playground Metrics (10 metrics, 13 panels affected)
```
playground_chat_messages_total
playground_llm_tokens_total
playground_llm_latency_seconds_bucket
playground_tool_calls_total
playground_tool_duration_seconds_bucket
playground_traces_total
playground_spans_total
playground_logs_total
playground_alerts_total
playground_active_alerts
```

**Location to Fix**: Playground application code (if exists in `src/`)

#### Builder Metrics (6 metrics, 8 panels affected)
```
builder_code_generation_total
builder_validation_total
builder_import_total
builder_workflow_node_count
otel_traces_exported_total
otel_spans_created_total
```

**Location to Fix**: Builder application code (if exists in `src/`)

#### Agent Metrics (2 metrics, 3 panels affected)
```
agent_calls_successful_total
agent_calls_failed_total
```

**Location to Fix**: `src/mcp_server_langgraph/core/agent.py`

**Example Implementation**:
```python
agent_calls_successful = Counter(
    'agent_calls_successful_total',
    'Successful agent invocations',
    ['agent_type']
)

agent_calls_failed = Counter(
    'agent_calls_failed_total',
    'Failed agent invocations',
    ['agent_type', 'error_type']
)
```

---

### 2. Qdrant Metrics Not Scraped (HIGH)

**Impact**: 14 metrics missing, Qdrant dashboard completely broken

**Missing Metrics**:
```
collection_points
collection_vectors
collection_running_optimizations
rest_responses_total
rest_responses_fail_total
rest_responses_avg_duration_seconds
rest_responses_max_duration_seconds
grpc_responses_total
grpc_responses_fail_total
collection_hardware_metric_vector_io_read
collection_hardware_metric_vector_io_write
collection_hardware_metric_vector_size_bytes
collection_segments
```

**Root Cause**: Qdrant is not being scraped by Alloy

**Fix**:
1. Verify Qdrant exposes metrics:
   ```bash
   curl http://localhost:6333/metrics
   ```

2. Add scrape job to `/monitoring/config/alloy/config.alloy`:
   ```hcl
   prometheus.scrape "qdrant" {
     targets = [
       {"__address__" = "qdrant:6333", "job" = "qdrant"},
     ]
     forward_to = [prometheus.remote_write.mimir.receiver]
     scrape_interval = "15s"
     scrape_timeout = "10s"
   }
   ```

3. Restart Alloy:
   ```bash
   docker-compose restart alloy
   ```

---

### 3. LGTM Stack Dashboard Metric Name Mismatches (MEDIUM)

**Impact**: 14 metrics "missing" but actually exist with different names

**Dashboard Expects**:
```
otelcol_receiver_accepted_spans
otelcol_receiver_accepted_metric_points
otelcol_receiver_accepted_log_records
otelcol_exporter_sent_spans
otelcol_exporter_sent_metric_points
otelcol_exporter_sent_log_records
otelcol_receiver_refused_spans
otelcol_receiver_refused_metric_points
otelcol_receiver_refused_log_records
```

**Actually Available**:
```
otelcol_exporter_loki_entries_processed
otelcol_exporter_loki_entries_failed
otelcol_exporter_loki_entries_total
otelcol_exporter_queue_capacity
otelcol_exporter_queue_size
otelcol_processor_batch_metadata_cardinality
```

**Root Cause**: Dashboard queries use generic OTLP metric names, but Alloy uses component-specific names

**Fix Options**:

**Option A**: Update dashboard to use actual Alloy metric names
```promql
# Instead of:
rate(otelcol_receiver_accepted_spans[5m])

# Use Alloy-specific metrics:
rate(otelcol_exporter_loki_entries_processed[5m])
```

**Option B**: Check Alloy configuration for OTLP receiver metrics
- Alloy might not be exposing all OTLP receiver metrics
- Review Alloy documentation for available metrics

**Option C**: Use Tempo metrics directly for traces
```promql
# For span/trace ingestion:
rate(tempo_distributor_spans_received_total[5m])
rate(tempo_distributor_bytes_received_total[5m])
```

---

### 4. Traefik Dashboard Missing Metrics (MEDIUM)

**Impact**: 4 metrics missing from Traefik dashboard

**Missing Metrics**:
```
traefik_entrypoint_requests_tls_total
traefik_service_retries_total
traefik_service_server_up
traefik_tls_certs_not_after
```

**Available Traefik Metrics** (21 total):
```
traefik_config_last_reload_success
traefik_config_reloads_total
traefik_entrypoint_request_duration_seconds_*
traefik_entrypoint_requests_bytes_total
traefik_entrypoint_requests_total
traefik_entrypoint_responses_bytes_total
traefik_open_connections
traefik_router_request_duration_seconds_*
traefik_router_requests_bytes_total
traefik_router_requests_total
traefik_router_responses_bytes_total
traefik_service_request_duration_seconds_*
traefik_service_requests_bytes_total
traefik_service_requests_total
traefik_service_responses_bytes_total
```

**Root Cause**: Dashboard expects metrics that Traefik doesn't expose by default

**Fix**:

1. **TLS metrics**: Traefik doesn't expose TLS-specific request counters separately. Use:
   ```promql
   # Instead of traefik_entrypoint_requests_tls_total
   # Filter standard request metrics by protocol label (if available)
   traefik_entrypoint_requests_total{protocol="https"}
   ```

2. **Retry metrics**: Enable in Traefik config:
   ```yaml
   # docker-compose.yml
   traefik:
     command:
       - --metrics.prometheus=true
       - --metrics.prometheus.addServicesLabels=true
   ```

3. **Service health**: Use `up` metric instead:
   ```promql
   # Instead of traefik_service_server_up
   up{job="traefik"}
   ```

4. **Certificate expiry**: Requires Traefik Enterprise or custom exporter

---

### 5. Container Metrics Missing (MEDIUM)

**Impact**: 8 metrics missing across Keycloak and LangGraph Agent dashboards

**Missing Metrics**:
```
container_cpu_usage_seconds_total
container_memory_working_set_bytes
container_spec_memory_limit_bytes
container_spec_cpu_quota
```

**Root Cause**: Docker Compose doesn't expose cAdvisor metrics by default

**Fix**:

**Option A**: Replace with process metrics (RECOMMENDED for Docker Compose)
```promql
# CPU Usage
rate(process_cpu_seconds_total{job="keycloak"}[5m])

# Memory Usage
process_resident_memory_bytes{job="keycloak"}

# Virtual Memory
process_virtual_memory_bytes{job="keycloak"}
```

**Option B**: Add cAdvisor to docker-compose.yml
```yaml
services:
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro
      - /dev/disk:/dev/disk:ro
    privileged: true
    devices:
      - /dev/kmsg
```

Then add cAdvisor scrape job to Alloy.

**Option C**: Use Docker stats API (requires docker-exporter)

---

### 6. Keycloak Metrics Limited (MEDIUM)

**Impact**: 1 custom metric missing, container metrics issue (covered above)

**Missing Metric**:
```
vendor_system_cpu_utilization
```

**Available Keycloak Metrics**: Very limited (only found `keycloak_credentials_password_hashing_validations_total`)

**Root Cause**: Keycloak Quarkus metrics not fully enabled

**Fix**:

1. Enable Quarkus metrics in Keycloak:
   ```yaml
   # docker-compose.yml
   keycloak:
     environment:
       QUARKUS_MICROMETER_EXPORT_PROMETHEUS_ENABLED: "true"
       QUARKUS_MICROMETER_EXPORT_PROMETHEUS_PATH: "/metrics"
       QUARKUS_MICROMETER_BINDER_JVM_ENABLED: "true"
       QUARKUS_MICROMETER_BINDER_SYSTEM_ENABLED: "true"
   ```

2. Verify metrics endpoint:
   ```bash
   curl http://localhost:8080/metrics
   ```

3. Add Keycloak scrape job to Alloy (if not already present)

---

### 7. PostgreSQL Metric Name Changes (LOW)

**Impact**: 2 metrics with potential naming mismatches

**Missing Metrics**:
```
pg_postmaster_start_time_seconds
pg_stat_statements_mean_exec_time_ms
```

**Likely Actual Names**:
```
pg_postmaster_start_time  (without _seconds suffix)
pg_stat_statements_mean_time_seconds  (different name)
```

**Fix**: Query Mimir to find exact names:
```bash
curl -s http://localhost:19009/prometheus/api/v1/label/__name__/values | jq -r '.data[]' | grep pg_postmaster
curl -s http://localhost:19009/prometheus/api/v1/label/__name__/values | jq -r '.data[]' | grep pg_stat_statements
```

Then update dashboard queries accordingly.

---

### 8. Redis Session Metrics Missing (LOW)

**Impact**: 3 custom session metrics missing

**Missing Metrics**:
```
auth_session_operations_duration_milliseconds_count
redis_client_pool_connections_in_use
redis_client_pool_max_connections
```

**Root Cause**: Custom session management code not instrumented

**Fix**:

1. Add session operation timing to auth code:
   ```python
   from prometheus_client import Histogram

   auth_session_operations_duration = Histogram(
       'auth_session_operations_duration_milliseconds',
       'Session operation duration',
       ['operation'],  # create, retrieve, refresh, revoke
       buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
   )
   ```

2. Use existing Redis metrics for connection pool:
   ```promql
   # Instead of redis_client_pool_connections_in_use
   redis_connected_clients{job="redis"}
   ```

---

### 9. SOC2 Compliance Metrics (LOW)

**Impact**: 2 custom compliance metrics missing

**Missing Metrics**:
```
compliance_job_executions_total
evidence_items_total
```

**Root Cause**: Compliance automation not implemented or not instrumented

**Fix**: Add if/when compliance automation is built.

---

### 10. SLA Monitoring Dependency Metrics (LOW)

**Impact**: 1 custom metric missing

**Missing Metric**:
```
dependency_request_duration_seconds_bucket
```

**Root Cause**: External dependency calls not instrumented

**Fix**: Add instrumentation for external API calls:
```python
from prometheus_client import Histogram

dependency_request_duration = Histogram(
    'dependency_request_duration_seconds',
    'External dependency request duration',
    ['dependency', 'operation'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)
```

---

## Recommendations by Priority

### Immediate (This Week)

1. **Add authentication instrumentation**
   - File: `src/mcp_server_langgraph/auth/session.py`, `auth/token.py`
   - Metrics: `auth_login_attempts_total`, `auth_token_verifications_total`, `auth_authorization_checks_total`
   - Impact: Fixes Authentication and Security dashboards

2. **Add agent call metrics**
   - File: `src/mcp_server_langgraph/core/agent.py`
   - Metrics: `agent_calls_successful_total`, `agent_calls_failed_total`
   - Impact: Fixes LLM Performance dashboard

3. **Configure Qdrant scraping**
   - File: `/monitoring/config/alloy/config.alloy`
   - Add Qdrant scrape job
   - Impact: Fixes Qdrant dashboard completely

### Short-term (Next Sprint)

4. **Fix LGTM Stack dashboard queries**
   - Update panel queries to use actual Alloy/Tempo metric names
   - Test each panel in Grafana Explore first
   - Impact: Makes LGTM monitoring accurate

5. **Replace container metrics with process metrics**
   - Update Keycloak and LangGraph Agent dashboards
   - Use `process_cpu_seconds_total`, `process_resident_memory_bytes`
   - Impact: Makes resource monitoring work in Docker Compose

6. **Enable Keycloak metrics**
   - Update docker-compose.yml with Quarkus metrics config
   - Impact: Improves Keycloak monitoring

### Medium-term (Next Month)

7. **Add Playground instrumentation** (if Playground exists)
   - Add all 10 playground metrics
   - Impact: Fixes Interactive Playground dashboard

8. **Add Builder instrumentation** (if Builder exists)
   - Add code generation and validation metrics
   - Impact: Fixes Visual Workflow Builder dashboard

9. **Fix Traefik dashboard queries**
   - Update queries to use available metrics
   - Add TLS filtering if protocol labels exist
   - Impact: Improves Traefik monitoring

### Long-term (Future)

10. **Consider cAdvisor** for production Kubernetes deployment
    - Provides accurate container metrics
    - Not needed for local Docker Compose

11. **Add compliance metrics** when automation is built

12. **Add dependency tracking** for SLA monitoring

---

## Testing Checklist

After implementing fixes, verify:

### 1. Metrics Are Exposed
```bash
# Check application metrics endpoint
curl http://localhost:8000/metrics | grep -E "(auth_|agent_|playground_|builder_)"

# Check Qdrant metrics
curl http://localhost:6333/metrics | grep -E "(collection_|rest_responses_)"

# Check Keycloak metrics
curl http://localhost:8080/metrics | grep -E "(vendor_|process_)"
```

### 2. Metrics Reached Mimir
```bash
# Query Mimir for new metrics
curl -s http://localhost:19009/prometheus/api/v1/label/__name__/values | jq -r '.data[]' | grep auth_
curl -s http://localhost:19009/prometheus/api/v1/label/__name__/values | jq -r '.data[]' | grep agent_
curl -s http://localhost:19009/prometheus/api/v1/label/__name__/values | jq -r '.data[]' | grep collection_
```

### 3. Dashboards Show Data
1. Open Grafana: http://localhost:3000
2. Navigate to each dashboard
3. Check that panels show data (not "No data" or query errors)
4. Use "Inspect > Query" to verify PromQL queries return results

### 4. Label Selectors Match
```promql
# In Grafana Explore, verify label values
label_values(up, job)
label_values(auth_login_attempts_total, job)

# Ensure dashboard queries use correct job label values
```

---

## Appendix: Metric Categorization

### Application Metrics (Need Instrumentation)
- Authentication: 5 metrics
- Authorization: 1 metric
- Agent: 2 metrics
- Playground: 10 metrics
- Builder: 6 metrics
- Session: 3 metrics
- Compliance: 2 metrics
- Dependency: 1 metric

**Total**: 30 metrics requiring application code changes

### Infrastructure Metrics (Need Configuration)
- Qdrant: 14 metrics (need scraping)
- LGTM Stack: 14 metrics (need query fixes)
- Traefik: 4 metrics (need query updates)
- Container: 8 metrics (need replacement metrics)
- Keycloak: 1 metric (need config)
- PostgreSQL: 2 metrics (need name verification)

**Total**: 43 metrics requiring configuration/query changes

---

## Appendix: Available vs Expected Metrics

### What IS Working ✅

**Alloy Metrics**: 25+ metrics including:
- `alloy_build_info`
- `alloy_component_evaluation_seconds_*`
- `alloy_resources_process_cpu_seconds_total`
- `alloy_resources_process_resident_memory_bytes`

**Tempo Metrics**: 300+ metrics including:
- `tempo_distributor_spans_received_total`
- `tempo_distributor_bytes_received_total`
- `tempo_ingester_live_traces`
- `tempo_query_frontend_queries_total`

**Traefik Metrics**: 21 metrics including:
- `traefik_entrypoint_requests_total`
- `traefik_entrypoint_request_duration_seconds_*`
- `traefik_service_requests_total`

**Playground Metrics** (partial): 5 metrics including:
- `playground_active_sessions` ✅
- `playground_chat_latency_seconds_*` ✅
- `playground_websocket_connections` ✅

**Agent Metrics** (partial): 2 metrics:
- `agent_active_sessions` ✅
- `agent_memory_bytes` ✅

### What Is NOT Working ❌

**Authentication**: 0 of 5 metrics exposed
**Authorization**: 0 of 1 metrics exposed
**Agent Calls**: 0 of 2 metrics exposed (success/failure counters)
**Playground Advanced**: 0 of 10 advanced metrics (LLM, tools, traces)
**Builder**: 0 of 6 metrics exposed
**Qdrant**: 0 of 14 metrics available (not scraped)

---

## Conclusion

The audit reveals two main categories of issues:

1. **Application instrumentation gaps** (30 metrics) - Requires code changes to add Prometheus metrics
2. **Configuration/query issues** (43 metrics) - Requires configuration updates or dashboard query fixes

The good news: Core infrastructure (Alloy, Tempo, Traefik) IS exposing metrics. The challenge is getting application code to expose business/functional metrics, and fixing some dashboard queries to match reality.

**Recommended Focus**:
1. Start with authentication/authorization metrics (highest impact)
2. Add agent success/failure tracking
3. Configure Qdrant scraping
4. Fix dashboard queries for LGTM stack

This will address ~70% of the issues and make the most critical dashboards functional.

---

**End of Report**
