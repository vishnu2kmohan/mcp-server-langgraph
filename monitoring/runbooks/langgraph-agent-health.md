# LangGraph Agent Health Runbook

## Overview

This runbook covers alerts related to the core LangGraph Agent service health.

---

## LangGraphAgentDown

### Alert Definition
```yaml
alert: LangGraphAgentDown
expr: up{job="langgraph-agent"} == 0
for: 1m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- All agent functionality unavailable
- Users cannot interact with the MCP server
- Downstream systems may fail

### Diagnosis

1. **Check pod status**
   ```bash
   kubectl get pods -l app=langgraph-agent -n mcp-server
   kubectl describe pod <pod-name> -n mcp-server
   ```

2. **Check recent events**
   ```bash
   kubectl get events -n mcp-server --sort-by='.lastTimestamp' | tail -20
   ```

3. **Check container logs**
   ```bash
   kubectl logs -l app=langgraph-agent -n mcp-server --tail=100
   ```

4. **Check resource constraints**
   ```bash
   kubectl top pods -l app=langgraph-agent -n mcp-server
   ```

### Resolution

1. **If pod is CrashLoopBackOff**
   - Check logs for startup errors
   - Verify environment variables are set
   - Check secrets are mounted correctly
   ```bash
   kubectl get secret langgraph-agent-secrets -n mcp-server -o yaml
   ```

2. **If pod is Pending**
   - Check for resource constraints
   - Verify node capacity
   ```bash
   kubectl describe nodes | grep -A 5 "Allocated resources"
   ```

3. **If pod is OOMKilled**
   - Increase memory limits in deployment
   ```bash
   kubectl set resources deployment/langgraph-agent -n mcp-server --limits=memory=2Gi
   ```

4. **Restart deployment**
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n mcp-server
   ```

### Escalation
- **On-call SRE**: Slack #sre-oncall
- **Service Owner**: @langgraph-team

---

## HighErrorRate

### Alert Definition
```yaml
alert: LangGraphAgentHighErrorRate
expr: rate(http_requests_total{job="langgraph-agent",status=~"5.."}[5m]) / rate(http_requests_total{job="langgraph-agent"}[5m]) > 0.05
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Degraded service quality
- Some requests failing
- User experience impacted

### Diagnosis

1. **Check error distribution by endpoint**
   ```promql
   sum by (path, status) (rate(http_requests_total{job="langgraph-agent", status=~"5.."}[5m]))
   ```

2. **Check application logs for error patterns**
   ```bash
   kubectl logs -l app=langgraph-agent -n mcp-server --tail=200 | grep -i error
   ```

3. **Check if errors correlate with specific endpoints**
   - View the Authentication dashboard for auth-related 401/403s
   - View the LLM Performance dashboard for LLM-related errors

4. **Check downstream dependencies**
   - PostgreSQL connectivity
   - Redis connectivity
   - Keycloak availability
   - OpenFGA availability

### Resolution

1. **If errors are auth-related (401/403)**
   - Check Keycloak health
   - Verify JWKS endpoint is responding
   - Check token validation configuration

2. **If errors are database-related**
   - Check PostgreSQL connection pool
   - Verify database is reachable
   - Check for slow queries

3. **If errors are LLM-related**
   - Check LLM provider status (OpenAI, Anthropic, etc.)
   - Verify API keys are valid
   - Check rate limits

### Escalation
- **On-call SRE**: Slack #sre-oncall

---

## SlowResponses

### Alert Definition
```yaml
alert: LangGraphAgentSlowResponses
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="langgraph-agent"}[5m])) > 2
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Poor user experience
- Potential SLA breach risk
- Possible downstream timeout cascades

### Diagnosis

1. **Identify slow endpoints**
   ```promql
   histogram_quantile(0.95, sum by (path, le) (rate(http_request_duration_seconds_bucket{job="langgraph-agent"}[5m])))
   ```

2. **Check LLM response times**
   - LLM calls are typically the slowest operation
   - View LLM Performance dashboard

3. **Check database query times**
   ```promql
   histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))
   ```

4. **Check resource utilization**
   ```bash
   kubectl top pods -l app=langgraph-agent -n mcp-server
   ```

### Resolution

1. **If LLM calls are slow**
   - Check LLM provider status pages
   - Consider enabling fallback models
   - Review prompt complexity

2. **If database queries are slow**
   - Check for missing indexes
   - Review connection pool settings
   - Consider query optimization

3. **If CPU is high**
   - Scale horizontally (add replicas)
   - Review for CPU-intensive operations

### Escalation
- **On-call SRE**: Slack #sre-oncall
- **Performance Team**: For persistent issues
