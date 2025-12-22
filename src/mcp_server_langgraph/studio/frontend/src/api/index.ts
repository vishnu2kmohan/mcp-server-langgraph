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
  SessionConfigUpdateRequest,
  Message,
  FeatureFlags,
  CostSummary,
  ModelCostData,
  TraceSpan,
  TraceDetail,
  TraceListItem,
  LogEntry,
  ObservabilityMetrics,
  ObservabilityAlert,
  ObservabilityAlertRule,
  AlertListParams,
  AlertRulesListParams,
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
  // AI Suggestions (legacy - deprecated)
  SuggestionRequest,
  AISuggestion,
  SuggestionsResponse,
  // Unified AI Suggestions (new endpoint)
  UnifiedSuggestionsRequest,
  UnifiedSuggestionsResponse,
  ChatFollowUpSuggestion,
  // Suggestion Analytics
  SuggestionClickRequest,
  SuggestionClickResponse,
  SuggestionFeedbackRequest,
  SuggestionFeedbackResponse,
  // Node Config Assistant
  NodeConfigHelpRequest,
  NodeConfigHelpResponse,
  // Feedback
  FeedbackRequest,
  FeedbackResponse,
  // Message Rating
  MessageRatingRequest,
  MessageRatingResponse,
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
  // Notification Preferences
  NotificationPreferences,
  UpdateNotificationPreferencesRequest,
  // User Preferences
  UserPreferences,
  UserPreferencesUpdate,
  // Session Export
  SessionExportRequest,
  ExportFormat,
  // Infrastructure Alerts & Remediations
  AIRecommendation,
  RemediationRequest,
  RemediationListParams,
  ApproveRemediationRequest,
  RejectRemediationRequest,
  // Agent HITL Requests
  PendingAgentRequestsResponse,
  AgentRequestActionResponse,
  ApproveAgentRequestParams,
  RejectAgentRequestParams,
  RespondAgentRequestParams,
  BatchApproveAgentRequestParams,
  BatchRejectAgentRequestParams,
  BatchAgentRequestResponse,
  ListPendingAgentRequestsParams,
  // MCP Protocol Types
  McpResourceListResponse,
  McpResourceContentResponse,
  McpReadResourceRequest,
  McpToolListResponse,
  McpInvokeToolRequest,
  McpToolInvocationResponse,
  McpSamplingRequest,
  McpSamplingResponse,
  McpElicitationRequest,
  McpElicitationResponse,
  McpPromptListResponse,
  McpGetPromptRequest,
  McpGetPromptResponse,
  McpTaskListResponse,
  McpTask,
} from "../types/api";
import type {
  CanvasArtifact,
  ArtifactVersion,
  CreateArtifactRequest,
  CreateArtifactResponse,
  UpdateArtifactRequest,
  UpdateArtifactResponse,
  ForkArtifactResponse,
  ListArtifactsResponse,
} from "../types/artifacts";
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
  ObservabilityAlert,
  ObservabilityAlertRule,
  AlertListParams,
  AlertRulesListParams,
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
  // User Preferences
  UserPreferences,
  UserPreferencesUpdate,
  // Session Export
  SessionExportRequest,
  ExportFormat,
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
  const end_date = now.toISOString().split("T")[0] ?? "";

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
  const start_date = startDate.toISOString().split("T")[0] ?? "";

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
    "Alert",
    "AlertRule",
    "FeatureFlags",
    "Project",
    "Connection",
    "Vector",
    "Agent",
    "AuditLog",
    "AdminUser",
    "Execution",
    "NotificationPreferences",
    "Survey",
    "Analytics",
    "ComplianceReport",
    "ConnectionTemplate",
    "ConnectionAudit",
    "UserPreferences",
    "InfraAlert",
    "Remediation",
    "Artifact",
    "AgentRequest",
    "AIUx",
    "Mcp",
  ],
  endpoints: (builder) => ({
    // Feature Flags
    getFeatureFlags: builder.query<FeatureFlags, void>({
      query: () => "/features",
      providesTags: ["FeatureFlags"],
      keepUnusedDataFor: 600, // 10 minutes - feature flags rarely change
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
              ...result.items.map(({ id }) => ({
                type: "Session" as const,
                id,
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

    generateSessionTitle: builder.mutation<
      { title: string },
      { message: string }
    >({
      query: (body) => ({
        url: "/sessions/generate-title",
        method: "POST",
        body,
      }),
    }),

    // Update session configuration (model, temperature, max_tokens)
    updateSessionConfig: builder.mutation<Session, SessionConfigUpdateRequest>({
      query: ({ session_id, ...body }) => ({
        url: `/sessions/${session_id}/config`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: (_result, _error, { session_id }) => [
        { type: "Session", id: session_id },
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
          user_id: params.user_id,
          workflow_id: params.workflow_id,
          project_id: params.project_id,
          organization_id: params.organization_id,
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

    // Alerts (LGTM Stack - Grafana Unified Alerting)
    listAlerts: builder.query<
      PaginatedResponse<ObservabilityAlert>,
      AlertListParams
    >({
      query: (params) => ({
        url: "/observability/alerts",
        params: filterParams({
          state: params.state,
          severity: params.severity,
          service_name: params.service_name,
          limit: params.limit ?? 100,
        }),
      }),
      providesTags: ["Alert"],
    }),

    getAlert: builder.query<ObservabilityAlert, string>({
      query: (id) => `/observability/alerts/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Alert", id }],
    }),

    listAlertRules: builder.query<
      ObservabilityAlertRule[],
      AlertRulesListParams
    >({
      query: (params) => ({
        url: "/observability/alerts/rules",
        params: filterParams({
          enabled_only: params?.enabled_only ?? true,
          limit: params?.limit ?? 100,
        }),
      }),
      providesTags: ["AlertRule"],
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
        url: `/connections/${id}/oauth/start`,
        method: "POST",
      }),
    }),

    // Vectors (Qdrant Proxy)
    listVectorCollections: builder.query<VectorCollection[], void>({
      query: () => "/vectors/collections",
      transformResponse: (response: { collections: VectorCollection[] }) =>
        response.collections,
      providesTags: ["Vector"],
      keepUnusedDataFor: 300, // 5 minutes - collection metadata is stable
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
      keepUnusedDataFor: 300, // 5 minutes - agent config rarely changes
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
      keepUnusedDataFor: 30, // 30 seconds - health status can change
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
      keepUnusedDataFor: 1800, // 30 minutes - workflow templates are stable
    }),

    // AI Suggestions (legacy - deprecated, use getAISuggestions instead)
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

    // Unified AI Suggestions (new endpoint)
    getAISuggestions: builder.mutation<
      UnifiedSuggestionsResponse,
      UnifiedSuggestionsRequest
    >({
      query: (body) => ({
        url: "/ai/suggestions",
        method: "POST",
        body,
      }),
    }),

    // Chat Follow-Up Suggestions (convenience wrapper)
    getChatFollowUpSuggestions: builder.mutation<
      { suggestions: ChatFollowUpSuggestion[] },
      { content: string; session_id?: string; max_suggestions?: number }
    >({
      query: ({ content, session_id, max_suggestions = 4 }) => ({
        url: "/ai/suggestions",
        method: "POST",
        body: {
          type: "chat_followup",
          content,
          session_id,
          max_suggestions,
        },
      }),
    }),

    // Track Suggestion Clicks (analytics)
    trackSuggestionClick: builder.mutation<
      SuggestionClickResponse,
      SuggestionClickRequest
    >({
      query: (body) => ({
        url: "/ai/suggestions/click",
        method: "POST",
        body,
      }),
    }),

    // Submit Suggestion Feedback (thumbs up/down)
    submitSuggestionFeedback: builder.mutation<
      SuggestionFeedbackResponse,
      SuggestionFeedbackRequest
    >({
      query: (body) => ({
        url: "/ai/suggestions/feedback",
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

    // URL Content Fetch (OpenWebUI-style "#URL" integration)
    fetchUrlContent: builder.mutation<
      {
        url: string;
        title: string | null;
        content: string;
        content_type: string;
        content_length: number;
        truncated: boolean;
      },
      { url: string }
    >({
      query: (body) => ({
        url: "/ai/fetch-url",
        method: "POST",
        body,
      }),
    }),

    // Current User Info (for persona detection)
    getCurrentUser: builder.query<
      {
        username: string;
        email?: string;
        first_name?: string;
        last_name?: string;
        display_name?: string;
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
          first_name?: string;
          last_name?: string;
          display_name?: string;
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
      keepUnusedDataFor: 3600, // 1 hour - identity providers are very stable
    }),

    // Feedback Submission (NPS/CSAT)
    submitFeedback: builder.mutation<FeedbackResponse, FeedbackRequest>({
      query: (body) => ({
        url: "/metrics/feedback",
        method: "POST",
        body,
      }),
    }),

    // Message Rating (Thumbs Up/Down) - persisted to PostgreSQL
    submitMessageRating: builder.mutation<
      MessageRatingResponse,
      MessageRatingRequest
    >({
      query: (body) => ({
        url: `/sessions/${body.session_id}/messages/${body.message_id}/rating`,
        method: "POST",
        body: {
          rating: body.rating,
          feedback: body.feedback,
        },
      }),
      invalidatesTags: (_result, _error, { session_id }) => [
        { type: "Session", id: session_id },
      ],
    }),

    // Notification Preferences
    getNotificationPreferences: builder.query<NotificationPreferences, void>({
      query: () => "/notifications/preferences",
      providesTags: ["NotificationPreferences"],
      keepUnusedDataFor: 120, // 2 minutes - user preferences
    }),

    updateNotificationPreferences: builder.mutation<
      NotificationPreferences,
      UpdateNotificationPreferencesRequest
    >({
      query: (body) => ({
        url: "/notifications/preferences",
        method: "PUT",
        body,
      }),
      invalidatesTags: ["NotificationPreferences"],
    }),

    resetNotificationPreferences: builder.mutation<
      NotificationPreferences,
      void
    >({
      query: () => ({
        url: "/notifications/preferences/reset",
        method: "POST",
      }),
      invalidatesTags: ["NotificationPreferences"],
    }),

    // =========================================================================
    // SUS Surveys
    // =========================================================================

    submitSusSurvey: builder.mutation<
      { id: string; sus_score: number; recorded_at: string },
      { responses: number[] }
    >({
      query: (body) => ({
        url: "/surveys/sus",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Survey"],
    }),

    getSusSummary: builder.query<
      {
        timeframe: string;
        avg_score: number | null;
        response_count: number;
        score_distribution: {
          excellent: number;
          good: number;
          ok: number;
          poor: number;
        };
      },
      { timeframe?: string }
    >({
      query: (params) => ({
        url: "/surveys/sus/summary",
        params: filterParams(params || { timeframe: "30d" }),
      }),
      providesTags: ["Survey"],
    }),

    // =========================================================================
    // HEART Analytics
    // =========================================================================

    trackHappinessMetric: builder.mutation<
      { id: string; recorded_at: string },
      {
        nps_score?: number;
        csat_score?: number;
        feedback?: string;
        context?: string;
      }
    >({
      query: (body) => ({
        url: "/analytics/heart/happiness",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Analytics"],
    }),

    trackEngagementMetric: builder.mutation<
      { id: string; recorded_at: string },
      {
        session_id: string;
        duration_seconds: number;
        features_used?: string[];
      }
    >({
      query: (body) => ({
        url: "/analytics/heart/engagement",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Analytics"],
    }),

    trackAdoptionMetric: builder.mutation<
      { id: string; recorded_at: string },
      { step: string; step_index: number; completed: boolean }
    >({
      query: (body) => ({
        url: "/analytics/heart/adoption",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Analytics"],
    }),

    trackRetentionMetric: builder.mutation<
      { id: string; recorded_at: string },
      { days_since_last_visit: number; return_visit: boolean }
    >({
      query: (body) => ({
        url: "/analytics/heart/retention",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Analytics"],
    }),

    trackTaskSuccessMetric: builder.mutation<
      { id: string; recorded_at: string },
      {
        task_id: string;
        success: boolean;
        duration_seconds: number;
        error_count?: number;
        error_message?: string;
      }
    >({
      query: (body) => ({
        url: "/analytics/heart/task-success",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Analytics"],
    }),

    getHeartAnalytics: builder.query<
      {
        timeframe: string;
        persona: string | null;
        happiness: {
          nps_score_avg: number | null;
          csat_score_avg: number | null;
          response_count: number;
        };
        engagement: {
          avg_session_duration_seconds: number;
          sessions_per_user: number;
          active_users: number;
        };
        adoption: {
          onboarding_completion_rate: number;
          feature_adoption: Record<string, number>;
        };
        retention: { d7_retention: number; d30_retention: number };
        task_success: {
          overall_success_rate: number;
          avg_task_duration_seconds: number;
        };
      },
      { timeframe?: string; persona?: string }
    >({
      query: (params) => ({
        url: "/analytics/heart",
        params: filterParams(params || {}),
      }),
      providesTags: ["Analytics"],
    }),

    // =========================================================================
    // Compliance Reports
    // =========================================================================

    getGdprReport: builder.query<
      Record<string, unknown>,
      { start_time: string; end_time: string }
    >({
      query: (params) => ({
        url: "/compliance/reports/gdpr",
        params,
      }),
      providesTags: ["ComplianceReport"],
      keepUnusedDataFor: 600, // 10 minutes - compliance reports are stable
    }),

    getHipaaReport: builder.query<
      Record<string, unknown>,
      { start_time: string; end_time: string }
    >({
      query: (params) => ({
        url: "/compliance/reports/hipaa",
        params,
      }),
      providesTags: ["ComplianceReport"],
      keepUnusedDataFor: 600, // 10 minutes - compliance reports are stable
    }),

    getSoc2Report: builder.query<
      Record<string, unknown>,
      { start_time: string; end_time: string }
    >({
      query: (params) => ({
        url: "/compliance/reports/soc2",
        params,
      }),
      providesTags: ["ComplianceReport"],
      keepUnusedDataFor: 600, // 10 minutes - compliance reports are stable
    }),

    getFedrampReport: builder.query<
      Record<string, unknown>,
      { start_time: string; end_time: string }
    >({
      query: (params) => ({
        url: "/compliance/reports/fedramp",
        params,
      }),
      providesTags: ["ComplianceReport"],
      keepUnusedDataFor: 600, // 10 minutes - compliance reports are stable
    }),

    getEuAiActReport: builder.query<
      Record<string, unknown>,
      { start_time: string; end_time: string }
    >({
      query: (params) => ({
        url: "/compliance/reports/eu-ai-act",
        params,
      }),
      providesTags: ["ComplianceReport"],
      keepUnusedDataFor: 600, // 10 minutes - compliance reports are stable
    }),

    getComplianceSummary: builder.query<
      Record<string, unknown>,
      { start_time: string; end_time: string }
    >({
      query: (params) => ({
        url: "/compliance/reports/summary",
        params,
      }),
      providesTags: ["ComplianceReport"],
      keepUnusedDataFor: 300, // 5 minutes - summary may be viewed more often
    }),

    // =========================================================================
    // Connection Templates
    // =========================================================================

    listTemplateCategories: builder.query<
      {
        categories: Array<{
          id: string;
          name: string;
          description: string;
        }>;
      },
      void
    >({
      query: () => "/connection-templates/categories",
      providesTags: ["ConnectionTemplate"],
      keepUnusedDataFor: 3600, // 1 hour - template categories are very stable
    }),

    listConnectionTemplates: builder.query<
      {
        templates: Array<{
          id: string;
          name: string;
          description: string;
          icon: string;
          auth_type: "none" | "api_key" | "oauth2";
          default_url: string;
          category: string;
          oauth2_scopes: string[];
          config_fields: Array<{
            name: string;
            label: string;
            type: "text" | "password" | "url" | "textarea";
            required: boolean;
            placeholder?: string;
            description?: string;
            default?: string;
          }>;
        }>;
      },
      { category?: string; auth_type?: string; search?: string }
    >({
      query: (params) => ({
        url: "/connection-templates",
        params: filterParams(params || {}),
      }),
      providesTags: ["ConnectionTemplate"],
      keepUnusedDataFor: 1800, // 30 minutes - templates rarely change
    }),

    getConnectionTemplate: builder.query<
      {
        id: string;
        name: string;
        description: string;
        icon: string;
        auth_type: "none" | "api_key" | "oauth2";
        default_url: string;
        category: string;
        oauth2_scopes: string[];
        config_fields: Array<{
          name: string;
          label: string;
          type: "text" | "password" | "url" | "textarea";
          required: boolean;
          placeholder?: string;
          description?: string;
          default?: string;
        }>;
      },
      string
    >({
      query: (templateId) => `/connection-templates/${templateId}`,
      providesTags: (_result, _error, templateId) => [
        { type: "ConnectionTemplate", id: templateId },
      ],
      keepUnusedDataFor: 1800, // 30 minutes - templates rarely change
    }),

    applyConnectionTemplate: builder.mutation<
      {
        connection: {
          name: string;
          description: string | null;
          url: string;
          auth_type: "none" | "api_key" | "oauth2";
          oauth2_client_id: string | null;
          oauth2_scopes: string[] | null;
        };
      },
      {
        templateId: string;
        name: string;
        description?: string;
        oauth2_client_id?: string;
        oauth2_scopes?: string[];
        api_key?: string;
        url?: string;
        project_id?: string;
      }
    >({
      query: ({ templateId, ...body }) => ({
        url: `/connection-templates/${templateId}/apply`,
        method: "POST",
        body,
      }),
    }),

    // =========================================================================
    // Connection Audit
    // =========================================================================

    logConnectionAuditEvent: builder.mutation<
      {
        id: string;
        event_type: string;
        resource_type: string;
        resource_id: string;
        actor_id: string;
        action: string;
        details: Record<string, unknown>;
        ip_address: string | null;
        user_agent: string | null;
        timestamp: string;
      },
      {
        event_type: string;
        resource_type: string;
        resource_id: string;
        actor_id: string;
        action: string;
        details?: Record<string, unknown>;
      }
    >({
      query: (body) => ({
        url: "/connections/audit/log",
        method: "POST",
        body,
      }),
      invalidatesTags: ["ConnectionAudit"],
    }),

    queryConnectionAuditLogs: builder.query<
      {
        logs: Array<{
          id: string;
          event_type: string;
          resource_type: string;
          resource_id: string;
          actor_id: string;
          action: string;
          details: Record<string, unknown>;
          ip_address: string | null;
          user_agent: string | null;
          timestamp: string;
        }>;
        total: number;
        limit: number;
        offset: number;
      },
      {
        resource_type?: string;
        resource_id?: string;
        actor_id?: string;
        event_type?: string;
        start_time?: string;
        end_time?: string;
        limit?: number;
        offset?: number;
      }
    >({
      query: (params) => ({
        url: "/connections/audit/logs",
        params: filterParams(params || {}),
      }),
      providesTags: ["ConnectionAudit"],
    }),

    getConnectionAuditLog: builder.query<
      {
        logs: Array<{
          id: string;
          event_type: string;
          resource_type: string;
          resource_id: string;
          actor_id: string;
          action: string;
          details: Record<string, unknown>;
          ip_address: string | null;
          user_agent: string | null;
          timestamp: string;
        }>;
        total: number;
        limit: number;
        offset: number;
      },
      { connectionId: string; limit?: number }
    >({
      query: ({ connectionId, limit }) => ({
        url: `/connections/${connectionId}/audit`,
        params: limit ? { limit } : undefined,
      }),
      providesTags: (_result, _error, { connectionId }) => [
        { type: "ConnectionAudit", id: connectionId },
      ],
    }),

    deleteOldAuditLogs: builder.mutation<
      { deleted_count: number; retention_days: number },
      { days?: number }
    >({
      query: (params) => ({
        url: "/connections/audit/retention",
        method: "DELETE",
        params: params.days ? { days: params.days } : undefined,
      }),
      invalidatesTags: ["ConnectionAudit"],
    }),

    exportConnectionAuditLogs: builder.query<
      Blob,
      {
        format?: "json" | "csv";
        resource_type?: string;
        resource_id?: string;
        actor_id?: string;
        event_type?: string;
        start_time?: string;
        end_time?: string;
      }
    >({
      query: (params) => ({
        url: "/connections/audit/export",
        params: filterParams(params || {}),
        responseHandler: (response) => response.blob(),
      }),
    }),

    // =========================================================================
    // Connections Bulk Operations
    // =========================================================================

    bulkDeleteConnections: builder.mutation<
      { deleted_count: number; failed_ids: string[] },
      { connection_ids: string[] }
    >({
      query: (body) => ({
        url: "/connections/bulk/delete",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Connection"],
    }),

    bulkTestConnections: builder.mutation<
      {
        results: Array<{
          connection_id: string;
          success: boolean;
          server_name: string | null;
          server_version: string | null;
          tool_count: number;
          error: string | null;
        }>;
        not_found: string[];
      },
      { connection_ids: string[] }
    >({
      query: (body) => ({
        url: "/connections/bulk/test",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Connection"],
    }),

    bulkUpdateConnectionStatus: builder.mutation<
      { updated_count: number; failed_ids: string[] },
      {
        connection_ids: string[];
        status:
          | "disconnected"
          | "connecting"
          | "connected"
          | "error"
          | "auth_required";
      }
    >({
      query: (body) => ({
        url: "/connections/bulk/status",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Connection"],
    }),

    // =========================================================================
    // User Preferences (UX Enhancement)
    // =========================================================================

    /**
     * Get current user's preferences
     */
    getUserPreferences: builder.query<UserPreferences, void>({
      query: () => "/preferences",
      providesTags: ["UserPreferences"],
      keepUnusedDataFor: 120, // 2 minutes - user preferences
    }),

    /**
     * Update user preferences (partial update)
     */
    updateUserPreferences: builder.mutation<
      UserPreferences,
      UserPreferencesUpdate
    >({
      query: (body) => ({
        url: "/preferences",
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["UserPreferences"],
    }),

    /**
     * Reset user preferences to defaults
     */
    resetUserPreferences: builder.mutation<UserPreferences, void>({
      query: () => ({
        url: "/preferences",
        method: "DELETE",
      }),
      invalidatesTags: ["UserPreferences"],
    }),

    // =========================================================================
    // Session Export (UX Enhancement)
    // =========================================================================

    /**
     * Export a session in the specified format
     *
     * Returns a Blob that can be downloaded as a file.
     */
    exportSession: builder.mutation<
      Blob,
      { sessionId: string; request: SessionExportRequest }
    >({
      query: ({ sessionId, request }) => ({
        url: `/sessions/${sessionId}/export`,
        method: "POST",
        body: request,
        responseHandler: async (response) => {
          // Handle blob response for file download
          if (response.ok) {
            return response.blob();
          }
          throw new Error("Export failed");
        },
      }),
    }),

    // =========================================================================
    // Infrastructure Alerts & Remediations (Admin Dashboard)
    // =========================================================================

    /**
     * Get AI-generated recommendation for an alert
     */
    getAlertRecommendation: builder.query<AIRecommendation, string>({
      query: (alertId) => `/alerts/${alertId}/recommendation`,
      providesTags: (_result, _error, alertId) => [
        { type: "InfraAlert", id: `RECOMMENDATION-${alertId}` },
      ],
    }),

    /**
     * Regenerate AI recommendation for an alert
     */
    regenerateAlertRecommendation: builder.mutation<AIRecommendation, string>({
      query: (alertId) => ({
        url: `/alerts/${alertId}/recommendation/regenerate`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, alertId) => [
        { type: "InfraAlert", id: `RECOMMENDATION-${alertId}` },
      ],
    }),

    /**
     * List pending remediation requests
     */
    listPendingRemediations: builder.query<
      PaginatedResponse<RemediationRequest>,
      RemediationListParams
    >({
      query: (params) => ({
        url: "/remediations/pending",
        params: filterParams({
          status: params.status,
          alert_id: params.alert_id,
          severity: params.severity,
          limit: params.limit ?? 50,
          cursor: params.cursor,
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ remediation_id }) => ({
                type: "Remediation" as const,
                id: remediation_id,
              })),
              { type: "Remediation", id: "PENDING" },
            ]
          : [{ type: "Remediation", id: "PENDING" }],
    }),

    /**
     * List remediation history (approved/rejected/completed/failed)
     */
    listRemediationHistory: builder.query<
      PaginatedResponse<RemediationRequest>,
      RemediationListParams
    >({
      query: (params) => ({
        url: "/remediations/history",
        params: filterParams({
          status: params.status,
          alert_id: params.alert_id,
          severity: params.severity,
          limit: params.limit ?? 50,
          cursor: params.cursor,
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ remediation_id }) => ({
                type: "Remediation" as const,
                id: remediation_id,
              })),
              { type: "Remediation", id: "HISTORY" },
            ]
          : [{ type: "Remediation", id: "HISTORY" }],
    }),

    /**
     * Approve a remediation request
     */
    approveRemediation: builder.mutation<
      RemediationRequest,
      ApproveRemediationRequest
    >({
      query: ({ remediation_id, ...body }) => ({
        url: `/remediations/${remediation_id}/approve`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { remediation_id }) => [
        { type: "Remediation", id: remediation_id },
        { type: "Remediation", id: "PENDING" },
        { type: "Remediation", id: "HISTORY" },
      ],
    }),

    /**
     * Reject a remediation request
     */
    rejectRemediation: builder.mutation<
      RemediationRequest,
      RejectRemediationRequest
    >({
      query: ({ remediation_id, ...body }) => ({
        url: `/remediations/${remediation_id}/reject`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { remediation_id }) => [
        { type: "Remediation", id: remediation_id },
        { type: "Remediation", id: "PENDING" },
        { type: "Remediation", id: "HISTORY" },
      ],
    }),

    // =========================================================================
    // Artifacts (Hybrid Canvas Multi-Layer Storage)
    // =========================================================================

    /**
     * List artifacts for a session with cursor-based pagination
     */
    listArtifacts: builder.query<
      ListArtifactsResponse,
      { session_id?: string; cursor?: string; limit?: number }
    >({
      query: (params) => ({
        url: "/artifacts",
        params: filterParams({
          session_id: params.session_id,
          cursor: params.cursor,
          limit: params.limit ?? 20,
        }),
      }),
      providesTags: (result) =>
        result?.items
          ? [
              ...result.items.map(({ id }) => ({
                type: "Artifact" as const,
                id,
              })),
              { type: "Artifact", id: "LIST" },
            ]
          : [{ type: "Artifact", id: "LIST" }],
    }),

    /**
     * Get a single artifact by ID
     */
    getArtifact: builder.query<CanvasArtifact, string>({
      query: (id) => `/artifacts/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Artifact", id }],
    }),

    /**
     * Create a new artifact
     */
    createArtifact: builder.mutation<CreateArtifactResponse, CreateArtifactRequest>({
      query: (body) => ({
        url: "/artifacts",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "Artifact", id: "LIST" }],
    }),

    /**
     * Update an artifact (creates new version)
     */
    updateArtifact: builder.mutation<
      UpdateArtifactResponse,
      { id: string } & UpdateArtifactRequest
    >({
      query: ({ id, ...body }) => ({
        url: `/artifacts/${id}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: "Artifact", id },
        { type: "Artifact", id: "LIST" },
      ],
    }),

    /**
     * Delete an artifact
     */
    deleteArtifact: builder.mutation<void, string>({
      query: (id) => ({
        url: `/artifacts/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: "Artifact", id },
        { type: "Artifact", id: "LIST" },
      ],
    }),

    /**
     * Get version history for an artifact
     */
    getArtifactVersions: builder.query<ArtifactVersion[], string>({
      query: (id) => `/artifacts/${id}/versions`,
      providesTags: (_result, _error, id) => [
        { type: "Artifact", id: `VERSIONS-${id}` },
      ],
    }),

    /**
     * Fork an artifact (create copy with parent reference)
     */
    forkArtifact: builder.mutation<
      ForkArtifactResponse,
      { id: string; newTitle?: string }
    >({
      query: ({ id, newTitle }) => ({
        url: `/artifacts/${id}/fork`,
        method: "POST",
        body: { new_title: newTitle },
      }),
      invalidatesTags: [{ type: "Artifact", id: "LIST" }],
    }),

    /**
     * Semantic search across artifacts using vector embeddings
     */
    semanticSearchArtifacts: builder.mutation<
      { results: Array<{ artifact_id: string; score: number; title: string | null }> },
      { query: string; limit?: number; session_id?: string }
    >({
      query: (body) => ({
        url: "/artifacts/search",
        method: "POST",
        body,
      }),
    }),

    /**
     * Find similar artifacts to a given artifact
     */
    findSimilarArtifacts: builder.query<
      { results: Array<{ artifact_id: string; score: number; title: string | null }> },
      { id: string; limit?: number }
    >({
      query: ({ id, limit }) => ({
        url: `/artifacts/${id}/similar`,
        params: limit ? { limit } : undefined,
      }),
      providesTags: (_result, _error, { id }) => [
        { type: "Artifact", id: `SIMILAR-${id}` },
      ],
    }),

    // =========================================================================
    // Agent HITL Requests
    // =========================================================================

    /**
     * List pending agent HITL requests (approvals and clarifications)
     */
    listPendingAgentRequests: builder.query<
      PendingAgentRequestsResponse,
      ListPendingAgentRequestsParams | void
    >({
      query: (params) => ({
        url: "/agents/requests/pending",
        params: params ? filterParams(params as Record<string, unknown>) : undefined,
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.approvals.map(({ request_id }) => ({
                type: "AgentRequest" as const,
                id: request_id,
              })),
              ...result.clarifications.map(({ request_id }) => ({
                type: "AgentRequest" as const,
                id: request_id,
              })),
              { type: "AgentRequest", id: "LIST" },
            ]
          : [{ type: "AgentRequest", id: "LIST" }],
    }),

    /**
     * Approve an agent request
     */
    approveAgentRequest: builder.mutation<
      AgentRequestActionResponse,
      ApproveAgentRequestParams
    >({
      query: ({ requestId, ...body }) => ({
        url: `/agents/requests/${requestId}/approve`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { requestId }) => [
        { type: "AgentRequest", id: requestId },
        { type: "AgentRequest", id: "LIST" },
      ],
    }),

    /**
     * Reject an agent request
     */
    rejectAgentRequest: builder.mutation<
      AgentRequestActionResponse,
      RejectAgentRequestParams
    >({
      query: ({ requestId, ...body }) => ({
        url: `/agents/requests/${requestId}/reject`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { requestId }) => [
        { type: "AgentRequest", id: requestId },
        { type: "AgentRequest", id: "LIST" },
      ],
    }),

    /**
     * Respond to an agent clarification request
     */
    respondToAgentRequest: builder.mutation<
      AgentRequestActionResponse,
      RespondAgentRequestParams
    >({
      query: (body) => ({
        url: `/agents/requests/${body.request_id}/respond`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { request_id }) => [
        { type: "AgentRequest", id: request_id },
        { type: "AgentRequest", id: "LIST" },
      ],
    }),

    /**
     * Batch approve multiple agent requests (admin only)
     */
    batchApproveAgentRequests: builder.mutation<
      BatchAgentRequestResponse,
      BatchApproveAgentRequestParams
    >({
      query: (body) => ({
        url: "/agents/requests/batch/approve",
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { request_ids }) => [
        ...request_ids.map((id) => ({ type: "AgentRequest" as const, id })),
        { type: "AgentRequest", id: "LIST" },
      ],
    }),

    /**
     * Batch reject multiple agent requests (admin only)
     */
    batchRejectAgentRequests: builder.mutation<
      BatchAgentRequestResponse,
      BatchRejectAgentRequestParams
    >({
      query: (body) => ({
        url: "/agents/requests/batch/reject",
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { request_ids }) => [
        ...request_ids.map((id) => ({ type: "AgentRequest" as const, id })),
        { type: "AgentRequest", id: "LIST" },
      ],
    }),

    // =========================================================================
    // AI UX Endpoints (Progressive Disclosure, Nudges, Error Recovery, etc.)
    // =========================================================================

    /**
     * Analyze progressive disclosure level for UI complexity
     */
    analyzeDisclosure: builder.mutation<
      {
        current_level: string;
        recommended_level: string;
        confidence: number;
        unlock_features: string[];
        personalized_message: string;
        reasoning?: string;
      },
      {
        current_level: string;
        persona?: string;
        context?: Record<string, unknown>;
        user_behavior?: {
          feature_usage: Record<string, number>;
          session_count: number;
          avg_session_duration?: number;
        };
      }
    >({
      query: (body) => ({
        url: "/ai/disclosure/analyze",
        method: "POST",
        body,
      }),
    }),

    /**
     * Get AI-generated suggestions for empty state screens
     */
    getEmptyStateSuggestions: builder.mutation<
      {
        suggestions: Array<{
          title: string;
          description: string;
          action_type: "navigate" | "create" | "learn" | "import";
          action_target: string;
          icon?: string;
          priority: number;
        }>;
        context_hint?: string;
      },
      {
        context: string;
        persona?: string;
        previous_actions?: string[];
        available_actions?: string[];
      }
    >({
      query: (body) => ({
        url: "/ai/empty-state/suggestions",
        method: "POST",
        body,
      }),
    }),

    /**
     * Get AI-generated nudge recommendations
     */
    getNudgeRecommendation: builder.mutation<
      {
        nudge_type: string;
        message: string;
        confidence: number;
        action_cta?: string;
        action_target?: string;
        dismiss_duration_ms?: number;
      },
      {
        context: string;
        user_actions?: string[];
        current_feature?: string;
        persona?: string;
      }
    >({
      query: (body) => ({
        url: "/ai/nudges/recommend",
        method: "POST",
        body,
      }),
    }),

    /**
     * Analyze error for recovery suggestions
     */
    analyzeError: builder.mutation<
      {
        error_type: string;
        recovery_steps: Array<{
          step_number: number;
          title: string;
          description: string;
          action_type: "automatic" | "manual" | "contact_support";
          action_target?: string;
        }>;
        auto_recoverable: boolean;
        suggested_action?: string;
        confidence: number;
      },
      {
        error_code: string;
        error_message: string;
        context?: Record<string, unknown>;
        stack_trace?: string;
      }
    >({
      query: (body) => ({
        url: "/ai/errors/analyze",
        method: "POST",
        body,
      }),
    }),

    /**
     * Personalize onboarding experience
     */
    personalizeOnboarding: builder.mutation<
      {
        recommended_steps: string[];
        skip_steps: string[];
        estimated_duration_minutes: number;
        personalization_applied: boolean;
        reasoning?: string;
      },
      {
        detected_persona?: string;
        experience_level?: "beginner" | "intermediate" | "expert";
        goals?: string[];
        previous_tool_experience?: string[];
      }
    >({
      query: (body) => ({
        url: "/ai/onboarding/personalize",
        method: "POST",
        body,
      }),
    }),

    /**
     * Get AI-generated insights from HEART metrics
     */
    getMetricsInsights: builder.query<
      {
        happiness_score: number;
        insights: Array<{
          category: "happiness" | "engagement" | "adoption" | "retention" | "task_success";
          title: string;
          description: string;
          trend: "improving" | "stable" | "declining";
          priority: "high" | "medium" | "low";
          suggested_action?: string;
        }>;
        overall_health: "excellent" | "good" | "needs_attention" | "critical";
        recommendations: string[];
      },
      { session_id?: string; period?: string }
    >({
      query: (params) => ({
        url: "/ai/metrics/insights",
        params: filterParams(params || {}),
      }),
      providesTags: ["AIUx"],
    }),

    /**
     * Analyze user behavior for persona detection/validation
     */
    analyzePersona: builder.mutation<
      {
        detected_persona: string;
        confidence: number;
        alternative_personas: Array<{
          persona: string;
          confidence: number;
        }>;
        behavior_indicators: Record<string, unknown>;
        recommendation?: string;
      },
      {
        behavior_data: Record<string, unknown>;
        current_persona?: string;
        session_id?: string;
      }
    >({
      query: (body) => ({
        url: "/ai/persona/analyze",
        method: "POST",
        body,
      }),
    }),

    /**
     * Composite analysis combining multiple AI UX insights
     */
    analyzeComposite: builder.mutation<
      {
        analysis_id: string;
        timestamp: string;
        disclosure?: {
          recommended_level: string;
          confidence: number;
        };
        nudge?: {
          nudge_type: string;
          message: string;
          confidence: number;
        };
        persona?: {
          detected_persona: string;
          confidence: number;
        };
        errors?: Array<{
          error_type: string;
          auto_recoverable: boolean;
        }>;
        overall_confidence: number;
      },
      {
        include_disclosure?: boolean;
        include_nudges?: boolean;
        include_persona?: boolean;
        include_errors?: boolean;
        context?: Record<string, unknown>;
        session_id?: string;
      }
    >({
      query: (body) => ({
        url: "/ai/composite/analyze",
        method: "POST",
        body,
      }),
    }),

    /**
     * Batch composite analysis for multiple contexts
     */
    batchCompositeAnalysis: builder.mutation<
      {
        results: Array<{
          analysis_id: string;
          timestamp: string;
          disclosure?: {
            recommended_level: string;
            confidence: number;
          };
          nudge?: {
            nudge_type: string;
            message: string;
            confidence: number;
          };
          persona?: {
            detected_persona: string;
            confidence: number;
          };
          errors?: Array<{
            error_type: string;
            auto_recoverable: boolean;
          }>;
          overall_confidence: number;
        }>;
        processed: number;
        failed: number;
      },
      {
        requests: Array<{
          include_disclosure?: boolean;
          include_nudges?: boolean;
          include_persona?: boolean;
          include_errors?: boolean;
          context?: Record<string, unknown>;
          session_id?: string;
        }>;
      }
    >({
      query: (body) => ({
        url: "/ai/composite/batch",
        method: "POST",
        body,
      }),
    }),

    // =========================================================================
    // Studio AI Endpoints (HybridShell AI Enhancement)
    // =========================================================================

    /**
     * Unified Studio AI analysis endpoint
     *
     * Executes multiple AI analysis tasks in parallel via StudioOrchestrator.
     * Supports all 8 task categories: UX, SESSION, CONVERSATION, CANVAS,
     * DIAGRAM, TRACE, HITL, COMMAND.
     *
     * Reference: HybridShell AI Enhancement Analysis Plan
     */
    studioAnalyze: builder.mutation<
      {
        user_id: string;
        session_id: string;
        analyses: Record<string, unknown>;
        cross_insights: string[];
        failed_analyses: string[];
        total_cost: string;
      },
      {
        user_id: string;
        session_id: string;
        persona?: string;
        tasks: Array<{
          category: string;
          type: string;
          data?: Record<string, unknown>;
        }>;
        context?: Record<string, unknown>;
      }
    >({
      query: (body) => ({
        url: "/studio/analyze",
        method: "POST",
        body,
      }),
    }),

    // =========================================================================
    // MCP Protocol Endpoints (2025-11-25)
    // =========================================================================

    /**
     * List available MCP resources
     *
     * Cache: 5 minutes - resources are relatively static
     */
    listMcpResources: builder.query<McpResourceListResponse, void>({
      query: () => "/mcp/resources",
      providesTags: [{ type: "Mcp", id: "RESOURCES" }],
      keepUnusedDataFor: 300, // 5 minutes
    }),

    /**
     * Read MCP resource content by URI
     */
    readMcpResource: builder.mutation<
      McpResourceContentResponse,
      McpReadResourceRequest
    >({
      query: ({ uri }) => ({
        url: "/mcp/resources/content",
        method: "GET",
        params: { uri },
      }),
    }),

    /**
     * List available MCP tools
     *
     * Cache: 5 minutes - tools are relatively static
     */
    listMcpTools: builder.query<McpToolListResponse, void>({
      query: () => "/mcp/tools",
      providesTags: [{ type: "Mcp", id: "TOOLS" }],
      keepUnusedDataFor: 300, // 5 minutes
    }),

    /**
     * Invoke an MCP tool
     *
     * Invalidates TASKS tag since tool invocations may create new background tasks.
     */
    invokeMcpTool: builder.mutation<
      McpToolInvocationResponse,
      McpInvokeToolRequest
    >({
      query: (body) => ({
        url: "/mcp/tools/call",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "Mcp", id: "TASKS" }],
    }),

    /**
     * Request LLM completion via MCP sampling
     *
     * May create background tasks for long-running completions.
     */
    requestMcpSampling: builder.mutation<McpSamplingResponse, McpSamplingRequest>(
      {
        query: (body) => ({
          url: "/mcp/sampling",
          method: "POST",
          body,
        }),
        invalidatesTags: [{ type: "Mcp", id: "TASKS" }],
      }
    ),

    /**
     * Request user input via MCP elicitation
     *
     * May create background tasks for pending user input.
     */
    requestMcpElicitation: builder.mutation<
      McpElicitationResponse,
      McpElicitationRequest
    >({
      query: (body) => ({
        url: "/mcp/elicitation",
        method: "POST",
        body,
      }),
      invalidatesTags: [{ type: "Mcp", id: "TASKS" }],
    }),

    /**
     * List available MCP prompts
     *
     * Cache: 5 minutes - prompts are relatively static
     */
    listMcpPrompts: builder.query<McpPromptListResponse, void>({
      query: () => "/mcp/prompts",
      providesTags: [{ type: "Mcp", id: "PROMPTS" }],
      keepUnusedDataFor: 300, // 5 minutes
    }),

    /**
     * Get MCP prompt with arguments
     */
    getMcpPrompt: builder.mutation<McpGetPromptResponse, McpGetPromptRequest>({
      query: (body) => ({
        url: "/mcp/prompts/get",
        method: "POST",
        body,
      }),
    }),

    /**
     * List active MCP tasks
     *
     * Cache: 30 seconds - tasks change frequently
     */
    listMcpTasks: builder.query<McpTaskListResponse, void>({
      query: () => "/mcp/tasks",
      providesTags: [{ type: "Mcp", id: "TASKS" }],
      keepUnusedDataFor: 30, // 30 seconds - tasks update frequently
    }),

    /**
     * Get MCP task by ID
     *
     * Cache: 30 seconds - task status changes frequently
     */
    getMcpTask: builder.query<McpTask, string>({
      query: (taskId) => `/mcp/tasks/${taskId}`,
      providesTags: (_result, _error, taskId) => [{ type: "Mcp", id: taskId }],
      keepUnusedDataFor: 30, // 30 seconds - tasks update frequently
    }),

    /**
     * Cancel an MCP task
     */
    cancelMcpTask: builder.mutation<McpTask, string>({
      query: (taskId) => ({
        url: `/mcp/tasks/${taskId}/cancel`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, taskId) => [
        { type: "Mcp", id: taskId },
        { type: "Mcp", id: "TASKS" },
      ],
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
  useGenerateSessionTitleMutation,
  useUpdateSessionConfigMutation,
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
  // Alerts (LGTM Stack)
  useListAlertsQuery,
  useGetAlertQuery,
  useListAlertRulesQuery,
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
  // AI Suggestions (legacy - deprecated)
  useGetWorkflowSuggestionsMutation,
  // Unified AI Suggestions (new)
  useGetAISuggestionsMutation,
  useGetChatFollowUpSuggestionsMutation,
  // Suggestion Analytics
  useTrackSuggestionClickMutation,
  useSubmitSuggestionFeedbackMutation,
  // Node Config Assistant
  useGetNodeConfigHelpMutation,
  // URL Content Fetch
  useFetchUrlContentMutation,
  // User Info
  useGetCurrentUserQuery,
  // Auth (Native Login/Logout)
  useLoginMutation,
  useLogoutMutation,
  useGetIdentityProvidersQuery,
  // Feedback
  useSubmitFeedbackMutation,
  // Message Rating
  useSubmitMessageRatingMutation,
  // Notification Preferences
  useGetNotificationPreferencesQuery,
  useUpdateNotificationPreferencesMutation,
  useResetNotificationPreferencesMutation,
  // SUS Surveys
  useSubmitSusSurveyMutation,
  useGetSusSummaryQuery,
  // HEART Analytics
  useTrackHappinessMetricMutation,
  useTrackEngagementMetricMutation,
  useTrackAdoptionMetricMutation,
  useTrackRetentionMetricMutation,
  useTrackTaskSuccessMetricMutation,
  useGetHeartAnalyticsQuery,
  // Compliance Reports
  useGetGdprReportQuery,
  useGetHipaaReportQuery,
  useGetSoc2ReportQuery,
  useGetFedrampReportQuery,
  useGetEuAiActReportQuery,
  useGetComplianceSummaryQuery,
  // Connection Templates
  useListTemplateCategoriesQuery,
  useListConnectionTemplatesQuery,
  useGetConnectionTemplateQuery,
  useApplyConnectionTemplateMutation,
  // Connection Audit
  useLogConnectionAuditEventMutation,
  useQueryConnectionAuditLogsQuery,
  useGetConnectionAuditLogQuery,
  useDeleteOldAuditLogsMutation,
  useExportConnectionAuditLogsQuery,
  // Connections Bulk Operations
  useBulkDeleteConnectionsMutation,
  useBulkTestConnectionsMutation,
  useBulkUpdateConnectionStatusMutation,
  // User Preferences
  useGetUserPreferencesQuery,
  useUpdateUserPreferencesMutation,
  useResetUserPreferencesMutation,
  // Session Export
  useExportSessionMutation,
  // Infrastructure Alerts & Remediations
  useGetAlertRecommendationQuery,
  useRegenerateAlertRecommendationMutation,
  useListPendingRemediationsQuery,
  useListRemediationHistoryQuery,
  useApproveRemediationMutation,
  useRejectRemediationMutation,
  // Artifacts (Hybrid Canvas)
  useListArtifactsQuery,
  useGetArtifactQuery,
  useCreateArtifactMutation,
  useUpdateArtifactMutation,
  useDeleteArtifactMutation,
  useGetArtifactVersionsQuery,
  useForkArtifactMutation,
  useSemanticSearchArtifactsMutation,
  useFindSimilarArtifactsQuery,
  // Agent HITL Requests
  useListPendingAgentRequestsQuery,
  useApproveAgentRequestMutation,
  useRejectAgentRequestMutation,
  useRespondToAgentRequestMutation,
  useBatchApproveAgentRequestsMutation,
  useBatchRejectAgentRequestsMutation,
  // AI UX Endpoints
  useAnalyzeDisclosureMutation,
  useGetEmptyStateSuggestionsMutation,
  useGetNudgeRecommendationMutation,
  useAnalyzeErrorMutation,
  usePersonalizeOnboardingMutation,
  useGetMetricsInsightsQuery,
  useAnalyzePersonaMutation,
  useAnalyzeCompositeMutation,
  useBatchCompositeAnalysisMutation,
  // Studio AI Endpoints (HybridShell)
  useStudioAnalyzeMutation,
  // MCP Protocol Endpoints
  useListMcpResourcesQuery,
  useReadMcpResourceMutation,
  useListMcpToolsQuery,
  useInvokeMcpToolMutation,
  useRequestMcpSamplingMutation,
  useRequestMcpElicitationMutation,
  useListMcpPromptsQuery,
  useGetMcpPromptMutation,
  useListMcpTasksQuery,
  useGetMcpTaskQuery,
  useCancelMcpTaskMutation,
} = api;
