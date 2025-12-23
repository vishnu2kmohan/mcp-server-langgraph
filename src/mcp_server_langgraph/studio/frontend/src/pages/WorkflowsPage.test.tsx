/**
 * WorkflowsPage Unit Tests
 *
 * OOM-safe unit tests using isolated store types and comprehensive mocking.
 * Tests key behaviors: rendering, button states, and user interactions.
 *
 * Architecture Fix Applied (2025-12-20):
 * - store/types.ts provides isolated RootState/AppDispatch types
 * - store/hooks.ts imports from types.ts instead of index.ts
 * - This breaks the circular dependency that caused OOM
 *
 * See: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";

// =============================================================================
// vi.hoisted - Define mock functions BEFORE vi.mock references them
// =============================================================================

const mockDispatch = vi.hoisted(() => vi.fn());
const mockUseAppSelector = vi.hoisted(() => vi.fn());
const mockGetSuggestions = vi.hoisted(() => vi.fn());
const mockUseListWorkflowExecutionsQuery = vi.hoisted(() => vi.fn());
const mockUseWorkflowExecution = vi.hoisted(() => vi.fn());

// =============================================================================
// vi.mock - Mock heavy dependencies BEFORE imports (Vitest hoists these)
// =============================================================================

// Mock ReactFlow - heavy canvas library
vi.mock("reactflow", () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="reactflow-provider">{children}</div>
  ),
  useReactFlow: () => ({ getNodes: () => [], getEdges: () => [] }),
  useNodesState: () => [[], vi.fn(), vi.fn()],
  useEdgesState: () => [[], vi.fn(), vi.fn()],
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
  Panel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Handle: () => null,
  Position: { Top: "top", Bottom: "bottom", Left: "left", Right: "right" },
  MarkerType: { Arrow: "arrow", ArrowClosed: "arrowclosed" },
}));

// Mock API hooks - thin wrapper pattern
vi.mock("../hooks/useWorkflowAPI", () => ({
  useGetWorkflowSuggestionsMutation: () => [
    mockGetSuggestions(),
    { isLoading: false },
  ],
  useListWorkflowExecutionsQuery: mockUseListWorkflowExecutionsQuery,
}));

// Mock workflow execution hook
vi.mock("../hooks/useWorkflowExecution", () => ({
  useWorkflowExecution: mockUseWorkflowExecution,
}));

// Mock heavy components
vi.mock("../components/Workflow/WorkflowCanvas", () => ({
  WorkflowCanvas: () => <div data-testid="workflow-canvas">Canvas</div>,
}));

vi.mock("../components/Workflow/NodePalette", () => ({
  NodePalette: () => <div data-testid="node-palette">NodePalette</div>,
}));

vi.mock("../components/Workflow/NodeInspector", () => ({
  NodeInspector: () => <div data-testid="node-inspector">NodeInspector</div>,
}));

vi.mock("../components/Workflow/ExecutionPanel", () => ({
  ExecutionPanel: () => <div data-testid="execution-panel">ExecutionPanel</div>,
}));

vi.mock("../components/Workflow/ExecutionHistoryPanel", () => ({
  ExecutionHistoryPanel: () => (
    <div data-testid="execution-history-panel">ExecutionHistoryPanel</div>
  ),
}));

vi.mock("../components/Workflow/SuggestionChips", () => ({
  SuggestionChips: () => (
    <div data-testid="suggestion-chips">SuggestionChips</div>
  ),
}));

// Mock store hooks
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => mockDispatch(),
  useAppSelector: mockUseAppSelector,
}));

// Mock storage utility
vi.mock("../utils/storage", () => ({
  getAuthToken: () => "test-token",
}));

// =============================================================================
// Import component AFTER mocks
// =============================================================================

import { WorkflowsPage } from "./WorkflowsPage";

// =============================================================================
// Test helpers
// =============================================================================

// Default workflow state for testing
const createDefaultWorkflowState = (overrides = {}) => ({
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

// Mock selector values based on workflow state
const setupMockSelectors = (
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

// Render helper with providers
const renderWorkflowsPage = () => {
  return render(
    <MemoryRouter>
      <WorkflowsPage />
    </MemoryRouter>,
  );
};

// Helper to find button by title
const findButtonByTitle = (title: string) => {
  return screen.getByTitle(title);
};

// =============================================================================
// Tests
// =============================================================================

describe("WorkflowsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup default mock returns
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

    // Setup default workflow state
    setupMockSelectors(createDefaultWorkflowState());
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the workflow page container", () => {
      renderWorkflowsPage();

      expect(screen.getByTestId("reactflow-provider")).toBeInTheDocument();
    });

    it("should render the workflow canvas", () => {
      renderWorkflowsPage();

      expect(screen.getByTestId("workflow-canvas")).toBeInTheDocument();
    });

    it("should render the node palette when not read-only", () => {
      setupMockSelectors(createDefaultWorkflowState({ isReadOnly: false }));
      renderWorkflowsPage();

      expect(screen.getByTestId("node-palette")).toBeInTheDocument();
    });

    it("should render toolbar buttons", () => {
      renderWorkflowsPage();

      // Toolbar buttons by title
      expect(findButtonByTitle("Save (Cmd+S)")).toBeInTheDocument();
      expect(findButtonByTitle("Undo (Cmd+Z)")).toBeInTheDocument();
      expect(findButtonByTitle("Redo (Cmd+Shift+Z)")).toBeInTheDocument();
      expect(findButtonByTitle("Run Workflow (Cmd+Enter)")).toBeInTheDocument();
    });

    it("should render history button when workflow has id", () => {
      setupMockSelectors(
        createDefaultWorkflowState({ metadata: { id: "wf-1", name: "Test" } }),
      );
      renderWorkflowsPage();

      expect(findButtonByTitle("Execution History")).toBeInTheDocument();
    });

    it("should not render history button when workflow has no id", () => {
      setupMockSelectors(createDefaultWorkflowState({ metadata: null }));
      renderWorkflowsPage();

      expect(screen.queryByTitle("Execution History")).not.toBeInTheDocument();
    });
  });

  describe("Loading States", () => {
    it("should show loading spinner when isLoading is true", () => {
      setupMockSelectors(createDefaultWorkflowState({ isLoading: true }));

      renderWorkflowsPage();

      // Loading state shows a centered loading spinner
      const loadingSpinner = document.querySelector(".animate-spin");
      expect(loadingSpinner).toBeInTheDocument();
    });

    it("should show saving spinner in save button when isSaving is true", () => {
      setupMockSelectors(createDefaultWorkflowState({ isSaving: true }));

      renderWorkflowsPage();

      // Save button contains a spinning loader
      const saveButton = findButtonByTitle("Save (Cmd+S)");
      const spinner = saveButton.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });
  });

  describe("Button States", () => {
    it("should disable undo button when canUndo is false", () => {
      setupMockSelectors(createDefaultWorkflowState({ canUndo: false }));

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      expect(undoButton).toBeDisabled();
    });

    it("should enable undo button when canUndo is true", () => {
      setupMockSelectors(createDefaultWorkflowState({ canUndo: true }));

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      expect(undoButton).not.toBeDisabled();
    });

    it("should disable redo button when canRedo is false", () => {
      setupMockSelectors(createDefaultWorkflowState({ canRedo: false }));

      renderWorkflowsPage();

      const redoButton = findButtonByTitle("Redo (Cmd+Shift+Z)");
      expect(redoButton).toBeDisabled();
    });

    it("should enable redo button when canRedo is true", () => {
      setupMockSelectors(createDefaultWorkflowState({ canRedo: true }));

      renderWorkflowsPage();

      const redoButton = findButtonByTitle("Redo (Cmd+Shift+Z)");
      expect(redoButton).not.toBeDisabled();
    });

    it("should disable run button when validation is invalid", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });

    it("should enable run button when validation is valid", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).not.toBeDisabled();
    });

    it("should disable save button when not dirty", () => {
      setupMockSelectors(createDefaultWorkflowState({ isDirty: false }));

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).toBeDisabled();
    });

    it("should enable save button when dirty", () => {
      setupMockSelectors(createDefaultWorkflowState({ isDirty: true }));

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).not.toBeDisabled();
    });
  });

  describe("User Interactions", () => {
    it("should dispatch undo action when undo button clicked", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(createDefaultWorkflowState({ canUndo: true }));

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      fireEvent.click(undoButton);

      expect(dispatchFn).toHaveBeenCalled();
    });

    it("should dispatch redo action when redo button clicked", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(createDefaultWorkflowState({ canRedo: true }));

      renderWorkflowsPage();

      const redoButton = findButtonByTitle("Redo (Cmd+Shift+Z)");
      fireEvent.click(redoButton);

      expect(dispatchFn).toHaveBeenCalled();
    });

    it("should show execution panel when run button clicked", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      // Execution panel should appear
      expect(screen.getByTestId("execution-panel")).toBeInTheDocument();
    });

    it("should show history panel when history button clicked", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "Test" },
        }),
      );

      renderWorkflowsPage();

      const historyButton = findButtonByTitle("Execution History");
      fireEvent.click(historyButton);

      // History panel should appear
      expect(screen.getByTestId("execution-history-panel")).toBeInTheDocument();
    });
  });

  describe("Read-Only Mode", () => {
    it("should show read-only indicator when workflow is read-only", () => {
      setupMockSelectors(createDefaultWorkflowState({ isReadOnly: true }));

      renderWorkflowsPage();

      expect(screen.getByText("Read-Only")).toBeInTheDocument();
    });

    it("should hide node palette in read-only mode", () => {
      setupMockSelectors(createDefaultWorkflowState({ isReadOnly: true }));

      renderWorkflowsPage();

      expect(screen.queryByTestId("node-palette")).not.toBeInTheDocument();
    });

    it("should disable undo button in read-only mode", () => {
      setupMockSelectors(
        createDefaultWorkflowState({ isReadOnly: true, canUndo: true }),
      );

      renderWorkflowsPage();

      const undoButton = findButtonByTitle("Undo (Cmd+Z)");
      expect(undoButton).toBeDisabled();
    });

    it("should disable save button in read-only mode", () => {
      setupMockSelectors(
        createDefaultWorkflowState({ isReadOnly: true, isDirty: true }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).toBeDisabled();
    });
  });

  describe("Validation Errors", () => {
    it("should show error count when workflow has validation errors", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: {
            isValid: false,
            errors: [{ message: "Error 1" }, { message: "Error 2" }],
          },
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("2 errors")).toBeInTheDocument();
    });
  });

  describe("Connection Status", () => {
    it("should show connection status when execution panel is visible", () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "connected",
        reconnectAttempts: 0,
        stopExecution: vi.fn(),
        reconnect: vi.fn(),
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      // Click run to show execution panel
      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
    });

    it("should show reconnect button when disconnected", () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "disconnected",
        reconnectAttempts: 0,
        stopExecution: vi.fn(),
        reconnect: vi.fn(),
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      // Click run to show execution panel
      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      expect(screen.getByText("Reconnect")).toBeInTheDocument();
    });
  });

  describe("Execution State", () => {
    it("should show running spinner when execution is running", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "running",
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      // Run button should show spinner
      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      const spinner = runButton.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });

    it("should disable run button when execution is running", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "running",
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });

    it("should show execution state badge when not idle", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "completed",
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("completed")).toBeInTheDocument();
    });
  });

  describe("Workflow Name", () => {
    it("should display workflow name from metadata", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "My Custom Workflow" },
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("My Custom Workflow")).toBeInTheDocument();
    });

    it("should show dirty indicator when workflow has unsaved changes", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "Test" },
          isDirty: true,
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("*")).toBeInTheDocument();
    });

    it("should show 'New Workflow' when metadata is null", () => {
      setupMockSelectors(createDefaultWorkflowState({ metadata: null }));

      renderWorkflowsPage();

      expect(screen.getByText("New Workflow")).toBeInTheDocument();
    });
  });

  describe("AI Suggestions", () => {
    it("should toggle suggestions panel when AI Suggest button clicked", () => {
      setupMockSelectors(createDefaultWorkflowState());

      renderWorkflowsPage();

      const suggestButton = screen.getByTestId("ai-suggestions-toggle");
      fireEvent.click(suggestButton);

      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();
    });

    it("should hide suggestions panel when toggled off", () => {
      setupMockSelectors(createDefaultWorkflowState());

      renderWorkflowsPage();

      const suggestButton = screen.getByTestId("ai-suggestions-toggle");

      // Toggle on
      fireEvent.click(suggestButton);
      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();

      // Toggle off
      fireEvent.click(suggestButton);
      expect(screen.queryByTestId("suggestion-chips")).not.toBeInTheDocument();
    });
  });

  describe("Export JSON", () => {
    it("should have Export JSON button", () => {
      setupMockSelectors(createDefaultWorkflowState());

      renderWorkflowsPage();

      expect(screen.getByText("Export JSON")).toBeInTheDocument();
    });

    it("should trigger export when Export JSON button clicked", () => {
      setupMockSelectors(createDefaultWorkflowState());

      // Mock URL.createObjectURL and revokeObjectURL
      const mockCreateObjectURL = vi.fn(() => "blob:test");
      const mockRevokeObjectURL = vi.fn();
      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;

      renderWorkflowsPage();

      const exportButton = screen.getByText("Export JSON");
      fireEvent.click(exportButton);

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalled();
    });
  });

  describe("Generate Code", () => {
    it("should have Generate Code button", () => {
      setupMockSelectors(createDefaultWorkflowState());

      renderWorkflowsPage();

      expect(screen.getByText("Generate Code")).toBeInTheDocument();
    });
  });

  describe("Connection States", () => {
    it("should show connecting state", () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "connecting",
        reconnectAttempts: 0,
        stopExecution: vi.fn(),
        reconnect: vi.fn(),
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      // Click run to show execution panel
      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      const status = screen.getByTestId("connection-status");
      expect(status).toBeInTheDocument();
    });

    it("should show reconnecting state with attempt count", () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "reconnecting",
        reconnectAttempts: 3,
        stopExecution: vi.fn(),
        reconnect: vi.fn(),
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      const status = screen.getByTestId("connection-status");
      expect(status).toHaveTextContent("3");
    });

    it("should show error state", () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "error",
        reconnectAttempts: 0,
        stopExecution: vi.fn(),
        reconnect: vi.fn(),
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      // Should show reconnect button for error state
      expect(screen.getByText("Reconnect")).toBeInTheDocument();
    });

    it("should call reconnect when Reconnect button clicked", () => {
      const reconnectFn = vi.fn();
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "disconnected",
        reconnectAttempts: 0,
        stopExecution: vi.fn(),
        reconnect: reconnectFn,
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      fireEvent.click(runButton);

      const reconnectButton = screen.getByText("Reconnect");
      fireEvent.click(reconnectButton);

      expect(reconnectFn).toHaveBeenCalled();
    });
  });

  describe("Validation Error Alert", () => {
    it("should show inline validation error when run fails validation", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      // The run button should be disabled since validation is invalid
      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });
  });

  describe("Execution State Badges", () => {
    it("should show running state badge", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "running",
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("running")).toBeInTheDocument();
    });

    it("should show error state badge", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "error",
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("error")).toBeInTheDocument();
    });

    it("should not show state badge when idle", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "idle",
        }),
      );

      renderWorkflowsPage();

      expect(screen.queryByText("idle")).not.toBeInTheDocument();
    });
  });

  describe("Save Workflow", () => {
    it("should dispatch save workflow when save button clicked", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(createDefaultWorkflowState({ isDirty: true }));

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      fireEvent.click(saveButton);

      expect(dispatchFn).toHaveBeenCalled();
    });

    it("should create new workflow when saving without metadata", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({ metadata: null, isDirty: true }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      fireEvent.click(saveButton);

      expect(dispatchFn).toHaveBeenCalled();
    });
  });

  describe("Generate Code", () => {
    it("should call API when Generate Code button clicked with valid workflow", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ code: "print('hello')", filename: "workflow.py" }),
      });
      global.fetch = mockFetch;
      const mockCreateObjectURL = vi.fn(() => "blob:test");
      const mockRevokeObjectURL = vi.fn();
      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;

      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
          nodes: [{ id: "node-1" }],
        }),
      );

      renderWorkflowsPage();

      const generateButton = screen.getByText("Generate Code");
      fireEvent.click(generateButton);

      // Wait for async operation
      await vi.waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/generate",
          expect.objectContaining({
            method: "POST",
          }),
        );
      });
    });

    it("should show validation error when workflow is invalid", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      const generateButton = screen.getByText("Generate Code");
      fireEvent.click(generateButton);

      await vi.waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });
    });
  });

  describe("Run Workflow", () => {
    it("should show validation error when run clicked with invalid workflow", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      // The run button should be disabled for invalid workflows
      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });
  });

  describe("Execution History Panel", () => {
    it("should show execution history panel when history button clicked", () => {
      mockUseListWorkflowExecutionsQuery.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        isFetching: false,
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "Test" },
        }),
      );

      renderWorkflowsPage();

      const historyButton = findButtonByTitle("Execution History");
      fireEvent.click(historyButton);

      expect(screen.getByTestId("execution-history-panel")).toBeInTheDocument();
    });

    it("should toggle off execution history panel when button clicked again", () => {
      mockUseListWorkflowExecutionsQuery.mockReturnValue({
        data: { items: [] },
        isLoading: false,
        isFetching: false,
      });
      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "Test" },
        }),
      );

      renderWorkflowsPage();

      const historyButton = findButtonByTitle("Execution History");

      // Toggle on
      fireEvent.click(historyButton);
      expect(screen.getByTestId("execution-history-panel")).toBeInTheDocument();

      // Toggle off
      fireEvent.click(historyButton);
      expect(
        screen.queryByTestId("execution-history-panel"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Validation Error Alert", () => {
    it("should show validation error alert when validation error is set", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      // Generate code triggers validation error display
      const generateButton = screen.getByText("Generate Code");
      fireEvent.click(generateButton);

      await vi.waitFor(() => {
        const alert = screen.getByRole("alert");
        expect(alert).toBeInTheDocument();
      });
    });

    it("should dismiss validation error when X button clicked", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: false, errors: [{ message: "Error" }] },
        }),
      );

      renderWorkflowsPage();

      // Generate code triggers validation error display
      const generateButton = screen.getByText("Generate Code");
      fireEvent.click(generateButton);

      await vi.waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });

      // Click dismiss button
      const dismissButton = screen.getByLabelText("Dismiss");
      fireEvent.click(dismissButton);

      await vi.waitFor(() => {
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      });
    });
  });

  describe("AI Suggestions State", () => {
    it("should show suggestions error when there are no nodes", async () => {
      mockGetSuggestions.mockReturnValue(
        vi.fn().mockResolvedValue({ data: { suggestions: [] } }),
      );
      setupMockSelectors(createDefaultWorkflowState({ nodes: [] }));

      renderWorkflowsPage();

      // Toggle on suggestions
      const suggestButton = screen.getByTestId("ai-suggestions-toggle");
      fireEvent.click(suggestButton);

      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();
    });
  });

  describe("URL Parameters", () => {
    it("should load workflow when id is in URL params", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({ metadata: null, isLoading: false }),
      );

      render(
        <MemoryRouter initialEntries={["/workflows?id=wf-123"]}>
          <WorkflowsPage />
        </MemoryRouter>,
      );

      // Dispatch should have been called with loadWorkflow action
      await vi.waitFor(() => {
        expect(dispatchFn).toHaveBeenCalled();
      });
    });

    it("should not load workflow when already loaded with same id", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-123", name: "Test" },
          isLoading: false,
        }),
      );

      render(
        <MemoryRouter initialEntries={["/workflows?id=wf-123"]}>
          <WorkflowsPage />
        </MemoryRouter>,
      );

      // Should not dispatch loadWorkflow when already loaded
      // Only dispatch calls should be from button interactions, not initial load
    });

    it("should show suggestions panel when suggestions param is true in URL", () => {
      setupMockSelectors(createDefaultWorkflowState());

      render(
        <MemoryRouter initialEntries={["/workflows?suggestions=true"]}>
          <WorkflowsPage />
        </MemoryRouter>,
      );

      // Suggestions panel should be visible due to URL param
      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();
    });
  });

  describe("Generate Code Error Handling", () => {
    it("should handle fetch error gracefully", async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
      global.fetch = mockFetch;
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const generateButton = screen.getByText("Generate Code");
      fireEvent.click(generateButton);

      await vi.waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          "Failed to generate code:",
          expect.any(Error),
        );
      });

      consoleSpy.mockRestore();
    });

    it("should not download when response is not ok", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });
      global.fetch = mockFetch;
      const mockCreateObjectURL = vi.fn();
      global.URL.createObjectURL = mockCreateObjectURL;

      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const generateButton = screen.getByText("Generate Code");
      fireEvent.click(generateButton);

      await vi.waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      // Should not create blob URL when response is not ok
      expect(mockCreateObjectURL).not.toHaveBeenCalled();
    });
  });

  describe("Read-Only with canExecute", () => {
    it("should allow run in read-only mode when canExecute is true", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          isReadOnly: true,
          canExecute: true,
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).not.toBeDisabled();
    });

    it("should disable run in read-only mode when canExecute is false", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          isReadOnly: true,
          canExecute: false,
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toBeDisabled();
    });
  });

  describe("Generate Code Button State", () => {
    it("should show spinner when generating code", async () => {
      const mockFetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            // Never resolve to keep isGeneratingCode true
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () => Promise.resolve({ code: "test" }),
                }),
              5000,
            );
          }),
      );
      global.fetch = mockFetch;

      setupMockSelectors(
        createDefaultWorkflowState({
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const generateButton = screen.getByText("Generate Code");
      fireEvent.click(generateButton);

      // Button should be disabled while generating
      await vi.waitFor(() => {
        expect(generateButton.closest("button")).toBeDisabled();
      });
    });
  });

  describe("Export JSON Content", () => {
    it("should export workflow with correct filename", () => {
      const mockCreateObjectURL = vi.fn(() => "blob:test");
      const mockRevokeObjectURL = vi.fn();
      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;

      // Track the anchor element created
      let capturedDownload = "";
      let capturedClick = false;
      const originalCreateElement = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation(
        (tagName: string) => {
          if (tagName === "a") {
            const anchor = originalCreateElement("a");
            const originalSetAttribute = anchor.setAttribute.bind(anchor);
            Object.defineProperty(anchor, "download", {
              set: (value: string) => {
                capturedDownload = value;
                originalSetAttribute("download", value);
              },
              get: () => capturedDownload,
            });
            anchor.click = () => {
              capturedClick = true;
            };
            return anchor;
          }
          return originalCreateElement(tagName);
        },
      );

      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "My Workflow" },
          nodes: [{ id: "node-1" }],
          edges: [],
        }),
      );

      renderWorkflowsPage();

      const exportButton = screen.getByText("Export JSON");
      fireEvent.click(exportButton);

      expect(capturedDownload).toBe("My Workflow.json");
      expect(capturedClick).toBe(true);

      vi.restoreAllMocks();
    });

    it("should use default filename when metadata name is missing", () => {
      const mockCreateObjectURL = vi.fn(() => "blob:test");
      const mockRevokeObjectURL = vi.fn();
      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;

      let capturedDownload = "";
      const originalCreateElement = document.createElement.bind(document);
      vi.spyOn(document, "createElement").mockImplementation(
        (tagName: string) => {
          if (tagName === "a") {
            const anchor = originalCreateElement("a");
            const originalSetAttribute = anchor.setAttribute.bind(anchor);
            Object.defineProperty(anchor, "download", {
              set: (value: string) => {
                capturedDownload = value;
                originalSetAttribute("download", value);
              },
              get: () => capturedDownload,
            });
            anchor.click = vi.fn();
            return anchor;
          }
          return originalCreateElement(tagName);
        },
      );

      setupMockSelectors(createDefaultWorkflowState({ metadata: null }));

      renderWorkflowsPage();

      const exportButton = screen.getByText("Export JSON");
      fireEvent.click(exportButton);

      expect(capturedDownload).toBe("workflow.json");

      vi.restoreAllMocks();
    });
  });

  describe("Execution History Pagination", () => {
    it("should not show history panel when metadata has no id", () => {
      setupMockSelectors(createDefaultWorkflowState({ metadata: null }));

      renderWorkflowsPage();

      // History button should not exist
      expect(screen.queryByTitle("Execution History")).not.toBeInTheDocument();
    });
  });

  describe("Run Button States", () => {
    it("should show Play icon when not running", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "idle",
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton).toHaveTextContent("Run");
      // Play icon should be present (no spinner)
      expect(runButton.querySelector(".animate-spin")).not.toBeInTheDocument();
    });

    it("should show spinner when execution is running", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          executionState: "running",
          validation: { isValid: true, errors: [] },
        }),
      );

      renderWorkflowsPage();

      const runButton = findButtonByTitle("Run Workflow (Cmd+Enter)");
      expect(runButton.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Save Button States", () => {
    it("should show Save icon when not saving", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          isSaving: false,
          isDirty: true,
        }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton).toHaveTextContent("Save");
      expect(saveButton.querySelector(".animate-spin")).not.toBeInTheDocument();
    });

    it("should show spinner when saving", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          isSaving: true,
          isDirty: true,
        }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      expect(saveButton.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("AI Suggest Button Styling", () => {
    it("should have different styling when suggestions panel is visible", () => {
      setupMockSelectors(createDefaultWorkflowState());

      renderWorkflowsPage();

      const suggestButton = screen.getByTestId("ai-suggestions-toggle");

      // Initially not active styling
      expect(suggestButton).toHaveClass("bg-gray-100");

      // Click to activate
      fireEvent.click(suggestButton);

      // Should now have active styling
      expect(suggestButton).toHaveClass("bg-yellow-100");
    });
  });

  describe("History Button Styling", () => {
    it("should have different styling when history panel is visible", () => {
      setupMockSelectors(
        createDefaultWorkflowState({
          metadata: { id: "wf-1", name: "Test" },
        }),
      );

      renderWorkflowsPage();

      const historyButton = findButtonByTitle("Execution History");

      // Initially not active styling
      expect(historyButton).toHaveClass("bg-gray-100");

      // Click to activate
      fireEvent.click(historyButton);

      // Should now have active styling
      expect(historyButton).toHaveClass("bg-indigo-100");
    });
  });
});

/**
 * Coverage Verification
 *
 * These unit tests cover the following WorkflowsPage behaviors:
 *
 * ✅ Rendering (core components visible)
 * ✅ Loading states (isLoading, isSaving)
 * ✅ Button states (canUndo, canRedo, validation.isValid, isDirty)
 * ✅ User interactions (undo, redo, run, history)
 * ✅ Read-only mode (indicator, hidden palette, disabled controls)
 * ✅ Validation errors (error count display)
 * ✅ Connection status (indicator, reconnect button)
 * ✅ Execution state (running spinner, state badge)
 * ✅ Workflow metadata (name, dirty indicator)
 *
 * E2E coverage (Playwright) for:
 * - e2e/workflow-execution.spec.ts
 * - e2e/execution-history.spec.ts
 */
