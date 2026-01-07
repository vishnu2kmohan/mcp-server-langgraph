# Alert Dashboard Alert Runbook

This runbook provides troubleshooting guidance for alerts related to the alert dashboard, AI recommendations, and remediation features.

## Overview

These alerts monitor the alert dashboard functionality including AI-powered recommendations, remediation execution, and WebSocket connectivity for real-time updates.

## Symptoms

When these alerts fire, you may observe:
- Slow or missing AI recommendations
- Remediation execution failures
- WebSocket connection issues
- Alert broadcast problems

---

## RemediationExecutionSlow

### Description
Remediation command execution is taking longer than expected.

### Impact
**Warning** - Delayed remediation response to alerts.

### Resolution
1. Check remediation execution logs
2. Review target system responsiveness
3. Check network connectivity to remediation targets
4. Consider timeout configuration adjustments

### Escalation
Notify on-call if affecting critical remediations.

---

## AlertWebSocketConnectionsHigh

### Description
Unusually high number of WebSocket connections to alert dashboard.

### Impact
**Warning** - May indicate connection leaks or unusual usage patterns.

### Resolution
1. Check connection count by client
2. Review connection lifecycle management
3. Look for clients not properly closing connections
4. Consider connection limits per client

### Escalation
Create ticket for connection management review.

---

## AlertBroadcastNoRecipients

### Description
Alert broadcast has no active recipients.

### Impact
**Warning** - Alerts may not be reaching intended users.

### Resolution
1. Check WebSocket connection status
2. Verify subscription configuration
3. Review user session activity
4. Check for authentication issues

### Escalation
Notify on-call if critical alerts are affected.

---

## AIRecommendationCacheHitRateLow

### Description
AI recommendation cache hit rate is below optimal threshold.

### Impact
**Info** - More LLM calls than necessary, increased latency and cost.

### Resolution
1. Review cache TTL configuration
2. Check cache eviction policies
3. Analyze recommendation request patterns
4. Consider cache warming strategies

### Escalation
Create optimization ticket.

---

## RemediationCommandsBlockedHigh

### Description
High rate of remediation commands being blocked by safety checks.

### Impact
**Info** - Remediation suggestions not being executed.

### Resolution
1. Review blocked command patterns
2. Check safety policy configuration
3. Verify commands are properly formatted
4. Consider policy adjustments if legitimate commands blocked

### Escalation
Notify security team for policy review.

---

## RemediationRejectionRateHigh

### Description
Users are rejecting AI remediation suggestions at high rate.

### Impact
**Info** - AI recommendations may not be relevant.

### Resolution
1. Review rejection reasons from feedback
2. Analyze rejected recommendation patterns
3. Consider prompt improvements
4. Review recommendation relevance

### Escalation
Create AI quality improvement ticket.

---

## AlertWebSocketNoConnections

### Description
No active WebSocket connections to alert dashboard.

### Impact
**Info** - May indicate no active users or connection issues.

### Resolution
1. Verify this is expected (off-hours, maintenance)
2. Check WebSocket endpoint health
3. Review load balancer configuration
4. Check for authentication issues

### Escalation
Investigate if during business hours.

---

## AlertFilterRateHigh

### Description
High rate of alerts being filtered out.

### Impact
**Info** - Many alerts may be suppressed.

### Resolution
1. Review filter configuration
2. Check if filters are too aggressive
3. Verify important alerts are not being filtered
4. Consider filter tuning

### Escalation
Create filter configuration review ticket.
