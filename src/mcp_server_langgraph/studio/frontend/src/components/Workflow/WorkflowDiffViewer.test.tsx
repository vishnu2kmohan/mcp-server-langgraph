/**
 * WorkflowDiffViewer Component Tests
 *
 * Tests for the version diff comparison component.
 * Enables side-by-side or inline diff view between workflow versions.
 *
 * Plan: greedy-wiggling-marshmallow.md, Phase 4
 * ADR: adr-0089-prompt-architecture-centralization.md
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

import workflowReducer from "../../store/slices/workflowSlice";

// Mock data
const mockVersionA = {
  id: "v1",
  workflow_id: "wf-123",
  version_number: 1,
  graph_json: {
    nodes: [{ id: "start", type: "start", data: { label: "Start" } }],
    edges: [],
  },
  commit_message: "Initial version",
  created_by: "alice",
  created_at: "2024-01-01T12:00:00Z",
};

const mockVersionB = {
  id: "v2",
  workflow_id: "wf-123",
  version_number: 2,
  graph_json: {
    nodes: [
      { id: "start", type: "start", data: { label: "Start" } },
      { id: "end", type: "end", data: { label: "End" } },
    ],
    edges: [{ id: "e1", source: "start", target: "end" }],
  },
  commit_message: "Added end node",
  created_by: "alice",
  created_at: "2024-01-02T12:00:00Z",
};

// Create a mock store
function createMockStore() {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
    },
    preloadedState: {
      workflow: {
        workflows: {},
        currentWorkflowId: "wf-123",
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

describe("WorkflowDiffViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  describe("rendering", () => {
    it("should render the diff viewer panel", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer versionA={mockVersionA} versionB={mockVersionB} />
        </Provider>,
      );

      expect(screen.getByTestId("diff-viewer")).toBeInTheDocument();
    });

    it("should display version labels", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer versionA={mockVersionA} versionB={mockVersionB} />
        </Provider>,
      );

      // Should show version numbers
      expect(screen.getByText(/v1/i)).toBeInTheDocument();
      expect(screen.getByText(/v2/i)).toBeInTheDocument();
    });

    it("should show diff mode toggle", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer versionA={mockVersionA} versionB={mockVersionB} />
        </Provider>,
      );

      // Should have toggle for side-by-side vs unified
      expect(screen.getByTestId("diff-mode-toggle")).toBeInTheDocument();
    });
  });

  describe("diff calculation", () => {
    it("should show additions in green", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer versionA={mockVersionA} versionB={mockVersionB} />
        </Provider>,
      );

      // Version B has added "end" node - should show as addition
      const additionIndicator = screen.getByTestId("diff-additions");
      expect(additionIndicator).toBeInTheDocument();
    });

    it("should show deletions in red", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      // Reverse versions to show deletion
      render(
        <Provider store={store}>
          <WorkflowDiffViewer versionA={mockVersionB} versionB={mockVersionA} />
        </Provider>,
      );

      // Version A (now B) has "end" node removed - should show as deletion
      const deletionIndicator = screen.getByTestId("diff-deletions");
      expect(deletionIndicator).toBeInTheDocument();
    });

    it("should show diff summary statistics", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer versionA={mockVersionA} versionB={mockVersionB} />
        </Provider>,
      );

      // Should show summary like "+1 node, +1 edge"
      expect(screen.getByTestId("diff-summary")).toBeInTheDocument();
    });
  });

  describe("view modes", () => {
    it("should support side-by-side view", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer
            versionA={mockVersionA}
            versionB={mockVersionB}
            defaultMode="side-by-side"
          />
        </Provider>,
      );

      expect(screen.getByTestId("side-by-side-view")).toBeInTheDocument();
    });

    it("should support unified view", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer
            versionA={mockVersionA}
            versionB={mockVersionB}
            defaultMode="unified"
          />
        </Provider>,
      );

      expect(screen.getByTestId("unified-view")).toBeInTheDocument();
    });

    it("should toggle between view modes", async () => {
      const user = userEvent.setup();
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer
            versionA={mockVersionA}
            versionB={mockVersionB}
            defaultMode="side-by-side"
          />
        </Provider>,
      );

      // Click unified button
      const unifiedButton = screen.getByRole("button", { name: /unified/i });
      await user.click(unifiedButton);

      await waitFor(() => {
        expect(screen.getByTestId("unified-view")).toBeInTheDocument();
      });
    });
  });

  describe("callbacks", () => {
    it("should call onClose when close button clicked", async () => {
      const user = userEvent.setup();
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();
      const onClose = vi.fn();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer
            versionA={mockVersionA}
            versionB={mockVersionB}
            onClose={onClose}
          />
        </Provider>,
      );

      const closeButton = screen.getByRole("button", { name: /close/i });
      await user.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("empty state", () => {
    it("should show no changes message when versions are identical", async () => {
      const { WorkflowDiffViewer } = await import("./WorkflowDiffViewer");
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowDiffViewer versionA={mockVersionA} versionB={mockVersionA} />
        </Provider>,
      );

      expect(screen.getByText(/no changes/i)).toBeInTheDocument();
    });
  });
});
