/**
 * WorkflowVersionHistory Component Tests
 *
 * Tests for the version history panel in WorkflowEditor.
 * Enables draft/publish lifecycle, diffing, rollback, and audit trails.
 *
 * Plan: greedy-wiggling-marshmallow.md, Phase 3
 * ADR: adr-0089-prompt-architecture-centralization.md
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

// Mock the API hooks
vi.mock("../../api", () => ({
  useGetWorkflowVersionsQuery: vi.fn(),
  useRestoreWorkflowVersionMutation: vi.fn(),
}));

import {
  useGetWorkflowVersionsQuery,
  useRestoreWorkflowVersionMutation,
} from "../../api";
import { WorkflowVersionHistory } from "./WorkflowVersionHistory";
import workflowReducer from "../../store/slices/workflowSlice";

// Mock data
const mockVersions = [
  {
    id: "v3",
    workflow_id: "wf-123",
    version_number: 3,
    graph_json: {
      nodes: [
        { id: "start", type: "start" },
        { id: "end", type: "end" },
      ],
      edges: [{ id: "e1", source: "start", target: "end" }],
    },
    commit_message: "Added end node",
    created_by: "alice",
    created_at: "2024-01-03T12:00:00Z",
    prompt_version: "v1",
    prompt_model: "claude-opus-4-5",
  },
  {
    id: "v2",
    workflow_id: "wf-123",
    version_number: 2,
    graph_json: {
      nodes: [{ id: "start", type: "start" }],
      edges: [],
    },
    commit_message: "Added start node",
    created_by: "alice",
    created_at: "2024-01-02T12:00:00Z",
    prompt_version: "v1",
    prompt_model: "claude-opus-4-5",
  },
  {
    id: "v1",
    workflow_id: "wf-123",
    version_number: 1,
    graph_json: {
      nodes: [],
      edges: [],
    },
    commit_message: "Initial version",
    created_by: "system",
    created_at: "2024-01-01T12:00:00Z",
  },
];

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

describe("WorkflowVersionHistory", () => {
  const mockRestoreVersion = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock for versions query
    (useGetWorkflowVersionsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockVersions,
      isLoading: false,
      error: null,
    });

    // Default mock for restore mutation
    mockRestoreVersion.mockReturnValue({
      unwrap: vi.fn().mockResolvedValue({}),
    });
    (
      useRestoreWorkflowVersionMutation as ReturnType<typeof vi.fn>
    ).mockReturnValue([mockRestoreVersion, { isLoading: false }]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  describe("rendering", () => {
    it("should render the version history panel", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("version-history-panel")).toBeInTheDocument();
    });

    it("should display version history heading", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByText(/Version History/i)).toBeInTheDocument();
    });

    it("should list all versions", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      // Each version item should be present
      expect(screen.getByTestId("version-item-v3")).toBeInTheDocument();
      expect(screen.getByTestId("version-item-v2")).toBeInTheDocument();
      expect(screen.getByTestId("version-item-v1")).toBeInTheDocument();
    });

    it("should display commit messages", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByText("Added end node")).toBeInTheDocument();
      expect(screen.getByText("Added start node")).toBeInTheDocument();
      expect(screen.getByText("Initial version")).toBeInTheDocument();
    });

    it("should display created by user", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getAllByText("alice")).toHaveLength(2);
      expect(screen.getByText("system")).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("should show loading spinner when fetching versions", () => {
      (useGetWorkflowVersionsQuery as ReturnType<typeof vi.fn>).mockReturnValue(
        {
          data: null,
          isLoading: true,
          error: null,
        },
      );

      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("should show empty state when no versions exist", () => {
      (useGetWorkflowVersionsQuery as ReturnType<typeof vi.fn>).mockReturnValue(
        {
          data: [],
          isLoading: false,
          error: null,
        },
      );

      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByText(/No versions yet/i)).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("should show error message when fetch fails", () => {
      (useGetWorkflowVersionsQuery as ReturnType<typeof vi.fn>).mockReturnValue(
        {
          data: null,
          isLoading: false,
          error: { message: "Failed to fetch versions" },
        },
      );

      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      expect(screen.getByText(/Failed to load versions/i)).toBeInTheDocument();
    });
  });

  describe("version selection", () => {
    it("should highlight selected version", async () => {
      const user = userEvent.setup();
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      // Click on version 2
      const v2Item = screen.getByTestId("version-item-v2");
      await user.click(v2Item);

      expect(v2Item).toHaveAttribute("data-selected", "true");
    });

    it("should call onVersionSelect callback when version clicked", async () => {
      const user = userEvent.setup();
      const store = createMockStore();
      const onVersionSelect = vi.fn();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory
            workflowId="wf-123"
            onVersionSelect={onVersionSelect}
          />
        </Provider>,
      );

      // Click on version 2
      await user.click(screen.getByTestId("version-item-v2"));

      expect(onVersionSelect).toHaveBeenCalledWith(mockVersions[1]);
    });
  });

  describe("restore version", () => {
    it("should show restore button for non-current versions", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" currentVersionId="v3" />
        </Provider>,
      );

      // v3 is current, so no restore button
      expect(screen.queryByTestId("restore-button-v3")).not.toBeInTheDocument();

      // v2 and v1 should have restore buttons
      expect(screen.getByTestId("restore-button-v2")).toBeInTheDocument();
      expect(screen.getByTestId("restore-button-v1")).toBeInTheDocument();
    });

    it("should call restore mutation when restore button clicked", async () => {
      const user = userEvent.setup();
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" currentVersionId="v3" />
        </Provider>,
      );

      // Click restore on v2
      await user.click(screen.getByTestId("restore-button-v2"));

      expect(mockRestoreVersion).toHaveBeenCalled();
    });
  });

  describe("telemetry display", () => {
    it("should show prompt version when available", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      // First two versions have prompt_version "v1" displayed in telemetry badges
      // Look for prompt version badges (displayed in gray background spans)
      const promptVersionBadges = screen
        .getAllByText("v1")
        .filter(
          (el) =>
            el.className.includes("bg-gray-100") ||
            el.className.includes("bg-gray-800"),
        );
      expect(promptVersionBadges.length).toBeGreaterThanOrEqual(2);
    });

    it("should show prompt model when available", () => {
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" />
        </Provider>,
      );

      // First two versions have prompt_model
      expect(screen.getAllByText(/claude-opus-4-5/i)).toHaveLength(2);
    });
  });

  describe("diff view", () => {
    it("should have Compare button when two versions selected", async () => {
      const user = userEvent.setup();
      const store = createMockStore();

      render(
        <Provider store={store}>
          <WorkflowVersionHistory workflowId="wf-123" enableDiff />
        </Provider>,
      );

      // Select first version (for comparison)
      await user.click(screen.getByTestId("version-checkbox-v3"));
      await user.click(screen.getByTestId("version-checkbox-v2"));

      expect(
        screen.getByRole("button", { name: /Compare/i }),
      ).toBeInTheDocument();
    });
  });
});
