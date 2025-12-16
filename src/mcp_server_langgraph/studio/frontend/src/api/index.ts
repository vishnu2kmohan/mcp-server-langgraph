/**
 * RTK Query API
 *
 * Unified API slice for all /api/v1/* endpoints with automatic caching,
 * invalidation, and real-time updates.
 */

import { createApi } from "@reduxjs/toolkit/query/react";

import { baseQueryWithReauth } from "./baseQueryWithReauth";

// Import types from centralized location
import type {
  Workflow,
  WorkflowSummary,
  Session,
  Message,
  FeatureFlags,
  CostSummary,
  ModelCostData,
  TraceSpan,
  TraceDetail,
  TraceListItem,
  LogEntry,
  ObservabilityMetrics,
  PaginatedResponse,
  PagePaginatedResponse,
  ChatCompletionRequest,
  ChatCompletionResponse,
  Project,
  ProjectDetail,
  WorkflowListParams,
  SessionListParams,
  TraceListParams,
  LogListParams,
  ProjectListParams,
  CostHistoryParams,
  CostHistoryPoint,
  VectorCollection,
  VectorSearchRequest,
  VectorSearchResult,
  VectorUpsertRequest,
  VectorCreateCollectionRequest,
  VectorTextSearchRequest,
  VectorTextUpsertRequest,
  VectorTextUpsertResponse,
  AgentConfig,
  AuditLogEntry,
  AuditLogListParams,
  HealthStatus,
  HEARTAggregateMetrics,
  BootstrapWorkflowResponse,
  WorkflowSharesResponse,
  AddWorkflowShareRequest,
  RemoveWorkflowShareRequest,
  UpdateWorkflowPublicRequest,
  GenerateWorkflowCodeRequest,
  GenerateWorkflowCodeResponse,
  // Project-scoped types
  ProjectObservabilityResponse,
  ProjectLogsResponse,
  ProjectAlertsResponse,
  ProjectCostSummaryResponse,
  ProjectModelCost,
  AddProjectMemberRequest,
  RemoveProjectMemberRequest,
  AddProjectConnectionRequest,
  // AI Suggestions
  SuggestionRequest,
  AISuggestion,
  SuggestionsResponse,
  // Node Config Assistant
  NodeConfigHelpRequest,
  NodeConfigHelpResponse,
  // Feedback
  FeedbackRequest,
  FeedbackResponse,
  // Admin User Management
  AdminUser,
  AdminUserListParams,
  AdminUserListResponse,
  CreateAdminUserRequest,
  UpdateAdminUserRequest,
  // Workflow Executions
  WorkflowExecution,
  WorkflowExecutionListParams,
  WorkflowExecutionListResponse,
} from "../types/api";
import type {
  MCPConnection,
  MCPConnectionCreate,
  MCPConnectionUpdate,
  MCPConnectionTestResult,
  OAuth2StartResponse,
  ConnectionListResponse,
  ConnectionFilterOptions,
} from "../types/connection";

// Re-export types for backward compatibility
export type {
  Workflow,
  WorkflowSummary,
  Session,
  Message,
  FeatureFlags,
  CostSummary,
  ModelCostData,
  TraceSpan,
  TraceDetail,
  TraceListItem,
  LogEntry,
  ObservabilityMetrics,
  PaginatedResponse,
  PagePaginatedResponse,
  ChatCompletionRequest,
  ChatCompletionResponse,
  Project,
  ProjectDetail,
  WorkflowListParams,
  SessionListParams,
  TraceListParams,
  LogListParams,
  ProjectListParams,
  CostHistoryParams,
  CostHistoryPoint,
  VectorCollection,
  VectorSearchRequest,
  VectorSearchResult,
  VectorUpsertRequest,
  VectorCreateCollectionRequest,
  VectorTextSearchRequest,
  VectorTextUpsertRequest,
  VectorTextUpsertResponse,
  AgentConfig,
  AuditLogEntry,
  AuditLogListParams,
  HealthStatus,
  HEARTAggregateMetrics,
  // AI Suggestions
  SuggestionRequest,
  AISuggestion,
  SuggestionsResponse,
  // Node Config Assistant
  NodeConfigHelpRequest,
  NodeConfigHelpResponse,
  // Admin User Management
  AdminUser,
  AdminUserListParams,
  AdminUserListResponse,
  CreateAdminUserRequest,
  UpdateAdminUserRequest,
  // Workflow Executions
  WorkflowExecution,
  WorkflowExecutionListParams,
  WorkflowExecutionListResponse,
};

/**
 * Helper to filter undefined values from params object
 */
function filterParams<T extends Record<string, unknown>>(
  params: T,
): Record<string, string | number> {
  const result: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      result[key] = value as string | number;
    }
  }
  return result;
}

/**
 * Convert period string to date range
 * @param period - 'day', 'week', 'month', or '30d' format
 * @returns { start_date, end_date } in YYYY-MM-DD format
 */
function periodToDateRange(period: string): {
  start_date: string;
  end_date: string;
} {
  const now = new Date();
  const end_date = now.toISOString().split("T")[0];

  let daysBack = 30; // default
  if (period === "day") {
    daysBack = 1;
  } else if (period === "week") {
    daysBack = 7;
  } else if (period === "month") {
    daysBack = 30;
  } else if (period.endsWith("d")) {
    daysBack = parseInt(period.slice(0, -1), 10) || 30;
  }

  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - daysBack);
  const start_date = startDate.toISOString().split("T")[0];

  return { start_date, end_date };
}

// API Definition
// Uses baseQueryWithReauth for automatic 401 handling and token refresh
export const api = createApi({
  reducerPath: "api",
  baseQuery: baseQueryWithReauth,
  tagTypes: [
    "Workflow",
    "Session",
    "Message",
    "Cost",
    "Trace",
    "FeatureFlags",
    "Project",
    "Connection",
    "Vector",
    "Agent",
    "AuditLog",
    "AdminUser",
    "Execution",
  ],
  endpoints: (builder) => ({
    // Feature Flags
    getFeatureFlags: builder.query<FeatureFlags, void>({
      query: () => "/features",
      providesTags: ["FeatureFlags"],
    }),

    // Workflows
    listWorkflows: builder.query<
      PaginatedResponse<WorkflowSummary>,
      WorkflowListParams
    >({
      query: (params) => ({
        url: "/workflows",
        params: filterParams({
          cursor: params.cursor,
          limit: params.limit ?? 20,
          search: params.search,
          sort_by: params.sort_by,
          sort_order: params.sort_order,
          status: params.status,
          owner_id: params.owner_id,
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ id }) => ({
                type: "Workflow" as const,
                id,
              })),
              { type: "Workflow", id: "LIST" },
            ]
          : [{ type: "Workflow", id: "LIST" }],
    }),

    getWorkflow: builder.query<Workflow, string>({
      query: (id) => `/workflows/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Workflow", id }],
    }),

    createWorkflow: builder.mutation<
      Workflow,
      {
        name: string;
        description?: string;
        nodes?: unknown[];
        edges?: unknown[];
      }
    >({
      query: (body) => ({
        url: "/workflows",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "Workflow", id: "LIST" }],
    }),

    updateWorkflow: builder.mutation<
      Workflow,
      {
        id: string;
        name?: string;
        description?: string;
        nodes?: unknown[];
        edges?: unknown[];
      }
    >({
      query: ({ id, ...body }) => ({
        url: `/workflows/${id}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: "Workflow", id },
        { type: "Workflow", id: "LIST" },
      ],
    }),

    deleteWorkflow: builder.mutation<void, string>({
      query: (id) => ({
        url: `/workflows/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: "Workflow", id },
        { type: "Workflow", id: "LIST" },
      ],
    }),

    // Bootstrap workflow from session
    bootstrapWorkflow: builder.mutation<BootstrapWorkflowResponse, string>({
      query: (sessionId) => ({
        url: `/sessions/${sessionId}/bootstrap-workflow`,
        method: "POST",
      }),
      invalidatesTags: [{ type: "Workflow", id: "LIST" }],
    }),

    // Workflow Sharing
    getWorkflowShares: builder.query<WorkflowSharesResponse, string>({
      query: (workflowId) => `/workflows/${workflowId}/shares`,
      providesTags: (_result, _error, workflowId) => [
        { type: "Workflow", id: `SHARES-${workflowId}` },
      ],
    }),

    addWorkflowShare: builder.mutation<void, AddWorkflowShareRequest>({
      query: ({ workflow_id, ...body }) => ({
        url: `/workflows/${workflow_id}/shares`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { workflow_id }) => [
        { type: "Workflow", id: `SHARES-${workflow_id}` },
      ],
    }),

    removeWorkflowShare: builder.mutation<void, RemoveWorkflowShareRequest>({
      query: ({ workflow_id, user_id }) => ({
        url: `/workflows/${workflow_id}/shares/${user_id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { workflow_id }) => [
        { type: "Workflow", id: `SHARES-${workflow_id}` },
      ],
    }),

    updateWorkflowPublic: builder.mutation<void, UpdateWorkflowPublicRequest>({
      query: ({ workflow_id, is_public }) => ({
        url: `/workflows/${workflow_id}/public`,
        method: "PUT",
        body: { is_public },
      }),
      invalidatesTags: (_result, _error, { workflow_id }) => [
        { type: "Workflow", id: `SHARES-${workflow_id}` },
      ],
    }),

    // Workflow Code Generation
    generateWorkflowCode: builder.mutation<
      GenerateWorkflowCodeResponse,
      GenerateWorkflowCodeRequest
    >({
      query: ({ workflow_id, language }) => ({
        url: "/workflows/generate",
        method: "POST",
        body: { workflow_id, language },
      }),
    }),

    // Shared Workflows (read-only access for standard users)
    getSharedWorkflows: builder.query<WorkflowSummary[], void>({
      query: () => "/workflows/shared-with-me",
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({ type: "Workflow" as const, id })),
              { type: "Workflow", id: "SHARED" },
            ]
          : [{ type: "Workflow", id: "SHARED" }],
    }),

    // Sessions
    listSessions: builder.query<PaginatedResponse<Session>, SessionListParams>({
      query: (params) => ({
        url: "/sessions",
        params: filterParams({
          cursor: params.cursor,
          limit: params.limit ?? 20,
          workflow_id: params.workflow_id,
          status: params.status,
          search: params.search,
          sort_by: params.sort_by,
          sort_order: params.sort_order,
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ session_id }) => ({
                type: "Session" as const,
                id: session_id,
              })),
              { type: "Session", id: "LIST" },
            ]
          : [{ type: "Session", id: "LIST" }],
    }),

    getSession: builder.query<Session, string>({
      query: (id) => `/sessions/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Session", id }],
    }),

    createSession: builder.mutation<
      Session,
      { name: string; workflow_id?: string }
    >({
      query: (body) => ({
        url: "/sessions",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "Session", id: "LIST" }],
    }),

    deleteSession: builder.mutation<void, string>({
      query: (id) => ({
        url: `/sessions/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: "Session", id },
        { type: "Session", id: "LIST" },
      ],
    }),

    // Messages
    getSessionMessages: builder.query<Message[], string>({
      query: (sessionId) => `/sessions/${sessionId}/messages`,
      providesTags: (_result, _error, sessionId) => [
        { type: "Message", id: `SESSION-${sessionId}` },
      ],
    }),

    // Chat
    sendChatMessage: builder.mutation<
      ChatCompletionResponse,
      ChatCompletionRequest
    >({
      query: (body) => ({
        url: "/chat/completions",
        method: "POST",
        body,
      }),
      invalidatesTags: (result) =>
        result?.session_id
          ? [{ type: "Message", id: `SESSION-${result.session_id}` }]
          : [],
    }),

    // Cost
    getCostSummary: builder.query<CostSummary, { period?: string }>({
      query: ({ period = "30d" }) => {
        const { start_date, end_date } = periodToDateRange(period);
        return {
          url: "/cost/summary",
          params: filterParams({ start_date, end_date }),
        };
      },
      providesTags: ["Cost"],
    }),

    getCostByModel: builder.query<ModelCostData[], { period?: string }>({
      query: ({ period = "30d" }) => {
        const { start_date, end_date } = periodToDateRange(period);
        return {
          url: "/cost/by-model",
          params: filterParams({ start_date, end_date }),
        };
      },
      providesTags: ["Cost"],
    }),

    // Observability
    listTraces: builder.query<
      PaginatedResponse<TraceListItem>,
      TraceListParams
    >({
      query: (params) => ({
        url: "/observability/traces",
        params: filterParams({
          cursor: params.cursor,
          limit: params.limit ?? 50,
          session_id: params.session_id,
          status: params.status,
          search: params.search,
          sort_by: params.sort_by,
          sort_order: params.sort_order,
          start_time: params.start_time,
          end_time: params.end_time,
        }),
      }),
      providesTags: ["Trace"],
    }),

    getTrace: builder.query<TraceDetail, string>({
      query: (id) => `/observability/traces/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Trace", id }],
    }),

    listLogs: builder.query<PaginatedResponse<LogEntry>, LogListParams>({
      query: (params) => ({
        url: "/observability/logs",
        params: filterParams({
          cursor: params.cursor,
          limit: params.limit ?? 50,
          level: params.level,
          service: params.service,
          search: params.search,
          sort_by: params.sort_by,
          sort_order: params.sort_order,
          start_time: params.start_time,
          end_time: params.end_time,
        }),
      }),
      providesTags: ["Trace"], // Using Trace tag for now, could add 'Log' tag
    }),

    getMetrics: builder.query<ObservabilityMetrics, void>({
      query: () => "/observability/metrics",
      providesTags: ["Trace"], // Metrics are related to traces
    }),

    // Projects
    listProjects: builder.query<
      PagePaginatedResponse<Project>,
      ProjectListParams
    >({
      query: (params) => ({
        url: "/projects",
        params: filterParams({
          page: params.page ?? 1,
          per_page: params.per_page ?? 20,
          search: params.search,
          sort_by: params.sort_by,
          sort_order: params.sort_order,
          status: params.status,
          organization_id: params.organization_id,
          owner_id: params.owner_id,
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ id }) => ({
                type: "Project" as const,
                id,
              })),
              { type: "Project", id: "LIST" },
            ]
          : [{ type: "Project", id: "LIST" }],
    }),

    getProject: builder.query<ProjectDetail, string>({
      query: (id) => `/projects/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Project", id }],
    }),

    createProject: builder.mutation<
      Project,
      { name: string; description?: string; organization_id?: string }
    >({
      query: (body) => ({
        url: "/projects",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "Project", id: "LIST" }],
    }),

    updateProject: builder.mutation<
      Project,
      { id: string; name?: string; description?: string; status?: string }
    >({
      query: ({ id, ...body }) => ({
        url: `/projects/${id}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: "Project", id },
        { type: "Project", id: "LIST" },
      ],
    }),

    deleteProject: builder.mutation<void, string>({
      query: (id) => ({
        url: `/projects/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: "Project", id },
        { type: "Project", id: "LIST" },
      ],
    }),

    // Project-scoped Observability
    getProjectObservability: builder.query<
      ProjectObservabilityResponse,
      string
    >({
      async queryFn(projectId, _queryApi, _extraOptions, fetchWithBQ) {
        try {
          const [tracesResult, metricsResult] = await Promise.all([
            fetchWithBQ(`/projects/${projectId}/observability/traces`),
            fetchWithBQ(`/projects/${projectId}/observability/metrics`),
          ]);

          if (tracesResult.error) return { error: tracesResult.error };
          if (metricsResult.error) return { error: metricsResult.error };

          const traces = tracesResult.data as { total?: number };
          const metrics = metricsResult.data as {
            requests_total?: number;
            errors_total?: number;
            avg_latency_ms?: number;
          };

          return {
            data: {
              traceCount: traces.total || 0,
              requestsTotal: metrics.requests_total || 0,
              errorsTotal: metrics.errors_total || 0,
              avgLatencyMs: metrics.avg_latency_ms || 0,
            },
          };
        } catch (error) {
          return { error: { status: "CUSTOM_ERROR", error: String(error) } };
        }
      },
      providesTags: (_result, _error, projectId) => [
        { type: "Project", id: `OBSERVABILITY-${projectId}` },
      ],
    }),

    getProjectLogs: builder.query<ProjectLogsResponse, string>({
      query: (projectId) => `/projects/${projectId}/observability/logs`,
      transformResponse: (response: { logs?: LogEntry[]; total?: number }) => ({
        logs: response.logs || [],
        total: response.total || 0,
      }),
      providesTags: (_result, _error, projectId) => [
        { type: "Project", id: `LOGS-${projectId}` },
      ],
    }),

    getProjectAlerts: builder.query<ProjectAlertsResponse, string>({
      query: (projectId) => `/projects/${projectId}/observability/alerts`,
      transformResponse: (response: {
        alerts?: Array<{
          id: string;
          severity: string;
          message: string;
          created_at: string;
        }>;
        total?: number;
      }) => ({
        alerts: (response.alerts || []).map((a) => ({
          id: a.id,
          severity: a.severity as "info" | "warning" | "critical",
          message: a.message,
          created_at: a.created_at,
        })),
        total: response.total || 0,
      }),
      providesTags: (_result, _error, projectId) => [
        { type: "Project", id: `ALERTS-${projectId}` },
      ],
    }),

    // Project-scoped Cost
    getProjectCostSummary: builder.query<ProjectCostSummaryResponse, string>({
      query: (projectId) => `/projects/${projectId}/cost/summary`,
      transformResponse: (response: {
        total_cost?: number;
        prompt_tokens?: number;
        completion_tokens?: number;
        session_count?: number;
      }) => ({
        total_cost: response.total_cost || 0,
        prompt_tokens: response.prompt_tokens || 0,
        completion_tokens: response.completion_tokens || 0,
        session_count: response.session_count || 0,
      }),
      providesTags: (_result, _error, projectId) => [
        { type: "Project", id: `COST-${projectId}` },
      ],
    }),

    getProjectCostByModel: builder.query<ProjectModelCost[], string>({
      query: (projectId) => `/projects/${projectId}/cost/by-model`,
      transformResponse: (response: { models?: ProjectModelCost[] }) =>
        response.models || [],
      providesTags: (_result, _error, projectId) => [
        { type: "Project", id: `COST-${projectId}` },
      ],
    }),

    // Project Members
    addProjectMember: builder.mutation<void, AddProjectMemberRequest>({
      query: ({ project_id, ...body }) => ({
        url: `/projects/${project_id}/members`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { project_id }) => [
        { type: "Project", id: project_id },
      ],
    }),

    removeProjectMember: builder.mutation<void, RemoveProjectMemberRequest>({
      query: ({ project_id, user_id }) => ({
        url: `/projects/${project_id}/members/${user_id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { project_id }) => [
        { type: "Project", id: project_id },
      ],
    }),

    // Project Connections
    addProjectConnection: builder.mutation<void, AddProjectConnectionRequest>({
      query: ({
        project_id,
        connection_type,
        connection_id,
        connection_name,
      }) => ({
        url: `/projects/${project_id}/connections`,
        method: "POST",
        params: {
          connection_type,
          connection_id,
          connection_name,
        },
      }),
      invalidatesTags: (_result, _error, { project_id }) => [
        { type: "Project", id: project_id },
      ],
    }),

    // Cost History - returns array of daily cost data
    getCostHistory: builder.query<CostHistoryPoint[], { period?: string }>({
      query: ({ period = "30d" }) => {
        const { start_date, end_date } = periodToDateRange(period);
        return {
          url: "/cost/history",
          params: filterParams({ start_date, end_date }),
        };
      },
      providesTags: ["Cost"],
    }),

    // Connections
    listConnections: builder.query<
      ConnectionListResponse,
      ConnectionFilterOptions | void
    >({
      query: (params = {}) => ({
        url: "/connections",
        params: filterParams({
          status: params?.status,
          auth_type: params?.auth_type,
          project_id: params?.project_id,
          search: params?.search,
          cursor: params?.cursor,
          limit: params?.limit ?? 20,
          sort_by: params?.sort_by ?? "created_at",
          sort_order: params?.sort_order ?? "desc",
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ id }) => ({
                type: "Connection" as const,
                id,
              })),
              { type: "Connection", id: "LIST" },
            ]
          : [{ type: "Connection", id: "LIST" }],
    }),

    getConnection: builder.query<MCPConnection, string>({
      query: (id) => `/connections/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Connection", id }],
    }),

    createConnection: builder.mutation<MCPConnection, MCPConnectionCreate>({
      query: (body) => ({
        url: "/connections",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "Connection", id: "LIST" }],
    }),

    updateConnection: builder.mutation<
      MCPConnection,
      { id: string } & MCPConnectionUpdate
    >({
      query: ({ id, ...body }) => ({
        url: `/connections/${id}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: "Connection", id },
        { type: "Connection", id: "LIST" },
      ],
    }),

    deleteConnection: builder.mutation<void, string>({
      query: (id) => ({
        url: `/connections/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: "Connection", id },
        { type: "Connection", id: "LIST" },
      ],
    }),

    testConnection: builder.mutation<MCPConnectionTestResult, string>({
      query: (id) => ({
        url: `/connections/${id}/test`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, id) => [{ type: "Connection", id }],
    }),

    startOAuth2Flow: builder.mutation<OAuth2StartResponse, string>({
      query: (id) => ({
        url: `/connections/${id}/oauth2/start`,
        method: "POST",
      }),
    }),

    // Vectors (Qdrant Proxy)
    listVectorCollections: builder.query<VectorCollection[], void>({
      query: () => "/vectors/collections",
      transformResponse: (response: { collections: VectorCollection[] }) =>
        response.collections,
      providesTags: ["Vector"],
    }),

    createVectorCollection: builder.mutation<
      void,
      VectorCreateCollectionRequest
    >({
      query: (body) => ({
        url: "/vectors/collections",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Vector"],
    }),

    deleteVectorCollection: builder.mutation<void, string>({
      query: (name) => ({
        url: `/vectors/collections/${name}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Vector"],
    }),

    searchVectors: builder.mutation<VectorSearchResult[], VectorSearchRequest>({
      query: (body) => ({
        url: "/vectors/search",
        method: "POST",
        body,
      }),
    }),

    upsertVectorPoints: builder.mutation<void, VectorUpsertRequest>({
      query: (body) => ({
        url: "/vectors/points",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Vector"],
    }),

    searchVectorsText: builder.mutation<
      VectorSearchResult[],
      VectorTextSearchRequest
    >({
      query: (body) => ({
        url: "/vectors/search-text",
        method: "POST",
        body,
      }),
    }),

    upsertVectorText: builder.mutation<
      VectorTextUpsertResponse,
      VectorTextUpsertRequest
    >({
      query: (body) => ({
        url: "/vectors/upsert-text",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Vector"],
    }),

    // Agents
    getAgentConfig: builder.query<AgentConfig, void>({
      query: () => "/agents/config",
      providesTags: ["Agent"],
    }),

    // Audit Logs (Admin)
    listAuditLogs: builder.query<
      PaginatedResponse<AuditLogEntry>,
      AuditLogListParams
    >({
      query: (params) => ({
        url: "/admin/audit-logs",
        params: filterParams({
          cursor: params.cursor,
          limit: params.limit ?? 50,
          user_id: params.user_id,
          action: params.action,
          resource_type: params.resource_type,
          start_time: params.start_time,
          end_time: params.end_time,
          sort_by: params.sort_by,
          sort_order: params.sort_order,
        }),
      }),
      providesTags: ["AuditLog"],
    }),

    // Admin Users (Admin)
    listAdminUsers: builder.query<AdminUserListResponse, AdminUserListParams>({
      query: (params) => ({
        url: "/admin/users",
        params: filterParams({
          search: params.search,
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ user_id }) => ({
                type: "AdminUser" as const,
                id: user_id,
              })),
              { type: "AdminUser", id: "LIST" },
            ]
          : [{ type: "AdminUser", id: "LIST" }],
    }),

    getAdminUser: builder.query<AdminUser, string>({
      query: (userId) => `/admin/users/${userId}`,
      providesTags: (_result, _error, userId) => [
        { type: "AdminUser", id: userId },
      ],
    }),

    createAdminUser: builder.mutation<AdminUser, CreateAdminUserRequest>({
      query: (body) => ({
        url: "/admin/users",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "AdminUser", id: "LIST" }],
    }),

    updateAdminUser: builder.mutation<AdminUser, UpdateAdminUserRequest>({
      query: ({ user_id, ...body }) => ({
        url: `/admin/users/${user_id}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: (_result, _error, { user_id }) => [
        { type: "AdminUser", id: user_id },
        { type: "AdminUser", id: "LIST" },
      ],
    }),

    deleteAdminUser: builder.mutation<void, string>({
      query: (userId) => ({
        url: `/admin/users/${userId}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, userId) => [
        { type: "AdminUser", id: userId },
        { type: "AdminUser", id: "LIST" },
      ],
    }),

    // Workflow Executions
    listWorkflowExecutions: builder.query<
      WorkflowExecutionListResponse,
      WorkflowExecutionListParams
    >({
      query: (params) => ({
        url: `/workflows/${params.workflow_id}/executions`,
        params: filterParams({
          status: params.status,
          limit: params.limit ?? 50,
          cursor: params.cursor,
        }),
      }),
      providesTags: (result, _error, params) =>
        result?.items
          ? [
              ...result.items.map(({ id }) => ({
                type: "Execution" as const,
                id,
              })),
              { type: "Execution", id: `WORKFLOW-${params.workflow_id}` },
            ]
          : [{ type: "Execution", id: `WORKFLOW-${params.workflow_id}` }],
    }),

    getWorkflowExecution: builder.query<
      WorkflowExecution,
      { workflow_id: string; execution_id: string }
    >({
      query: ({ workflow_id, execution_id }) =>
        `/workflows/${workflow_id}/executions/${execution_id}`,
      providesTags: (_result, _error, { execution_id }) => [
        { type: "Execution", id: execution_id },
      ],
    }),

    // Health
    getHealth: builder.query<HealthStatus, void>({
      query: () => "/health",
    }),

    // HEART Metrics
    getHeartMetrics: builder.query<
      HEARTAggregateMetrics,
      { period?: string; app?: string }
    >({
      query: (params = {}) => ({
        url: "/metrics/heart/aggregate",
        params: filterParams({
          period: params.period ?? "7d",
          app: params.app,
        }),
      }),
    }),

    // Workflow Templates
    getWorkflowTemplates: builder.query<
      {
        id: string;
        name: string;
        description: string;
        category: string;
        tags: string[];
      }[],
      void
    >({
      query: () => "/studio/templates",
    }),

    // AI Suggestions
    getWorkflowSuggestions: builder.mutation<
      SuggestionsResponse,
      SuggestionRequest
    >({
      query: (body) => ({
        url: "/studio/suggestions",
        method: "POST",
        body,
      }),
    }),

    // Node Config Assistant
    getNodeConfigHelp: builder.mutation<
      NodeConfigHelpResponse,
      NodeConfigHelpRequest
    >({
      query: (body) => ({
        url: "/ai/node-config/help",
        method: "POST",
        body,
      }),
    }),

    // Current User Info (for persona detection)
    getCurrentUser: builder.query<
      {
        username: string;
        email?: string;
        roles: string[];
        persona: "admin" | "developer" | "user";
      },
      void
    >({
      query: () => "/me",
    }),

    // Native Login (ROPC grant - no Keycloak UI redirect)
    login: builder.mutation<
      {
        access_token: string;
        refresh_token?: string;
        token_type: string;
        expires_in: number;
        user: {
          user_id: string;
          username: string;
          email?: string;
          roles: string[];
          persona: "admin" | "developer" | "user";
          keycloak_id?: string;
        };
      },
      { username: string; password: string }
    >({
      query: (credentials) => ({
        url: "/login",
        method: "POST",
        body: credentials,
      }),
    }),

    // Native Logout (token revocation - no Keycloak UI redirect)
    logout: builder.mutation<
      { success: boolean; message: string; keycloak_logout_url?: string },
      { refresh_token?: string } | void
    >({
      query: (body) => ({
        url: "/logout",
        method: "POST",
        body: body || {},
      }),
    }),

    // Identity Provider Discovery (SSO IdPs for login page)
    getIdentityProviders: builder.query<
      {
        identity_providers: Array<{
          alias: string;
          display_name: string;
          provider_type: "social" | "enterprise";
          provider_id: string;
          icon: string;
          login_url: string;
        }>;
        has_social_login: boolean;
        has_enterprise_sso: boolean;
        error?: string;
      },
      void
    >({
      query: () => "/identity-providers",
    }),

    // Feedback Submission (NPS/CSAT)
    submitFeedback: builder.mutation<FeedbackResponse, FeedbackRequest>({
      query: (body) => ({
        url: "/metrics/feedback",
        method: "POST",
        body,
      }),
    }),
  }),
});

// Export hooks for usage in components
export const {
  // Feature Flags
  useGetFeatureFlagsQuery,
  // Workflows
  useListWorkflowsQuery,
  useGetWorkflowQuery,
  useCreateWorkflowMutation,
  useUpdateWorkflowMutation,
  useDeleteWorkflowMutation,
  useBootstrapWorkflowMutation,
  useGetWorkflowSharesQuery,
  useAddWorkflowShareMutation,
  useRemoveWorkflowShareMutation,
  useUpdateWorkflowPublicMutation,
  useGenerateWorkflowCodeMutation,
  useGetSharedWorkflowsQuery,
  // Sessions
  useListSessionsQuery,
  useGetSessionQuery,
  useCreateSessionMutation,
  useDeleteSessionMutation,
  // Messages
  useGetSessionMessagesQuery,
  // Chat
  useSendChatMessageMutation,
  // Cost
  useGetCostSummaryQuery,
  useGetCostByModelQuery,
  useGetCostHistoryQuery,
  // Observability
  useListTracesQuery,
  useGetTraceQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  // Projects
  useListProjectsQuery,
  useGetProjectQuery,
  useCreateProjectMutation,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
  // Project-scoped Observability
  useGetProjectObservabilityQuery,
  useGetProjectLogsQuery,
  useGetProjectAlertsQuery,
  // Project-scoped Cost
  useGetProjectCostSummaryQuery,
  useGetProjectCostByModelQuery,
  // Project Members
  useAddProjectMemberMutation,
  useRemoveProjectMemberMutation,
  // Project Connections
  useAddProjectConnectionMutation,
  // Connections
  useListConnectionsQuery,
  useGetConnectionQuery,
  useCreateConnectionMutation,
  useUpdateConnectionMutation,
  useDeleteConnectionMutation,
  useTestConnectionMutation,
  useStartOAuth2FlowMutation,
  // Vectors
  useListVectorCollectionsQuery,
  useCreateVectorCollectionMutation,
  useDeleteVectorCollectionMutation,
  useSearchVectorsMutation,
  useUpsertVectorPointsMutation,
  useSearchVectorsTextMutation,
  useUpsertVectorTextMutation,
  // Agents
  useGetAgentConfigQuery,
  // Audit Logs
  useListAuditLogsQuery,
  // Admin Users
  useListAdminUsersQuery,
  useGetAdminUserQuery,
  useCreateAdminUserMutation,
  useUpdateAdminUserMutation,
  useDeleteAdminUserMutation,
  // Workflow Executions
  useListWorkflowExecutionsQuery,
  useGetWorkflowExecutionQuery,
  // Health & Metrics
  useGetHealthQuery,
  useGetHeartMetricsQuery,
  // Workflow Templates
  useGetWorkflowTemplatesQuery,
  // AI Suggestions
  useGetWorkflowSuggestionsMutation,
  // Node Config Assistant
  useGetNodeConfigHelpMutation,
  // User Info
  useGetCurrentUserQuery,
  // Auth (Native Login/Logout)
  useLoginMutation,
  useLogoutMutation,
  useGetIdentityProvidersQuery,
  // Feedback
  useSubmitFeedbackMutation,
} = api;
