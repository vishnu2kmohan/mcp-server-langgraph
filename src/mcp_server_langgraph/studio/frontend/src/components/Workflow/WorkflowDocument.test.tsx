/**
 * WorkflowDocument Component Tests
 *
 * TDD tests for the workflow document component used in MainDock tabs.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { WorkflowDocument } from "./WorkflowDocument";
import workflowReducer from "../../store/slices/workflowSlice";
import uiReducer from "../../store/slices/uiSlice";

// Mock React Flow
vi.mock("reactflow", () => ({
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="reactflow-provider">{children}</div>
  ),
  useReactFlow: () => ({
    fitView: vi.fn(),
    getNodes: () => [],
    getEdges: () => [],
  }),
}));

// Mock workflow components
vi.mock("./WorkflowCanvas", () => ({
  WorkflowCanvas: () => <div data-testid="workflow-canvas">Canvas</div>,
}));

vi.mock("./NodePalette", () => ({
  NodePalette: () => <div data-testid="node-palette">Palette</div>,
}));

vi.mock("./NodeInspector", () => ({
  NodeInspector: () => <div data-testid="node-inspector">Inspector</div>,
}));

// Create test store with preloaded state
const createTestStore = (workflowName?: string) => {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
      ui: uiReducer,
    },
    preloadedState: workflowName
      ? {
          workflow: {
            metadata: {
              id: "wf-123",
              name: workflowName,
              description: "Test workflow",
              version: 1,
              createdAt: Date.now(),
              updatedAt: Date.now(),
            },
            nodes: [],
            edges: [],
            selectedNodeIds: [],
            selectedEdgeIds: [],
            undoStack: [],
            redoStack: [],
            validation: { isValid: true, errors: [], warnings: [] },
            isDirty: false,
            isSaving: false,
            isLoading: false,
            error: null,
            executionState: "idle" as const,
            nodeStatuses: {},
            executionLogs: [],
            isReadOnly: false,
            canExecute: true,
          },
          ui: {
            sidebarCollapsed: false,
            rightSidebarCollapsed: false,
            bottomPanelCollapsed: false,
          },
        }
      : undefined,
  });
};

const renderWithProviders = (ui: React.ReactElement, workflowName?: string) => {
  const store = createTestStore(workflowName);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>,
    ),
  };
};

describe("WorkflowDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(
        <WorkflowDocument workflowId="wf-123" />,
        "Test Workflow",
      );
      expect(screen.getByTestId("workflow-document")).toBeInTheDocument();
    });

    it("should display workflow name when loaded", () => {
      renderWithProviders(
        <WorkflowDocument workflowId="wf-123" />,
        "Test Workflow wf-123",
      );
      expect(screen.getByText(/Test Workflow wf-123/i)).toBeInTheDocument();
    });

    it("should show empty state when no workflowId provided", () => {
      renderWithProviders(<WorkflowDocument workflowId="" />);
      expect(screen.getByText(/No workflow selected/i)).toBeInTheDocument();
    });

    it("should apply compact mode styling when compact prop is true", () => {
      renderWithProviders(
        <WorkflowDocument workflowId="wf-123" compact />,
        "Test Workflow",
      );
      const doc = screen.getByTestId("workflow-document");
      expect(doc).toHaveClass("text-sm");
    });
  });

  describe("Props", () => {
    it("should accept workflowId prop", () => {
      // Note: The workflowId is used to load the workflow - when already loaded
      // in state with matching ID, displays the metadata name
      renderWithProviders(
        <WorkflowDocument workflowId="wf-123" />,
        "Custom Workflow Name",
      );
      expect(screen.getByText(/Custom Workflow Name/i)).toBeInTheDocument();
    });

    it("should accept className prop", () => {
      renderWithProviders(
        <WorkflowDocument workflowId="wf-123" className="custom-class" />,
        "Test Workflow",
      );
      const doc = screen.getByTestId("workflow-document");
      expect(doc).toHaveClass("custom-class");
    });
  });

  describe("Workflow Components", () => {
    it("should render WorkflowCanvas when workflow is loaded", () => {
      renderWithProviders(
        <WorkflowDocument workflowId="wf-123" />,
        "Test Workflow",
      );
      expect(screen.getByTestId("workflow-canvas")).toBeInTheDocument();
    });

    it("should render NodePalette when not read-only", () => {
      renderWithProviders(
        <WorkflowDocument workflowId="wf-123" />,
        "Test Workflow",
      );
      expect(screen.getByTestId("node-palette")).toBeInTheDocument();
    });
  });
});
