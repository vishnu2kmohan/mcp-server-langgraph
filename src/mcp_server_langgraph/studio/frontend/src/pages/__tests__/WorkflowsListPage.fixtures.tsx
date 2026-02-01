/**
 * WorkflowsListPage Test Fixtures
 *
 * Shared test data and utilities for WorkflowsListPage test shards.
 *
 * IMPORTANT: Each test file must define its own hoisted mocks before vi.mock():
 *
 * ```typescript
 * const mockListWorkflowsQuery = vi.hoisted(() => vi.fn());
 * const mockDeleteWorkflowMutation = vi.hoisted(() => vi.fn());
 *
 * vi.mock("../../api", () => ({
 *   useListWorkflowsQuery: () => mockListWorkflowsQuery(),
 *   useDeleteWorkflowMutation: () => mockDeleteWorkflowMutation(),
 * }));
 * ```
 *
 * Then create a mocks object to pass to setupDefaultMocks:
 * ```typescript
 * const mocks = { mockListWorkflowsQuery, mockDeleteWorkflowMutation };
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

// =============================================================================
// Mock Workflow Data (camelCase - after RTK Query transformation)
// =============================================================================

export const mockWorkflowAlpha = {
  id: "wf-1",
  name: "Workflow Alpha",
  description: "First workflow for data processing",
  nodeCount: 5,
  edgeCount: 4,
  createdAt: "2025-01-01T00:00:00Z",
  updatedAt: "2025-01-02T00:00:00Z",
};

export const mockWorkflowBeta = {
  id: "wf-2",
  name: "Workflow Beta",
  description: "Second workflow for analysis",
  nodeCount: 8,
  edgeCount: 7,
  createdAt: "2025-01-03T00:00:00Z",
  updatedAt: "2025-01-04T00:00:00Z",
};

export const mockWorkflowGamma = {
  id: "wf-3",
  name: "Workflow Gamma",
  description: "Third workflow with no description",
  nodeCount: 3,
  edgeCount: 2,
  createdAt: "2025-01-05T00:00:00Z",
  updatedAt: "2025-01-06T00:00:00Z",
};

// =============================================================================
// Cursor-Paginated Response Mocks
// =============================================================================

export const mockWorkflowsListData = {
  items: [mockWorkflowAlpha, mockWorkflowBeta],
  pagination: {
    count: 2,
    has_next: false,
    has_prev: false,
    next_cursor: null,
    prev_cursor: null,
  },
  count: 2,
  hasNext: false,
  hasPrev: false,
  nextCursor: undefined,
  prevCursor: undefined,
};

export const mockSingleWorkflowData = {
  items: [mockWorkflowAlpha],
  pagination: {
    count: 1,
    has_next: false,
    has_prev: false,
    next_cursor: null,
    prev_cursor: null,
  },
  count: 1,
  hasNext: false,
  hasPrev: false,
  nextCursor: undefined,
  prevCursor: undefined,
};

export const mockEmptyWorkflowsData = {
  items: [],
  pagination: {
    count: 0,
    has_next: false,
    has_prev: false,
    next_cursor: null,
    prev_cursor: null,
  },
  count: 0,
  hasNext: false,
  hasPrev: false,
  nextCursor: undefined,
  prevCursor: undefined,
};

export const mockPaginatedWorkflowsData = {
  items: [mockWorkflowAlpha, mockWorkflowBeta, mockWorkflowGamma],
  pagination: {
    count: 3,
    has_next: true,
    has_prev: false,
    next_cursor: "cursor-next-page",
    prev_cursor: null,
  },
  count: 3,
  hasNext: true,
  hasPrev: false,
  nextCursor: "cursor-next-page",
  prevCursor: undefined,
};

export const mockSecondPageData = {
  items: [
    {
      id: "wf-4",
      name: "Workflow Delta",
      description: "Fourth workflow",
      nodeCount: 2,
      edgeCount: 1,
      createdAt: "2025-01-07T00:00:00Z",
      updatedAt: "2025-01-08T00:00:00Z",
    },
  ],
  pagination: {
    count: 1,
    has_next: false,
    has_prev: true,
    next_cursor: null,
    prev_cursor: "cursor-prev-page",
  },
  count: 1,
  hasNext: false,
  hasPrev: true,
  nextCursor: undefined,
  prevCursor: "cursor-prev-page",
};

// =============================================================================
// Mock Setup Helpers
// =============================================================================

interface MockFunctions {
  mockListWorkflowsQuery: ReturnType<typeof vi.fn>;
  mockDeleteWorkflowMutation: ReturnType<typeof vi.fn>;
}

/**
 * Create a mock mutation trigger that returns an RTK Query-like result with unwrap().
 * RTK Query mutations return { unwrap: () => Promise<result> }, not a direct Promise.
 */
const createMockMutationTrigger = (mockDeleteFn: ReturnType<typeof vi.fn>) => {
  // Track calls to mockDeleteFn but return RTK Query-like structure
  return (id: string) => {
    // Call the mock function to track invocations
    (mockDeleteFn as (id: string) => void)(id);
    return {
      unwrap: () => Promise.resolve({ data: {} }),
    };
  };
};

/**
 * Setup default mock implementations for RTK Query hooks.
 *
 * @param mocks - Object containing the hoisted mock functions from the test file
 * @param mockDeleteFn - Mock function for delete mutation trigger
 */
export const setupDefaultMocks = (
  mocks: MockFunctions,
  mockDeleteFn: ReturnType<typeof vi.fn>,
) => {
  mocks.mockListWorkflowsQuery.mockReturnValue({
    data: undefined,
    isLoading: true,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  });
  mocks.mockDeleteWorkflowMutation.mockReturnValue([
    createMockMutationTrigger(mockDeleteFn),
    { isLoading: false },
  ]);
};

/**
 * Setup mock with loaded workflows data.
 */
export const setupLoadedMocks = (
  mocks: MockFunctions,
  mockDeleteFn: ReturnType<typeof vi.fn>,
  data = mockWorkflowsListData,
) => {
  mocks.mockListWorkflowsQuery.mockReturnValue({
    data,
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  });
  mocks.mockDeleteWorkflowMutation.mockReturnValue([
    createMockMutationTrigger(mockDeleteFn),
    { isLoading: false },
  ]);
};
