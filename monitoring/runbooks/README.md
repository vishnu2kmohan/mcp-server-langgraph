# Alerting Runbooks

This directory contains runbooks for responding to alerts from the MCP Server with LangGraph observability stack.

## Runbook Structure

Each runbook follows a standard template:
- **Alert**: The alert name and description
- **Severity**: Critical, Warning, or Info
- **Impact**: What is affected when this alert fires
- **Diagnosis**: Steps to investigate the root cause
- **Resolution**: Steps to remediate the issue
- **Escalation**: Who to contact if initial resolution fails

## Available Runbooks

| Alert Category | Runbook | Severity |
|---------------|---------|----------|
| Service Health | [langgraph-agent-health.md](langgraph-agent-health.md) | Critical |
| Authentication | [authentication-alerts.md](authentication-alerts.md) | Critical/Warning |
| LLM Performance | [llm-performance-alerts.md](llm-performance-alerts.md) | Warning |
| Infrastructure | [infrastructure-alerts.md](infrastructure-alerts.md) | Critical/Warning |
| SLA Breaches | [sla-alerts.md](sla-alerts.md) | Critical |

## Alert Routing

Alerts are defined in:
- `monitoring/prometheus/alerts/langgraph-agent.yaml` - Service health, performance
- `monitoring/prometheus/alerts/sla.yaml` - SLA-specific alerts
- `docker/mimir/rules/lgtm-alerts.yaml` - LGTM stack health

## Quick Reference

### Critical Alerts (Immediate Response Required)

| Alert | Impact | Quick Fix |
|-------|--------|-----------|
| `LangGraphAgentDown` | Service unavailable | Check pod status, restart if needed |
| `KeycloakDown` | Auth failures for all users | Check Keycloak deployment, DB connection |
| `OpenFGADown` | Authorization failures | Check OpenFGA deployment, PostgreSQL |
| `SLAUptimeBreach` | Customer-facing outage | Immediate incident escalation |

### Warning Alerts (Response Within 30 Minutes)

| Alert | Impact | Quick Fix |
|-------|--------|-----------|
| `HighErrorRate` | Degraded service quality | Check logs for error patterns |
| `SlowLLMResponses` | Poor user experience | Check LLM provider status |
| `AuthenticationFailureSpike` | Potential attack or misconfiguration | Review auth logs |

## Creating New Runbooks

Use the template at `.claude/templates/runbook-template.md` when creating new runbooks:

```bash
cp .claude/templates/runbook-template.md monitoring/runbooks/new-alert.md
```

## Related Documentation

- [Grafana Dashboards](../grafana/dashboards/README.md)
- [Alerting Rules](../prometheus/alerts/)
- [SLA Targets](../../deployments/helm/mcp-server-langgraph/values.yaml)
