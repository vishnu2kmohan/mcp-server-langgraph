# Unified Frontend API Coverage Audit

**Date**: 2025-12-14
**Status**: Comprehensive Audit Complete
**Auditor**: Claude Code

---

## Executive Summary

This audit evaluates the frontend's coverage of the unified backend API (`/api/v1`). The analysis reveals:

- **50+ backend endpoints** available across 11 router modules
- **Significant gaps** in frontend CRUD operation coverage
- **Incomplete pagination/sorting/filtering/search** implementation
- **Mixed API patterns** (RTK Query vs direct fetch) creating inconsistency

### Coverage Score: **68%** (estimated)

| Category | Backend Support | Frontend Implementation | Gap |
|----------|----------------|------------------------|-----|
| Sessions CRUD | Full | Partial | Medium |
| Workflows CRUD | Full | Partial | Medium |
| Projects CRUD | Full | Good | Low |
| Vectors CRUD | Full | Good | Low |
| Cost API | Full | Good | Low |
| Observability | Full | Partial | Medium |
| User/Auth | Full | Good | Low |
| Features | Full | Good | None |
| MCP WebSocket | Full | Partial | High |
| Pagination | Full | Minimal | **High** |
| Sorting | Full | None | **Critical** |
| Filtering | Full | Minimal | **High** |
| Search | Full | None | **Critical** |

---

## 1. CRUD Operations Audit

### 1.1 Sessions

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **List** | `GET /sessions` | `sessionSlice.fetchSessions()` | Partial - No pagination params |
| **Get** | `GET /sessions/{id}` | `sessionSlice.loadSession()` | Complete |
| **Create** | `POST /sessions` | `sessionSlice.createSession()` | Complete |
| **Update** | `PATCH /sessions/{id}` | `sessionSlice.renameSession()` | Partial - Name only |
| **Delete** | `DELETE /sessions/{id}` | `sessionSlice.deleteSession()` | Complete |
| **Get Messages** | `GET /sessions/{id}/messages` | RTK Query `getSessionMessages` | Complete |
| **Add Message** | `POST /sessions/{id}/messages` | `sessionSlice.sendMessage()` | Complete |

**Gaps**:
- No cursor pagination implementation
- No sorting by created_at, updated_at, title
- No filtering by workflow_id, status
- No search by session title
- Update limited to name only (no metadata update)

### 1.2 Workflows

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **List** | `GET /workflows` | RTK Query defined but **unused** | Gap |
| **Get** | `GET /workflows/{id}` | `workflowSlice.loadWorkflow()` | Complete |
| **Create** | `POST /workflows` | RTK Query `createWorkflow` | Complete |
| **Update** | `PUT /workflows/{id}` | `workflowSlice.saveWorkflow()` | Complete |
| **Delete** | `DELETE /workflows/{id}` | RTK Query `deleteWorkflow` | Complete |
| **Execute** | `POST /workflows/{id}/execute` | `workflowSlice.executeWorkflow()` | Complete |
| **Generate Code** | `POST /workflows/generate` | WorkflowsPage direct fetch | Complete |
| **Bootstrap** | `POST /sessions/{id}/bootstrap-workflow` | SaveAsWorkflowButton | Complete |

**Gaps**:
- `useListWorkflowsQuery` hook defined but never called
- No workflow list page with pagination
- WorkflowsPage is a visual builder, not a list
- No sorting, filtering, or search for workflows

### 1.3 Projects

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **List** | `GET /projects` | ProjectsPage direct fetch | Complete |
| **Get** | `GET /projects/{id}` | ProjectDetailPage direct fetch | Complete |
| **Create** | `POST /projects` | `projectSlice.createProject()` | Complete |
| **Update** | `PUT /projects/{id}` | `projectSlice.updateProject()` | Complete |
| **Delete** | `DELETE /projects/{id}` | `projectSlice.deleteProject()` | Complete |
| **List Workflows** | `GET /projects/{id}/workflows` | ProjectDetailPage | Complete |
| **Add Workflow** | `POST /projects/{id}/workflows` | ProjectDetailPage | Complete |
| **Remove Workflow** | `DELETE /projects/{id}/workflows/{wf_id}` | **Not implemented** | Gap |
| **List Sessions** | `GET /projects/{id}/sessions` | ProjectDetailPage | Complete |
| **Add Session** | `POST /projects/{id}/sessions` | ProjectDetailPage | Complete |
| **Remove Session** | `DELETE /projects/{id}/sessions/{s_id}` | **Not implemented** | Gap |
| **List Connections** | `GET /projects/{id}/connections` | ProjectDetailPage | Complete |
| **Add Connection** | `POST /projects/{id}/connections` | **Not implemented** | Gap |
| **List Members** | `GET /projects/{id}/members` | ProjectDetailPage | Complete |
| **Add Member** | `POST /projects/{id}/members` | ProjectDetailPage | Complete |
| **Remove Member** | `DELETE /projects/{id}/members/{uid}` | ProjectDetailPage | Complete |
| **Scoped Traces** | `GET /projects/{id}/observability/traces` | ProjectDetailPage | Complete |
| **Scoped Metrics** | `GET /projects/{id}/observability/metrics` | ProjectDetailPage | Complete |
| **Scoped Logs** | `GET /projects/{id}/observability/logs` | ProjectDetailPage | Complete |
| **Scoped Alerts** | `GET /projects/{id}/observability/alerts` | ProjectDetailPage | Complete |
| **Cost Summary** | `GET /projects/{id}/cost/summary` | ProjectDetailPage | Complete |
| **Cost by Model** | `GET /projects/{id}/cost/by-model` | ProjectDetailPage | Complete |
| **Cost History** | `GET /projects/{id}/cost/history` | **Not implemented** | Gap |

**Gaps**:
- Remove workflow from project not implemented
- Remove session from project not implemented
- Add connection dialog not implemented
- Cost history for project not fetched
- No pagination despite API supporting page/per_page

### 1.4 Vectors

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **List Collections** | `GET /vectors/collections` | VectorsPage | Complete |
| **Create Collection** | `POST /vectors/collections` | VectorsPage | Complete |
| **Delete Collection** | `DELETE /vectors/collections/{name}` | VectorsPage | Complete |
| **Search** | `POST /vectors/search` | VectorsPage | Complete |
| **Upsert Points** | `POST /vectors/points` | VectorsPage | Complete |

**Status**: Full coverage

### 1.5 Cost

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **Summary** | `GET /cost/summary` | CostPage | Complete |
| **By Model** | `GET /cost/by-model` | CostPage | Complete |
| **History** | `GET /cost/history` | CostPage | Complete |

**Gaps**:
- Uses direct fetch instead of RTK Query
- No start_date/end_date params (uses preset periods only)

### 1.6 Observability

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **List Traces** | `GET /observability/traces` | ObservabilityPage | Partial |
| **Get Trace** | `GET /observability/traces/{id}` | RTK Query defined | Complete |
| **Metrics** | `GET /observability/metrics` | ObservabilityPage | Complete |
| **Logs** | `GET /observability/logs` | ObservabilityPage | Complete |

**Gaps**:
- `useListTracesQuery` RTK Query defined but not used
- No pagination for traces
- No filtering by session_id, status
- No time range filtering

### 1.7 User/Auth

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **Get Current User** | `GET /me` | App.tsx | Complete |
| **Login** | `POST /auth/login` | authSlice | Complete |
| **Refresh Token** | `POST /auth/refresh` | authSlice | Complete |
| **Switch Org** | `POST /auth/switch-org` | authSlice | Complete |

**Status**: Full coverage

### 1.8 Features

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **Get Flags** | `GET /features` | RTK Query `getFeatureFlags` | Complete |

**Status**: Full coverage

### 1.9 MCP WebSocket

| Operation | Backend Endpoint | Frontend Implementation | Status |
|-----------|------------------|------------------------|--------|
| **Connect** | `WS /mcp/ws` | useMCPConnection hook | Partial |
| **Connect with Session** | `WS /mcp/ws/{session_id}` | useMCPConnection hook | Partial |
| **List Tools** | `tools/list` | useMCPConnection | Complete |
| **Call Tool** | `tools/call` | useMCPConnection | Complete |
| **List Resources** | `resources/list` | **Not implemented** | Gap |
| **Read Resource** | `resources/read` | **Not implemented** | Gap |
| **List Prompts** | `prompts/list` | **Not implemented** | Gap |
| **Get Prompt** | `prompts/get` | **Not implemented** | Gap |
| **Streaming** | `$/streaming/*` | useStreamingChat (SSE fallback) | Partial |
| **Trace Events** | `$/trace/*` | **Not implemented** | Gap |

**Gaps**:
- Resources API not exposed
- Prompts API not exposed
- WebSocket streaming not fully utilized (falls back to SSE)
- Trace events not consumed

---

## 2. Pagination, Sorting, Filtering, Search Audit

### 2.1 API Capabilities vs Frontend Implementation

| Resource | API Pagination | Frontend Pagination | Gap Level |
|----------|----------------|---------------------|-----------|
| Sessions | cursor, limit | None | **Critical** |
| Workflows | cursor, limit | None (RTK unused) | **Critical** |
| Projects | page, per_page | None | **High** |
| Traces | cursor, limit | None | **High** |
| Messages | None | N/A | None |

| Resource | API Sorting | Frontend Sorting | Gap Level |
|----------|-------------|------------------|-----------|
| Sessions | sort_by, sort_order | Client-side only | **Critical** |
| Workflows | sort_by, sort_order | None | **Critical** |
| Projects | sort_by, sort_order | None | **Critical** |
| Traces | sort_by, sort_order | None | **High** |

| Resource | API Filtering | Frontend Filtering | Gap Level |
|----------|---------------|-------------------|-----------|
| Sessions | workflow_id, status | None | **High** |
| Workflows | status, owner_id | None | **Critical** |
| Projects | status, owner_id, organization_id | None | **High** |
| Traces | session_id | None | **High** |
| Cost | period | Implemented | None |

| Resource | API Search | Frontend Search | Gap Level |
|----------|------------|-----------------|-----------|
| Sessions | search (title) | None | **Critical** |
| Workflows | search (name, desc) | None | **Critical** |
| Projects | search (name, desc) | None | **Critical** |
| Traces | search (name) | None | **High** |

### 2.2 Detailed Gap Analysis

#### Sessions (`/api/v1/sessions`)

**Backend Supports**:
```
GET /sessions?cursor=&limit=&workflow_id=&status=&search=&sort_by=&sort_order=
```

**Frontend Implements**:
```typescript
// sessionSlice.ts line 51
fetch('/api/v1/sessions')  // NO query params
```

**Missing**:
- `cursor` - No pagination
- `limit` - No limit control
- `workflow_id` - No filtering by workflow
- `status` - No status filtering (active/archived)
- `search` - No title search
- `sort_by` - No sorting (title, created_at, updated_at)
- `sort_order` - No asc/desc control

#### Workflows (`/api/v1/workflows`)

**Backend Supports**:
```
GET /workflows?cursor=&limit=&status=&owner_id=&search=&sort_by=&sort_order=
```

**Frontend Implements**:
```typescript
// api/index.ts lines 61-76 - RTK Query defined but NEVER USED
listWorkflows: builder.query({
  query: ({ cursor, limit = 20 }) => ({
    url: '/workflows',
    params: { cursor, limit },  // Only cursor/limit, no filters
  }),
})
```

**Missing**:
- Hook is never called in any component
- No workflow list page exists
- `status` - No draft/published/archived filter
- `owner_id` - No owner filter
- `search` - No name/description search
- `sort_by` / `sort_order` - No sorting

#### Projects (`/api/v1/projects`)

**Backend Supports**:
```
GET /projects?page=&per_page=&organization_id=&status=&owner_id=&search=&sort_by=&sort_order=
```

**Frontend Implements**:
```typescript
// ProjectsPage.tsx line 57
fetch('/api/v1/projects')  // NO query params
```

**Response includes** (but ignored):
```typescript
interface ProjectListResponse {
  projects: Project[];
  total: number;    // ← Not used for pagination
  page: number;     // ← Not used
  per_page: number; // ← Not used
}
```

**Missing**:
- `page` / `per_page` - No pagination despite API support
- `organization_id` - No org filtering
- `status` - No status filtering
- `owner_id` - No owner filtering
- `search` - No search by name/description
- `sort_by` / `sort_order` - No sorting

#### Traces (`/api/v1/observability/traces`)

**Backend Supports**:
```
GET /observability/traces?cursor=&limit=&session_id=&search=&sort_by=&sort_order=
```

**Frontend Implements**:
```typescript
// ObservabilityPage.tsx line 63
fetch('/api/v1/observability/traces')  // NO query params
```

**Missing**:
- `cursor` / `limit` - No pagination
- `session_id` - No session filtering
- `search` - No trace name search
- `sort_by` / `sort_order` - No sorting by time, duration

---

## 3. API Pattern Inconsistencies

### 3.1 RTK Query vs Direct Fetch

| Resource | Expected Pattern | Actual Pattern | Issue |
|----------|------------------|----------------|-------|
| Workflows | RTK Query | Mixed (RTK + thunk) | Inconsistent |
| Sessions | RTK Query | Redux thunk only | Bypasses caching |
| Projects | RTK Query | Direct fetch | No RTK Query defined |
| Cost | RTK Query | Direct fetch | Bypasses caching |
| Traces | RTK Query | Direct fetch | RTK defined but unused |

### 3.2 Recommended Standardization

All list operations should use RTK Query with consistent patterns:
```typescript
// Recommended pattern
listResources: builder.query<
  PaginatedResponse<Resource>,
  {
    cursor?: string;
    limit?: number;
    search?: string;
    status?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  }
>({
  query: (params) => ({
    url: '/resources',
    params,
  }),
  providesTags: ['Resources'],
})
```

---

## 4. Missing Endpoints Summary

### 4.1 Completely Missing from Frontend

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `DELETE /projects/{id}/workflows/{wf_id}` | Remove workflow from project | High |
| `DELETE /projects/{id}/sessions/{s_id}` | Remove session from project | High |
| `POST /projects/{id}/connections` | Add connection to project | High |
| `GET /projects/{id}/cost/history` | Project cost history | Medium |
| `resources/list` (MCP) | List MCP resources | Medium |
| `resources/read` (MCP) | Read MCP resource | Medium |
| `prompts/list` (MCP) | List MCP prompts | Low |
| `prompts/get` (MCP) | Get MCP prompt | Low |
| `$/trace/*` (MCP) | Trace events | Low |

### 4.2 Defined but Unused

| Hook/Function | Location | Reason Unused |
|--------------|----------|---------------|
| `useListWorkflowsQuery` | api/index.ts | No workflow list page |
| `useListTracesQuery` | api/index.ts | ObservabilityPage uses fetch |
| `useGetCostSummaryQuery` | api/index.ts | CostPage uses fetch |
| `useGetCostByModelQuery` | api/index.ts | CostPage uses fetch |

---

## 5. UI Components Needed

### 5.1 Pagination Components

| Component | Purpose | Pages Affected |
|-----------|---------|----------------|
| `CursorPagination` | Cursor-based pagination controls | Sessions, Workflows, Traces |
| `PagePagination` | Page-based pagination controls | Projects |
| `LoadMoreButton` | Infinite scroll alternative | SessionPanel |

### 5.2 Filter/Sort Components

| Component | Purpose | Pages Affected |
|-----------|---------|----------------|
| `StatusFilter` | Filter by status (active/archived/draft) | All list pages |
| `OwnerFilter` | Filter by owner | Projects, Workflows |
| `SortDropdown` | Sort by field with order toggle | All list pages |
| `SearchInput` | Text search with debounce | All list pages |
| `DateRangeFilter` | Filter by date range | Cost, Traces |

---

## 6. Recommendations

### Priority 1: Critical (Immediate)

1. **Implement pagination for Sessions**
   - Add cursor/limit params to `fetchSessions` thunk
   - Create pagination UI in SessionPanel
   - Add "Load more" functionality

2. **Implement search across all resources**
   - Add SearchInput component
   - Update RTK Query endpoints with search param
   - Add debounced search to list pages

3. **Standardize on RTK Query**
   - Replace direct fetch in ProjectsPage with RTK Query
   - Replace direct fetch in CostPage with RTK Query hooks
   - Replace direct fetch in ObservabilityPage with RTK Query

### Priority 2: High

4. **Implement sorting**
   - Add SortDropdown component
   - Update all list endpoints with sort_by/sort_order
   - Default to created_at desc for most resources

5. **Implement status filtering**
   - Add StatusFilter component
   - Update endpoints with status param
   - Add filter state to URL for deep linking

6. **Complete Project child resource removal**
   - Implement DELETE /projects/{id}/workflows/{wf_id}
   - Implement DELETE /projects/{id}/sessions/{s_id}
   - Add connection dialog

### Priority 3: Medium

7. **Add workflow list page**
   - Create new page with useListWorkflowsQuery
   - Implement full pagination/sort/filter/search
   - Link from sidebar

8. **Implement MCP resources/prompts**
   - Add resources/list and resources/read to useMCPConnection
   - Create UI for browsing MCP resources

9. **Add date range filtering**
   - Add DateRangePicker component
   - Implement start_date/end_date for Cost and Traces

### Priority 4: Low

10. **Optimize with URL-based state**
    - Store pagination/sort/filter state in URL
    - Enable deep linking and browser back/forward

---

## 7. Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create reusable Pagination component
- [ ] Create reusable SearchInput component with debounce
- [ ] Create reusable SortDropdown component
- [ ] Create reusable StatusFilter component
- [ ] Write tests for all new components (TDD)

### Phase 2: Sessions & Workflows (Week 2)
- [ ] Update sessionSlice with pagination params
- [ ] Implement SessionPanel pagination
- [ ] Create WorkflowListPage with full features
- [ ] Wire up useListWorkflowsQuery
- [ ] Write integration tests

### Phase 3: Projects & Observability (Week 3)
- [ ] Create Projects RTK Query endpoints
- [ ] Replace ProjectsPage fetch with RTK Query
- [ ] Add pagination/sort/filter to ProjectsPage
- [ ] Implement missing project child operations
- [ ] Update ObservabilityPage to use RTK Query
- [ ] Write integration tests

### Phase 4: MCP & Polish (Week 4)
- [ ] Implement MCP resources API
- [ ] Implement MCP prompts API
- [ ] Add URL-based state management
- [ ] Performance optimization
- [ ] Write E2E tests

---

## 8. Test Coverage Requirements

Each new feature requires:
1. **Unit tests** for new components
2. **Integration tests** for API calls
3. **Redux tests** for state changes
4. **E2E tests** for critical user flows

Minimum coverage target: **80%** for new code

---

## Appendix A: Backend API Parameter Reference

### Sessions
```
GET /api/v1/sessions
  ?cursor=<string>          # Pagination cursor
  &limit=<1-100>            # Items per page (default: 20)
  &workflow_id=<uuid>       # Filter by workflow
  &status=<active|archived> # Filter by status
  &search=<string>          # Search in title
  &sort_by=<title|created_at|updated_at>
  &sort_order=<asc|desc>
```

### Workflows
```
GET /api/v1/workflows
  ?cursor=<string>          # Pagination cursor
  &limit=<1-100>            # Items per page (default: 20)
  &status=<draft|published|archived>
  &owner_id=<string>        # Filter by owner
  &search=<string>          # Search in name/description
  &sort_by=<name|created_at|updated_at>
  &sort_order=<asc|desc>
```

### Projects
```
GET /api/v1/projects
  ?page=<1-n>               # Page number (1-indexed)
  &per_page=<1-100>         # Items per page (default: 20)
  &organization_id=<uuid>   # Filter by organization
  &status=<active|archived> # Filter by status
  &owner_id=<string>        # Filter by owner
  &search=<string>          # Search in name/description
  &sort_by=<name|created_at|updated_at>
  &sort_order=<asc|desc>
```

### Traces
```
GET /api/v1/observability/traces
  ?cursor=<string>          # Pagination cursor
  &limit=<1-100>            # Items per page (default: 50)
  &session_id=<uuid>        # Filter by session
  &search=<string>          # Search in trace name
  &sort_by=<name|start_time|duration_ms>
  &sort_order=<asc|desc>
```

### Cost
```
GET /api/v1/cost/summary
  ?start_date=<YYYY-MM-DD>  # Start date
  &end_date=<YYYY-MM-DD>    # End date
  OR
  ?period=<day|week|month|30d>
```

---

*End of Audit Report*
