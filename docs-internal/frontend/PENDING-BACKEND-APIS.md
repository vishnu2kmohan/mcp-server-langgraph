# Backend APIs for Frontend Features

This document tracks backend API endpoints for frontend features and their implementation status.

## Implementation Status

| Feature | Status | Backend Location |
|---------|--------|------------------|
| Session Goal Tracking | ✅ Fully Implemented | `api/v1/sessions.py` |
| AI Predictions | ✅ Implemented (stub) | `api/v1/ai.py` |

**Note**: Session Goal Tracking is fully implemented with PostgreSQL persistence, audit logging, and error handling. AI Predictions returns empty predictions pending ML pipeline integration.

---

## Session Goal Tracking

**Feature**: Allow users to set, complete, and track session goals

**Status**: ✅ Fully Implemented (PostgreSQL persistence, audit logging, error handling)

### Set Session Goal

```
POST /api/v1/sessions/{session_id}/goal
```

**Request Body**:
```json
{
  "goal": "string",
  "set_at": 1705123456789
}
```

**Response**: `201 Created`
```json
{
  "session_id": "string",
  "goal": "string",
  "set_at": 1705123456789
}
```

**Backend Location**: `src/mcp_server_langgraph/api/v1/sessions.py`

**Frontend Integration**: `src/components/Chat/ChatDocument.tsx` (uses `useSetSessionGoalMutation`)

### Complete Session Goal

```
POST /api/v1/sessions/{session_id}/goal/complete
```

**Request Body**:
```json
{
  "goal": "string",
  "achieved": "boolean | 'partial'",
  "feedback": "string (optional)",
  "completed_at": 1705123456789
}
```

**Response**: `200 OK`
```json
{
  "session_id": "string",
  "goal": "string",
  "achieved": "boolean | 'partial'",
  "feedback": "string | null",
  "set_at": 1705123456789,
  "completed_at": 1705123456789
}
```

**Backend Location**: `src/mcp_server_langgraph/api/v1/sessions.py`

**Frontend Integration**: `src/components/Chat/ChatDocument.tsx` (uses `useCompleteSessionGoalMutation`)

### Get Session Goal History

```
GET /api/v1/sessions/{session_id}/goals?limit=50&offset=0
```

**Response**: `200 OK`
```json
{
  "session_id": "string",
  "goals": [
    {
      "id": "string",
      "goal": "string",
      "achieved": "boolean | 'partial' | null",
      "feedback": "string | null",
      "set_at": 1705123456789,
      "completed_at": 1705123456789
    }
  ],
  "total": 10
}
```

**Backend Location**: `src/mcp_server_langgraph/api/v1/sessions.py`

**Frontend Integration**: `src/components/Chat/ChatDocument.tsx` (uses `useGetSessionGoalHistoryQuery`)

### Get Current Session Goal

```
GET /api/v1/sessions/{session_id}/goal/current
```

**Response**: `200 OK`
```json
{
  "session_id": "string",
  "goal": {
    "id": "string",
    "goal": "string",
    "achieved": null,
    "feedback": null,
    "set_at": 1705123456789,
    "completed_at": null
  }
}
```

Returns `goal: null` if no active goal exists.

**Backend Location**: `src/mcp_server_langgraph/api/v1/sessions.py`

**Frontend Integration**: Available via `useGetCurrentSessionGoalQuery`

### Delete Session Goal

```
DELETE /api/v1/sessions/{session_id}/goals/{goal_id}
```

**Response**: `204 No Content`

**Backend Location**: `src/mcp_server_langgraph/api/v1/sessions.py`

**Frontend Integration**: Available via `useDeleteSessionGoalMutation`

---

## AI Predictions

**Feature**: Predictive analytics for HEART metrics (churn risk, adoption forecasts)

**Status**: ✅ Implemented (stub - returns empty predictions, ML pipeline integration pending)

### Get Predictions

```
GET /api/v1/ai/predictions
```

**Query Parameters**:
- `session_id` (optional): Filter by session
- `type` (optional): Filter by prediction type (churn_risk, adoption_forecast, engagement_decline)
- `min_confidence` (optional): Minimum confidence threshold (0-1)

**Response**: `200 OK`
```json
{
  "predictions": [
    {
      "id": "string",
      "type": "churn_risk | adoption_forecast | engagement_decline",
      "metric": "string",
      "predicted_value": 0.75,
      "confidence": 0.85,
      "timeframe": "7d | 30d | 90d",
      "factors": [
        {
          "name": "string",
          "impact": 0.3
        }
      ],
      "created_at": 1705123456789
    }
  ]
}
```

**Backend Location**: `src/mcp_server_langgraph/api/v1/ai.py`

**Frontend Integration**: `src/hooks/useAIMetricsInsights.ts` (uses `useGetPredictionsQuery`)

**ADR Reference**: ADR-0091 Phase 7

---

## RTK Query Integration Status

| Endpoint | RTK Query Hook | Status |
|----------|----------------|--------|
| `GET /api/v1/ai/predictions` | `useGetPredictionsQuery` | ✅ Integrated |
| `POST /api/v1/sessions/{id}/goal` | `useSetSessionGoalMutation` | ✅ Integrated |
| `POST /api/v1/sessions/{id}/goal/complete` | `useCompleteSessionGoalMutation` | ✅ Integrated |
| `GET /api/v1/sessions/{id}/goals` | `useGetSessionGoalHistoryQuery` | ✅ Integrated |
| `GET /api/v1/sessions/{id}/goal/current` | `useGetCurrentSessionGoalQuery` | ✅ Integrated |
| `DELETE /api/v1/sessions/{id}/goals/{goal_id}` | `useDeleteSessionGoalMutation` | ✅ Integrated |

All endpoints are typed and integrated. Frontend consumers import hooks from:

```typescript
import {
  useGetPredictionsQuery,
  useSetSessionGoalMutation,
  useCompleteSessionGoalMutation,
  useGetSessionGoalHistoryQuery,
  useGetCurrentSessionGoalQuery,
  useDeleteSessionGoalMutation,
} from "../api";
```

---

## Database Schema

### Session Goals (Implemented)

```sql
CREATE TABLE session_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    goal TEXT NOT NULL,
    achieved VARCHAR(10) CHECK (achieved IN ('true', 'false', 'partial')),
    feedback TEXT,
    set_at BIGINT NOT NULL,
    completed_at BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_session_goals_session_id ON session_goals(session_id);
CREATE INDEX idx_session_goals_user_id ON session_goals(user_id);
```

**Migration**: `alembic/versions/z6a7b8c9d0e1_add_session_goals_table.py`

### AI Predictions (Pending)

```sql
CREATE TABLE ai_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    type VARCHAR(50) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    predicted_value DECIMAL(5,4) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    factors JSONB DEFAULT '[]',
    created_at BIGINT NOT NULL,
    expires_at BIGINT
);

CREATE INDEX idx_ai_predictions_session_id ON ai_predictions(session_id);
CREATE INDEX idx_ai_predictions_type ON ai_predictions(type);
CREATE INDEX idx_ai_predictions_confidence ON ai_predictions(confidence);
```

---

## Testing

### Backend Tests

```bash
# Session Goals (60 tests)
uv run pytest tests/unit/api/v1/test_session_goals.py \
  tests/unit/api/v1/test_session_goals_wired.py \
  tests/unit/api/v1/test_session_goals_audit_error.py \
  tests/unit/repositories/test_session_goal.py \
  tests/unit/core/test_session_goal_dependency.py -v

# AI Predictions
uv run pytest tests/unit/api/v1/test_ai_predictions.py -v
```

### Frontend Tests

```bash
npm run test -- --run src/api/endpoints.test.tsx
```

---

## Error Responses

### Session Goal Endpoints

- `404 Not Found`: Session or goal not found
- `400 Bad Request`: Invalid goal data (empty goal, missing fields)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Database or repository error

### AI Predictions Endpoint

- `400 Bad Request`: Invalid query parameters
- `401 Unauthorized`: Missing or invalid authentication
