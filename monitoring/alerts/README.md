# Prometheus Alert Rules

This directory contains Prometheus alert rules for monitoring the MCP Server with LangGraph.

## Alert Rules

### File: `langgraph-agent.yaml`

Comprehensive alert rules covering:

- **Critical Service Health**
  - ServiceDown: Service unavailable for >2 minutes
  - HighErrorRate: Error rate >10% for 5 minutes
  - AuthenticationFailureSpike: >10 auth failures/sec (possible attack)
  - AuthorizationFailureSpike: >5 authz failures/sec

- **Performance Degradation**
  - HighResponseTime: p95 response time >5s
  - SlowLLMResponses: p95 LLM response time >10s
  - HighMemoryUsage: Memory usage >85%
  - HighCPUUsage: CPU usage >80%

- **Availability**
  - PodRestartingFrequently: Pod restarts in 15min window
  - InsufficientReplicas: <2 replicas available
  - HealthCheckFailing: Health endpoint not responding

- **Dependencies**
  - OpenFGAConnectionFailing: OpenFGA service unavailable
  - LLMProviderErrors: LLM provider returning errors
  - InfisicalConnectionFailing: Secrets manager unavailable

- **Capacity Planning**
  - HighRequestRate: >100 req/sec for 15min (scale up)
  - LowRequestRate: <0.1 req/sec for 1h (scale down)
  - DiskSpaceRunningLow: <15% disk space remaining

- **Security**
  - UnauthorizedAccessAttempts: Failed auth attempts
  - SuspiciousActivityPattern: High authz failure rate
  - TokenValidationFailures: JWT validation errors

## Deployment

### Kubernetes with Prometheus Operator

```bash
# Apply alert rules
kubectl apply -f langgraph-agent.yaml

# Verify rules are loaded
kubectl get prometheusrule -n langgraph-agent

# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
# Visit: http://localhost:9090/rules
```

### Standalone Prometheus

```bash
# Add to prometheus.yml
rule_files:
  - /etc/prometheus/rules/langgraph-agent.yaml

# Copy rules file
cp langgraph-agent.yaml /etc/prometheus/rules/

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload
```

## Alert Severity Levels

- **critical**: Immediate action required, service degradation or outage
- **warning**: Attention needed, potential issues developing
- **info**: Informational, capacity planning, non-urgent

## Runbook Links

Each alert includes a `runbook_url` annotation pointing to troubleshooting documentation.

Create runbooks in `docs/runbooks/` with these files:

- `service-down.md` - Service unavailable troubleshooting
- `high-error-rate.md` - Error investigation steps
- `auth-spike.md` - Authentication attack response
- `authz-spike.md` - Authorization failure investigation
- `high-latency.md` - Performance troubleshooting
- `slow-llm.md` - LLM provider issue resolution
- `high-memory.md` - Memory leak investigation
- `high-cpu.md` - CPU usage optimization
- `pod-restarts.md` - Container restart debugging
- `insufficient-replicas.md` - Scaling troubleshooting
- `health-check-failing.md` - Health endpoint debugging
- `openfga-down.md` - OpenFGA connectivity issues
- `llm-provider-errors.md` - LLM provider troubleshooting
- `infisical-down.md` - Secrets manager issues
- `scale-up.md` - Scaling up procedure
- `scale-down.md` - Scaling down procedure
- `low-disk-space.md` - Disk cleanup procedures
- `unauthorized-access.md` - Security incident response
- `suspicious-activity.md` - Attack investigation
- `token-validation-failures.md` - JWT troubleshooting

## Testing Alerts

### Trigger ServiceDown alert

```bash
# Scale deployment to 0
kubectl scale deployment langgraph-agent --replicas=0 -n langgraph-agent

# Wait 2 minutes, check Alertmanager
# Restore
kubectl scale deployment langgraph-agent --replicas=3 -n langgraph-agent
```

### Trigger HighErrorRate alert

```bash
# Send invalid requests to trigger errors
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/chat \
    -H "Authorization: Bearer invalid-token" \
    -H "Content-Type: application/json" \
    -d '{"message": "test"}'
done
```

### Trigger HighMemoryUsage alert

```bash
# Set very low memory limit temporarily
kubectl set resources deployment langgraph-agent \
  --limits=memory=128Mi \
  -n langgraph-agent

# Load test to trigger memory pressure
# Restore original limits
kubectl set resources deployment langgraph-agent \
  --limits=memory=2Gi \
  -n langgraph-agent
```

## Integration with Alertmanager

Configure Alertmanager to route alerts:

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      continue: true
    - match:
        severity: warning
      receiver: slack
    - match:
        severity: info
      receiver: email

receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<your-pagerduty-key>'

  - name: 'slack'
    slack_configs:
      - api_url: '<your-slack-webhook>'
        channel: '#alerts'

  - name: 'email'
    email_configs:
      - to: 'team@example.com'
```

## Metrics Required

These alerts assume the following metrics are exported:

- `up` - Service health (standard Prometheus)
- `agent_calls_successful_total` - Successful agent calls
- `agent_calls_failed_total` - Failed agent calls
- `auth_failures_total` - Authentication failures
- `authz_failures_total` - Authorization failures
- `agent_response_duration_bucket` - Response time histogram
- `llm_request_duration_bucket` - LLM request duration histogram
- `agent_tool_calls_total` - Total tool invocations
- `openfga_client_errors_total` - OpenFGA errors
- `llm_provider_errors_total` - LLM provider errors
- `infisical_client_errors_total` - Infisical errors
- `jwt_validation_errors_total` - JWT validation errors

Standard Kubernetes metrics (kube-state-metrics):
- `kube_pod_container_status_restarts_total`
- `kube_deployment_status_replicas_available`
- `container_memory_working_set_bytes`
- `container_spec_memory_limit_bytes`
- `container_cpu_usage_seconds_total`
- `container_spec_cpu_quota`
- `node_filesystem_avail_bytes`
- `node_filesystem_size_bytes`

## Dashboard Integration

Each alert includes a `dashboard_url` annotation. Create dashboards in Grafana showing:

- Service overview (uptime, request rate, error rate)
- Performance metrics (latency percentiles, throughput)
- Resource usage (CPU, memory, disk)
- Security metrics (auth/authz failures)
- Dependency health (OpenFGA, LLM providers, Infisical)

See `../grafana/dashboards/` for dashboard JSON files.

## Customization

Adjust thresholds based on your SLOs:

```yaml
# Example: Lower error rate threshold
- alert: HighErrorRate
  expr: |
    (rate(agent_calls_failed_total[5m]) / ...) > 0.05  # 5% instead of 10%
```

Update `for:` durations to reduce alert noise:

```yaml
# Example: Longer grace period
- alert: HighCPUUsage
  expr: ...
  for: 20m  # 20 minutes instead of 10
```

## Troubleshooting

### Alerts not firing

1. Check Prometheus rules are loaded:
   ```bash
   curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[].name'
   ```

2. Verify metrics are being scraped:
   ```bash
   curl http://localhost:9090/api/v1/query?query=up{job="langgraph-agent"}
   ```

3. Check for syntax errors:
   ```bash
   promtool check rules langgraph-agent.yaml
   ```

### Too many alerts

- Increase `for:` duration to reduce flapping
- Adjust thresholds based on baseline metrics
- Add `group_wait` and `group_interval` to Alertmanager

### Alerts not reaching Alertmanager

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Alertmanager configuration
curl http://localhost:9093/api/v2/status
```

## References

- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [PromQL Functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Grafana Alerting](https://grafana.com/docs/grafana/latest/alerting/)
