# ADR-0091: API Response Transformation Strategy

| Status | Accepted |
|--------|----------|
| Date | 2026-01-04 |
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
| **Generic** | `transformSnakeToCamel<T>` | Recursive conversion for any structure |

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
