# Monitoring Quick Start Guide

This guide helps you quickly set up and use the comprehensive monitoring stack for MCP Server LangGraph.

## 🚀 Quick Start (30 seconds)

```bash
# 1. Start monitoring infrastructure
make setup-infra

# 2. Wait for services to be ready (15-20 seconds)
make health-check

# 3. Open Grafana dashboards
make monitoring-dashboard
```

That's it! You now have:
- ✅ Prometheus collecting metrics
- ✅ Grafana dashboards configured
- ✅ Jaeger tracing UI
- ✅ OpenTelemetry collector running

## 📊 Available Dashboards

### Core Monitoring

#### 1. **LangGraph Agent Dashboard**
- **URL**: http://localhost:3000/d/langgraph-agent
- **Purpose**: Overall agent performance and health
- **Key Metrics**:
  - Request rate and latency
  - LLM call duration
  - Tool execution times
  - Error rates
  - Active conversations

#### 2. **LLM Performance Dashboard**
- **URL**: http://localhost:3000/d/llm-performance
- **Purpose**: Multi-LLM provider performance tracking
- **Key Metrics**:
  - Provider-specific latencies
  - Token usage and costs
  - Model comparison
  - Fallback events
  - Rate limiting

### Security & Compliance

#### 3. **Security Dashboard**
- **URL**: http://localhost:3000/d/security
- **Purpose**: Security event monitoring
- **Key Metrics**:
  - Authentication attempts (success/failure)
  - Authorization denials
  - Suspicious activity patterns
  - Security alerts

#### 4. **Authentication Dashboard**
- **URL**: http://localhost:3000/d/authentication
- **Purpose**: Detailed authentication metrics
- **Key Metrics**:
  - Login success/failure rates
  - Token generation/validation
  - Session creation/expiration
  - MFA usage
  - Geographic distribution

#### 5. **OpenFGA Dashboard**
- **URL**: http://localhost:3000/d/openfga
- **Purpose**: Authorization system monitoring
- **Key Metrics**:
  - Check API latency
  - Authorization decisions (allow/deny)
  - Tuple operations
  - Model changes

#### 6. **SLA Monitoring Dashboard**
- **URL**: http://localhost:3000/d/sla-monitoring
- **Purpose**: Service Level Agreement tracking
- **Key Metrics**:
  - Uptime percentage
  - SLA breach alerts
  - P95/P99 latencies
  - Error budget consumption

#### 7. **SOC2 Compliance Dashboard**
- **URL**: http://localhost:3000/d/soc2-compliance
- **Purpose**: Compliance evidence collection
- **Key Metrics**:
  - Access reviews
  - Audit log coverage
  - Encryption status
  - Backup verification
  - Security controls

### Infrastructure

#### 8. **Keycloak SSO Dashboard**
- **URL**: http://localhost:3000/d/keycloak
- **Purpose**: SSO and identity provider monitoring
- **Key Metrics**:
  - User logins
  - Session management
  - Token exchanges
  - Client activity

#### 9. **Redis Sessions Dashboard**
- **URL**: http://localhost:3000/d/redis-sessions
- **Purpose**: Session storage performance
- **Key Metrics**:
  - Session operations (get/set/delete)
  - Memory usage
  - Hit/miss ratio
  - Eviction events

## 🔍 Accessing UIs

### Grafana
- **URL**: http://localhost:3000
- **Default credentials**: admin / admin
- **First login**: You'll be prompted to change the password

### Prometheus
- **URL**: http://localhost:9090
- **Use for**: Query metrics directly, view targets, check alerts
- **Quick command**: `make prometheus-ui`

### Jaeger
- **URL**: http://localhost:16686
- **Use for**: Distributed tracing, request flow analysis
- **Quick command**: `make jaeger-ui`

## 📈 Common Monitoring Tasks

### Check System Health
```bash
make health-check
```
Verifies all services are running and ports are accessible.

### View Live Logs
```bash
# All services
make logs-follow

# Specific services
make logs-prometheus
make logs-grafana
make logs-agent
```

### Query Metrics Directly
```bash
# Open Prometheus UI
make prometheus-ui

# Example queries:
# - agent_requests_total
# - llm_call_duration_seconds_bucket
# - openfga_check_duration_seconds
# - session_operations_total
```

### View Distributed Traces
```bash
# Open Jaeger UI
make jaeger-ui

# Search by:
# - Service: "mcp-server-langgraph"
# - Operation: "llm.call", "openfga.check", etc.
# - Tags: user_id, model_name, etc.
```

## 🎯 Key Metrics to Monitor

### Performance
- **`agent_response_time_seconds`** - End-to-end latency (target: p95 < 5s)
- **`llm_call_duration_seconds`** - LLM provider latency (target: p95 < 10s)
- **`tool_execution_duration_seconds`** - Tool performance

### Reliability
- **`agent_requests_total`** - Request rate and trends
- **`agent_errors_total`** - Error rate (target: < 1%)
- **`llm_fallback_events_total`** - Provider failovers

### Security
- **`auth_attempts_total{status="failure"}`** - Failed logins
- **`openfga_check_total{decision="deny"}`** - Authorization denials
- **`hipaa_access_events_total`** - PHI access tracking

### Compliance
- **`sla_uptime_percentage`** - Service availability (target: > 99.9%)
- **`soc2_audit_coverage_ratio`** - Audit log completeness
- **`gdpr_data_requests_total`** - Data subject rights requests

## 🚨 Alerting

Prometheus alerting rules are pre-configured in:
- `monitoring/prometheus/alerts/langgraph-agent.yaml` - Agent alerts
- `monitoring/prometheus/alerts/sla.yaml` - SLA breach alerts

### View Active Alerts
```bash
# In Prometheus UI
make prometheus-ui
# Navigate to: Status → Alerts
```

### Configure Alert Destinations
Edit `monitoring/prometheus/prometheus.yml`:
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093  # Add your alertmanager
```

## 📊 Dashboard Customization

### Importing Custom Dashboards
1. Open Grafana: http://localhost:3000
2. Navigate to: Dashboards → Import
3. Upload JSON or paste dashboard ID
4. Select Prometheus as datasource

### Modifying Existing Dashboards
1. Open any dashboard
2. Click gear icon (⚙️) → Dashboard settings
3. Edit panels, queries, thresholds
4. Save changes

### Exporting Dashboards
```bash
# Dashboards are stored in:
monitoring/grafana/dashboards/*.json

# After modifying in UI, export and save to version control
```

## 🔧 Troubleshooting

### Dashboard Not Loading
```bash
# Check Grafana logs
make logs-grafana

# Verify Prometheus is accessible
curl http://localhost:9090/-/healthy

# Restart services
make clean && make setup-infra
```

### No Metrics Showing
```bash
# Check if Prometheus is scraping
make prometheus-ui
# Go to: Status → Targets

# Verify app is running and exposing metrics
curl http://localhost:8000/metrics
```

### Missing Traces
```bash
# Check OpenTelemetry collector
docker compose logs otel-collector

# Verify Jaeger is receiving spans
make jaeger-ui
```

## 📚 Additional Resources

- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/
- **Jaeger Docs**: https://www.jaegertracing.io/docs/
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/

## 🎓 Next Steps

1. **Set up alerts** for critical metrics
2. **Configure long-term storage** for metrics (Thanos, Cortex, or Mimir)
3. **Integrate with incident management** (PagerDuty, Opsgenie)
4. **Create custom dashboards** for your specific use cases
5. **Set up log aggregation** (Loki, ELK stack)

---

**Quick Reference Commands**:
```bash
make monitoring-dashboard   # Open Grafana
make prometheus-ui         # Open Prometheus
make jaeger-ui            # Open Jaeger
make health-check         # System health
make logs-follow          # Live logs
```

For detailed monitoring architecture, see `docs/guides/observability.mdx`.
