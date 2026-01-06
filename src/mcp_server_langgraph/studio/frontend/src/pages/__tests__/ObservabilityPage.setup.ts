/**
 * ObservabilityPage Test Setup
 *
 * Shared mocks, utilities, and fixtures for ObservabilityPage test shards.
 * This file centralizes mock implementations to reduce duplication and
 * ensure consistent test behavior across all shard files.
 *
 * Split from ObservabilityPage.test.tsx for memory optimization.
 * See: ~/.claude/plans/spicy-honking-rain.md (Phase 2)
 */

import { vi } from "vitest";

// =============================================================================
// MOCK REFETCH FUNCTIONS
// =============================================================================

export const mockRefetchTraces = vi.fn();
export const mockRefetchLogs = vi.fn();
export const mockRefetchMetrics = vi.fn();
export const mockRefetchAlerts = vi.fn();
export const mockRefetchSessions = vi.fn();
export const mockRefetchWorkflows = vi.fn();

// =============================================================================
// MOCK DATA
// =============================================================================

export const mockTraces = [
  {
    traceId: "1",
    spanId: "s1",
    name: "chat/completion",
    startTime: new Date().toISOString(),
    endTime: new Date(Date.now() + 1234).toISOString(),
    status: "success",
    attributes: {},
  },
  {
    traceId: "2",
    spanId: "s2",
    name: "tools/execute",
    startTime: new Date(Date.now() - 60000).toISOString(),
    endTime: new Date(Date.now() - 60000 + 567).toISOString(),
    status: "success",
    attributes: {},
  },
];

export const mockLogs = [
  {
    id: "log-1",
    level: "info",
    message: "Processing request",
    timestamp: new Date().toISOString(),
    service: "agent",
  },
  {
    id: "log-2",
    level: "error",
    message: "Connection failed",
    timestamp: new Date().toISOString(),
    service: "mcp",
  },
];

export const mockMetrics = {
  requestsTotal: 1523,
  errorsTotal: 12,
  avgLatencyMs: 234,
  p99LatencyMs: 890,
  tokensUsed: 45678,
  activeSessions: 8,
};

export const mockAlerts = [
  {
    alertId: "alert-1",
    name: "High Memory Usage",
    severity: "warning",
    state: "firing",
    message: "Memory usage is above 80%",
    labels: { service: "mcp-server", severity: "warning" },
    annotations: { summary: "High memory alert" },
    startedAt: new Date().toISOString(),
    endedAt: null,
    generatorUrl: "http://grafana/alerting/1",
  },
  {
    alertId: "alert-2",
    name: "API Latency High",
    severity: "critical",
    state: "firing",
    message: "API latency exceeds threshold",
    labels: { service: "api-gateway", severity: "critical" },
    annotations: { summary: "High latency detected" },
    startedAt: new Date(Date.now() - 300000).toISOString(),
    endedAt: null,
    generatorUrl: null,
  },
];

export const mockSessions = [
  {
    id: "session-1",
    name: "Agent Chat Session",
    workflowId: null,
    userId: "user-123",
    status: "active",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    config: null,
  },
  {
    id: "session-2",
    name: "Data Analysis Session",
    workflowId: "workflow-1",
    userId: "user-456",
    status: "archived",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    config: null,
  },
];

export const mockWorkflows = [
  {
    id: "workflow-1",
    name: "Data Pipeline",
    description: "ETL workflow for data processing",
    nodeCount: 5,
    edgeCount: 4,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "workflow-2",
    name: "Report Generator",
    description: "Automated report generation workflow",
    nodeCount: 3,
    edgeCount: 2,
    createdAt: new Date(Date.now() - 172800000).toISOString(),
    updatedAt: new Date(Date.now() - 172800000).toISOString(),
  },
];

// =============================================================================
// TRACE INTELLIGENCE MOCK STATE
// =============================================================================

export const mockTraceSummary = {
  summary: null,
  totalDurationMs: null,
  stepCount: null,
  toolCallCount: null,
  success: null,
  keyActions: [],
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

export const mockTraceAnomaly = {
  anomalies: [],
  bottlenecks: [],
  healthScore: null,
  optimizationSuggestions: [],
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

// =============================================================================
// MOCK IMPLEMENTATIONS (for vi.mock)
// =============================================================================

/**
 * API mock implementation.
 * Usage: vi.mock("../../api", async (importOriginal) => apiMockFactory(importOriginal))
 */
export const apiMockFactory = async (
  importOriginal: () => Promise<typeof import("../../api")>,
) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useListTracesQuery: vi.fn(),
    useListLogsQuery: vi.fn(),
    useGetMetricsQuery: vi.fn(),
    useGetTraceQuery: vi.fn(),
    useListAlertsQuery: vi.fn(),
    useListSessionsQuery: vi.fn(),
    useListWorkflowsQuery: vi.fn(),
  };
};

/**
 * Trace Intelligence mock implementation.
 */
export const traceIntelligenceMock = {
  useTraceSummary: vi.fn(() => mockTraceSummary),
  useTraceAnomaly: vi.fn(() => mockTraceAnomaly),
};

/**
 * Feature Flag mock implementation.
 */
export const featureFlagMock = {
  useFeatureFlag: vi.fn(() => false),
};

// =============================================================================
// SETUP HELPERS
// =============================================================================

/**
 * Resets all mock functions and state.
 * Call in beforeEach to ensure clean test isolation.
 */
export function resetAllMocks(): void {
  mockRefetchTraces.mockReset();
  mockRefetchLogs.mockReset();
  mockRefetchMetrics.mockReset();
  mockRefetchAlerts.mockReset();
  mockRefetchSessions.mockReset();
  mockRefetchWorkflows.mockReset();
  mockTraceSummary.refetch.mockReset();
  mockTraceAnomaly.refetch.mockReset();
}

/**
 * Default mock return values setup.
 * Call in beforeEach after importing mocked hooks.
 */
export function setupDefaultMocks(mocks: {
  useListTracesQuery: ReturnType<typeof vi.fn>;
  useListLogsQuery: ReturnType<typeof vi.fn>;
  useGetMetricsQuery: ReturnType<typeof vi.fn>;
  useGetTraceQuery: ReturnType<typeof vi.fn>;
  useListAlertsQuery: ReturnType<typeof vi.fn>;
  useListSessionsQuery: ReturnType<typeof vi.fn>;
  useListWorkflowsQuery: ReturnType<typeof vi.fn>;
}): void {
  mocks.useListTracesQuery.mockReturnValue({
    data: { items: mockTraces, total: 2, limit: 50 },
    isLoading: false,
    error: null,
    refetch: mockRefetchTraces,
  });

  mocks.useListLogsQuery.mockReturnValue({
    data: { items: mockLogs, total: 2, limit: 50 },
    isLoading: false,
    error: null,
    refetch: mockRefetchLogs,
  });

  mocks.useGetMetricsQuery.mockReturnValue({
    data: mockMetrics,
    isLoading: false,
    error: null,
    refetch: mockRefetchMetrics,
  });

  mocks.useListAlertsQuery.mockReturnValue({
    data: { items: mockAlerts, total: 2 },
    isLoading: false,
    error: null,
    refetch: mockRefetchAlerts,
  });

  mocks.useGetTraceQuery.mockReturnValue({
    data: null,
    isLoading: false,
    error: null,
  });

  mocks.useListSessionsQuery.mockReturnValue({
    data: { items: mockSessions, total: 2, nextCursor: null },
    isLoading: false,
    error: null,
    refetch: mockRefetchSessions,
  });

  mocks.useListWorkflowsQuery.mockReturnValue({
    data: { items: mockWorkflows, total: 2, nextCursor: null },
    isLoading: false,
    error: null,
    refetch: mockRefetchWorkflows,
  });
}

/**
 * Helper to flush all pending promises.
 */
export function flushPromises(): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, 0);
  });
}
