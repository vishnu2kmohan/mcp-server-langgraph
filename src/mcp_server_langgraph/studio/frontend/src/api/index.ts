/**
 * RTK Query API
 *
 * Unified API slice for all /api/v1/* endpoints with automatic caching,
 * invalidation, and real-time updates.
 */

import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

// Types
export interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  user_id?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  node_count: number;
  edge_count: number;
  created_at: string;
  updated_at: string;
}

export interface Session {
  session_id: string;
  name: string;
  workflow_id?: string;
  user_id?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface FeatureFlags {
  enable_workflows_feature: boolean;
  enable_sessions_feature: boolean;
  enable_cost_dashboard: boolean;
  enable_cost_dashboard_users: boolean;
  enable_observability_ui: boolean;
  enable_code_export: boolean;
  enable_ai_suggestions: boolean;
  enable_mcp_websocket: boolean;
}

export interface CostSummary {
  total_cost: number;
  total_tokens: number;
  period: string;
  breakdown_by_model: Record<string, { cost: number; tokens: number }>;
}

export interface TraceSpan {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  name: string;
  start_time: string;
  end_time: string;
  status: string;
  attributes: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  cursor?: string;
  next_cursor?: string;
}

export interface ChatCompletionRequest {
  session_id?: string;
  messages: Array<{ role: string; content: string }>;
  model?: string;
  stream?: boolean;
}

export interface ChatCompletionResponse {
  id: string;
  session_id: string;
  message: Message;
  model: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// API Definition
export const api = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1',
    prepareHeaders: (headers) => {
      // Add auth token if available
      const token = localStorage.getItem('auth_token');
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: ['Workflow', 'Session', 'Message', 'Cost', 'Trace', 'FeatureFlags'],
  endpoints: (builder) => ({
    // Feature Flags
    getFeatureFlags: builder.query<FeatureFlags, void>({
      query: () => '/features',
      providesTags: ['FeatureFlags'],
    }),

    // Workflows
    listWorkflows: builder.query<
      PaginatedResponse<WorkflowSummary>,
      { cursor?: string; limit?: number }
    >({
      query: ({ cursor, limit = 20 }) => ({
        url: '/workflows',
        params: { cursor, limit },
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Workflow' as const, id })),
              { type: 'Workflow', id: 'LIST' },
            ]
          : [{ type: 'Workflow', id: 'LIST' }],
    }),

    getWorkflow: builder.query<Workflow, string>({
      query: (id) => `/workflows/${id}`,
      providesTags: (result, error, id) => [{ type: 'Workflow', id }],
    }),

    createWorkflow: builder.mutation<
      Workflow,
      { name: string; description?: string; nodes?: unknown[]; edges?: unknown[] }
    >({
      query: (body) => ({
        url: '/workflows',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'Workflow', id: 'LIST' }],
    }),

    updateWorkflow: builder.mutation<
      Workflow,
      { id: string; name?: string; description?: string; nodes?: unknown[]; edges?: unknown[] }
    >({
      query: ({ id, ...body }) => ({
        url: `/workflows/${id}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: (result, error, { id }) => [
        { type: 'Workflow', id },
        { type: 'Workflow', id: 'LIST' },
      ],
    }),

    deleteWorkflow: builder.mutation<void, string>({
      query: (id) => ({
        url: `/workflows/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Workflow', id },
        { type: 'Workflow', id: 'LIST' },
      ],
    }),

    // Sessions
    listSessions: builder.query<
      PaginatedResponse<Session>,
      { cursor?: string; limit?: number }
    >({
      query: ({ cursor, limit = 20 }) => ({
        url: '/sessions',
        params: { cursor, limit },
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ session_id }) => ({
                type: 'Session' as const,
                id: session_id,
              })),
              { type: 'Session', id: 'LIST' },
            ]
          : [{ type: 'Session', id: 'LIST' }],
    }),

    getSession: builder.query<Session, string>({
      query: (id) => `/sessions/${id}`,
      providesTags: (result, error, id) => [{ type: 'Session', id }],
    }),

    createSession: builder.mutation<
      Session,
      { name: string; workflow_id?: string }
    >({
      query: (body) => ({
        url: '/sessions',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'Session', id: 'LIST' }],
    }),

    deleteSession: builder.mutation<void, string>({
      query: (id) => ({
        url: `/sessions/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, id) => [
        { type: 'Session', id },
        { type: 'Session', id: 'LIST' },
      ],
    }),

    // Messages
    getSessionMessages: builder.query<Message[], string>({
      query: (sessionId) => `/sessions/${sessionId}/messages`,
      providesTags: (result, error, sessionId) => [
        { type: 'Message', id: `SESSION-${sessionId}` },
      ],
    }),

    // Chat
    sendChatMessage: builder.mutation<ChatCompletionResponse, ChatCompletionRequest>({
      query: (body) => ({
        url: '/chat/completions',
        method: 'POST',
        body,
      }),
      invalidatesTags: (result) =>
        result?.session_id
          ? [{ type: 'Message', id: `SESSION-${result.session_id}` }]
          : [],
    }),

    // Cost
    getCostSummary: builder.query<CostSummary, { period?: string }>({
      query: ({ period = '30d' }) => ({
        url: '/cost/summary',
        params: { period },
      }),
      providesTags: ['Cost'],
    }),

    getCostByModel: builder.query<
      Record<string, { cost: number; tokens: number }>,
      { period?: string }
    >({
      query: ({ period = '30d' }) => ({
        url: '/cost/by-model',
        params: { period },
      }),
      providesTags: ['Cost'],
    }),

    // Observability
    listTraces: builder.query<
      PaginatedResponse<TraceSpan>,
      { cursor?: string; limit?: number }
    >({
      query: ({ cursor, limit = 50 }) => ({
        url: '/observability/traces',
        params: { cursor, limit },
      }),
      providesTags: ['Trace'],
    }),

    getTrace: builder.query<TraceSpan, string>({
      query: (id) => `/observability/traces/${id}`,
      providesTags: (result, error, id) => [{ type: 'Trace', id }],
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
  // Observability
  useListTracesQuery,
  useGetTraceQuery,
} = api;
