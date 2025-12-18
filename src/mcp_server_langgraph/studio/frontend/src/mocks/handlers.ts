/**
 * MSW Request Handlers
 *
 * Mock handlers for API endpoints used in tests.
 * Based on actual API structure from RTK Query hooks.
 *
 * These handlers provide realistic API mocking for:
 * - Consistent test data across tests
 * - Network-level interception (more realistic than module mocking)
 * - Easy customization per test via override handlers
 */

import { http, HttpResponse, delay } from "msw";
import type {
  CostSummary,
  ModelCostData,
  CostHistoryPoint,
  HealthStatus,
} from "../types/api";
import type {
  MCPConnectionSummary,
  ConnectionStatus,
  AuthType,
  TransportProtocol,
} from "../types/connection";
import type { WorkflowSummary, Session, FeatureFlags } from "../types";

// =============================================================================
// Mock Data Factories
// =============================================================================

export const createMockWorkflow = (
  overrides: Partial<WorkflowSummary> = {},
): WorkflowSummary => ({
  id: `wf-${crypto.randomUUID().slice(0, 8)}`,
  name: "Test Workflow",
  description: "A test workflow for unit tests",
  node_count: 5,
  edge_count: 4,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
});

export const createMockSession = (
  overrides: Partial<Session> = {},
): Session => ({
  id: `session-${crypto.randomUUID().slice(0, 8)}`, // Changed from session_id
  name: "Test Session",
  status: "active",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
});

export const createMockConnection = (
  overrides: Partial<MCPConnectionSummary> = {},
): MCPConnectionSummary => ({
  id: `conn-${crypto.randomUUID().slice(0, 8)}`,
  name: "Test Connection",
  url: "https://api.example.com",
  transport: "streamable_http" as TransportProtocol,
  auth_type: "api_key" as AuthType,
  status: "connected" as ConnectionStatus,
  server_name: "Example MCP Server",
  tool_count: 10,
  resource_count: 5,
  prompt_count: 3,
  last_connected_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  ...overrides,
});

export const createMockCostSummary = (
  overrides: Partial<CostSummary> = {},
): CostSummary => ({
  total_cost: 125.5,
  prompt_tokens: 300000,
  completion_tokens: 200000,
  total_tokens: 500000,
  period_start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  period_end: new Date().toISOString(),
  ...overrides,
});

export const createMockModelCost = (
  overrides: Partial<ModelCostData> = {},
): ModelCostData => ({
  model: "gpt-4",
  cost: 75.0,
  requests: 1000,
  ...overrides,
});

// =============================================================================
// Default Mock Data
// =============================================================================

export const mockWorkflows: WorkflowSummary[] = [
  createMockWorkflow({ id: "wf-1", name: "Data Pipeline" }),
  createMockWorkflow({ id: "wf-2", name: "Chat Assistant" }),
  createMockWorkflow({ id: "wf-3", name: "Code Review Bot" }),
];

export const mockSessions: Session[] = [
  createMockSession({ id: "session-1", name: "Session 1" }),
  createMockSession({ id: "session-2", name: "Session 2" }),
];

export const mockConnections: MCPConnectionSummary[] = [
  createMockConnection({
    id: "conn-1",
    name: "Production Server",
    auth_type: "oauth2",
    status: "connected",
  }),
  createMockConnection({
    id: "conn-2",
    name: "Development Server",
    auth_type: "api_key",
    status: "disconnected",
  }),
  createMockConnection({
    id: "conn-3",
    name: "Local Server",
    auth_type: "none",
    status: "error",
  }),
];

export const mockModelCosts: ModelCostData[] = [
  createMockModelCost({ model: "gpt-4", cost: 75.0, requests: 500 }),
  createMockModelCost({ model: "gpt-3.5-turbo", cost: 25.5, requests: 1500 }),
  createMockModelCost({ model: "claude-3-opus", cost: 25.0, requests: 200 }),
];

export const mockCostHistory: CostHistoryPoint[] = [
  { date: "2025-01-01", cost: 45.0 },
  { date: "2025-01-02", cost: 52.3 },
  { date: "2025-01-03", cost: 38.7 },
  { date: "2025-01-04", cost: 61.2 },
  { date: "2025-01-05", cost: 55.8 },
  { date: "2025-01-06", cost: 48.5 },
  { date: "2025-01-07", cost: 50.0 },
];

export const mockHealthStatus: HealthStatus = {
  status: "healthy",
  version: "1.0.0",
  uptime_seconds: 86400,
};

export const mockFeatureFlags: FeatureFlags = {
  enable_workflows_feature: true,
  enable_sessions_feature: true,
  enable_cost_dashboard: true,
  enable_cost_dashboard_users: true,
  enable_observability_ui: true,
  enable_code_export: true,
  enable_ai_suggestions: true,
  enable_mcp_websocket: true,
};

// =============================================================================
// MSW Request Handlers
// =============================================================================

export const handlers = [
  // Health
  http.get("/api/v1/health", async () => {
    await delay(50);
    return HttpResponse.json(mockHealthStatus);
  }),

  // Feature Flags
  http.get("/api/v1/features", async () => {
    await delay(50);
    return HttpResponse.json(mockFeatureFlags);
  }),

  // User Info
  http.get("/api/v1/user/me", async () => {
    await delay(50);
    return HttpResponse.json({
      username: "test-user",
      email: "test@example.com",
      roles: ["user", "developer"],
    });
  }),

  // Workflows
  http.get("/api/v1/workflows", async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const search = url.searchParams.get("search") ?? "";
    const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);

    let filtered = mockWorkflows;
    if (search) {
      filtered = filtered.filter((w) =>
        w.name.toLowerCase().includes(search.toLowerCase()),
      );
    }

    return HttpResponse.json({
      items: filtered.slice(0, limit),
      next_cursor: null,
      has_more: false,
    });
  }),

  http.get("/api/v1/workflows/:id", async ({ params }) => {
    await delay(50);
    const workflow = mockWorkflows.find((w) => w.id === params.id);
    if (!workflow) {
      return HttpResponse.json(
        { detail: "Workflow not found" },
        { status: 404 },
      );
    }
    return HttpResponse.json(workflow);
  }),

  http.post("/api/v1/workflows", async ({ request }) => {
    await delay(100);
    const body = (await request.json()) as {
      name?: string;
      description?: string;
    };
    const newWorkflow = createMockWorkflow({
      name: body.name || "New Workflow",
      description: body.description,
    });
    return HttpResponse.json(newWorkflow, { status: 201 });
  }),

  http.delete("/api/v1/workflows/:id", async () => {
    await delay(50);
    return new HttpResponse(null, { status: 204 });
  }),

  // Sessions
  http.get("/api/v1/sessions", async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);

    return HttpResponse.json({
      items: mockSessions.slice(0, limit),
      next_cursor: null,
      has_more: false,
    });
  }),

  http.post("/api/v1/sessions", async ({ request }) => {
    await delay(100);
    const body = (await request.json()) as { name?: string };
    const newSession = createMockSession({
      name: body.name || "New Session",
    });
    return HttpResponse.json(newSession, { status: 201 });
  }),

  // Bootstrap workflow from session
  http.post(
    "/api/v1/sessions/:sessionId/bootstrap-workflow",
    async ({ params }) => {
      await delay(100);
      return HttpResponse.json({
        workflow_id: `wf-from-${params.sessionId}`,
        name: "Bootstrapped Workflow",
      });
    },
  ),

  // Connections
  http.get("/api/v1/connections", async ({ request }) => {
    await delay(100);
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const authType = url.searchParams.get("auth_type");

    let filtered = mockConnections;
    if (status) {
      filtered = filtered.filter((c) => c.status === status);
    }
    if (authType) {
      filtered = filtered.filter((c) => c.auth_type === authType);
    }

    return HttpResponse.json({
      items: filtered,
      total: filtered.length,
      cursor: null,
    });
  }),

  http.get("/api/v1/connections/:id", async ({ params }) => {
    await delay(50);
    const connection = mockConnections.find((c) => c.id === params.id);
    if (!connection) {
      return HttpResponse.json(
        { detail: "Connection not found" },
        { status: 404 },
      );
    }
    return HttpResponse.json(connection);
  }),

  http.post("/api/v1/connections/:id/test", async () => {
    await delay(200);
    return HttpResponse.json({
      success: true,
      latency_ms: 150,
      message: "Connection test successful",
    });
  }),

  http.post("/api/v1/connections/:id/oauth2/start", async () => {
    await delay(100);
    return HttpResponse.json({
      auth_url:
        "https://oauth.example.com/authorize?client_id=test&redirect_uri=...",
      state: "random-state-token",
    });
  }),

  http.post("/api/v1/connections/oauth/callback", async ({ request }) => {
    await delay(100);
    const body = (await request.json()) as { code?: string; state?: string };
    if (!body.code) {
      return HttpResponse.json(
        { detail: "Missing authorization code" },
        { status: 400 },
      );
    }
    if (!body.state) {
      return HttpResponse.json(
        { detail: "Missing state parameter" },
        { status: 400 },
      );
    }
    return HttpResponse.json({
      success: true,
      connection_id: "conn-oauth-result",
    });
  }),

  // Cost Endpoints
  http.get("/api/v1/cost/summary", async () => {
    await delay(100);
    return HttpResponse.json(createMockCostSummary());
  }),

  http.get("/api/v1/cost/by-model", async () => {
    await delay(100);
    return HttpResponse.json(mockModelCosts);
  }),

  http.get("/api/v1/cost/history", async () => {
    await delay(100);
    return HttpResponse.json(mockCostHistory);
  }),

  // Agents Config
  http.get("/api/v1/agents/config", async () => {
    await delay(100);
    return HttpResponse.json({
      model: "gpt-4",
      provider: "openai",
      temperature: 0.7,
      verification_enabled: true,
      tools: [
        { name: "web_search", description: "Search the web for information" },
        { name: "code_executor", description: "Execute code snippets safely" },
      ],
    });
  }),

  // Vectors
  http.get("/api/v1/vectors/collections", async () => {
    await delay(100);
    return HttpResponse.json([
      { name: "documents", vectors_count: 1500 },
      { name: "embeddings", vectors_count: 500 },
    ]);
  }),

  http.post("/api/v1/vectors/search-text", async () => {
    await delay(150);
    return HttpResponse.json({
      results: [
        {
          id: "point-1",
          score: 0.95,
          payload: { text: "Relevant document 1" },
        },
        {
          id: "point-2",
          score: 0.87,
          payload: { text: "Relevant document 2" },
        },
      ],
    });
  }),

  // Projects
  http.get("/api/v1/projects", async () => {
    await delay(100);
    return HttpResponse.json({
      items: [
        {
          id: "proj-1",
          name: "Main Project",
          description: "Primary development project",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: "proj-2",
          name: "Testing Project",
          description: "QA and testing project",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
      total_pages: 1,
    });
  }),

  // Metrics
  http.get("/api/v1/metrics/heart/aggregate", async () => {
    await delay(100);
    return HttpResponse.json({
      period: "7d",
      nps_score_avg: 7.5,
      satisfaction_avg: 4.2,
      task_success_rate: 0.85,
      total_tasks_started: 100,
      total_tasks_completed: 85,
      avg_session_duration_ms: 300000,
      new_users_count: 50,
      avg_return_visits: 3.2,
    });
  }),

  // Admin Users
  http.get("/api/v1/admin/users", async () => {
    await delay(100);
    return HttpResponse.json({
      items: [
        {
          user_id: "user-1",
          username: "admin",
          email: "admin@example.com",
          roles: ["admin"],
          active: true,
        },
        {
          user_id: "user-2",
          username: "developer",
          email: "dev@example.com",
          roles: ["developer"],
          active: true,
        },
      ],
      total: 2,
    });
  }),

  http.get("/api/v1/admin/users/:userId", async ({ params }) => {
    await delay(50);
    return HttpResponse.json({
      user_id: params.userId,
      username: "testuser",
      email: "test@example.com",
      roles: ["user"],
      active: true,
    });
  }),

  http.post("/api/v1/admin/users", async ({ request }) => {
    await delay(100);
    const body = (await request.json()) as {
      username?: string;
      email?: string;
      roles?: string[];
    };
    return HttpResponse.json(
      {
        user_id: `user-${crypto.randomUUID().slice(0, 8)}`,
        username: body.username || "newuser",
        email: body.email || "new@example.com",
        roles: body.roles || ["user"],
        active: true,
      },
      { status: 201 },
    );
  }),

  http.put("/api/v1/admin/users/:userId", async ({ params, request }) => {
    await delay(50);
    const body = (await request.json()) as {
      email?: string;
      roles?: string[];
      active?: boolean;
    };
    return HttpResponse.json({
      user_id: params.userId,
      username: "updated",
      email: body.email || "updated@example.com",
      roles: body.roles || ["user"],
      active: body.active ?? true,
    });
  }),

  http.delete("/api/v1/admin/users/:userId", async () => {
    await delay(50);
    return new HttpResponse(null, { status: 204 });
  }),

  // Audit Logs
  http.get("/api/v1/admin/audit-logs", async () => {
    await delay(100);
    return HttpResponse.json({
      items: [
        {
          id: "log-1",
          timestamp: new Date().toISOString(),
          user_id: "user-123",
          action: "create",
          resource_type: "workflow",
          resource_id: "wf-1",
        },
        {
          id: "log-2",
          timestamp: new Date().toISOString(),
          user_id: "user-456",
          action: "update",
          resource_type: "connection",
          resource_id: "conn-1",
        },
      ],
      next_cursor: null,
      has_more: false,
    });
  }),

  // Workflow Shares
  http.get("/api/v1/workflows/:id/shares", async () => {
    await delay(50);
    return HttpResponse.json({
      shares: [
        { user_id: "user-1", email: "alice@example.com", permission: "edit" },
        { user_id: "user-2", email: "bob@example.com", permission: "view" },
      ],
      is_public: false,
      share_link: null,
    });
  }),

  http.post("/api/v1/workflows/:id/shares", async () => {
    await delay(50);
    return HttpResponse.json({ success: true });
  }),

  http.delete("/api/v1/workflows/:id/shares/:userId", async () => {
    await delay(50);
    return new HttpResponse(null, { status: 204 });
  }),

  http.put("/api/v1/workflows/:id/public", async () => {
    await delay(50);
    return HttpResponse.json({
      is_public: true,
      share_link: "https://example.com/share/abc123",
    });
  }),

  // Connection Audit Logs
  http.get("/api/v1/connections/audit/logs", async () => {
    await delay(100);
    return HttpResponse.json({
      items: [
        {
          id: "audit-1",
          connection_id: "conn-1",
          action: "created",
          user_id: "user-123",
          timestamp: new Date().toISOString(),
          details: { name: "Production Server" },
        },
      ],
      next_cursor: null,
      has_more: false,
    });
  }),

  // Connection Templates
  http.get("/api/v1/connections/templates", async () => {
    await delay(100);
    return HttpResponse.json({
      templates: [
        {
          id: "tpl-1",
          name: "OpenAI",
          description: "Connect to OpenAI API",
          auth_type: "api_key",
          config_schema: {
            type: "object",
            properties: { api_key: { type: "string" } },
          },
        },
        {
          id: "tpl-2",
          name: "Google Cloud",
          description: "Connect to Google Cloud services",
          auth_type: "oauth2",
          config_schema: { type: "object", properties: {} },
        },
      ],
    });
  }),

  // Bulk Connection Operations
  http.post("/api/v1/connections/bulk/test", async () => {
    await delay(200);
    return HttpResponse.json({
      results: [
        { id: "conn-1", success: true, latency_ms: 150 },
        { id: "conn-2", success: false, error: "Connection refused" },
      ],
    });
  }),

  http.post("/api/v1/connections/bulk/delete", async () => {
    await delay(100);
    return HttpResponse.json({
      deleted: ["conn-1", "conn-2"],
      failed: [],
    });
  }),

  // MCP WebSocket status endpoint (for useMCPConnection hook)
  http.get("/api/v1/mcp/status", async () => {
    await delay(50);
    return HttpResponse.json({
      connected: true,
      server_name: "Test MCP Server",
      capabilities: ["tools", "resources", "prompts"],
    });
  }),

  // MCP tools endpoint (for REST fallback in useMCPConnection hook)
  http.get("/api/v1/mcp/tools", async () => {
    await delay(50);
    return HttpResponse.json({
      tools: [
        { name: "web_search", description: "Search the web for information" },
        { name: "code_executor", description: "Execute code snippets safely" },
        { name: "file_reader", description: "Read contents of files" },
      ],
    });
  }),

  // Observability WebSocket status (for useTraceWebSocket hook)
  http.get("/api/v1/observability/ws/status", async () => {
    await delay(50);
    return HttpResponse.json({
      connected: true,
      active_subscriptions: 5,
    });
  }),

  // ==========================================================================
  // Notification Preferences
  // ==========================================================================

  // Get notification preferences
  http.get("/api/v1/notifications/preferences", async () => {
    await delay(50);
    return HttpResponse.json({
      info_enabled: true,
      success_enabled: true,
      warning_enabled: true,
      error_enabled: true,
    });
  }),

  // Update notification preferences
  http.patch("/api/v1/notifications/preferences", async ({ request }) => {
    await delay(50);
    const body = (await request.json()) as Record<string, boolean>;
    return HttpResponse.json({
      info_enabled: body.info_enabled ?? true,
      success_enabled: body.success_enabled ?? true,
      warning_enabled: body.warning_enabled ?? true,
      error_enabled: body.error_enabled ?? true,
    });
  }),

  // Reset notification preferences to defaults
  http.post("/api/v1/notifications/preferences/reset", async () => {
    await delay(50);
    return HttpResponse.json({
      info_enabled: true,
      success_enabled: true,
      warning_enabled: true,
      error_enabled: true,
    });
  }),
];

// =============================================================================
// Error Handler Factories
// =============================================================================

/** Create a handler that returns a 401 Unauthorized error */
export const createUnauthorizedHandler = (path: string) =>
  http.get(path, () =>
    HttpResponse.json({ detail: "Authentication required" }, { status: 401 }),
  );

/** Create a handler that returns a 500 Internal Server Error */
export const createServerErrorHandler = (
  path: string,
  method: "get" | "post" | "delete" = "get",
) =>
  http[method](path, () =>
    HttpResponse.json({ detail: "Internal server error" }, { status: 500 }),
  );

/** Create a handler that simulates network failure */
export const createNetworkErrorHandler = (path: string) =>
  http.get(path, () => HttpResponse.error());

/** Create a handler with custom delay (for loading state tests) */
export const createDelayedHandler = (
  path: string,
  data: unknown,
  delayMs: number,
) =>
  http.get(path, async () => {
    await delay(delayMs);
    return HttpResponse.json(data as Record<string, unknown>);
  });
