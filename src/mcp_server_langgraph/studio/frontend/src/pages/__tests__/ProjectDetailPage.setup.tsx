/**
 * ProjectDetailPage Test Setup
 *
 * Shared mocks, utilities, and fixtures for all ProjectDetailPage test shards.
 * Split from ProjectDetailPage.test.tsx for memory optimization.
 */

import { vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { api } from "../../api";
import { ProjectDetailPage } from "../ProjectDetailPage";
import type { ReactNode as _ReactNode } from "react";

// =============================================================================
// MOCK DATA
// =============================================================================

// Mock data uses camelCase to match the transformed API response
// (API uses transformSnakeToCamel before returning data from useGetProjectQuery)
export const mockProject = {
  id: "project-123",
  name: "Test Project",
  description: "A test project for testing",
  organizationId: "org-1",
  ownerId: "user-1",
  createdAt: "2025-01-01T00:00:00Z",
  updatedAt: "2025-01-02T00:00:00Z",
  workflowCount: 2,
  sessionCount: 3,
  connectionCount: 1,
  status: "active",
  workflows: [
    { id: "wf-1", name: "Workflow One", createdAt: "2025-01-01T00:00:00Z" },
    { id: "wf-2", name: "Workflow Two", createdAt: null },
  ],
  sessions: [
    {
      id: "sess-1",
      name: "Session One",
      messageCount: 10,
      createdAt: "2025-01-01T00:00:00Z",
    },
    { id: "sess-2", name: "Session Two", messageCount: 5, createdAt: null },
    { id: "sess-3", name: "Session Three", messageCount: 0, createdAt: null },
  ],
  connections: [
    { id: "conn-1", name: "MCP Server", type: "mcp", status: "active" },
  ],
  members: [
    { userId: "user-1", role: "owner", addedAt: "2025-01-01T00:00:00Z" },
    { userId: "user-2", role: "editor", addedAt: "2025-01-02T00:00:00Z" },
    { userId: "user-3", role: "viewer", addedAt: "2025-01-03T00:00:00Z" },
  ],
};

export const mockEmptyProject = {
  ...mockProject,
  workflowCount: 0,
  sessionCount: 0,
  connectionCount: 0,
  workflows: [],
  sessions: [],
  connections: [],
  members: [],
};

// Default observability data
export const mockObservabilityData = {
  traceCount: 100,
  requestsTotal: 500,
  errorsTotal: 10,
  avgLatencyMs: 150,
};

// Default cost summary data
export const mockCostSummaryData = {
  total_cost: 25.5,
  prompt_tokens: 10000,
  completion_tokens: 5000,
  session_count: 15,
};

// Default cost by model data
export const mockCostByModelData = [
  { model: "gpt-4", cost: 20.0, tokens: 12000 },
  { model: "gpt-3.5-turbo", cost: 5.5, tokens: 8000 },
];

// =============================================================================
// MOCK FUNCTIONS
// =============================================================================

export const mockRefetch = vi.fn();
export const mockAddMember = vi.fn();
export const mockRemoveMember = vi.fn();
export const mockAddConnection = vi.fn();

// =============================================================================
// FEATURE FLAGS INTERFACE
// =============================================================================

export interface FeatureFlagsState {
  workflows?: boolean;
  observability?: boolean;
  cost_dashboard?: boolean;
}

// =============================================================================
// STORE FACTORY
// =============================================================================

export const createStore = () => {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
};

// =============================================================================
// SETUP HELPERS
// =============================================================================

interface MockHooks {
  useGetFeatureFlagsQuery: ReturnType<typeof vi.fn>;
  useGetProjectQuery: ReturnType<typeof vi.fn>;
  useGetProjectObservabilityQuery: ReturnType<typeof vi.fn>;
  useGetProjectLogsQuery: ReturnType<typeof vi.fn>;
  useGetProjectAlertsQuery: ReturnType<typeof vi.fn>;
  useGetProjectCostSummaryQuery: ReturnType<typeof vi.fn>;
  useGetProjectCostByModelQuery: ReturnType<typeof vi.fn>;
  useAddProjectMemberMutation: ReturnType<typeof vi.fn>;
  useRemoveProjectMemberMutation: ReturnType<typeof vi.fn>;
  useAddProjectConnectionMutation: ReturnType<typeof vi.fn>;
}

export function resetAllMocks(): void {
  mockRefetch.mockReset();
  mockAddMember.mockReset();
  mockRemoveMember.mockReset();
  mockAddConnection.mockReset();
}

export function setupDefaultMocks(mocks: MockHooks): void {
  // Feature flags - default all enabled
  // Note: Uses API response names (e.g., "workflows" not "enable_workflows_feature")
  mocks.useGetFeatureFlagsQuery.mockReturnValue({
    data: {
      workflows: true,
      observability: true,
      cost_dashboard: true,
    },
    isLoading: false,
    error: null,
  });

  // Project query - default loaded
  mocks.useGetProjectQuery.mockReturnValue({
    data: mockProject,
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: mockRefetch,
  });

  // Observability hooks
  mocks.useGetProjectObservabilityQuery.mockReturnValue({
    data: mockObservabilityData,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  });

  mocks.useGetProjectLogsQuery.mockReturnValue({
    data: { logs: [], total: 0 },
    isLoading: false,
    error: null,
  });

  mocks.useGetProjectAlertsQuery.mockReturnValue({
    data: { alerts: [], total: 0 },
    isLoading: false,
    error: null,
  });

  // Cost hooks
  mocks.useGetProjectCostSummaryQuery.mockReturnValue({
    data: mockCostSummaryData,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  });

  mocks.useGetProjectCostByModelQuery.mockReturnValue({
    data: mockCostByModelData,
    isLoading: false,
    error: null,
  });

  // Mutation hooks
  mocks.useAddProjectMemberMutation.mockReturnValue([
    mockAddMember.mockReturnValue({ unwrap: () => Promise.resolve() }),
    { isLoading: false },
  ]);

  mocks.useRemoveProjectMemberMutation.mockReturnValue([
    mockRemoveMember.mockReturnValue({ unwrap: () => Promise.resolve() }),
    { isLoading: false },
  ]);

  mocks.useAddProjectConnectionMutation.mockReturnValue([
    mockAddConnection.mockReturnValue({ unwrap: () => Promise.resolve() }),
    { isLoading: false },
  ]);

  // Global fetch mock for child tab operations
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      }),
    ),
  );
}

export function setupFeatureFlags(
  mockUseGetFeatureFlagsQuery: ReturnType<typeof vi.fn>,
  flags: FeatureFlagsState = {},
): void {
  // Note: Uses API response names (e.g., "workflows" not "enable_workflows_feature")
  mockUseGetFeatureFlagsQuery.mockReturnValue({
    data: {
      workflows: flags.workflows ?? true,
      observability: flags.observability ?? true,
      cost_dashboard: flags.cost_dashboard ?? true,
    },
    isLoading: false,
    error: null,
  });
}

// =============================================================================
// RENDER HELPER
// =============================================================================

export function renderWithRouter(
  projectId = "project-123",
  featureFlags: FeatureFlagsState = {},
  mockUseGetFeatureFlagsQuery?: ReturnType<typeof vi.fn>,
): ReturnType<typeof render> {
  // Update feature flags if provided
  if (mockUseGetFeatureFlagsQuery) {
    setupFeatureFlags(mockUseGetFeatureFlagsQuery, featureFlags);
  }

  const store = createStore();
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[`/studio/projects/${projectId}`]}>
        <Routes>
          <Route
            path="/studio/projects/:projectId"
            element={<ProjectDetailPage />}
          />
          <Route path="/studio/projects" element={<div>Projects List</div>} />
          <Route path="/studio/chat" element={<div>Chat Page</div>} />
          <Route path="/studio/workflows" element={<div>Workflows Page</div>} />
        </Routes>
      </MemoryRouter>
    </Provider>,
  );
}
