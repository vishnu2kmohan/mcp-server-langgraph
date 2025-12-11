# Infrastructure Alerts Runbook

## Overview

This runbook covers alerts related to infrastructure dependencies (PostgreSQL, Redis, LGTM stack).

---

## PostgreSQLDown

### Alert Definition
```yaml
alert: PostgreSQLDown
expr: up{job="postgres"} == 0
for: 1m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- Database operations fail
- Session persistence lost
- Keycloak authentication fails
- OpenFGA authorization fails

### Diagnosis

1. **Check PostgreSQL pod status**
   ```bash
   kubectl get pods -l app=postgres -n database
   kubectl describe pod -l app=postgres -n database
   ```

2. **Check PostgreSQL logs**
   ```bash
   kubectl logs -l app=postgres -n database --tail=100
   ```

3. **Check storage**
   ```bash
   kubectl get pvc -n database
   kubectl describe pvc postgres-data -n database
   ```

4. **Check database connectivity**
   ```bash
   kubectl exec -it postgres-0 -n database -- psql -U postgres -c "SELECT 1"
   ```

### Resolution

1. **If pod is in CrashLoopBackOff**
   - Check for corrupted data files
   - Verify PVC is mounted correctly
   - Check for OOM kills

2. **If storage is full**
   ```bash
   # Check disk usage
   kubectl exec -it postgres-0 -n database -- df -h /var/lib/postgresql/data
   # Expand PVC if supported
   kubectl patch pvc postgres-data -n database -p '{"spec": {"resources": {"requests": {"storage": "20Gi"}}}}'
   ```

3. **If recovery needed**
   - Restore from backup
   - Check replication lag if replica exists

### Escalation
- **On-call SRE**: Immediately
- **Database Team**: For data recovery

---

## RedisDown

### Alert Definition
```yaml
alert: RedisDown
expr: up{job="redis"} == 0
for: 1m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- Session storage unavailable
- LangGraph checkpoint storage fails
- Cache operations fail
- Potential data loss for in-flight sessions

### Diagnosis

1. **Check Redis pod status**
   ```bash
   kubectl get pods -l app=redis -n cache
   kubectl describe pod -l app=redis -n cache
   ```

2. **Check Redis logs**
   ```bash
   kubectl logs -l app=redis -n cache --tail=100
   ```

3. **Check Redis connectivity**
   ```bash
   kubectl exec -it redis-0 -n cache -- redis-cli ping
   ```

4. **Check memory usage**
   ```bash
   kubectl exec -it redis-0 -n cache -- redis-cli info memory
   ```

### Resolution

1. **If OOM killed**
   - Increase memory limits
   - Review eviction policy
   - Check for memory leaks in client connections

2. **If connectivity issue**
   - Check network policies
   - Verify service endpoints
   - Check TLS certificates if enabled

3. **Restart Redis**
   ```bash
   kubectl rollout restart statefulset/redis -n cache
   ```

### Escalation
- **On-call SRE**: Immediately
- **Application Team**: For session recovery

---

## LokiDown

### Alert Definition
```yaml
alert: LokiDown
expr: up{job="loki"} == 0
for: 2m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Log ingestion stops
- Historical log queries unavailable
- Debugging capability reduced
- No immediate user-facing impact

### Diagnosis

1. **Check Loki pod status**
   ```bash
   kubectl get pods -l app=loki -n monitoring
   kubectl describe pod -l app=loki -n monitoring
   ```

2. **Check Loki logs (if any)**
   ```bash
   kubectl logs -l app=loki -n monitoring --tail=100
   ```

3. **Check storage backend**
   - Verify object storage connectivity (S3/GCS/MinIO)
   - Check storage credentials

### Resolution

1. **Restart Loki**
   ```bash
   kubectl rollout restart deployment/loki -n monitoring
   ```

2. **If storage issue**
   - Verify storage bucket exists
   - Check IAM permissions
   - Verify network connectivity to storage

3. **If memory issue**
   - Increase memory limits
   - Review retention settings
   - Check for query cardinality issues

### Escalation
- **On-call SRE**: Slack #sre-oncall
- **Observability Team**: For configuration issues

---

## TempoDown

### Alert Definition
```yaml
alert: TempoDown
expr: up{job="tempo"} == 0
for: 2m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Trace ingestion stops
- Distributed tracing unavailable
- No immediate user-facing impact
- Debugging capability reduced

### Diagnosis

1. **Check Tempo pod status**
   ```bash
   kubectl get pods -l app=tempo -n monitoring
   ```

2. **Check Tempo logs**
   ```bash
   kubectl logs -l app=tempo -n monitoring --tail=100
   ```

### Resolution

1. **Restart Tempo**
   ```bash
   kubectl rollout restart deployment/tempo -n monitoring
   ```

2. **Verify OTLP ingestion**
   ```bash
   # Check OTLP receiver is working
   curl http://tempo:4318/v1/traces -X POST -d '{}'
   ```

### Escalation
- **On-call SRE**: Slack #sre-oncall

---

## MimirDown

### Alert Definition
```yaml
alert: MimirDown
expr: up{job="mimir"} == 0
for: 2m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Metrics storage unavailable
- Long-term metrics queries fail
- Alerting may be impacted
- Dashboard queries return no data

### Diagnosis

1. **Check Mimir pod status**
   ```bash
   kubectl get pods -l app=mimir -n monitoring
   ```

2. **Check Mimir logs**
   ```bash
   kubectl logs -l app=mimir -n monitoring --tail=100
   ```

3. **Check storage backend**
   - Verify object storage connectivity
   - Check storage credentials

### Resolution

1. **Restart Mimir**
   ```bash
   kubectl rollout restart deployment/mimir -n monitoring
   ```

2. **Verify Prometheus remote write**
   - Check Prometheus logs for write errors
   - Verify remote write endpoint configuration

### Escalation
- **On-call SRE**: Slack #sre-oncall

---

## HighCPUUsage

### Alert Definition
```yaml
alert: HighCPUUsage
expr: rate(process_cpu_seconds_total{job="langgraph-agent"}[5m]) * 100 > 80
for: 10m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Performance degradation
- Request latency increase
- Potential service instability

### Diagnosis

1. **Check CPU utilization**
   ```bash
   kubectl top pods -l app=langgraph-agent
   ```

2. **Identify hot spots**
   - Check Grafana dashboards for CPU trends
   - Look for correlation with traffic or specific operations

### Resolution

1. **Scale horizontally**
   ```bash
   kubectl scale deployment/langgraph-agent --replicas=5
   ```

2. **Enable autoscaling**
   ```bash
   kubectl autoscale deployment/langgraph-agent --min=3 --max=10 --cpu-percent=70
   ```

### Escalation
- **On-call SRE**: For immediate scaling
- **Performance Team**: For root cause analysis
