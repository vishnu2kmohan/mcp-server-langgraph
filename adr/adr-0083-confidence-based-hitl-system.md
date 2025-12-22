# 83. Confidence-Based Human-in-the-Loop (HITL) System

Date: 2025-12-21

## Status

Accepted

## Category

Architecture & Multi-Agent Orchestration

## Context

The multi-agent orchestrator needs a mechanism to pause for human approval when agent confidence drops below configurable thresholds. This enables human oversight for critical decisions while maintaining automation efficiency for high-confidence operations.

**Key Requirements**:

| Requirement | Description |
|-------------|-------------|
| Confidence Tracking | Track confidence scores in agent results |
| Threshold-Based Pausing | Pause agents when confidence < threshold |
| Real-Time Notifications | Push approval requests via WebSocket |
| Approval Workflow | Approve/reject with optional reason |
| Clarification Requests | Allow agents to ask clarifying questions |
| Batch Approvals | Handle multiple similar requests efficiently |
| Rotating Thresholds | Auto-adjust thresholds based on patterns |
| Audit Trail | Track all approval decisions for compliance |
| Observability | Metrics, alerts, and dashboards for HITL |

**UX Best Practices** (from research):

1. **Don't Over-Review**: Only pause for truly critical decisions
2. **Confidence Visualization**: Color-coded confidence indicators
3. **Explainability**: Show why approval is needed
4. **Batch Processing**: Reduce approval fatigue
5. **Progressive Thresholds**: Adjust based on user patterns

## Decision

Implement a comprehensive HITL system with the following architecture:

### 1. Backend Components

#### 1.1 Agent Request Models

**File**: `src/mcp_server_langgraph/api/v1/agent_requests.py`

```python
class AgentRequestType(str, Enum):
    APPROVAL = "approval"       # Low confidence approval
    CLARIFICATION = "clarification"  # Agent needs info

class AgentApprovalRequest(BaseModel):
    request_id: str
    request_type: AgentRequestType
    session_id: str
    task_id: str
    agent_name: str
    confidence: float  # 0-1
    threshold: float   # 0-1
    trigger_reason: str
    proposed_action: str
    context: dict

class ApprovalDecision(BaseModel):
    request_id: str
    decision: Literal["approved", "rejected"]
    reason: str | None
    decided_by: str
    decided_at: str
```

#### 1.2 Confidence Interrupt Node

**File**: `src/mcp_server_langgraph/core/interrupts/confidence.py`

Uses LangGraph's `interrupt()` pattern to pause execution:

```python
from langgraph.types import interrupt

def confidence_approval_node(state: dict, threshold: float = 0.7) -> dict:
    confidence = state.get("verification_score")
    if confidence is not None and confidence < threshold:
        response = interrupt({
            "type": "low_confidence",
            "confidence": confidence,
            "threshold": threshold,
        })
        if not response.get("approved"):
            state["workflow_halted"] = True
    return state
```

#### 1.3 REST API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agents/requests/pending` | GET | List pending approvals |
| `/agents/requests/{id}` | GET | Get specific request |
| `/agents/requests/{id}/approve` | POST | Approve request |
| `/agents/requests/{id}/reject` | POST | Reject request |
| `/agents/requests/batch` | POST | Batch approve/reject |
| `/agents/requests/threshold/recommendation` | GET | Get threshold recommendation |
| `/agents/requests/threshold/settings` | GET/PUT | Manage threshold settings |

#### 1.4 WebSocket Handler

**File**: `src/mcp_server_langgraph/api/v1/agent_request_websocket.py`

Message types:
- `approval_required` - Server pushes new approval request
- `clarification_required` - Server pushes clarification request
- `execution_resumed` - Agent resumed after decision
- `approval_response` - Client sends approval decision

### 2. Frontend Components

#### 2.1 State Management

**Extended Agent Status**:

```typescript
type AgentStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "awaiting_approval"
  | "awaiting_clarification";
```

**New Slice**: `backgroundAgentSlice` extended with approval tracking

#### 2.2 Dialog Components

| Component | Purpose |
|-----------|---------|
| `AgentApprovalDialog` | Display approval request with confidence gauge |
| `ClarificationDialog` | Handle agent clarification requests |
| `BatchApprovalPanel` | Process multiple requests efficiently |
| `AgentApprovalAuditLog` | Display approval history |

#### 2.3 Hooks

| Hook | Purpose |
|------|---------|
| `useAgentRequestWebSocket` | WebSocket connection for approvals |
| `useBatchApprovals` | Batch approval/rejection logic |
| `useThresholdSettings` | Threshold configuration management |
| `useHITLDialogs` | Dialog state management |

### 3. Threshold Configuration

#### 3.1 Confidence Thresholds

| Level | Threshold | Behavior |
|-------|-----------|----------|
| Auto-Approve | >= 90% | Proceed without approval |
| Notify | 70-89% | Proceed with notification |
| Require Approval | 50-69% | **Pause for approval** |
| Block | < 50% | Block with explanation |

#### 3.2 Rotating Thresholds

Based on approval history patterns:

```python
class ThresholdCalculator:
    def calculate_recommendation(self, history: list[ApprovalHistory]) -> ThresholdRecommendation:
        # High approval rate (>80%) → lower threshold
        # High rejection rate (>50%) → raise threshold
        # Insufficient data → keep current
```

**Feature Flag**: `enable_rotating_thresholds` (default: True)

### 4. Observability

#### 4.1 Metrics

| Metric | Type | Purpose |
|--------|------|---------|
| `agent_hitl_request_count_total` | Counter | Total HITL requests |
| `agent_hitl_decision_count_total` | Counter | Decisions by outcome |
| `agent_hitl_response_latency` | Histogram | Time to user response |
| `agent_hitl_trigger_confidence` | Histogram | Confidence distribution |
| `agent_hitl_pending_count` | Gauge | Current queue depth |

#### 4.2 Alerts

| Alert | Severity | Threshold |
|-------|----------|-----------|
| HITLInterventionRateHigh | Warning | >30% for 10min |
| HITLInterventionRateCritical | Critical | >50% for 5min |
| HITLResponseTimeSlow | Warning | p95 >5min for 15min |
| HITLQueueBacklog | Warning | >10 pending for 5min |

#### 4.3 Dashboard

**File**: `monitoring/grafana/dashboards/Application/hitl-metrics.json`

Panels: Request rate, confidence distribution, response latency, decision breakdown, queue depth

### 5. Feature Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `enable_agent_hitl` | true | Master toggle for HITL |
| `agent_hitl_confidence_threshold` | 0.7 | Default threshold |
| `enable_hitl_auto_approve` | true | Auto-approve high confidence |
| `hitl_auto_approve_threshold` | 0.9 | Auto-approve above this |
| `enable_batch_approvals` | true | Enable batch processing |
| `enable_rotating_thresholds` | true | Enable threshold adjustment |

## Consequences

### Positive

1. **Human Oversight**: Critical decisions require human approval
2. **Automation Efficiency**: High-confidence operations proceed automatically
3. **Adaptive Thresholds**: System learns from approval patterns
4. **Audit Compliance**: Full audit trail for all decisions
5. **User Experience**: Real-time notifications, batch processing
6. **Observability**: Comprehensive metrics and alerting

### Negative

1. **Latency**: HITL adds wait time for user response
2. **Complexity**: Additional WebSocket, dialogs, and state
3. **User Fatigue**: Too many approvals can overwhelm users

### Mitigations

| Concern | Mitigation |
|---------|------------|
| Response latency | Push notifications, configurable timeouts |
| User fatigue | Batch approvals, rotating thresholds |
| Complexity | Feature flags for gradual rollout |

## Implementation Status

| Phase | Component | Status |
|-------|-----------|--------|
| 1 | Backend confidence tracking | ✅ Complete |
| 2 | REST API endpoints | ✅ Complete |
| 3 | WebSocket handler | ✅ Complete |
| 4 | Frontend state management | ✅ Complete |
| 5 | Approval/Clarification dialogs | ✅ Complete |
| 6 | Batch approvals | ✅ Complete |
| 7 | Rotating thresholds | ✅ Complete |
| 8 | Audit log UI | ✅ Complete |
| 9 | Observability (metrics, alerts) | ✅ Complete |
| 10 | Runbook documentation | ✅ Complete |

## Files Created/Modified

### New Files

| Path | Purpose |
|------|---------|
| `api/v1/agent_requests.py` | REST API endpoints |
| `api/v1/agent_request_websocket.py` | WebSocket handler |
| `core/interrupts/confidence.py` | Confidence interrupt node |
| `core/interrupts/clarification.py` | Clarification helpers |
| `studio/frontend/src/components/Admin/AgentApprovalDialog.tsx` | Approval dialog |
| `studio/frontend/src/components/Admin/ClarificationDialog.tsx` | Clarification dialog |
| `studio/frontend/src/components/Admin/BatchApprovalPanel.tsx` | Batch processing |
| `studio/frontend/src/components/Admin/AgentApprovalAuditLog.tsx` | Audit log |
| `studio/frontend/src/hooks/useAgentRequestWebSocket.ts` | WebSocket hook |
| `studio/frontend/src/hooks/useBatchApprovals.ts` | Batch approval hook |
| `studio/frontend/src/hooks/useThresholdSettings.ts` | Threshold hook |
| `studio/frontend/src/hooks/useHITLDialogs.ts` | Dialog state hook |
| `monitoring/grafana/dashboards/Application/hitl-metrics.json` | Dashboard |
| `docs-internal/runbooks/HITL_OPERATIONS.md` | Runbook |

### Modified Files

| Path | Changes |
|------|---------|
| `agents/subagent.py` | Added confidence to SubagentResult |
| `agents/orchestrator.py` | Added execute_with_hitl() method |
| `agents/metrics.py` | Added HITL metrics |
| `core/feature_flags.py` | Added HITL feature flags |
| `api/v1/router.py` | Registered new routers |
| `studio/frontend/src/store/slices/backgroundAgentSlice.ts` | Added awaiting_approval status |
| `studio/frontend/src/layout/HybridShellLayout.tsx` | Integrated HITL dialogs |
| `deployments/monitoring/alerting-rules/hitl-alerts.yaml` | Alert definitions |

## Related ADRs

- ADR-0077: Claude Agent SDK Integration (interrupt patterns)
- ADR-0078: Multi-Agent Orchestrator Patterns
- ADR-0026: Resilience Patterns (alert architecture)

## References

- [LangGraph Interrupts](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/)
- [Claude Agent SDK Best Practices](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Designing AI Confidence UX](https://www.smashingmagazine.com/2025/09/psychology-trust-ai-guide-measuring-designing-user-confidence/)
