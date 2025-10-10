# Grafana Dashboards

This directory contains pre-built Grafana dashboards for monitoring the MCP Server with LangGraph.

## Dashboards

### 1. `langgraph-agent.json` - Overview Dashboard

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

### 2. `security.json` - Security Dashboard

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

## Installation

### Option 1: Import via Grafana UI

1. **Open Grafana** (http://localhost:3000 or your Grafana URL)
2. **Navigate to Dashboards** → **Import**
3. **Upload JSON file** or paste contents
4. **Select Prometheus datasource**
5. **Click Import**

### Option 2: Provision via ConfigMap (Kubernetes)

```bash
# Create ConfigMap with dashboards
kubectl create configmap grafana-dashboards \
  --from-file=langgraph-agent.json \
  --from-file=security.json \
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
      langgraph-overview:
        file: dashboards/langgraph-agent.json
      langgraph-security:
        file: dashboards/security.json
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
