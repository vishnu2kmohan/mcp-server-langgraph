/**
 * ProjectsPage Test Fixtures
 *
 * Shared test data and utilities for ProjectsPage test shards.
 *
 * IMPORTANT: Each test file must define its own hoisted mocks before vi.mock():
 *
 * ```typescript
 * const mockListProjectsQuery = vi.hoisted(() => vi.fn());
 * const mockCreateProjectMutation = vi.hoisted(() => vi.fn());
 * const mockDeleteProjectMutation = vi.hoisted(() => vi.fn());
 *
 * vi.mock("../../api", () => ({
 *   useListProjectsQuery: () => mockListProjectsQuery(),
 *   useCreateProjectMutation: () => mockCreateProjectMutation(),
 *   useDeleteProjectMutation: () => mockDeleteProjectMutation(),
 * }));
 * ```
 *
 * Then create a mocks object to pass to setupDefaultMocks:
 * ```typescript
 * const mocks = { mockListProjectsQuery, mockCreateProjectMutation, mockDeleteProjectMutation };
 * ```
 */

import React from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { vi } from "vitest";
import personaReducer from "../../store/slices/personaSlice";
import sessionReducer from "../../store/slices/sessionSlice";

// =============================================================================
// Render Helper
// =============================================================================

/**
 * Render helper that includes MemoryRouter and Redux Provider.
 * Redux is required for AIEmptyState component which reads persona state.
 */
export const renderWithRouter = (component: React.ReactNode) => {
  const store = configureStore({
    reducer: {
      persona: personaReducer,
      session: sessionReducer,
    },
  });

  return render(
    <Provider store={store}>
      <MemoryRouter>{component}</MemoryRouter>
    </Provider>,
  );
};

// Shared mock data - using snake_case to match API/component expectations
export const mockProjectAlpha = {
  id: "proj-1",
  name: "Project Alpha",
  description: "First project",
  workflow_count: 3,
  session_count: 5,
  connection_count: 2,
  status: "active" as const,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-02T00:00:00Z",
  owner_id: "user-1",
  organization_id: null,
};

export const mockProjectBeta = {
  id: "proj-2",
  name: "Project Beta",
  description: "Second project",
  workflow_count: 1,
  session_count: 10,
  connection_count: 0,
  status: "active" as const,
  created_at: "2025-01-03T00:00:00Z",
  updated_at: "2025-01-04T00:00:00Z",
  owner_id: "user-1",
  organization_id: null,
};

export const mockProjectsListData = {
  items: [mockProjectAlpha, mockProjectBeta],
  total: 2,
  page: 1,
  perPage: 20,
  totalPages: 1,
};

export const mockSingleProjectData = {
  items: [mockProjectAlpha],
  total: 1,
  page: 1,
  perPage: 20,
  totalPages: 1,
};

export const mockEmptyProjectsData = {
  items: [],
  total: 0,
  page: 1,
  perPage: 20,
  totalPages: 0,
};

export const mockPaginatedData = {
  items: [
    {
      id: "proj-1",
      name: "Project One",
      description: "First",
      workflow_count: 1,
      session_count: 1,
      connection_count: 1,
      status: "active" as const,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      owner_id: "user-1",
      organization_id: null,
    },
  ],
  total: 45,
  page: 1,
  per_page: 20,
  total_pages: 3,
};

// =============================================================================
// Mock Setup Helpers
// =============================================================================

interface MockFunctions {
  mockListProjectsQuery: ReturnType<typeof vi.fn>;
  mockCreateProjectMutation: ReturnType<typeof vi.fn>;
  mockDeleteProjectMutation: ReturnType<typeof vi.fn>;
}

/**
 * Setup default mock implementations for RTK Query hooks.
 *
 * @param mocks - Object containing the hoisted mock functions from the test file
 * @param mockCreateFn - Mock function for create mutation trigger
 * @param mockDeleteFn - Mock function for delete mutation trigger
 */
export const setupDefaultMocks = (
  mocks: MockFunctions,
  mockCreateFn: ReturnType<typeof vi.fn>,
  mockDeleteFn: ReturnType<typeof vi.fn>,
) => {
  mocks.mockListProjectsQuery.mockReturnValue({
    data: undefined,
    isLoading: true,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  });
  mocks.mockCreateProjectMutation.mockReturnValue([
    mockCreateFn.mockResolvedValue({ data: {} }),
    { isLoading: false },
  ]);
  mocks.mockDeleteProjectMutation.mockReturnValue([
    mockDeleteFn.mockResolvedValue({ data: {} }),
    { isLoading: false },
  ]);
};
