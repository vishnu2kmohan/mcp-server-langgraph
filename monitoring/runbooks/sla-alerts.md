# SLA Alerts Runbook

## Overview

This runbook covers alerts related to SLA breaches and compliance.

**SLA Targets:**
- Uptime: 99.9% (43.2 minutes/month downtime budget)
- Response Time (p95): < 500ms
- Error Rate: < 1%

---

## SLAUptimeBreach

### Alert Definition
```yaml
alert: SLAUptimeBreach
expr: (sum(up{job="langgraph-agent"}) / count(up{job="langgraph-agent"}) * 100) < 99.9
for: 5m
severity: critical
```

### Severity
**CRITICAL** - Immediate incident response

### Impact
- Contractual SLA breach
- Customer-facing outage
- Potential financial penalties
- Trust and reputation impact

### Diagnosis

1. **Determine scope of outage**
   ```promql
   # Check which instances are down
   up{job="langgraph-agent"} == 0
   ```

2. **Calculate downtime duration**
   - Check when `up` metric first went to 0
   - Calculate accumulated downtime this month

3. **Check for cascading failures**
   - Verify all dependencies are healthy
   - Check infrastructure (nodes, network, storage)

### Resolution

This is a critical incident. Follow incident response procedure:

1. **Declare incident**
   - Notify #sre-oncall immediately
   - Start incident channel
   - Assign incident commander

2. **Immediate mitigation**
   - Attempt service restart
   - Scale up replicas if partial outage
   - Failover to backup region if available

3. **Restore service**
   - Address root cause
   - Verify all instances healthy
   - Confirm metrics show > 99.9% uptime

4. **Post-incident**
   - Calculate total downtime
   - Update SLA tracking
   - Schedule post-mortem

### Escalation
- **Incident Commander**: Immediately
- **Engineering Lead**: Within 5 minutes
- **Management**: Within 15 minutes for customer-facing impact

---

## SLAResponseTimeBreach

### Alert Definition
```yaml
alert: SLAResponseTimeBreach
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="langgraph-agent"}[5m])) * 1000 > 500
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 15 minutes

### Impact
- Poor user experience
- SLA target at risk
- Potential customer complaints

### Diagnosis

1. **Identify slow endpoints**
   ```promql
   histogram_quantile(0.95, sum by (path, le) (rate(http_request_duration_seconds_bucket{job="langgraph-agent"}[5m]))) * 1000
   ```

2. **Check for resource contention**
   ```bash
   kubectl top pods -l app=langgraph-agent
   ```

3. **Check dependency latencies**
   - Database query times
   - LLM API response times
   - Redis cache hit rates

### Resolution

1. **If LLM responses are slow**
   - Check LLM provider status page
   - Enable fallback model if available
   - Consider request timeout tuning

2. **If database is slow**
   - Check connection pool utilization
   - Look for slow queries
   - Verify indexes are being used

3. **If high traffic**
   - Scale horizontally
   - Enable autoscaling if not active

### Escalation
- **On-call SRE**: Slack #sre-oncall
- **Performance Team**: If persistent

---

## SLAErrorRateBreach

### Alert Definition
```yaml
alert: SLAErrorRateBreach
expr: (sum(rate(http_requests_total{job="langgraph-agent",status=~"5.."}[5m])) / sum(rate(http_requests_total{job="langgraph-agent"}[5m])) * 100) > 1
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 15 minutes

### Impact
- SLA target at risk
- User requests failing
- Potential data loss or corruption

### Diagnosis

1. **Check error distribution**
   ```promql
   sum by (status) (rate(http_requests_total{job="langgraph-agent",status=~"5.."}[5m]))
   ```

2. **Identify error patterns**
   ```bash
   kubectl logs -l app=langgraph-agent --tail=200 | grep -E "ERROR|CRITICAL"
   ```

3. **Correlate with deployments**
   - Check if recent deployment
   - Compare with previous error rate

### Resolution

1. **If 500 errors (Internal Server Error)**
   - Check application logs for stack traces
   - Review recent code changes
   - Consider rollback if deployment related

2. **If 502/503/504 errors (Gateway errors)**
   - Check upstream services
   - Verify load balancer health
   - Check container health probes

3. **If rate limited (429)**
   - Check for traffic spike
   - Review rate limiting configuration
   - Consider temporary limit increase

### Escalation
- **On-call SRE**: Slack #sre-oncall
- **Engineering Team**: For code-related issues

---

## MonthlyDowntimeBudgetLow

### Alert Definition
```yaml
alert: MonthlyDowntimeBudgetLow
expr: (43.2 - (sum(rate(up{job="langgraph-agent"}[30d])) / count(up{job="langgraph-agent"}) * 30 * 24 * 60)) < 10
for: 1h
severity: warning
```

### Severity
**WARNING** - Proactive alert

### Impact
- Approaching monthly SLA breach
- Limited remaining downtime budget
- Increased risk of contractual breach

### Diagnosis

1. **Check remaining budget**
   - View SLA Monitoring dashboard
   - Calculate exact minutes remaining

2. **Review month-to-date incidents**
   - Count and duration of outages
   - Identify patterns

3. **Assess upcoming risks**
   - Planned maintenance
   - Deployments scheduled
   - Known issues

### Resolution

1. **Reduce planned downtime**
   - Postpone non-critical maintenance
   - Use rolling deployments
   - Consider blue-green deployments

2. **Increase reliability**
   - Add redundancy if single point of failure
   - Review and fix flaky components
   - Improve monitoring coverage

3. **Communicate proactively**
   - Notify stakeholders of SLA risk
   - Prepare customer communication if breach likely

### Escalation
- **SRE Lead**: For planning
- **Management**: For customer communication
