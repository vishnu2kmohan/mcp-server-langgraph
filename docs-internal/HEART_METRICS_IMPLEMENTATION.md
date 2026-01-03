# HEART Metrics Implementation Guide

**Author**: System
**Last Updated**: 2026-01-03
**Status**: Active
**Related ADRs**: ADR-0088 (Frontend Hook Selection)

---

## Overview

This document provides comprehensive documentation for the HEART metrics framework implementation in MCP Server LangGraph. It covers the Goals-Signals-Metrics (GSM) framework, WebSocket streaming, frontend integration, and observability patterns.

## HEART Framework

The HEART framework is a Google-developed methodology for measuring user experience quality. It consists of five dimensions:

| Dimension | Description | Example Metrics |
|-----------|-------------|-----------------|
| **H**appiness | User satisfaction and sentiment | NPS score, satisfaction rating, feedback sentiment |
| **E**ngagement | User activity levels and depth | DAU/MAU ratio, session duration, actions per session |
| **A**doption | New user success and feature discovery | Onboarding completion, feature first use |
| **R**etention | Return visits and continued usage | D1/D7/D30 retention rates |
| **T**ask Success | Goal completion and error rates | Task completion rate, error rate |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HEART Metrics Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────┐    ┌──────────────────┐                      │
│  │  Frontend Hooks   │    │  React Components │                      │
│  │ useHeartDashboard │───▶│  HEARTComponents  │                      │
│  │ useHeartMetrics   │    │  AnalyticsPage    │                      │
│  │ useHeartMetrics   │    └──────────────────┘                      │
│  │   WebSocket       │              │                                │
│  └───────┬───────────┘              │                                │
│          │                          ▼                                │
│          │              ┌───────────────────────┐                    │
│          │              │  HeartAggregator      │                    │
│          │              │  - Event batching     │                    │
│          │              │  - Session context    │                    │
│          │              └───────────┬───────────┘                    │
│          │                          │                                │
│          ▼                          ▼                                │
│  ┌───────────────────┐    ┌──────────────────┐                      │
│  │   WebSocket API   │    │   REST API       │                      │
│  │ /api/v1/ws/       │    │ /api/v1/metrics/ │                      │
│  │ metrics/heart     │    │ heart/batch      │                      │
│  └───────┬───────────┘    └────────┬─────────┘                      │
│          │                          │                                │
│          ▼                          ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              HeartMetricsHandler / Service                   │    │
│  │  ┌─────────────────────────────────────────────────────┐    │    │
│  │  │            HeartMetricsServiceAdapter               │    │    │
│  │  │  - Queries Prometheus/Mimir for live metrics        │    │    │
│  │  │  - Falls back to stub data for dev/testing          │    │    │
│  │  └─────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                          │                                          │
│                          ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   Prometheus / Mimir                         │    │
│  │  Metrics:                                                    │    │
│  │  - heart_happiness_score                                     │    │
│  │  - heart_engagement_rate                                     │    │
│  │  - heart_adoption_rate                                       │    │
│  │  - heart_retention_rate                                      │    │
│  │  - heart_task_success_rate                                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Goals-Signals-Metrics (GSM) Framework

The GSM framework structures HEART metrics collection:

### Goals

Goals define what we want to achieve for each HEART dimension.

**Location**: `studio/frontend/src/analytics/gsm/GoalsDefinition.ts`

```typescript
interface HeartGoal {
  id: string;                    // Unique identifier
  dimension: HeartDimension;     // happiness, engagement, etc.
  description: string;           // Human-readable goal
  targetValue: number;           // Target to achieve
  unit: string;                  // Unit of measurement
  signals: string[];             // Signal IDs that contribute
  metricType: "average" | "percentage" | "count" | "nps" | "ratio";
}
```

**Example Goals**:

| Dimension | Goal ID | Target | Description |
|-----------|---------|--------|-------------|
| Happiness | `happiness_nps` | 50 | Achieve high NPS from users |
| Engagement | `engagement_dau_mau` | 0.4 | Maintain healthy DAU/MAU ratio |
| Adoption | `adoption_onboarding` | 0.8 | 80% onboarding completion |
| Retention | `retention_d7` | 0.35 | 35% D7 retention rate |
| Task Success | `task_success_completion` | 0.9 | 90% task completion rate |

### Signals

Signals are user actions or events that indicate progress toward goals.

**Location**: `studio/frontend/src/analytics/gsm/SignalsRegistry.ts`

```typescript
interface Signal {
  id: string;                    // Unique signal identifier
  name: string;                  // Human-readable name
  description: string;           // What this signal measures
  valueType: "number" | "boolean" | "string" | "counter";
}
```

**Signal Categories**:

| Category | Signal Examples |
|----------|-----------------|
| Happiness | `happiness_nps_score`, `happiness_satisfaction_rating`, `happiness_feedback` |
| Engagement | `engagement_feature_click`, `engagement_session_duration`, `engagement_daily_active` |
| Adoption | `adoption_onboarding_started`, `adoption_onboarding_complete`, `adoption_feature_first_use` |
| Retention | `retention_return_visit`, `retention_days_since_last_visit` |
| Task Success | `task_completed`, `task_failed`, `task_duration` |

### Recording Signals

```typescript
import { recordSignal } from "./gsm/SignalsRegistry";

// Record a feature click
recordSignal("engagement_feature_click", 1, { feature: "workflow_builder" });

// Record task completion
recordSignal("task_completed", true, { task_type: "workflow_execution" });

// Record session duration
recordSignal("engagement_session_duration", 300000, { session_id: "abc123" });
```

---

## WebSocket Streaming

### Backend Implementation

**Location**: `websocket/handlers/heart_metrics.py`

The `HeartMetricsHandler` extends `WebSocketBase` to provide real-time HEART metrics streaming:

```python
from mcp_server_langgraph.websocket.handlers.heart_metrics import HeartMetricsHandler
from mcp_server_langgraph.websocket.types import WebSocketConfig

handler = HeartMetricsHandler(
    config=WebSocketConfig(
        endpoint_name="heart-metrics",
        require_auth=True,
        authz_resource_type="observability",
        authz_resource_id="heart",
        authz_required_relation="viewer",
    ),
    metrics_service=get_heart_metrics_service(),
)
```

### Message Protocol

**Client → Server**:

| Message Type | Payload | Description |
|--------------|---------|-------------|
| `set_time_range` | `{time_range: "24h"}` | Set metrics time range (1h, 6h, 24h, 7d, 30d, 90d) |
| `subscribe_dimension` | `{dimension: "happiness"}` | Subscribe to dimension updates |
| `unsubscribe_dimension` | `{dimension: "happiness"}` | Unsubscribe from dimension |

**Server → Client**:

| Message Type | Payload | Description |
|--------------|---------|-------------|
| `metrics_snapshot` | Full HEART snapshot | Initial or updated metrics |
| `dimension_update` | Single dimension data | Update for subscribed dimension |
| `threshold_alert` | Alert details | Metric crossed threshold |
| `unsubscribed` | Confirmation | Unsubscription confirmed |
| `error` | Error details | Error occurred |

### Metrics Snapshot Format

```json
{
  "type": "metrics_snapshot",
  "metrics": {
    "happiness": {"score": 85, "trend": "up", "change": 2.5},
    "engagement": {"score": 72, "trend": "stable", "change": 0.3},
    "adoption": {"score": 90, "trend": "up", "change": 5.0},
    "retention": {"score": 88, "trend": "stable", "change": -0.5},
    "task_success": {"score": 95, "trend": "up", "change": 1.2}
  },
  "time_range": "24h",
  "last_updated": "2026-01-03T12:00:00Z"
}
```

### Service Adapter

**Location**: `websocket/services/heart_metrics.py`

The `HeartMetricsServiceAdapter` provides metrics data:

```python
class HeartMetricsServiceAdapter:
    """
    Adapter for HEART framework metrics in WebSocket handlers.
    Uses Prometheus/Mimir backend when available, stubs otherwise.
    """

    async def get_current_snapshot(self, time_range: str = "24h") -> dict:
        """Get current HEART metrics snapshot."""
        if self._metrics_client is not None:
            return await self._query_heart_metrics_from_prometheus(time_range)
        return self._get_stub_data()

    async def get_dimension_metrics(self, dimension: str, time_range: str = "24h") -> dict:
        """Get detailed metrics for a specific dimension."""
        ...
```

---

## Frontend Integration

### Primary Hook: `useHeartDashboard`

**Location**: `studio/frontend/src/hooks/useHeartDashboard.ts`

Provides both polling and real-time WebSocket modes:

```tsx
import { useHeartDashboard } from "../hooks/useHeartDashboard";

function HeartDashboard() {
  const {
    loading,
    error,
    dimensions,
    overallScore,
    timeRange,
    setTimeRange,
    refresh,
    wsStatus,
    isRealtime,
    alerts,
    subscribeDimension,
    unsubscribeDimension,
  } = useHeartDashboard({
    autoRefreshMs: 60000,
    enableRealtime: true,
    wsUrl: "/api/v1/ws/metrics/heart",
  });

  if (loading) return <Loading />;
  if (error) return <Error message={error} />;

  return (
    <>
      <OverallHealthScore score={overallScore} />
      <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      {dimensions.map(dim => (
        <DimensionCard key={dim.dimension} {...dim} />
      ))}
      {alerts.map(alert => (
        <AlertBanner key={alert.dimension} {...alert} />
      ))}
    </>
  );
}
```

### WebSocket-Only Hook: `useHeartMetricsWebSocket`

**Location**: `studio/frontend/src/hooks/useHeartMetricsWebSocket.ts`

For pure WebSocket integration:

```tsx
import { useHeartMetricsWebSocket } from "../hooks/useHeartMetricsWebSocket";

function RealtimeMetrics() {
  const {
    status,
    snapshot,
    timeRange,
    subscribedDimensions,
    alerts,
    error,
    setTimeRange,
    subscribeDimension,
    unsubscribeDimension,
    refresh,
    getDimension,
    clearAlerts,
  } = useHeartMetricsWebSocket({
    onSnapshot: (snap) => console.log("New snapshot", snap),
    onThresholdAlert: (alert) => notifyUser(alert),
  });

  return (
    <div>
      <p>Connection: {status}</p>
      <p>Happiness: {getDimension("happiness")?.score}</p>
    </div>
  );
}
```

### HeartAggregator

**Location**: `studio/frontend/src/analytics/HeartAggregator.ts`

Batches events for efficient server submission:

```typescript
import { HeartAggregator } from "../analytics/HeartAggregator";

const aggregator = new HeartAggregator({
  flushIntervalMs: 30000,  // Auto-flush every 30s
  maxBatchSize: 50,        // Or when 50 events queued
  batchEndpoint: "/api/v1/metrics/heart/batch",
});

// Set session context
aggregator.setSessionContext({
  sessionId: "session-123",
  persona: "admin",
  username: "alice",
});

// Queue events
aggregator.queueEvent("engagement", { feature: "chat", action: "send" });
aggregator.queueEvent("task_success", { task: "workflow", success: true });

// Manual flush
await aggregator.flush();

// Get statistics
console.log(aggregator.getStats());
// { totalQueued: 2, totalFlushed: 2, flushCount: 1, failedFlushes: 0 }

// Cleanup
await aggregator.destroy(true); // flush pending before destroy
```

---

## Components

**Location**: `studio/frontend/src/components/Analytics/HEARTComponents.tsx`

### DimensionCard

Displays an individual HEART dimension:

```tsx
<DimensionCard
  dimension="happiness"
  score={85}
  hasData={true}
/>
```

### OverallHealthScore

Aggregate health score visualization:

```tsx
<OverallHealthScore score={78} />
```

### TimeRangeSelector

Time period selector:

```tsx
<TimeRangeSelector
  value="30d"
  onChange={(range) => setTimeRange(range)}
/>
```

---

## Prometheus Integration

### Metrics Names

The service queries these Prometheus metrics:

| Metric Name | Description |
|-------------|-------------|
| `heart_happiness_score` | User satisfaction score (0-100) |
| `heart_engagement_rate` | User engagement rate (0-100) |
| `heart_adoption_rate` | Feature adoption rate (0-100) |
| `heart_retention_rate` | User retention rate (0-100) |
| `heart_task_success_rate` | Task completion rate (0-100) |

### Sample PromQL Queries

```promql
# Current happiness score
heart_happiness_score

# Average engagement over time range
avg_over_time(heart_engagement_rate[24h])

# Retention trend comparison
(heart_retention_rate - heart_retention_rate offset 7d) / heart_retention_rate offset 7d
```

### Feature Flag

Enable/disable enhanced metrics with the feature flag:

```python
from mcp_server_langgraph.core.feature_flags import get_feature_flags

flags = get_feature_flags()
if flags.enable_websocket_enhanced_metrics:
    # Query real metrics from Prometheus
    metrics = await service.get_current_snapshot()
else:
    # Return minimal/stub data
    metrics = service._get_minimal_snapshot()
```

---

## API Endpoints

### WebSocket Endpoint

```
GET /api/v1/ws/metrics/heart
```

**Authorization**: `observability:heart:viewer` (via OpenFGA)

**Query Parameters**:
- `v`: Protocol version (e.g., `1.0.0`)
- `token`: JWT token for authentication

### REST Endpoints

```
GET /api/v1/metrics/heart/aggregate?range=30d
POST /api/v1/metrics/heart/batch
```

---

## Testing

### Unit Tests

**Location**: `tests/unit/websocket_pkg/services/test_heart_metrics_service.py`

```python
@pytest.mark.unit
async def test_get_current_snapshot_returns_all_dimensions():
    service = HeartMetricsServiceAdapter()
    snapshot = await service.get_current_snapshot("24h")

    assert "happiness" in snapshot
    assert "engagement" in snapshot
    assert "adoption" in snapshot
    assert "retention" in snapshot
    assert "task_success" in snapshot
```

### Integration Tests

**Location**: `tests/integration/websocket/test_heart_metrics_websocket.py`

```python
@pytest.mark.integration
@pytest.mark.websocket
class TestHeartMetricsWebSocket:
    def test_set_time_range_returns_snapshot(self, test_client):
        with test_client.websocket_connect("/api/v1/ws/metrics/heart?v=1.0.0") as ws:
            ws.send_json({
                "type": "set_time_range",
                "id": "test-1",
                "payload": {"time_range": "7d"}
            })
            response = ws.receive_json()
            assert response["type"] == "metrics_snapshot"
```

### Frontend Tests

**Location**: `studio/frontend/src/hooks/useHeartDashboard.test.tsx`

```typescript
describe("useHeartDashboard", () => {
  it("fetches metrics on mount", async () => {
    const { result } = renderHook(() => useHeartDashboard());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.dimensions).toHaveLength(5);
    expect(result.current.overallScore).toBeGreaterThan(0);
  });

  it("switches to real-time mode when enableRealtime=true", async () => {
    const { result } = renderHook(() =>
      useHeartDashboard({ enableRealtime: true })
    );

    await waitFor(() => {
      expect(result.current.wsStatus).toBe("connected");
    });

    expect(result.current.isRealtime).toBe(true);
  });
});
```

---

## Dashboard Configuration

### Grafana Dashboard

**Location**: `monitoring/grafana/dashboards/HEART/heart-metrics.json`

The dashboard displays:
- Overall health score gauge
- Dimension score panels (5 panels)
- Trend graphs over time
- Alert thresholds visualization
- Historical comparison

### Alerting

Configure alerts for low scores:

```yaml
# Alert when happiness drops below 60
- alert: LowHappinessScore
  expr: heart_happiness_score < 60
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "User happiness score is low"
    description: "Happiness score {{ $value }} is below threshold 60"
```

---

## Best Practices

### 1. Use Real-time Mode for Dashboards

```tsx
// Good: Enable real-time for dashboard views
useHeartDashboard({ enableRealtime: true })

// Fallback: Polling when WebSocket unavailable
useHeartDashboard({ autoRefreshMs: 60000 })
```

### 2. Batch Event Submissions

```typescript
// Good: Use aggregator for batching
const aggregator = new HeartAggregator({ maxBatchSize: 50 });
aggregator.queueEvent("engagement", payload);

// Bad: Individual API calls for each event
await fetch("/api/v1/metrics/heart/event", { body: payload });
```

### 3. Set Session Context Early

```typescript
// Set context on login/session start
aggregator.setSessionContext({
  sessionId: currentSession.id,
  persona: user.persona,
  username: user.username,
});
```

### 4. Handle Connection States

```tsx
function Dashboard() {
  const { wsStatus, isRealtime, error } = useHeartDashboard({
    enableRealtime: true,
  });

  if (wsStatus === "error") {
    return <ErrorBanner message={error} />;
  }

  if (wsStatus === "reconnecting") {
    return <ReconnectingIndicator />;
  }

  return <DashboardContent isLive={isRealtime} />;
}
```

---

## Troubleshooting

### Common Issues

1. **Metrics Not Updating**
   - Check WebSocket connection status
   - Verify `enable_websocket_enhanced_metrics` feature flag
   - Check Prometheus/Mimir connectivity

2. **All Scores Are Zero**
   - Feature flag may be disabled
   - Prometheus metrics may not be populated
   - Service may be using stub data

3. **WebSocket Connection Failing**
   - Verify authentication token is valid
   - Check OpenFGA authorization (`observability:heart:viewer`)
   - Review rate limiting configuration

### Debugging Commands

```bash
# Check WebSocket health
curl http://localhost:8080/api/v1/health/websocket

# Query Prometheus directly
curl "http://prometheus:9090/api/v1/query?query=heart_happiness_score"

# Check feature flag
curl http://localhost:8080/api/v1/feature-flags | jq '.enable_websocket_enhanced_metrics'
```

---

## Related Documentation

- [WebSocket Standardization](./WEBSOCKET_STANDARDIZATION.md) - WebSocket infrastructure patterns
- [OpenFGA Architecture](./OPENFGA_ARCHITECTURE.md) - Authorization for HEART endpoints
- [ADR-0088: Frontend Hook Selection](../adr/adr-0088-frontend-hook-selection-guidance.md) - When to use which hook
- [Frontend Design System](./frontend/DESIGN_SYSTEM.md) - Component styling guidelines
