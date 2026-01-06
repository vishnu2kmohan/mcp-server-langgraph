# ADR-0091: API Response Transformation Strategy

| Status | Implemented (Phase 5, 6, 8 & 9 Complete) |
|--------|----------|
| Date | 2026-01-05 |
| Authors | Claude Opus 4.5 |
| Deciders | Engineering Team |
| Consulted | Frontend Architecture |
| Informed | All Contributors |

## Context and Problem Statement

The backend API uses Python/FastAPI conventions with `snake_case` field names (e.g., `alert_id`, `started_at`, `total_cost`), while the frontend uses TypeScript/JavaScript conventions with `camelCase` field names (e.g., `alertId`, `startedAt`, `totalCost`).

This mismatch creates several problems:

1. **Inconsistent Code**: Mix of snake_case and camelCase in frontend components
2. **Developer Confusion**: Unclear which case convention to use
3. **Refactoring Risk**: Each component manually converting fields
4. **Type Safety Gaps**: Types don't reflect actual API response format
5. **Maintenance Burden**: 165+ instances of snake_case access across 21+ files

## Decision

We will implement a **centralized API response transformation layer** using RTK Query's `transformResponse` feature. All API responses will be converted from `snake_case` to `camelCase` at the API boundary before reaching components.

### Implementation Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Backend API                                    │
│                    (snake_case responses)                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    RTK Query transformResponse                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Domain-Specific Transforms (src/api/transforms.ts)               │   │
│  │                                                                   │   │
│  │ - transformTraceItem()     - transformBudgetStatus()             │   │
│  │ - transformSpan()          - transformCostSummary()              │   │
│  │ - transformAlert()         - transformSession()                   │   │
│  │ - transformMetrics()       - transformAuditLog()                 │   │
│  │ - transformOrgCost()       - transformRemediation()              │   │
│  │ - transformProjectCost()   - transformAIRecommendation()         │   │
│  │ - transformTeamCost()      - transformConnection()               │   │
│  │ - transformAgentMetrics()  - transformWorkflow()                 │   │
│  │ - transformSnakeToCamel()  (generic recursive transform)         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       React Components                                   │
│                     (camelCase only)                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Transform Function Catalog

| Category | Transform Functions | Key Fields |
|----------|-------------------|------------|
| **Observability** | `transformTraceItem`, `transformSpan`, `transformAlert`, `transformMetrics` | `traceId`, `spanId`, `startTime`, `durationMs`, `serviceName` |
| **Cost** | `transformOrgCost`, `transformProjectCost`, `transformTeamCost`, `transformBudgetStatus`, `transformCostSummary`, `transformCostForecast` | `totalCost`, `totalTokens`, `requestCount`, `percentUsed` |
| **Session** | `transformSession` | `sessionId`, `userId`, `createdAt`, `tokenCount` |
| **Audit** | `transformAuditLog` | `userId`, `userEmail`, `resourceType`, `ipAddress` |
| **Admin** | `transformRemediation`, `transformAIRecommendation` | `remediationId`, `stepNumber`, `riskLevel`, `rootCauseAnalysis` |
| **Config** | `transformThinkingBudget`, `transformOrchestratorInfo`, `transformProviderInfo` | `defaultLevel`, `taskCategories`, `supportedModelTypes` |
| **Connection** | `transformConnection` | `authType`, `oauth2Config.clientId` |
| **Workflow** | `transformWorkflow` | `ownerId`, `organizationId`, `nodeCount`, `edgeCount` |
| **Generic** | `transformSnakeToCamel<T>`, `transformCamelToSnake<T>` | Bidirectional recursive conversion |

## Phase 5: RTK Query Migration (Complete)

### Implementation Status

Phase 5 added `transformResponse` to RTK Query endpoints and `transformCamelToSnake` for request bodies:

**Transform Functions** (commit 86cee9ad):
- `toCamelCase(str)` - Single string snake_case to camelCase
- `transformSnakeToCamel<T>(obj)` - Recursive response transformation
- `toSnakeCase(str)` - Single string camelCase to snake_case
- `transformCamelToSnake<T>(obj)` - Recursive request transformation
- 108 comprehensive tests (round-trip symmetry verified)

**Response Transforms Applied To (65+ endpoints):**
- Config: `getFeatureFlags`, `getServerConfig`
- Workflow: `getWorkflow`, `getWorkflowShares`, `getWorkflowVersions`, `listWorkflowExecutions`
- Session: `getSession`, `getSessionMessages`, `listSessions`
- Cost: `getCostSummary`, `getCostByModel`, `getCostHistory`, `getBudgetStatus`, `getCostForecast`, `getCostByOrganization`, `getCostByProject`, `getCostByTeam`
- Observability: `getTrace`, `getMetrics`, `getAlert`, `listTraces`, `listLogs`, `listAlerts`
- Project: `getProject`, `createProject`, `updateProject`
- Connection: `getConnection`, `listConnections`, `createConnection`, `updateConnection`
- Agent: `getAgentConfig`, `getAgentMetrics`
- User: `getCurrentUser`, `getUserPreferences`, `getNotificationPreferences`
- Admin: `getAdminUser`, `listAuditLogs`
- Artifacts: `getArtifact`, `createArtifact`, `updateArtifact`
- MCP: `listAggregatedTools`, `listAggregatedResources`, `listAggregatedPrompts`, `listAggregatedServers`, `listMcpResources`

**Request + Response Transforms Applied To:**
- `createWorkflow`, `updateWorkflow`
- `createSession`
- `createProject`, `updateProject`
- `createConnection`, `updateConnection`
- `createArtifact`, `updateArtifact`
- `approveRemediation`, `rejectRemediation`

---

## Phase 6: Component Migration (Complete)

### Summary

Phase 6 migrated all 16 component directories from snake_case property access to camelCase,
leveraging the RTK Query transformations established in Phase 5.

### Components Migrated (50+ files)

| Directory | Key Files Updated |
|-----------|-------------------|
| **Agents/** | `AgentMetricsCard`, `LLMProvidersCard`, `OrchestratorsListCard`, `TaskMappingCard`, `ThinkingBudgetCard` |
| **MCP/** | `ToolExplorer`, `ResourceViewer`, `ResourceBrowser`, `PromptLibrary`, `AggregatedCapabilities`, `AddConnectionDialog` |
| **Observability/** | `TraceViewer` |
| **PlanEditor/** | `PlanEditor`, `PlanSearch` |
| **Analytics/** | `CrossInsightsPanel` |
| **Connection/** | `ConnectionDialog`, `ConnectionHealthDashboard`, `ConnectionAuditLog`, `ConnectionTemplateSelector` |
| **DevTools/** | `AIInsightsTab`, `LLMStreamingTab`, `useObservabilityAI`, `useDevToolsWebSocketBridge` |
| **Workflow/** | `ExecutionHistoryPanel`, `WorkflowDiffViewer`, `WorkflowVersionHistory`, `ShareWorkflowDialog` |
| **Project/** | `SessionsTab`, `WorkflowsTab`, `ProjectDocument` |
| **Session/** | `SessionList`, `SimilarSessionsPanel` |
| **Settings/** | `SettingsPanel`, `AuditEventPanel`, `NotificationPreferencesSettings` |
| **Admin/** | `AlertDetailPanel`, `RemediationApprovalDialog`, `ClarificationDialog`, `AlertGroupsPanel` |
| **TemplateSelector/** | `TemplateSelector` |
| **Cost/** | `OrganizationCostDashboard` |
| **Insights/** | `CostDocument`, `ObservabilityDocument` |
| **Layout/** | `SessionNav` |

### Types Updated (20+ interfaces)

- `WorkflowExecution` - `workflowId`, `startedAt`, `completedAt`, `inputData`, `outputData`
- `ThinkingLevelInfo` - `claudeOpusEffort`, `otherModelsTokens`
- `MCPConnectionCreate` - `authType`, `apiKey`, `oauth2ClientId`, `projectId`
- `OrchestratorInfo` - `displayName`, `featureFlag`, `taskCategories`
- `ProviderInfo` - `displayName`, `supportedModelTypes`, `requiresApiKey`
- `ConnectionHealth` - All properties to camelCase
- `AlertData` - `startedAt`
- `PersonaAnalysisResult` - `assignedPersona`, `detectedPersona`, `behaviorSignals`
- `DisclosureAnalysisResult` - `currentLevel`, `recommendedLevel`, `unlockFeatures`

### ESLint Override Cleanup

**Removed (16 patterns):**
- `**/components/Agents/*.tsx`
- `**/components/MCP/*.tsx`
- `**/components/Observability/*.tsx`
- `**/components/PlanEditor/*.tsx`
- `**/components/Analytics/*.tsx`
- `**/components/Connection/*.tsx`
- `**/components/DevTools/**/*.{tsx,ts}`
- `**/components/Workflow/*.tsx`
- `**/components/Project/*.tsx`
- `**/components/Session/*.tsx`
- `**/components/Settings/*.tsx`
- `**/components/Admin/*.tsx`
- `**/components/TemplateSelector/*.tsx`
- `**/components/Cost/*.tsx`
- `**/components/Insights/*.tsx`
- `**/components/Chat/*.tsx`

**Retained (API Boundary - By Design):**

| Pattern | Reason |
|---------|--------|
| `**/layout/*.tsx` | `StudioShellLayout` uses Admin HITL callback types (snake_case API contract) |
| `**/pages/*.tsx` | Pages are API boundary; some transform data at boundary |
| `**/api/**/*.ts` | API layer defines transforms and works with raw snake_case |
| `**/mocks/**/*.ts` | Mock handlers return snake_case to simulate backend |
| `**/types/api.ts` | Type definitions match backend API contract |
| `**/hooks/use*WebSocket.ts` | WebSocket message handlers receive snake_case payloads |
| `**/store/slices/*.ts` | Redux slices may cache API data in original format |

---

## Phase 7: Future Enhancements (Low Priority)

### Admin HITL Types

The Admin HITL types (`ApproveAgentRequestParams`, `RejectAgentRequestParams`, etc.) currently
use snake_case to match the backend API contract. Migration assessed as **LOW PRIORITY** because:

1. Types are tightly coupled to backend WebSocket payloads
2. Changes would require coordinated backend/frontend updates
3. Current implementation is internally consistent
4. ESLint override for `layout/*.tsx` appropriately scopes exceptions

If migration is desired in the future:
1. Add CamelCase type aliases (e.g., `ApproveAgentRequestParamsCamelCase`)
2. Apply transforms in `useAgentRequestWebSocket` hook
3. Update `StudioShellLayout` callback types
4. Remove `layout/*.tsx` ESLint override

### Implementation Pattern

```typescript
// Response-only (queries)
getWorkflow: builder.query<Workflow, string>({
  query: (id) => `/workflows/${id}`,
  transformResponse: (response: Workflow) => transformSnakeToCamel(response),
  providesTags: (_result, _error, id) => [{ type: "Workflow", id }],
}),

// Request + Response (mutations)
createWorkflow: builder.mutation<Workflow, CreateWorkflowRequest>({
  query: (body) => ({
    url: "/workflows",
    method: "POST",
    body: transformCamelToSnake(body),
  }),
  transformResponse: (response: Workflow) => transformSnakeToCamel(response),
  invalidatesTags: [{ type: "Workflow", id: "LIST" }],
}),
```

---

## Phase 8: Generated OpenAPI Types at API Boundary

### Problem Statement

The frontend had manual type definitions in `api/index.ts` that could drift from the backend Pydantic schemas, causing 422 Unprocessable Entity errors. The `generated-api.ts` file (auto-generated from OpenAPI spec) was only used in 2 places despite being the source of truth.

### Solution

Use generated types from `src/types/generated-api.ts` for RTK Query mutations/queries at the API boundary:

```typescript
// BEFORE: Hand-rolled inline types (prone to drift)
getNudgeRecommendation: builder.mutation<
  { nudge_type: string; message: string; confidence: number },
  { user_id: string; current_context: { page: string } }
>({...});

// AFTER: Generated types from OpenAPI spec (ADR-0091 Phase 8)
import type { components } from "../types/generated-api";
type NudgeRecommendRequest = components["schemas"]["NudgeRecommendRequest"];
type NudgeRecommendResponse = components["schemas"]["NudgeRecommendResponse"];

getNudgeRecommendation: builder.mutation<
  NudgeRecommendResponse,
  NudgeRecommendRequest
>({...});
```

### Type Export Locations

| File | Purpose |
|------|---------|
| `src/types/generated-api.ts` | Auto-generated OpenAPI types (source of truth) |
| `src/types/api-generated.ts` | Re-exports with `Api*` prefix for clarity |
| `src/api/index.ts` | RTK Query endpoints using generated types |

### AI UX Endpoints Aligned (2026-01-06)

| Endpoint | Request Type | Response Type |
|----------|--------------|---------------|
| `POST /api/v1/ai/nudges/recommend` | `NudgeRecommendRequest` | `NudgeRecommendResponse` |
| `POST /api/v1/ai/onboarding/personalize` | `OnboardingPersonalizeRequest` | `OnboardingPersonalizeResponse` |
| `POST /api/v1/ai/persona/analyze` | `PersonaAnalyzeRequest` | `PersonaAnalyzeResponse` |

### Contract Test Coverage

New contract tests validate frontend types match generated OpenAPI types:

- `src/api/aiUxContract.test.ts` - 34 tests validating request/response structures
- Type guards validate runtime objects match generated schemas
- Tests cover required fields, optional fields, and nested structures

### Usage Guidelines

1. **New Endpoints**: Import types from `generated-api.ts` for RTK Query mutations
2. **Request Bodies**: Use generated request types (snake_case matches Pydantic)
3. **Response Bodies**: Use generated response types, apply transforms for camelCase
4. **Hooks**: Transform generated response to hook's camelCase interface
5. **Tests**: Update mock data to match generated response structure

### Regenerating Types

When backend schemas change, regenerate types:

```bash
cd src/mcp_server_langgraph/studio/frontend
npm run generate:api  # Generates src/types/generated-api.ts from OpenAPI spec
```

---

## Phase 9: Backend Pydantic Schema Alignment (Complete)

### Problem Statement

Backend Pydantic schemas for AI UX endpoints had diverged from frontend inline TypeScript types,
causing type mismatches in tests and runtime validation errors. Key issues:

1. **ErrorAnalyzeRequest**: Tests used deprecated `ErrorInfo(name=, message=)` instead of `ErrorAnalyzeRequest(error_code=, error_message=)`
2. **ErrorAnalyzeResponse**: Field `classification` renamed to `error_type` for clarity
3. **DisclosureAnalyzeResponse**: `current_level` and `recommended_level` changed from enum to string for flexibility
4. **Schema coupling**: Service code compared against enum values when response fields were now strings

### Solution

Aligned all 8 AI UX test files with the new Pydantic schemas and fixed service code:

| Model | Old Field | New Field | Type Change |
|-------|-----------|-----------|-------------|
| `ErrorAnalyzeRequest` | `error: ErrorInfo` | `error_code`, `error_message` | Flattened structure |
| `ErrorAnalyzeResponse` | `classification` | `error_type` | Semantic rename |
| `ErrorAnalyzeResponse` | `suggestions` | `recovery_steps` | Semantic rename |
| `DisclosureAnalyzeResponse` | `current_level: DisclosureLevel` | `current_level: str` | Enum → String |
| `DisclosureAnalyzeResponse` | `recommended_level: DisclosureLevel` | `recommended_level: str` | Enum → String |
| `DisclosureAnalyzeResponse` | `personalized_message: str \| None` | `personalized_message: str` | Required with default |

### Test Files Updated

| File | Tests | Changes |
|------|-------|---------|
| `test_ai_ux_endpoints.py` | 4 | Request schema alignment |
| `test_ai_ux_enhancements.py` | 41 | Response field access |
| `test_ai_ux_model_selector.py` | 13 | Request/response alignment |
| `test_ai_ux_production_features.py` | 23 | Schema alignment |
| `test_ai_ux_session_cache.py` | 7+2 xfail | Removed invalid `session_id` param |
| `test_ai_ux_artifact_storage.py` | 9 | Request alignment |
| `test_ai_ux_composite_analysis.py` | 10 | String-based disclosure levels |
| `test_ai_ux_llm_service.py` | 38 | Full schema alignment |

### Service Code Fixed

Fixed `_generate_cross_insights` in `ai_ux_service.py:2663-2670`:

```python
# BEFORE: Enum comparison and .value access
if disclosure_result.current_level == DisclosureLevel.BEGINNER:
    f"'{disclosure_result.current_level.value}'. Consider upgrade."

# AFTER: String comparison (Phase 9 aligned)
if disclosure_result.current_level == "beginner":
    f"'{disclosure_result.current_level}'. Consider upgrade."
```

### Validation Results

```
================== 243 passed, 2 xfailed in 154.50s ==================
```

- **243 tests pass** across all AI UX test files
- **2 xfailed** (TDD placeholders for future error_analysis session storage feature)

---

## Consequences

### Positive Consequences

1. **Consistency**: All frontend code uses camelCase exclusively
2. **Type Safety**: TypeScript types reflect actual data shape
3. **Single Transformation Point**: Changes isolated to `transforms.ts`
4. **Developer Experience**: Clear convention reduces cognitive load
5. **Maintainability**: Easier refactoring and updates
6. **Prevention**: ESLint warns on snake_case usage in new code

### Negative Consequences

1. **Migration Effort**: 165+ existing instances need updating
2. **Bundle Size**: Small increase from transform functions (~3KB)
3. **Runtime Overhead**: Transformation adds ~1-5ms per response (negligible)
4. **Learning Curve**: Developers must learn the transform pattern

## Related Decisions

- ADR-0088: Frontend Hook Selection Guidance
- ADR-0045: RTK Query API Design (if exists)

## References

- RTK Query transformResponse: https://redux-toolkit.js.org/rtk-query/usage/customizing-queries
- Transform implementation: `src/mcp_server_langgraph/studio/frontend/src/api/transforms.ts`
- ESLint configuration: `src/mcp_server_langgraph/studio/frontend/eslint.config.js`
