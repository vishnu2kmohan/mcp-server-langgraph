/**
 * WorkflowsPage Test Fixtures
 *
 * Shared state creators and render helpers for WorkflowsPage tests.
 * Centralizes test setup to reduce duplication across test shards.
 *
 * NOTE: Hoisted mocks CANNOT be exported and must be defined in each test file.
 */

import React from "react";
import { vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
export { waitFor };
import { MemoryRouter } from "react-router";
import { WorkflowsPage } from "../WorkflowsPage";

// =============================================================================
// Default Workflow State Factory
// =============================================================================

export const createDefaultWorkflowState = (overrides = {}) => ({
  metadata: { id: "workflow-1", name: "Test Workflow" },
  nodes: [],
  edges: [],
  isDirty: false,
  isSaving: false,
  isLoading: false,
  validation: { isValid: true, errors: [] },
  canUndo: false,
  canRedo: false,
  executionState: "idle", // String, not object!
  isReadOnly: false,
  canExecute: true,
  ...overrides,
});

// =============================================================================
// Mock Selector Setup
// =============================================================================

export const setupMockSelectors = (
  mockUseAppSelector: ReturnType<typeof vi.fn>,
  workflowState: ReturnType<typeof createDefaultWorkflowState>,
) => {
  mockUseAppSelector.mockImplementation(
    (selector: (state: unknown) => unknown) => {
      // Map selectors to state values based on selector name
      const selectorName = selector.name || selector.toString();

      if (selectorName.includes("Metadata")) return workflowState.metadata;
      if (selectorName.includes("Nodes")) return workflowState.nodes;
      if (selectorName.includes("Edges")) return workflowState.edges;
      if (selectorName.includes("IsDirty")) return workflowState.isDirty;
      if (selectorName.includes("IsSaving")) return workflowState.isSaving;
      if (selectorName.includes("IsLoading")) return workflowState.isLoading;
      if (selectorName.includes("Validation")) return workflowState.validation;
      if (selectorName.includes("CanUndo")) return workflowState.canUndo;
      if (selectorName.includes("CanRedo")) return workflowState.canRedo;
      if (selectorName.includes("ExecutionState"))
        return workflowState.executionState;
      if (selectorName.includes("IsReadOnly")) return workflowState.isReadOnly;
      if (selectorName.includes("CanExecute")) return workflowState.canExecute;

      // Default return for unmatched selectors
      return undefined;
    },
  );
};

// =============================================================================
// Render Helpers
// =============================================================================

export const renderWorkflowsPage = () => {
  return render(
    <MemoryRouter>
      <WorkflowsPage />
    </MemoryRouter>,
  );
};

export const renderWorkflowsPageWithRoute = (route: string) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <WorkflowsPage />
    </MemoryRouter>,
  );
};

// =============================================================================
// Test Utilities
// =============================================================================

export const findButtonByTitle = (title: string) => {
  return screen.getByTitle(title);
};

// =============================================================================
// Default Mock Setup (for beforeEach)
// =============================================================================

export const setupDefaultMocks = (
  mockDispatch: ReturnType<typeof vi.fn>,
  mockGetSuggestions: ReturnType<typeof vi.fn>,
  mockUseListWorkflowExecutionsQuery: ReturnType<typeof vi.fn>,
  mockUseWorkflowExecution: ReturnType<typeof vi.fn>,
  mockUseAppSelector: ReturnType<typeof vi.fn>,
) => {
  vi.clearAllMocks();

  mockDispatch.mockReturnValue(vi.fn());
  mockGetSuggestions.mockReturnValue(vi.fn());
  mockUseListWorkflowExecutionsQuery.mockReturnValue({
    data: { items: [] },
    isLoading: false,
    isFetching: false,
  });
  mockUseWorkflowExecution.mockReturnValue({
    connectionStatus: "connected",
    reconnectAttempts: 0,
    stopExecution: vi.fn(),
    reconnect: vi.fn(),
  });

  setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());
};
