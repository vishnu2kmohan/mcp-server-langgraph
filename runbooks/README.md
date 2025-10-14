# Operational Runbooks

This directory contains runbooks for responding to alerts and operational incidents for the LangGraph MCP Agent system.

## Quick Reference

| Alert | Severity | Component | Runbook |
|-------|----------|-----------|---------|
| **Authentication & SSO** |
| KeycloakDown | Critical | keycloak | [keycloak-down.md](./keycloak-down.md) |
| KeycloakHighLatency | Warning | keycloak | [keycloak-slow.md](./keycloak-slow.md) |
| KeycloakTokenRefreshFailures | Warning | keycloak | [keycloak-token-refresh.md](./keycloak-token-refresh.md) |
| **Session Storage** |
| RedisSessionStoreDown | Critical | redis | [redis-down.md](./redis-down.md) |
| RedisHighMemoryUsage | Warning | redis | [redis-memory.md](./redis-memory.md) |
| RedisConnectionPoolExhausted | Warning | redis | [redis-pool.md](./redis-pool.md) |
| SessionStoreErrors | Warning | sessions | [session-errors.md](./session-errors.md) |
| SessionTTLViolations | Info | sessions | [session-ttl.md](./session-ttl.md) |

## Runbook Structure

Each runbook follows a consistent structure:

1. **Alert Description** - What triggered this alert
2. **Impact** - User, service, and business impact
3. **Symptoms** - What you'll observe
4. **Diagnosis** - How to investigate the issue
5. **Resolution** - Step-by-step fixes for common scenarios
6. **Verification** - How to confirm the fix worked
7. **Prevention** - How to avoid this in the future
8. **Related Alerts** - Connected issues to watch for
9. **Escalation** - When and how to escalate

## Alert Severity Levels

- **Critical**: Immediate action required, service is down or severely degraded
- **Warning**: Action needed soon, service is degraded but functional
- **Info**: Informational, may not require immediate action

## Common Tools and Commands

### Kubernetes

```bash
# Check pod status
kubectl get pods -n langgraph-agent

# View logs
kubectl logs -n langgraph-agent -l app=<component> --tail=100

# Describe resource
kubectl describe pod -n langgraph-agent <pod-name>

# Execute command in pod
kubectl exec -n langgraph-agent -it <pod-name> -- <command>

# Port forward for debugging
kubectl port-forward -n langgraph-agent svc/<service> <local-port>:<remote-port>
```

### Redis

```bash
# Connect to Redis CLI
kubectl exec -n langgraph-agent -it $(kubectl get pod -n langgraph-agent -l app=redis-session -o jsonpath='{.items[0].metadata.name}') -- redis-cli -a "${REDIS_PASSWORD}"

# Check memory
redis-cli INFO memory

# Check stats
redis-cli INFO stats

# List keys
redis-cli --scan --pattern "session:*"

# Get key TTL
redis-cli TTL <key>
```

### Keycloak

```bash
# Port forward to access admin console
kubectl port-forward -n langgraph-agent svc/keycloak 8080:8080

# Access at: http://localhost:8080/admin/master/console/

# Check health
curl http://localhost:8080/health
```

### Prometheus

```bash
# Query metrics
curl -s 'http://localhost:9090/api/v1/query?query=<promql>'

# Example: Check error rate
curl -s 'http://localhost:9090/api/v1/query?query=rate(session_store_errors_total[5m])'
```

## Environment-Specific Configurations

### Development
- Namespace: `langgraph-agent-dev`
- Auth provider: `inmemory`
- Session backend: `memory`
- Replicas: 1
- Lower resource limits

### Staging
- Namespace: `langgraph-agent-staging`
- Auth provider: `keycloak`
- Session backend: `redis`
- Replicas: 2
- Full observability enabled

### Production
- Namespace: `langgraph-agent`
- Auth provider: `keycloak` (SSL verified)
- Session backend: `redis` (SSL enabled)
- Replicas: 3+
- High availability configured

## Escalation Procedures

### Level 1 - On-Call Engineer
- Investigate using runbooks
- Implement fixes for known scenarios
- Monitor for resolution
- Document actions taken

### Level 2 - Senior SRE
Escalate if:
- Issue persists > 1 hour after attempted fixes
- Root cause is unclear
- Multiple related alerts firing
- Customer impact is significant

### Level 3 - Development Team
Escalate if:
- Code changes required
- Database/data corruption suspected
- Architecture changes needed
- Security incident suspected

### Incident Response
Invoke incident response for:
- Complete service outage > 30 minutes
- Data breach or security incident
- Cascading failures across multiple services
- SLA violations

## Additional Resources

- [Main Documentation](../README.md)
- [Deployment Guide](../../deployments/README.md)
- [Keycloak Integration](../integrations/keycloak.md)
- [Monitoring Configuration](../../monitoring/prometheus/alerts/langgraph-agent.yaml)
- [Prometheus Alerts](../../monitoring/prometheus/alerts/langgraph-agent.yaml)

## Contributing

When creating new runbooks:

1. Follow the standard template structure
2. Include specific commands and outputs
3. Provide multiple resolution scenarios
4. Add verification steps
5. Link to related documentation
6. Update this README with the new runbook

## Support

For questions or issues with runbooks:
- Create an issue: https://github.com/vishnu2kmohan/mcp-server-langgraph/issues
- Contact: SRE team via on-call rotation
