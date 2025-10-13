# Grafana Dashboards

This directory contains pre-built Grafana dashboards for monitoring the MCP Server with LangGraph.

## Dashboards

### 1. `authentication.json` - Authentication Dashboard (NEW in v2.1.0)

**Comprehensive authentication and session management metrics:**

- **Service Status** - Authentication service availability gauge
- **Login Activity Rate** - Login attempts, successes, and failures per second
- **Login Failure Rate** - Percentage gauge with color-coded thresholds
- **Response Time Percentiles** - p50, p95, p99 latency for login operations
- **Active Sessions** - Current active session count
- **Token Operations** - Token creation, verification, and refresh rates
- **JWKS Cache Performance** - Cache hit rate percentage
- **Login Failures by Reason** - Breakdown of failure types
- **Session Lifecycle Operations** - Create, retrieve, refresh, revoke rates
- **Auth Provider Operations** - Operations by provider type

**Use Cases:**
- Authentication performance monitoring
- Session management oversight
- Token lifecycle tracking
- Login failure analysis
- JWKS cache optimization

### 2. `openfga.json` - OpenFGA Authorization Dashboard (NEW in v2.1.0)

**Fine-grained authorization and relationship-based access control metrics:**

- **OpenFGA Service Status** - Service availability gauge
- **Authorization Check Rate** - Total checks, allowed, and denied per second
- **Denial Rate** - Authorization denial percentage
- **Total Relationship Tuples** - Current tuple count in OpenFGA
- **Check Latency Percentiles** - p50, p95, p99 for authorization checks
- **Checks by Relation** - Authorization checks grouped by relation type
- **Tuple Write Operations** - Tuples written and deleted rates
- **Sync Operations** - OpenFGA sync status (success/failure)
- **Role Sync Latency** - Latency percentiles for role synchronization
- **Synced Tuples by Role** - Tuple distribution across roles
- **Role Mapping Rules Applied** - Rules applied by type (simple, group, conditional)

**Use Cases:**
- Authorization performance tracking
- Access pattern analysis
- Tuple management monitoring
- Role sync oversight
- Policy effectiveness evaluation

### 3. `llm-performance.json` - LLM Performance Dashboard (NEW in v2.1.0)

**LLM and agent performance metrics:**

- **Agent Service Status** - Service availability gauge
- **Agent Call Rate** - Successful and failed calls per second
- **Error Rate** - Agent error percentage with thresholds
- **Response Time Percentiles** - p50, p95, p99 for agent responses
- **Tool Calls** - 5-minute rate of tool invocations
- **LLM Invocations by Model** - Success and failure rates per model
- **Fallback Model Usage** - Automatic fallback activation tracking
- **Tool Usage Rate** - Tool invocations by tool name
- **Model Performance Summary** - Table view of model statistics
- **Average Response Time by Operation** - Latency breakdown by operation type

**Use Cases:**
- LLM performance monitoring
- Model comparison and selection
- Fallback mechanism validation
- Tool usage analysis
- Operation-level performance tracking

### 4. `sla-monitoring.json` - SLA Monitoring Dashboard (NEW in v2.1.0)

**Comprehensive SLA tracking and alerting metrics:**

- **Overall SLA Compliance Score** - Weighted composite score (40% uptime, 30% response time, 30% error rate)
- **Uptime SLA Gauge** - 99.9% target with color-coded thresholds
- **Response Time SLA Gauge** - p95 <500ms target
- **Error Rate SLA Gauge** - <1% target
- **Uptime Percentage Trend** - Historical uptime tracking
- **Monthly Downtime Budget** - Remaining budget (43.2 min/month for 99.9% SLA)
- **Response Time Percentiles** - p50, p95, p99 latency trends
- **Error Rate Trend** - API error rate over time
- **Errors by Status Code** - 5xx error breakdown
- **System Throughput** - Current vs 7-day average
- **Dependency Health Status** - Postgres, Redis, OpenFGA, Keycloak availability
- **Dependency Performance** - p95 latency for dependencies
- **CPU Utilization** - Resource monitoring
- **Memory Utilization** - Resource monitoring
- **Uptime Forecast** - 24-hour prediction based on 4-hour trend

**Use Cases:**
- SLA compliance monitoring
- Breach detection and alerting
- Capacity planning
- Performance troubleshooting
- Monthly/quarterly SLA reporting

### 5. `soc2-compliance.json` - SOC 2 Compliance Dashboard (NEW in v2.1.0)

**Automated SOC 2 evidence collection and compliance reporting:**

- **Overall Compliance Score** - Weighted score (passed + partial*0.5)
- **Control Status Distribution** - Pie chart of passed/failed/partial controls
- **Evidence by Control Category** - Evidence distribution across TSC categories
- **CC6.1 - Active Sessions** - Access control evidence
- **CC6.6 - Audit Log Rate** - Logging system status
- **CC7.2 - Metrics Collection** - System monitoring evidence
- **A1.2 - System Uptime** - Availability SLA tracking
- **A1.2 - Last Backup** - Backup verification timestamp
- **Evidence Collection Rate by Type** - Evidence gathering operations
- **Compliance Reports Generated** - Daily/weekly/monthly report tracking
- **Compliance Score Trend** - 30-day historical compliance
- **Access Review Items** - Weekly access review findings
- **Inactive User Accounts** - Security audit findings
- **Compliance Job Executions** - Automated scheduler status

**Use Cases:**
- SOC 2 Type II audit preparation
- Continuous compliance monitoring
- Evidence collection automation
- Trust Services Criteria validation
- Quarterly compliance reporting

### 6. `langgraph-agent.json` - Overview Dashboard

**Primary metrics for service health and performance:**

- **Service Status** - Uptime gauge
- **Request Rate** - Requests per second by tool
- **Error Rate** - Percentage of failed requests
- **Response Time Percentiles** - p50, p95, p99 latency
- **Memory Usage** - Per-pod memory consumption
- **CPU Usage** - Per-pod CPU utilization
- **Request Success/Failure Count** - Stacked area chart

**Use Cases:**
- Daily monitoring and ops dashboard
- Performance troubleshooting
- Capacity planning
- SLA validation

### 7. `security.json` - Security Dashboard

**Security-focused metrics:**

- **Auth Failures** - Authentication failures per second
- **AuthZ Failures** - Authorization failures per second
- **JWT Validation Errors** - Token validation errors
- **Security Status** - Overall security posture gauge
- **Authentication Failures by Reason** - Breakdown by failure type
- **Authorization Failures by Resource** - Access patterns
- **Failed Auth Attempts by User** - Top violators (pie chart)
- **Failed Auth Attempts by IP** - Geographic/IP patterns (pie chart)
- **Top 10 Users by Failed Auth** - Table of potential issues

**Use Cases:**
- Security monitoring
- Attack detection
- Incident response
- Access audit
- Compliance reporting

### 8. `keycloak.json` - Keycloak SSO Dashboard

**Keycloak authentication and SSO metrics:**

- **Service Status** - Keycloak availability gauge
- **Response Time** - p50, p95, p99 latency for Keycloak requests
- **Login Request Rate** - Login attempts, successes, and failures
- **Error Rates** - Login and token refresh error percentages
- **Active Sessions and Users** - Current active sessions count
- **CPU Usage** - Keycloak pod CPU utilization
- **Memory Usage** - Memory consumption vs limits

**Use Cases:**
- SSO service monitoring
- Authentication performance tracking
- Capacity planning for Keycloak
- Troubleshooting login issues
- Session management oversight

### 9. `redis-sessions.json` - Redis Session Store Dashboard

**Redis session storage metrics:**

- **Service Status** - Redis session store availability
- **Memory Usage** - Percentage and absolute memory consumption
- **Active Sessions** - Current session count (key count)
- **Operations Rate** - Redis commands per second
- **Connection Pool** - Pool utilization and available connections
- **Evictions** - Session eviction rate and total
- **Session Operations** - Create, get, delete, refresh rates by operation
- **Error Rate** - Session store operation failures
- **Memory Fragmentation** - Redis memory fragmentation ratio

**Use Cases:**
- Session store health monitoring
- Memory pressure detection
- Performance troubleshooting
- Capacity planning
- Connection pool tuning
- Eviction policy validation

## Installation

### Option 1: Import via Grafana UI

1. **Open Grafana** (http://localhost:3000 or your Grafana URL)
2. **Navigate to Dashboards** → **Import**
3. **Upload JSON file** or paste contents
4. **Select Prometheus datasource**
5. **Click Import**

### Option 2: Provision via ConfigMap (Kubernetes)

```bash
# Create ConfigMap with all dashboards (v2.1.0)
kubectl create configmap grafana-dashboards \
  --from-file=authentication.json \
  --from-file=openfga.json \
  --from-file=llm-performance.json \
  --from-file=sla-monitoring.json \
  --from-file=soc2-compliance.json \
  --from-file=langgraph-agent.json \
  --from-file=security.json \
  --from-file=keycloak.json \
  --from-file=redis-sessions.json \
  -n monitoring

# Add to Grafana deployment
kubectl edit deployment grafana -n monitoring
```

Add volume mount:
```yaml
spec:
  template:
    spec:
      containers:
      - name: grafana
        volumeMounts:
        - name: dashboards
          mountPath: /var/lib/grafana/dashboards
      volumes:
      - name: dashboards
        configMap:
          name: grafana-dashboards
```

### Option 3: Provision via Helm

Add to `values.yaml`:

```yaml
grafana:
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
      - name: 'langgraph-agent'
        orgId: 1
        folder: 'MCP Server with LangGraph'
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards/langgraph

  dashboards:
    langgraph-agent:
      authentication:
        file: dashboards/authentication.json
      openfga:
        file: dashboards/openfga.json
      llm-performance:
        file: dashboards/llm-performance.json
      sla-monitoring:
        file: dashboards/sla-monitoring.json
      soc2-compliance:
        file: dashboards/soc2-compliance.json
      langgraph-overview:
        file: dashboards/langgraph-agent.json
      langgraph-security:
        file: dashboards/security.json
      keycloak-sso:
        file: dashboards/keycloak.json
      redis-sessions:
        file: dashboards/redis-sessions.json
```

## Dashboard Configuration

### Variables (Optional)

Add template variables for filtering:

1. **Namespace** - Filter by Kubernetes namespace
   ```promql
   label_values(up{job="langgraph-agent"}, namespace)
   ```

2. **Pod** - Filter by specific pod
   ```promql
   label_values(up{job="langgraph-agent", namespace="$namespace"}, pod)
   ```

3. **Tool** - Filter by tool name
   ```promql
   label_values(agent_tool_calls_total, tool)
   ```

### Time Range Presets

Recommended quick ranges:
- Last 5 minutes (real-time monitoring)
- Last 15 minutes (incident investigation)
- Last 1 hour (performance analysis)
- Last 6 hours (trend analysis)
- Last 24 hours (daily review)
- Last 7 days (capacity planning)

### Annotations

Add annotations for deployments and incidents:

```json
{
  "annotations": {
    "list": [
      {
        "datasource": "Prometheus",
        "enable": true,
        "expr": "changes(kube_deployment_status_observed_generation{deployment=\"langgraph-agent\"}[5m]) > 0",
        "iconColor": "blue",
        "name": "Deployments",
        "tagKeys": "deployment",
        "textFormat": "Deployment: {{deployment}}",
        "titleFormat": "Deployment Event"
      }
    ]
  }
}
```

## Required Metrics

Ensure these metrics are exported by the application:

### Core Metrics
- `up{job="langgraph-agent"}` - Service health
- `agent_tool_calls_total` - Tool invocation counter
- `agent_calls_successful_total` - Successful requests
- `agent_calls_failed_total` - Failed requests
- `agent_response_duration_bucket` - Response time histogram
- `agent_response_duration_sum` - Total response time
- `agent_response_duration_count` - Request count

### Security Metrics
- `auth_failures_total` - Authentication failures
- `authz_failures_total` - Authorization failures
- `jwt_validation_errors_total` - JWT validation errors

### Keycloak Metrics
- `up{job="keycloak"}` - Keycloak service health
- `keycloak_request_duration_bucket` - Response time histogram
- `keycloak_login_attempts_total` - Total login attempts
- `keycloak_login_success_total` - Successful logins
- `keycloak_login_failed_total` - Failed logins
- `keycloak_token_refresh_total` - Token refresh attempts
- `keycloak_token_refresh_failed_total` - Failed token refreshes
- `keycloak_active_sessions` - Currently active sessions
- `keycloak_active_users` - Currently active users

### Redis Session Store Metrics
- `up{job="redis-session"}` - Redis service health
- `redis_memory_used_bytes` - Current memory usage
- `redis_memory_max_bytes` - Maximum memory limit
- `redis_db_keys` - Number of keys (sessions)
- `redis_commands_processed_total` - Total commands processed
- `redis_connected_clients` - Active client connections
- `redis_evicted_keys_total` - Evicted keys counter
- `redis_mem_fragmentation_ratio` - Memory fragmentation
- `redis_client_pool_connections_in_use` - Active pool connections
- `redis_client_pool_max_connections` - Maximum pool size
- `session_store_operations_total` - Session operations by type
- `session_store_errors_total` - Session operation errors

### Resource Metrics (from kube-state-metrics)
- `container_memory_working_set_bytes`
- `container_spec_memory_limit_bytes`
- `container_cpu_usage_seconds_total`
- `container_spec_cpu_quota`
- `kube_pod_container_status_restarts_total`
- `kube_deployment_status_replicas_available`

## Alert Correlation

Dashboards include links to related alerts:

- Click alert icons to view active alerts
- Hover over panels for alert thresholds
- Use dashboard annotations to see when alerts fired

## Customization

### Add New Panel

1. **Click "Add panel"** in dashboard edit mode
2. **Select visualization type** (time series, gauge, table, etc.)
3. **Add Prometheus query:**
   ```promql
   rate(your_metric_total[5m])
   ```
4. **Configure thresholds and styling**
5. **Save dashboard**

### Modify Thresholds

Update color thresholds in panel settings:

```json
{
  "thresholds": {
    "mode": "absolute",
    "steps": [
      {"color": "green", "value": null},
      {"color": "yellow", "value": 3000},
      {"color": "red", "value": 5000}
    ]
  }
}
```

### Change Refresh Rate

Update dashboard settings:
```json
{
  "refresh": "10s"  // Options: 5s, 10s, 30s, 1m, 5m
}
```

## Troubleshooting

### No Data Displayed

1. **Check Prometheus datasource:**
   ```bash
   # Test query
   curl -g 'http://localhost:9090/api/v1/query?query=up{job="langgraph-agent"}'
   ```

2. **Verify metrics are being scraped:**
   - Visit Prometheus UI: http://localhost:9090/targets
   - Ensure `langgraph-agent` target is UP

3. **Check time range:**
   - Adjust dashboard time range
   - Ensure application was running during selected period

### Panel Shows "N/A"

- Metric may not exist (check spelling)
- No data in selected time range
- Prometheus query error (check query syntax)

### High Cardinality Warning

If Grafana shows cardinality warnings:

1. **Reduce label dimensions:**
   ```promql
   # Instead of:
   sum by (user_id, source_ip, method, path) (...)

   # Use:
   sum by (method) (...)
   ```

2. **Add recording rules in Prometheus:**
   ```yaml
   groups:
     - name: langgraph_agent
       interval: 30s
       rules:
         - record: job:agent_calls_total:rate5m
           expr: sum(rate(agent_calls_total[5m])) by (job)
   ```

## Best Practices

1. **Use template variables** for multi-environment setups
2. **Set appropriate refresh rates** (10s for real-time, 1m for historical)
3. **Add panel descriptions** to document metrics
4. **Use consistent time ranges** across panels in same dashboard
5. **Group related panels** with rows
6. **Add links to runbooks** in panel descriptions
7. **Export dashboards** regularly as JSON backups
8. **Version control** dashboard JSON in git
9. **Test dashboards** in staging before production
10. **Document custom queries** in panel descriptions

## Dashboard Links

Add navigation between dashboards:

```json
{
  "links": [
    {
      "title": "Security Dashboard",
      "type": "link",
      "url": "/d/langgraph-agent-security/security"
    },
    {
      "title": "Alert Rules",
      "type": "link",
      "url": "/alerting/list"
    }
  ]
}
```

## Exporting Data

### Export to PDF/PNG

1. **Open dashboard**
2. **Click share icon** (top right)
3. **Select "Export"**
4. **Choose PDF or PNG**

### Export to CSV

1. **Click panel title** → **Inspect** → **Data**
2. **Click "Download CSV"**

## References

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/dashboards/)
- [Panel Types](https://grafana.com/docs/grafana/latest/panels-visualizations/)
