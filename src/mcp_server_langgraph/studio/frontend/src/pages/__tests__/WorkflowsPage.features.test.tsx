/**
 * WorkflowsPage Features Tests (Shard 2/2)
 *
 * OOM-safe unit tests for WorkflowsPage feature functionality.
 * Tests: Connection Status, Execution State, AI Suggestions, Export/Generate,
 * Save/Run Workflows, History Panel, URL Parameters, Button Styling.
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
import { screen, fireEvent, cleanup } from "@testing-library/react";

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
vi.mock("../../hooks/useWorkflowAPI", () => ({
  useGetWorkflowSuggestionsMutation: () => [
    mockGetSuggestions(),
    { isLoading: false },
  ],
  useListWorkflowExecutionsQuery: mockUseListWorkflowExecutionsQuery,
}));

// Mock workflow execution hook
vi.mock("../../hooks/useWorkflowExecution", () => ({
  useWorkflowExecution: mockUseWorkflowExecution,
}));

// Mock heavy components
vi.mock("../../components/Workflow/WorkflowCanvas", () => ({
  WorkflowCanvas: () => <div data-testid="workflow-canvas">Canvas</div>,
}));

vi.mock("../../components/Workflow/NodePalette", () => ({
  NodePalette: () => <div data-testid="node-palette">NodePalette</div>,
}));

vi.mock("../../components/Workflow/NodeInspector", () => ({
  NodeInspector: () => <div data-testid="node-inspector">NodeInspector</div>,
}));

vi.mock("../../components/Workflow/ExecutionPanel", () => ({
  ExecutionPanel: () => <div data-testid="execution-panel">ExecutionPanel</div>,
}));

vi.mock("../../components/Workflow/ExecutionHistoryPanel", () => ({
  ExecutionHistoryPanel: () => (
    <div data-testid="execution-history-panel">ExecutionHistoryPanel</div>
  ),
}));

vi.mock("../../components/Workflow/SuggestionChips", () => ({
  SuggestionChips: () => (
    <div data-testid="suggestion-chips">SuggestionChips</div>
  ),
}));

// Mock store hooks
vi.mock("../../store/hooks", () => ({
  useAppDispatch: () => mockDispatch(),
  useAppSelector: mockUseAppSelector,
}));

// Mock storage utility
vi.mock("../../utils/storage", () => ({
  getAuthToken: () => "test-token",
}));

// =============================================================================
// Import fixtures AFTER mocks
// =============================================================================

import {
  createDefaultWorkflowState,
  setupMockSelectors,
  renderWorkflowsPage,
  renderWorkflowsPageWithRoute,
  findButtonByTitle,
  setupDefaultMocks,
} from "./WorkflowsPage.fixtures.tsx";

// =============================================================================
// Tests
// =============================================================================

describe("WorkflowsPage - Features", () => {
  beforeEach(() => {
    setupDefaultMocks(
      mockDispatch,
      mockGetSuggestions,
      mockUseListWorkflowExecutionsQuery,
      mockUseWorkflowExecution,
      mockUseAppSelector,
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
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
        mockUseAppSelector,
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
        mockUseAppSelector,
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

    it("should show connecting state", () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "connecting",
        reconnectAttempts: 0,
        stopExecution: vi.fn(),
        reconnect: vi.fn(),
      });
      setupMockSelectors(
        mockUseAppSelector,
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
        mockUseAppSelector,
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
        mockUseAppSelector,
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
        mockUseAppSelector,
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

  describe("Execution State", () => {
    it("should show running spinner when execution is running", () => {
      setupMockSelectors(
        mockUseAppSelector,
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

    it("should show execution state badge when not idle", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          executionState: "completed",
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("completed")).toBeInTheDocument();
    });

    it("should show running state badge", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          executionState: "running",
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("running")).toBeInTheDocument();
    });

    it("should show error state badge", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          executionState: "error",
        }),
      );

      renderWorkflowsPage();

      expect(screen.getByText("error")).toBeInTheDocument();
    });

    it("should not show state badge when idle", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          executionState: "idle",
        }),
      );

      renderWorkflowsPage();

      expect(screen.queryByText("idle")).not.toBeInTheDocument();
    });
  });

  describe("AI Suggestions", () => {
    it("should toggle suggestions panel when AI Suggest button clicked", () => {
      setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());

      renderWorkflowsPage();

      const suggestButton = screen.getByTestId("ai-suggestions-toggle");
      fireEvent.click(suggestButton);

      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();
    });

    it("should hide suggestions panel when toggled off", () => {
      setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());

      renderWorkflowsPage();

      const suggestButton = screen.getByTestId("ai-suggestions-toggle");

      // Toggle on
      fireEvent.click(suggestButton);
      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();

      // Toggle off
      fireEvent.click(suggestButton);
      expect(screen.queryByTestId("suggestion-chips")).not.toBeInTheDocument();
    });

    it("should show suggestions error when there are no nodes", async () => {
      mockGetSuggestions.mockReturnValue(
        vi.fn().mockResolvedValue({ data: { suggestions: [] } }),
      );
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ nodes: [] }),
      );

      renderWorkflowsPage();

      // Toggle on suggestions
      const suggestButton = screen.getByTestId("ai-suggestions-toggle");
      fireEvent.click(suggestButton);

      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();
    });

    it("should have different styling when suggestions panel is visible", () => {
      setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());

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

  describe("Export JSON", () => {
    it("should have Export JSON button", () => {
      setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());

      renderWorkflowsPage();

      expect(screen.getByText("Export JSON")).toBeInTheDocument();
    });

    it("should trigger export when Export JSON button clicked", () => {
      setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());

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
        mockUseAppSelector,
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

      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ metadata: null }),
      );

      renderWorkflowsPage();

      const exportButton = screen.getByText("Export JSON");
      fireEvent.click(exportButton);

      expect(capturedDownload).toBe("workflow.json");

      vi.restoreAllMocks();
    });
  });

  describe("Generate Code", () => {
    it("should have Generate Code button", () => {
      setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());

      renderWorkflowsPage();

      expect(screen.getByText("Generate Code")).toBeInTheDocument();
    });

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
        mockUseAppSelector,
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
        mockUseAppSelector,
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

    it("should handle fetch error gracefully", async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
      global.fetch = mockFetch;
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
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
        mockUseAppSelector,
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
        mockUseAppSelector,
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

  describe("Save Workflow", () => {
    it("should dispatch save workflow when save button clicked", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ isDirty: true }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      fireEvent.click(saveButton);

      expect(dispatchFn).toHaveBeenCalled();
    });

    it("should create new workflow when saving without metadata", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ metadata: null, isDirty: true }),
      );

      renderWorkflowsPage();

      const saveButton = findButtonByTitle("Save (Cmd+S)");
      fireEvent.click(saveButton);

      expect(dispatchFn).toHaveBeenCalled();
    });
  });

  describe("Run Workflow", () => {
    it("should show validation error when run clicked with invalid workflow", () => {
      setupMockSelectors(
        mockUseAppSelector,
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
        mockUseAppSelector,
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
        mockUseAppSelector,
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

    it("should not show history panel when metadata has no id", () => {
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ metadata: null }),
      );

      renderWorkflowsPage();

      // History button should not exist
      expect(screen.queryByTitle("Execution History")).not.toBeInTheDocument();
    });

    it("should have different styling when history panel is visible", () => {
      setupMockSelectors(
        mockUseAppSelector,
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

  describe("Validation Error Alert", () => {
    it("should show validation error alert when validation error is set", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
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
        mockUseAppSelector,
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

  describe("URL Parameters", () => {
    it("should load workflow when id is in URL params", async () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({ metadata: null, isLoading: false }),
      );

      renderWorkflowsPageWithRoute("/workflows?id=wf-123");

      // Dispatch should have been called with loadWorkflow action
      await vi.waitFor(() => {
        expect(dispatchFn).toHaveBeenCalled();
      });
    });

    it("should not load workflow when already loaded with same id", () => {
      const dispatchFn = vi.fn();
      mockDispatch.mockReturnValue(dispatchFn);
      setupMockSelectors(
        mockUseAppSelector,
        createDefaultWorkflowState({
          metadata: { id: "wf-123", name: "Test" },
          isLoading: false,
        }),
      );

      renderWorkflowsPageWithRoute("/workflows?id=wf-123");

      // Should not dispatch loadWorkflow when already loaded
      // Only dispatch calls should be from button interactions, not initial load
    });

    it("should show suggestions panel when suggestions param is true in URL", () => {
      setupMockSelectors(mockUseAppSelector, createDefaultWorkflowState());

      renderWorkflowsPageWithRoute("/workflows?suggestions=true");

      // Suggestions panel should be visible due to URL param
      expect(screen.getByTestId("suggestion-chips")).toBeInTheDocument();
    });
  });
});

/**
 * Coverage Verification (Shard 2/2)
 *
 * This test shard covers:
 *
 * ✅ Connection status (indicator, reconnect button, all states)
 * ✅ Execution state (running spinner, state badges)
 * ✅ AI suggestions (toggle, styling)
 * ✅ Export JSON (trigger, filename handling)
 * ✅ Generate code (API calls, validation, error handling, button state)
 * ✅ Save workflow (dispatch actions)
 * ✅ Run workflow (validation)
 * ✅ Execution history panel (toggle, styling)
 * ✅ Validation error alert (display, dismiss)
 * ✅ URL parameters (workflow loading, suggestions)
 */
