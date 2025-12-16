/**
 * WorkflowsPage Tests
 *
 * TDD tests for the workflow builder page.
 * Tests cover:
 * - Loading state
 * - Toolbar functionality
 * - Node management
 * - Save workflow
 * - Undo/Redo
 * - Export functionality
 *
 * Uses Redux store with Provider for state management.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { WorkflowsPage } from "./WorkflowsPage";
import { api } from "../api";
import workflowReducer, {
  initialWorkflowState,
} from "../store/slices/workflowSlice";
import type { WorkflowSliceState } from "../store/slices/workflowSlice";
import type { WorkflowNode } from "../types/workflow";

// Mock useWorkflowExecution to prevent WebSocket connections in tests
vi.mock("../hooks/useWorkflowExecution", () => ({
  useWorkflowExecution: vi.fn(() => ({
    connectionStatus: "connected",
    reconnectAttempts: 0,
    isExecuting: false,
    startExecution: vi.fn(),
    stopExecution: vi.fn(),
    disconnect: vi.fn(),
    reconnect: vi.fn(),
  })),
}));

// Note: Onboarding is now handled globally in App.tsx with OnboardingWizard
// No longer need to mock useOnboarding for WorkflowsPage tests

// Use vi.hoisted() to ensure mock functions are available when vi.mock is hoisted
const {
  _mockGetSuggestions,
  mockGetNodeConfigHelp,
  mockUseGetWorkflowTemplatesQueryFn,
  mockUseGetWorkflowSuggestionsMutationFn,
  mockUseListWorkflowExecutionsQueryFn,
} = vi.hoisted(() => {
  const getSuggestions = vi.fn().mockReturnValue({
    unwrap: () =>
      Promise.resolve({
        suggestions: [],
        workflow_id: "test-workflow",
      }),
  });
  const getNodeConfigHelp = vi.fn().mockReturnValue({
    unwrap: () =>
      Promise.resolve({
        answer: "This is a test answer",
        examples: [],
        suggested_config: null,
      }),
  });
  return {
    _mockGetSuggestions: getSuggestions,
    mockGetNodeConfigHelp: getNodeConfigHelp,
    mockUseGetWorkflowTemplatesQueryFn: vi.fn(() => ({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })),
    mockUseGetWorkflowSuggestionsMutationFn: vi.fn(() => [
      getSuggestions,
      { isLoading: false },
    ]),
    mockUseListWorkflowExecutionsQueryFn: vi.fn(() => ({
      data: {
        items: [
          {
            id: "exec-1",
            workflow_id: "wf-1",
            status: "completed",
            started_at: "2025-01-01T10:00:00Z",
            completed_at: "2025-01-01T10:05:00Z",
            input_data: { query: "test" },
            output_data: { result: "success" },
            error: null,
          },
          {
            id: "exec-2",
            workflow_id: "wf-1",
            status: "running",
            started_at: "2025-01-01T11:00:00Z",
            completed_at: null,
            input_data: {},
            output_data: null,
            error: null,
          },
        ],
        total: 2,
        next_cursor: null,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })),
  };
});

vi.mock("../api", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    // Return the mock function directly so .mockReturnValue() works in tests
    useGetWorkflowTemplatesQuery: mockUseGetWorkflowTemplatesQueryFn,
    useGetWorkflowSuggestionsMutation: mockUseGetWorkflowSuggestionsMutationFn,
    useListWorkflowExecutionsQuery: mockUseListWorkflowExecutionsQueryFn,
    useGetNodeConfigHelpMutation: () => [
      mockGetNodeConfigHelp,
      { isLoading: false },
    ],
  };
});

// Mock SuggestionChips component
vi.mock("../components/Workflow/SuggestionChips", () => ({
  SuggestionChips: ({
    isLoading,
    error,
  }: {
    isLoading: boolean;
    error: string | null;
  }) => (
    <div data-testid="suggestions-panel">
      <span>AI Suggestions Panel</span>
      {isLoading && <span>Loading suggestions...</span>}
      {error && <span>{error}</span>}
    </div>
  ),
}));

// Import the mocked function for test manipulation
import { useWorkflowExecution } from "../hooks/useWorkflowExecution";
const mockUseWorkflowExecution = vi.mocked(useWorkflowExecution);
// Use the mock functions defined above for test manipulation (prefixed with _ since not used after onboarding removal)
const _mockUseGetWorkflowTemplatesQuery = mockUseGetWorkflowTemplatesQueryFn;

// Mock fetch for code generation
// Note: We assign in beforeEach because MSW server.listen() overrides global.fetch
const mockFetch = vi.fn();

// Create a test store with custom workflow state
const createTestStore = (workflowState: Partial<WorkflowSliceState> = {}) => {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
    preloadedState: {
      workflow: { ...initialWorkflowState, ...workflowState },
    },
  });
};

// Helper to render with store and router
const renderWithProviders = (
  component: React.ReactNode,
  {
    workflowState = {},
    initialEntries = ["/"],
  }: {
    workflowState?: Partial<WorkflowSliceState>;
    initialEntries?: string[];
  } = {},
) => {
  const store = createTestStore(workflowState);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={initialEntries}
        >
          {component}
        </MemoryRouter>
      </Provider>,
    ),
  };
};

// Mock node for testing
const mockNode: WorkflowNode = {
  id: "node-1",
  type: "default",
  position: { x: 100, y: 100 },
  data: {
    label: "Test Node",
    nodeType: "llm",
    config: {},
  },
};

describe("WorkflowsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Assign mock after MSW has started (in test setup beforeAll)
    global.fetch = mockFetch;
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });

    // Reset mock to default implementation
    mockUseWorkflowExecution.mockImplementation(() => ({
      connectionStatus: "connected",
      reconnectAttempts: 0,
      isExecuting: false,
      startExecution: vi.fn(),
      stopExecution: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    }));
  });

  describe("Loading State", () => {
    it("should show loading spinner when loading", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: { isLoading: true },
      });

      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Toolbar", () => {
    it("should display workflow name", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "My Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });

      expect(screen.getByText("My Workflow")).toBeInTheDocument();
    });

    it('should display "New Workflow" when no metadata', () => {
      renderWithProviders(<WorkflowsPage />);

      expect(screen.getByText("New Workflow")).toBeInTheDocument();
    });

    it("should show dirty indicator when changes exist", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "My Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isDirty: true,
        },
      });

      expect(screen.getByText("*")).toBeInTheDocument();
    });

    it("should show error count when validation fails", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          validation: {
            isValid: false,
            errors: [
              { nodeId: "n1", type: "error", message: "Error 1" },
              { nodeId: "n2", type: "error", message: "Error 2" },
            ],
            warnings: [],
          },
        },
      });

      expect(screen.getByText("2 errors")).toBeInTheDocument();
    });
  });

  describe("Undo/Redo", () => {
    it("should disable undo button when no undo history", () => {
      renderWithProviders(<WorkflowsPage />);

      const undoButton = screen.getByTitle("Undo (Cmd+Z)");
      expect(undoButton).toBeDisabled();
    });

    it("should enable undo button when undo history exists", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          undoStack: [{ nodes: [], edges: [], timestamp: Date.now() }],
        },
      });

      const undoButton = screen.getByTitle("Undo (Cmd+Z)");
      expect(undoButton).not.toBeDisabled();
    });

    it("should dispatch undo when undo button is clicked", () => {
      const { store } = renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          nodes: [mockNode],
          undoStack: [{ nodes: [], edges: [], timestamp: Date.now() }],
        },
      });

      fireEvent.click(screen.getByTitle("Undo (Cmd+Z)"));

      // After undo, the nodes should be empty (restored from snapshot)
      expect(store.getState().workflow.nodes).toHaveLength(0);
    });

    it("should disable redo button when no redo history", () => {
      renderWithProviders(<WorkflowsPage />);

      const redoButton = screen.getByTitle("Redo (Cmd+Shift+Z)");
      expect(redoButton).toBeDisabled();
    });

    it("should dispatch redo when redo button is clicked", () => {
      const { store } = renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          nodes: [],
          redoStack: [{ nodes: [mockNode], edges: [], timestamp: Date.now() }],
        },
      });

      fireEvent.click(screen.getByTitle("Redo (Cmd+Shift+Z)"));

      // After redo, the nodes should have mockNode (restored from redo snapshot)
      expect(store.getState().workflow.nodes).toHaveLength(1);
    });
  });

  describe("Save Workflow", () => {
    it("should have save button", () => {
      renderWithProviders(<WorkflowsPage />);

      expect(screen.getByText("Save")).toBeInTheDocument();
    });

    it("should disable save button when not dirty", () => {
      renderWithProviders(<WorkflowsPage />);

      const saveButton = screen.getByText("Save");
      expect(saveButton.closest("button")).toBeDisabled();
    });

    it("should enable save button when dirty", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: { isDirty: true },
      });

      const saveButton = screen.getByText("Save");
      expect(saveButton.closest("button")).not.toBeDisabled();
    });

    it("should dispatch saveWorkflow when save is clicked with existing metadata", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      });

      const { store } = renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "My Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isDirty: true,
        },
      });

      fireEvent.click(screen.getByText("Save"));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/wf-1",
          expect.objectContaining({ method: "PUT" }),
        );
      });

      // After successful save, isDirty should be false
      await waitFor(() => {
        expect(store.getState().workflow.isDirty).toBe(false);
      });
    });

    it("should create workflow if none exists before saving", async () => {
      const { store } = renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: null,
          isDirty: true,
        },
      });

      fireEvent.click(screen.getByText("Save"));

      // After clicking save with no metadata, a workflow should be created
      await waitFor(() => {
        expect(store.getState().workflow.metadata).not.toBeNull();
        expect(store.getState().workflow.metadata?.name).toBe("New Workflow");
      });
    });
  });

  describe("Workflow Canvas", () => {
    it("should render React Flow canvas area", () => {
      renderWithProviders(<WorkflowsPage />);

      // Canvas is rendered via WorkflowCanvas component
      expect(document.querySelector(".react-flow")).toBeInTheDocument();
    });

    it("should have Run button", () => {
      renderWithProviders(<WorkflowsPage />);

      expect(screen.getByText("Run")).toBeInTheDocument();
    });

    it("should show execution state when running", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: { executionState: "running" },
      });

      expect(screen.getByText("running")).toBeInTheDocument();
    });

    it("should show completed state after execution", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: { executionState: "completed" },
      });

      expect(screen.getByText("completed")).toBeInTheDocument();
    });

    it("should show error state after failed execution", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: { executionState: "error" },
      });

      expect(screen.getByText("error")).toBeInTheDocument();
    });

    it("should disable Run button when workflow is invalid", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          validation: {
            isValid: false,
            errors: [{ nodeId: "n1", type: "error", message: "Error" }],
            warnings: [],
          },
        },
      });

      const runButton = screen.getByText("Run");
      expect(runButton.closest("button")).toBeDisabled();
    });

    it("should show execution panel when Run is clicked with valid workflow", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          nodes: [mockNode],
          edges: [],
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Run"));

      // ExecutionPanel should appear with its heading
      await waitFor(() => {
        expect(screen.getByText("Execution Logs")).toBeInTheDocument();
      });
    });

    it("should close execution panel when X button is clicked", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          nodes: [mockNode],
          edges: [],
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      // Click Run to open execution panel
      fireEvent.click(screen.getByText("Run"));

      // Wait for panel to appear
      await waitFor(() => {
        expect(screen.getByText("Execution Logs")).toBeInTheDocument();
      });

      // Find and click the close button (X icon button)
      const closeButtons = document.querySelectorAll("button");
      const closeButton = Array.from(closeButtons).find((btn) =>
        btn.querySelector("svg.lucide-x"),
      );
      if (closeButton) {
        fireEvent.click(closeButton);
      }

      // Panel should be hidden
      await waitFor(() => {
        expect(screen.queryByText("Execution Logs")).not.toBeInTheDocument();
      });
    });
  });

  describe("Export", () => {
    it("should have Generate Code button", () => {
      renderWithProviders(<WorkflowsPage />);

      expect(screen.getByText("Generate Code")).toBeInTheDocument();
    });

    it("should have Export JSON button", () => {
      renderWithProviders(<WorkflowsPage />);

      expect(screen.getByText("Export JSON")).toBeInTheDocument();
    });

    it("should export JSON when Export JSON button is clicked", () => {
      // Mock URL methods and document.createElement
      const mockClick = vi.fn();
      const mockAnchor = { href: "", download: "", click: mockClick };
      const originalCreateObjectURL = URL.createObjectURL;
      const originalRevokeObjectURL = URL.revokeObjectURL;
      const originalCreateElement = document.createElement.bind(document);

      URL.createObjectURL = vi.fn(() => "blob:test");
      URL.revokeObjectURL = vi.fn();
      document.createElement = vi.fn((tag: string) => {
        if (tag === "a") return mockAnchor as unknown as HTMLAnchorElement;
        return originalCreateElement(tag);
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          nodes: [mockNode],
          edges: [],
        },
      });

      fireEvent.click(screen.getByText("Export JSON"));

      expect(URL.createObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
      expect(mockAnchor.download).toBe("Test Workflow.json");
      expect(URL.revokeObjectURL).toHaveBeenCalled();

      // Cleanup
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
      document.createElement = originalCreateElement;
    });

    it("should generate and download code when Generate Code is clicked with valid workflow", async () => {
      const mockCode = "from langgraph import StateGraph";
      const mockClick = vi.fn();
      const mockAnchor = { href: "", download: "", click: mockClick };
      const originalCreateObjectURL = URL.createObjectURL;
      const originalRevokeObjectURL = URL.revokeObjectURL;
      const originalCreateElement = document.createElement.bind(document);

      URL.createObjectURL = vi.fn(() => "blob:test");
      URL.revokeObjectURL = vi.fn();
      document.createElement = vi.fn((tag: string) => {
        if (tag === "a") return mockAnchor as unknown as HTMLAnchorElement;
        return originalCreateElement(tag);
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({ code: mockCode, filename: "workflow.py" }),
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          nodes: [mockNode],
          edges: [],
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Generate Code"));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/generate",
          expect.objectContaining({ method: "POST" }),
        );
      });

      await waitFor(() => {
        expect(URL.createObjectURL).toHaveBeenCalled();
        expect(mockClick).toHaveBeenCalled();
      });

      // Cleanup
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
      document.createElement = originalCreateElement;
    });

    it("should show inline error when Generate Code is clicked with invalid workflow", async () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          validation: {
            isValid: false,
            errors: [{ nodeId: "n1", type: "error", message: "Error" }],
            warnings: [],
          },
        },
      });

      fireEvent.click(screen.getByText("Generate Code"));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText(/fix validation errors/i)).toBeInTheDocument();
      });
    });

    it("should handle code generation error gracefully", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          nodes: [mockNode],
          edges: [],
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Generate Code"));

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          "Failed to generate code:",
          expect.any(Error),
        );
      });

      consoleSpy.mockRestore();
    });
  });

  describe("Workflow Query Parameter", () => {
    it("should load workflow from query parameter", async () => {
      const mockWorkflowData = {
        metadata: {
          id: "workflow-123",
          name: "Loaded Workflow",
          description: "",
          version: 1,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
        nodes: [mockNode],
        edges: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockWorkflowData),
      });

      const { store } = renderWithProviders(<WorkflowsPage />, {
        initialEntries: ["/studio/workflows?id=workflow-123"],
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/workflow-123",
          expect.objectContaining({ credentials: "include" }),
        );
      });

      await waitFor(() => {
        expect(store.getState().workflow.metadata?.id).toBe("workflow-123");
      });
    });

    it("should not load workflow when no query param", () => {
      renderWithProviders(<WorkflowsPage />, {
        initialEntries: ["/studio/workflows"],
      });

      // Should not call fetch for loading a workflow when no ID provided
      expect(mockFetch).not.toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/v1\/workflows\/\w+/),
      );
    });
  });

  describe("Read-Only Mode", () => {
    it("should show read-only badge when in read-only mode", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-shared",
            name: "Shared Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isReadOnly: true,
        },
      });

      expect(screen.getByText("Read-Only")).toBeInTheDocument();
    });

    it("should disable save button in read-only mode", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-shared",
            name: "Shared Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isDirty: true,
          isReadOnly: true,
        },
      });

      const saveButton = screen.getByText("Save");
      expect(saveButton.closest("button")).toBeDisabled();
    });

    it("should disable run button in read-only mode without execute permission", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-shared",
            name: "Shared Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isReadOnly: true,
          canExecute: false,
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      const runButton = screen.getByText("Run");
      expect(runButton.closest("button")).toBeDisabled();
    });

    it("should enable run button in read-only mode with execute permission", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-shared",
            name: "Shared Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isReadOnly: true,
          canExecute: true,
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      const runButton = screen.getByText("Run");
      expect(runButton.closest("button")).not.toBeDisabled();
    });

    it("should disable undo/redo buttons in read-only mode", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-shared",
            name: "Shared Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isReadOnly: true,
          undoStack: [{ nodes: [], edges: [], timestamp: Date.now() }],
          redoStack: [{ nodes: [], edges: [], timestamp: Date.now() }],
        },
      });

      const undoButton = screen.getByTitle("Undo (Cmd+Z)");
      const redoButton = screen.getByTitle("Redo (Cmd+Shift+Z)");
      expect(undoButton).toBeDisabled();
      expect(redoButton).toBeDisabled();
    });

    it("should still allow export in read-only mode", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-shared",
            name: "Shared Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          isReadOnly: true,
        },
      });

      const exportButton = screen.getByText("Export JSON");
      expect(exportButton.closest("button")).not.toBeDisabled();
    });
  });

  describe("Connection Status Indicator", () => {
    it("should show connected indicator when WebSocket is connected", async () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "connected",
        reconnectAttempts: 0,
        isExecuting: false,
        startExecution: vi.fn(),
        stopExecution: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      // Open execution panel to trigger WebSocket connection
      fireEvent.click(screen.getByText("Run"));

      // Should show connection status indicator
      await waitFor(() => {
        expect(screen.getByTestId("connection-status")).toBeInTheDocument();
        expect(screen.getByTitle("Connection: connected")).toBeInTheDocument();
      });
    });

    it("should show reconnecting indicator with attempt count", async () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "reconnecting",
        reconnectAttempts: 2,
        isExecuting: false,
        startExecution: vi.fn(),
        stopExecution: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Run"));

      await waitFor(() => {
        expect(screen.getByTestId("connection-status")).toBeInTheDocument();
        expect(
          screen.getByTitle("Connection: reconnecting (attempt 2)"),
        ).toBeInTheDocument();
        expect(screen.getByText("2")).toBeInTheDocument(); // Attempt number shown
      });
    });

    it("should show disconnected indicator when WebSocket is disconnected", async () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "disconnected",
        reconnectAttempts: 0,
        isExecuting: false,
        startExecution: vi.fn(),
        stopExecution: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Run"));

      await waitFor(() => {
        expect(screen.getByTestId("connection-status")).toBeInTheDocument();
        expect(
          screen.getByTitle("Connection: disconnected"),
        ).toBeInTheDocument();
      });
    });

    it("should not show connection status when execution panel is closed", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });

      // Connection status should not be visible before execution panel is opened
      expect(screen.queryByTestId("connection-status")).not.toBeInTheDocument();
    });

    it("should show Reconnect button when disconnected", async () => {
      const mockReconnect = vi.fn();
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "disconnected",
        reconnectAttempts: 0,
        isExecuting: false,
        startExecution: vi.fn(),
        stopExecution: vi.fn(),
        disconnect: vi.fn(),
        reconnect: mockReconnect,
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Run"));

      await waitFor(() => {
        expect(screen.getByText("Reconnect")).toBeInTheDocument();
      });
    });

    it("should call reconnect when Reconnect button is clicked", async () => {
      const mockReconnect = vi.fn();
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "disconnected",
        reconnectAttempts: 0,
        isExecuting: false,
        startExecution: vi.fn(),
        stopExecution: vi.fn(),
        disconnect: vi.fn(),
        reconnect: mockReconnect,
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Run"));

      await waitFor(() => {
        expect(screen.getByText("Reconnect")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Reconnect"));

      expect(mockReconnect).toHaveBeenCalledTimes(1);
    });

    it("should not show Reconnect button when connected", async () => {
      mockUseWorkflowExecution.mockReturnValue({
        connectionStatus: "connected",
        reconnectAttempts: 0,
        isExecuting: false,
        startExecution: vi.fn(),
        stopExecution: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          validation: { isValid: true, errors: [], warnings: [] },
        },
      });

      fireEvent.click(screen.getByText("Run"));

      await waitFor(() => {
        expect(screen.getByTestId("connection-status")).toBeInTheDocument();
      });

      expect(screen.queryByText("Reconnect")).not.toBeInTheDocument();
    });
  });

  // Note: Onboarding Modal tests removed - onboarding is now handled globally
  // in App.tsx with OnboardingWizard component. See App.test.tsx for onboarding tests.

  describe("Execution History Panel", () => {
    // useListWorkflowExecutionsQuery mock is defined at the top level

    it("should have History button in toolbar when workflow has an ID", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });

      expect(screen.getByText("History")).toBeInTheDocument();
    });

    it("should not show History button when workflow has no ID", () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: null,
        },
      });

      expect(screen.queryByText("History")).not.toBeInTheDocument();
    });

    it("should toggle execution history panel when History button is clicked", async () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });

      // Click History button
      fireEvent.click(screen.getByText("History"));

      // ExecutionHistoryPanel should appear
      await waitFor(() => {
        expect(screen.getByText("Execution History")).toBeInTheDocument();
      });
    });

    it("should show execution list in history panel", async () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });

      fireEvent.click(screen.getByText("History"));

      await waitFor(() => {
        // Should show execution count
        expect(screen.getByText(/2 executions/i)).toBeInTheDocument();
      });
    });

    it("should close history panel when close button is clicked", async () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          metadata: {
            id: "wf-1",
            name: "Test Workflow",
            description: "",
            version: 1,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
        },
      });

      // Open history panel
      fireEvent.click(screen.getByText("History"));

      await waitFor(() => {
        expect(screen.getByText("Execution History")).toBeInTheDocument();
      });

      // Click History button again to toggle off
      fireEvent.click(screen.getByText("History"));

      await waitFor(() => {
        expect(screen.queryByText("Execution History")).not.toBeInTheDocument();
      });
    });
  });

  describe("AI Suggestions", () => {
    it("should have AI Suggest toggle button in toolbar", () => {
      renderWithProviders(<WorkflowsPage />);

      expect(screen.getByTestId("ai-suggestions-toggle")).toBeInTheDocument();
      expect(screen.getByText("AI Suggest")).toBeInTheDocument();
    });

    it("should toggle suggestions panel when AI Suggest button is clicked", async () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          nodes: [mockNode],
          edges: [],
        },
      });

      // Click AI Suggest button
      fireEvent.click(screen.getByTestId("ai-suggestions-toggle"));

      // Suggestions panel should appear (mocked component)
      await waitFor(() => {
        expect(screen.getByTestId("suggestions-panel")).toBeInTheDocument();
        expect(screen.getByText("AI Suggestions Panel")).toBeInTheDocument();
      });
    });

    it("should highlight AI Suggest button when suggestions panel is open", async () => {
      renderWithProviders(<WorkflowsPage />, {
        workflowState: {
          nodes: [mockNode],
          edges: [],
        },
      });

      const button = screen.getByTestId("ai-suggestions-toggle");

      // Click to open
      fireEvent.click(button);

      // Button should have highlighted style (yellow background)
      await waitFor(() => {
        expect(button.className).toContain("bg-yellow");
      });
    });

    it("should show suggestions panel when URL has suggestions=true param", () => {
      renderWithProviders(<WorkflowsPage />, {
        initialEntries: ["/?suggestions=true"],
      });

      // Suggestions panel should be visible (mocked component)
      expect(screen.getByTestId("suggestions-panel")).toBeInTheDocument();
    });
  });
});
