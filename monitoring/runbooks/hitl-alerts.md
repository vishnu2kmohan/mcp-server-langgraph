# Human-in-the-Loop (HITL) Alert Runbook

This runbook provides troubleshooting guidance for HITL workflow alerts.

## Overview

HITL alerts monitor the human-in-the-loop approval workflow including approval rates, action volumes, and workflow health.

## Symptoms

When these alerts fire, you may observe:
- Low approval rates for agent actions
- High volume of destructive action requests
- Unusual patterns in API access requests
- Stalled HITL workflows

---

## HITLLowApprovalRate

### Description
Agent action approval rate is below expected threshold.

### Impact
**Info** - May indicate overly cautious users or poor action quality.

### Resolution
1. Review rejection reasons from feedback
2. Analyze rejected action patterns
3. Check if agent is proposing appropriate actions
4. Consider action quality improvements

### Escalation
Create AI quality review ticket.

---

## HITLDestructiveActionVolume

### Description
High volume of destructive action requests requiring approval.

### Impact
**Info** - Many risky actions being proposed.

### Resolution
1. Review destructive action patterns
2. Check if agent is being overly aggressive
3. Consider adjusting agent behavior
4. Verify classification of destructive actions

### Escalation
Notify AI team for behavior review.

---

## HITLExternalAPIVolume

### Description
High volume of external API calls requiring approval.

### Impact
**Info** - May indicate unusual agent behavior.

### Resolution
1. Review external API call patterns
2. Check for legitimate use cases
3. Consider auto-approval for safe APIs
4. Review API allowlist configuration

### Escalation
Create API policy review ticket.

---

## HITLNoActivity

### Description
No HITL activity detected for extended period.

### Impact
**Info** - May indicate workflow issues or no agent activity.

### Resolution
1. Verify agents are running
2. Check HITL workflow health
3. Review agent activity logs
4. Confirm this is expected (off-hours)

### Escalation
Investigate if during active usage periods.
