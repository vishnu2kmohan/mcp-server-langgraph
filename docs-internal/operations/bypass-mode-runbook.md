# Bypass Mode Operations Runbook

## Overview

This runbook covers operational procedures for the Risk-Aware Bypass Mode feature, which allows authorized users to auto-approve low-risk execution plans without manual intervention.

**Feature Flags**: `bypass_risk_aware_enabled`, `execution_mode_toggle`
**Permission**: `bypass_executor` on `system:global` (OpenFGA)
**Components**: BypassManager, bypass_prometheus_metrics, bypass_audit

---

## Bypass High Auto-Approval Rate Alert

### Alert Definition
```yaml
alert: BypassHighAutoApprovalRate
expr: |
  sum(rate(bypass_approvals_total{approval_type="auto"}[5m]))
  /
  sum(rate(bypass_approvals_total[5m])) > 0.95
for: 10m
severity: warning
```

### Severity
**WARNING** - Investigate within 30 minutes

### Impact
- Potentially risky operations being auto-approved without review
- Reduced human oversight on execution plans
- Possible misconfiguration of risk thresholds

### Diagnosis

1. **Check auto-approval breakdown by risk level**
   ```promql
   sum by (risk_level, complexity) (
     rate(bypass_approvals_total{approval_type="auto"}[1h])
   )
   ```

2. **Identify users with high bypass usage**
   ```promql
   topk(10, sum by (user) (
     rate(bypass_activations_total[1h])
   ))
   ```

3. **Check for tool escalations not triggering**
   ```promql
   rate(bypass_tool_escalations_total[1h])
   ```

### Resolution

1. **If mostly low-risk/simple plans**
   - This may be expected behavior for the user's workflow
   - Monitor but no action needed

2. **If tool escalations are low**
   - Verify SANDBOX_REQUIRED_TOOLS list is up to date
   - Check if new dangerous tools need to be added
   ```bash
   grep -n "SANDBOX_REQUIRED_TOOLS" src/mcp_server_langgraph/api/v1/tools.py
   ```

3. **If single user is responsible**
   - Review user's permission grant in OpenFGA
   - Consider revoking `bypass_executor` permission
   ```bash
   # Check user's bypass permission
   python -c "
   from mcp_server_langgraph.auth.openfga import OpenFGAClient
   # Query user:suspicious_user bypass_executor system:global
   "
   ```

### Escalation
- **On-call SRE**: #ops-alerts Slack channel
- **Security Team**: security@company.com (if suspicious activity)

---

## Bypass Permission Denied Spike

### Alert Definition
```yaml
alert: BypassPermissionDeniedSpike
expr: |
  rate(bypass_permission_checks_total{result="denied"}[5m])
  > 0.5
for: 5m
severity: info
```

### Severity
**INFO** - Review next business day

### Impact
- Users attempting to use bypass mode without permission
- Possible confusion about feature availability
- May indicate need for permission grants

### Diagnosis

1. **Check denial rate trend**
   ```promql
   rate(bypass_permission_checks_total{result="denied"}[1h])
   ```

2. **Check audit logs for denied users**
   ```sql
   SELECT actor_id, COUNT(*) as attempts
   FROM audit_events
   WHERE event_type = 'execution_mode.bypass.activated'
     AND outcome = 'denied'
     AND created_at > NOW() - INTERVAL '1 hour'
   GROUP BY actor_id
   ORDER BY attempts DESC;
   ```

### Resolution

1. **If legitimate users need access**
   - Grant `bypass_executor` permission in OpenFGA
   ```json
   {
     "user": "user:alice",
     "relation": "bypass_executor",
     "object": "system:global"
   }
   ```

2. **If unauthorized access attempts**
   - Log for security review
   - No immediate action needed (permission system is working)

### Escalation
- **Team Owner**: Platform team lead

---

## Bypass Tool Escalation Storm

### Alert Definition
```yaml
alert: BypassToolEscalationStorm
expr: |
  rate(bypass_tool_escalations_total[5m]) > 10
for: 5m
severity: warning
```

### Severity
**WARNING** - Investigate within 30 minutes

### Impact
- Many plans requiring risk escalation
- Increased user friction (more approval dialogs)
- May indicate change in user behavior patterns

### Diagnosis

1. **Identify which tools are causing escalations**
   ```promql
   topk(5, sum by (tool) (
     rate(bypass_tool_escalations_total[1h])
   ))
   ```

2. **Check escalation patterns by from/to levels**
   ```promql
   sum by (from_level, to_level) (
     rate(bypass_tool_escalations_total[1h])
   )
   ```

### Resolution

1. **If `execute_bash` dominates**
   - Expected for CLI-heavy workflows
   - Consider if users need alternatives (safer sandboxed commands)

2. **If new tool is causing escalations**
   - Review TOOL_RISK_ESCALATION mapping in bypass_manager.py
   - Adjust risk level if warranted
   ```python
   TOOL_RISK_ESCALATION: dict[str, RiskLevel] = {
       "execute_bash": "high",
       "execute_python": "medium",
       # ... adjust as needed
   }
   ```

### Escalation
- **Team Owner**: Platform team lead

---

## High Estimated Cost Plans

### Alert Definition
```yaml
alert: BypassHighEstimatedCost
expr: |
  bypass_plan_estimated_cost{complexity="complex"} > 1.0
for: 5m
severity: info
```

### Severity
**INFO** - Review for cost optimization

### Impact
- Higher than expected LLM costs
- Budget utilization concerns

### Diagnosis

1. **Check cost distribution by complexity**
   ```promql
   avg by (complexity, risk_level) (bypass_plan_estimated_cost)
   ```

2. **Identify high-cost patterns**
   - Complex tasks with deep thinking budgets
   - Multiple critique rounds

### Resolution

1. **Review thinking budget settings**
   - Consider if "deep" thinking is needed for all complex tasks
   - Adjust defaults in feature flags

2. **Optimize critique rounds**
   - Reduce default critique_rounds for non-critical tasks

### Escalation
- **Team Owner**: Platform team lead
- **Finance**: For budget concerns

---

## Bypass Mode Disabled Emergency

### Procedure for Emergency Disablement

1. **Disable via feature flag**
   ```bash
   # Update feature flag in environment
   export BYPASS_RISK_AWARE_ENABLED=false

   # Or update in database/config
   ```

2. **Revoke all bypass permissions (nuclear option)**
   ```bash
   # Remove all bypass_executor tuples from OpenFGA
   python scripts/docker/seed_openfga.py revoke-bypass-permissions
   ```

3. **Monitor for effects**
   ```promql
   rate(bypass_approvals_total[1m])  # Should drop to zero
   ```

4. **Notify users**
   - Post in #engineering channel
   - Update status page if customer-facing

---

## Grafana Dashboard Links

- **Bypass Mode Overview**: `/d/bypass-mode-overview`
- **Execution Mode Metrics**: `/d/execution-mode-metrics`
- **Audit Trail**: `/d/audit-events`

---

## Related Documentation

- [Chat Input UX Plan](/.claude/plans/breezy-roaming-flame.md)
- [OpenFGA Model](config/openfga/modules/04-access-control.fga)
- [Bypass Manager Source](src/mcp_server_langgraph/execution/bypass_manager.py)
- [Cost Estimator](src/mcp_server_langgraph/execution/cost_estimator.py)

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-19 | Claude | Initial runbook creation |
