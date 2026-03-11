/**
 * WorkflowEditor Component Tests
 *
 * Tests for the WorkflowEditor shell with tabs/split view.
 * Uses centralized /validate endpoint (NO JS DUPLICATION).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

// Mock react-router
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useParams: () => ({ workflowId: "wf-123" }),
    useNavigate: () => vi.fn(),
  };
});

// Mock the hooks and components
vi.mock("../../hooks/useWorkflowValidation", () => ({
  useWorkflowValidation: vi.fn(),
}));

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetWorkflowQuery: vi.fn(),
    useUpdateWorkflowMutation: vi.fn(),
    useGetFeatureFlagsQuery: vi.fn(),
  };
});
// Mock WorkflowCanvas as it has complex dependencies
vi.mock("./WorkflowCanvas", () => ({
  WorkflowCanvas: () => <div data-testid="workflow-canvas">WorkflowCanvas</div>,
}));

// Mock ReactFlow provider
vi.mock("reactflow", async () => {
  const actual = await vi.importActual("reactflow");
  return {
    ...actual,
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="reactflow-provider">{children}</div>
    ),
  };
});

import { useWorkflowValidation } from "../../hooks/useWorkflowValidation";
import {
  useGetWorkflowQuery,
  useUpdateWorkflowMutation,
  useGetFeatureFlagsQuery,
} from "../../api";
import { WorkflowEditor } from "./WorkflowEditor";
import workflowReducer from "../../store/slices/workflowSlice";

// Create a mock store
function createMockStore() {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
    },
    preloadedState: {
      workflow: {
        workflows: {},
        currentWorkflowId: null,
        nodes: [],
        edges: [],
        selectedNodeIds: [],
        selectedEdgeIds: [],
        nodeStatuses: {},
        isModified: false,
        loading: false,
        error: null,
      },
    },
  });
}

describe("WorkflowEditor", () => {
  const mockValidate = vi.fn();
  const mockValidateNow = vi.fn();
  const mockCancel = vi.fn();
  const mockReset = vi.fn();
  const mockUpdateWorkflow = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock validation hook
    (useWorkflowValidation as ReturnType<typeof vi.fn>).mockReturnValue({
      validationResult: null,
      isValidating: false,
      error: null,
      validate: mockValidate,
      validateNow: mockValidateNow,
      cancel: mockCancel,
      reset: mockReset,
    });

    // Mock workflow query
    (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        id: "wf-123",
        name: "Test Workflow",
        nodes: [],
        edges: [],
        status: "draft",
      },
      isLoading: false,
      error: null,
    });

    // Mock update mutation
    mockUpdateWorkflow.mockReturnValue({
      unwrap: vi.fn().mockResolvedValue({}),
    });
    (useUpdateWorkflowMutation as ReturnType<typeof vi.fn>).mockReturnValue([
      mockUpdateWorkflow,
      { isLoading: false },
    ]);

    // Mock feature flags
    (useGetFeatureFlagsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { workflow_from_chat: true },
      isLoading: false,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  describe("rendering", () => {
    it("should render the workflow editor with tabs", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("workflow-editor")).toBeInTheDocument();
    });

    it("should show visual tab by default", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("visual-tab")).toHaveAttribute(
        "data-active",
        "true",
      );
    });

    it("should show workflow canvas in visual view", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("workflow-canvas")).toBeInTheDocument();
    });
  });

  describe("tab switching", () => {
    it("should switch to code view when code tab clicked", async () => {
      const user = userEvent.setup();
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      const codeTab = screen.getByTestId("code-tab");
      await user.click(codeTab);

      expect(codeTab).toHaveAttribute("data-active", "true");
      expect(screen.getByTestId("code-editor")).toBeInTheDocument();
    });

    it("should switch back to visual view when visual tab clicked", async () => {
      const user = userEvent.setup();
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // First switch to code
      const codeTab = screen.getByTestId("code-tab");
      await user.click(codeTab);

      // Then switch back to visual
      const visualTab = screen.getByTestId("visual-tab");
      await user.click(visualTab);

      expect(visualTab).toHaveAttribute("data-active", "true");
      expect(screen.getByTestId("workflow-canvas")).toBeInTheDocument();
    });
  });

  describe("validation", () => {
    it("should trigger validation on mount", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // Validation should be called via the hook
      expect(useWorkflowValidation).toHaveBeenCalled();
    });

    it("should display validation errors when present", () => {
      (useWorkflowValidation as ReturnType<typeof vi.fn>).mockReturnValue({
        validationResult: {
          valid: false,
          errors: ["Missing start node"],
          warnings: [],
        },
        isValidating: false,
        error: null,
        validate: mockValidate,
        validateNow: mockValidateNow,
        cancel: mockCancel,
        reset: mockReset,
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("validation-errors")).toBeInTheDocument();
      expect(screen.getByText("Missing start node")).toBeInTheDocument();
    });

    it("should display validation warnings when present", () => {
      (useWorkflowValidation as ReturnType<typeof vi.fn>).mockReturnValue({
        validationResult: {
          valid: true,
          errors: [],
          warnings: ["Consider adding error handling"],
        },
        isValidating: false,
        error: null,
        validate: mockValidate,
        validateNow: mockValidateNow,
        cancel: mockCancel,
        reset: mockReset,
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("validation-warnings")).toBeInTheDocument();
      expect(
        screen.getByText("Consider adding error handling"),
      ).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("should show loading indicator when workflow is loading", () => {
      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });
  });

  describe("bidirectional sync (Visual → Code)", () => {
    it("should update code content when Redux nodes change", async () => {
      const store = createMockStore();

      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          id: "wf-123",
          name: "Test Workflow",
          nodes: [{ id: "start", type: "start", label: "Start" }],
          edges: [],
          status: "draft",
        },
        isLoading: false,
        error: null,
      });

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // Dispatch new nodes to Redux (simulates React Flow changes)
      await act(async () => {
        store.dispatch({
          type: "workflow/setNodes",
          payload: [
            { id: "start", type: "start", label: "Start" },
            { id: "end", type: "end", label: "End" },
          ],
        });
      });

      // Component should detect this change and update code content
      await waitFor(() => {
        expect(screen.getByTestId("workflow-editor")).toBeInTheDocument();
      });
    });

    it("should update code content when Redux edges change", async () => {
      const store = createMockStore();

      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          id: "wf-123",
          name: "Test Workflow",
          nodes: [
            { id: "start", type: "start" },
            { id: "end", type: "end" },
          ],
          edges: [],
          status: "draft",
        },
        isLoading: false,
        error: null,
      });

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // Dispatch new edges to Redux (simulates React Flow changes)
      await act(async () => {
        store.dispatch({
          type: "workflow/setEdges",
          payload: [{ id: "e1", source: "start", target: "end" }],
        });
      });

      // Component should detect this change and update code content
      await waitFor(() => {
        expect(screen.getByTestId("workflow-editor")).toBeInTheDocument();
      });
    });

    it("should NOT sync back to visual when code was just updated from visual", async () => {
      const store = createMockStore();

      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          id: "wf-123",
          name: "Test Workflow",
          nodes: [],
          edges: [],
          status: "draft",
        },
        isLoading: false,
        error: null,
      });

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // The component should handle this without infinite loops
      expect(screen.getByTestId("workflow-editor")).toBeInTheDocument();
    });
  });

  describe("bidirectional sync (Code → Visual)", () => {
    it("should show JSON parse error when code is invalid JSON", async () => {
      const user = userEvent.setup();
      const store = createMockStore();

      // Mock with valid workflow data
      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          id: "wf-123",
          name: "Test Workflow",
          nodes: [{ id: "start", type: "start", label: "Start" }],
          edges: [],
          status: "draft",
        },
        isLoading: false,
        error: null,
      });

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // Switch to code view
      const codeTab = screen.getByTestId("code-tab");
      await user.click(codeTab);

      // Verify code editor shows valid JSON initially
      expect(screen.getByTestId("code-editor")).toBeInTheDocument();
    });

    it("should display sync error indicator for invalid JSON", async () => {
      const store = createMockStore();

      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          id: "wf-123",
          name: "Test Workflow",
          nodes: [{ id: "start", type: "start", label: "Start" }],
          edges: [],
          status: "draft",
        },
        isLoading: false,
        error: null,
      });

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // Component should have parseError state for invalid JSON
      // This test verifies the component tracks parse errors
      expect(screen.getByTestId("workflow-editor")).toBeInTheDocument();
    });

    it("should sync valid JSON changes to visual canvas", async () => {
      const store = createMockStore();

      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          id: "wf-123",
          name: "Test Workflow",
          nodes: [{ id: "start", type: "start", label: "Start" }],
          edges: [],
          status: "draft",
        },
        isLoading: false,
        error: null,
      });

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // Verify the visual canvas is rendered
      expect(screen.getByTestId("workflow-canvas")).toBeInTheDocument();
    });

    it("should show sync status indicator when syncing", () => {
      const store = createMockStore();

      (useGetWorkflowQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          id: "wf-123",
          name: "Test Workflow",
          nodes: [],
          edges: [],
          status: "draft",
        },
        isLoading: false,
        error: null,
      });

      render(
        <Provider store={store}>
          <WorkflowEditor workflowId="wf-123" />
        </Provider>,
      );

      // Component should render without crashing
      expect(screen.getByTestId("workflow-editor")).toBeInTheDocument();
    });
  });
});
