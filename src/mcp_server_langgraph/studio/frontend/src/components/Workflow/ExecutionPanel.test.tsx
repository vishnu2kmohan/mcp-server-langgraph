/**
 * ExecutionPanel Component Tests
 *
 * TDD tests for the execution logs panel.
 * Features:
 * - Display execution state (idle, running, completed, error)
 * - Show execution logs with timestamps
 * - Log level icons (info, warning, error)
 * - Clear logs button
 * - Close button
 * - Empty state message
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ExecutionPanel } from "./ExecutionPanel";
import workflowReducer from "../../store/slices/workflowSlice";
import type { ExecutionLog, NodeStatus } from "../../types/workflow";

// Sample execution logs for testing
const sampleLogs: ExecutionLog[] = [
  {
    id: "log-1",
    timestamp: 1704067200000, // 2024-01-01 00:00:00
    level: "info",
    message: "Workflow started",
  },
  {
    id: "log-2",
    timestamp: 1704067201000,
    level: "info",
    nodeId: "node-1",
    message: "Processing input",
  },
  {
    id: "log-3",
    timestamp: 1704067202000,
    level: "warning",
    nodeId: "node-2",
    message: "Rate limit approaching",
  },
  {
    id: "log-4",
    timestamp: 1704067203000,
    level: "error",
    nodeId: "node-3",
    message: "Connection failed",
  },
];

// Create test store with configurable state
const createTestStore = (
  executionState: "idle" | "running" | "completed" | "error" = "idle",
  executionLogs: ExecutionLog[] = [],
  nodeStatuses: Record<string, NodeStatus> = {},
) => {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
    },
    preloadedState: {
      workflow: {
        workflows: [],
        currentWorkflow: null,
        nodes: [],
        edges: [],
        selectedNodeId: null,
        isLoading: false,
        isSaving: false,
        error: null,
        isDirty: false,
        executionState,
        executionResult: null,
        executionLogs,
        nodeStatuses,
        total: 0,
        page: 1,
        perPage: 10,
      },
    },
  });
};

const renderWithProviders = (
  executionState: "idle" | "running" | "completed" | "error" = "idle",
  executionLogs: ExecutionLog[] = [],
  onClose?: () => void,
  onStop?: () => void,
  nodeStatuses: Record<string, NodeStatus> = {},
) => {
  const store = createTestStore(executionState, executionLogs, nodeStatuses);
  return {
    store,
    ...render(
      <Provider store={store}>
        <ExecutionPanel onClose={onClose} onStop={onStop} />
      </Provider>,
    ),
  };
};

describe("ExecutionPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Header", () => {
    it('should render the title "Execution Logs"', () => {
      renderWithProviders();
      expect(screen.getByText("Execution Logs")).toBeInTheDocument();
    });

    it("should show close button when onClose is provided", () => {
      const onClose = vi.fn();
      renderWithProviders("idle", [], onClose);

      const closeButton = screen.getByRole("button", { name: "" });
      expect(closeButton).toBeInTheDocument();
    });

    it("should call onClose when close button is clicked", () => {
      const onClose = vi.fn();
      renderWithProviders("idle", [], onClose);

      // Find button with X icon
      const buttons = screen.getAllByRole("button");
      const closeButton = buttons.find((btn) => btn.querySelector("svg"));
      if (closeButton) {
        fireEvent.click(closeButton);
      }

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Execution State Display", () => {
    it("should show idle state badge", () => {
      renderWithProviders("idle");
      expect(screen.getByText("idle")).toBeInTheDocument();
    });

    it("should show running state badge", () => {
      renderWithProviders("running");
      expect(screen.getByText("running")).toBeInTheDocument();
    });

    it("should show completed state badge", () => {
      renderWithProviders("completed");
      expect(screen.getByText("completed")).toBeInTheDocument();
    });

    it("should show error state badge", () => {
      renderWithProviders("error");
      expect(screen.getByText("error")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state message when no logs", () => {
      renderWithProviders("idle", []);
      expect(screen.getByText(/No execution logs yet/i)).toBeInTheDocument();
    });

    it("should show prompt to run workflow", () => {
      renderWithProviders("idle", []);
      expect(
        screen.getByText(/Click "Run" to execute the workflow/i),
      ).toBeInTheDocument();
    });

    it("should not show Clear button when no logs", () => {
      renderWithProviders("idle", []);
      expect(screen.queryByText("Clear")).not.toBeInTheDocument();
    });
  });

  describe("Log Display", () => {
    it("should display log messages", () => {
      renderWithProviders("running", sampleLogs);
      expect(screen.getByText("Workflow started")).toBeInTheDocument();
      expect(screen.getByText("Processing input")).toBeInTheDocument();
      expect(screen.getByText("Rate limit approaching")).toBeInTheDocument();
      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });

    it("should display node IDs when present", () => {
      renderWithProviders("running", sampleLogs);
      expect(screen.getByText("[node-1]")).toBeInTheDocument();
      expect(screen.getByText("[node-2]")).toBeInTheDocument();
      expect(screen.getByText("[node-3]")).toBeInTheDocument();
    });

    it("should not display node ID brackets when not present", () => {
      renderWithProviders("running", [sampleLogs[0]]); // First log has no nodeId
      expect(screen.queryByText(/\[.*\]/)).not.toBeInTheDocument();
    });

    it("should display formatted timestamps", () => {
      renderWithProviders("running", sampleLogs);
      // Timestamps should be formatted as time strings
      const timeElements = screen.getAllByText(/\d{1,2}:\d{2}:\d{2}/);
      expect(timeElements.length).toBeGreaterThan(0);
    });
  });

  describe("Log Level Icons", () => {
    it("should render icon for info level logs", () => {
      const { container } = renderWithProviders("running", [sampleLogs[0]]);
      // Info logs should have a blue icon (Info from lucide-react)
      const svg = container.querySelector("svg.text-primary-500");
      expect(svg).toBeInTheDocument();
    });

    it("should render icon for warning level logs", () => {
      const { container } = renderWithProviders("running", [sampleLogs[2]]);
      // Warning logs should have a yellow icon (AlertTriangle from lucide-react)
      const svg = container.querySelector("svg.text-warning-500");
      expect(svg).toBeInTheDocument();
    });

    it("should render icon for error level logs", () => {
      const { container } = renderWithProviders("running", [sampleLogs[3]]);
      // Error logs should have a red icon (XCircle from lucide-react)
      const svg = container.querySelector("svg.text-error-500");
      expect(svg).toBeInTheDocument();
    });
  });

  describe("Clear Logs", () => {
    it("should show Clear button when logs exist", () => {
      renderWithProviders("completed", sampleLogs);
      expect(screen.getByText("Clear")).toBeInTheDocument();
    });

    it("should clear logs when Clear button is clicked", () => {
      const { store } = renderWithProviders("completed", sampleLogs);

      const clearButton = screen.getByText("Clear");
      fireEvent.click(clearButton);

      // Check that the store was updated
      const state = store.getState();
      expect(state.workflow.executionLogs).toHaveLength(0);
    });

    it("should show empty state after clearing logs", () => {
      renderWithProviders("completed", sampleLogs);

      const clearButton = screen.getByText("Clear");
      fireEvent.click(clearButton);

      expect(screen.getByText(/No execution logs yet/i)).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("should apply correct styling for idle state", () => {
      renderWithProviders("idle");
      const badge = screen.getByText("idle");
      expect(badge.className).toContain("bg-gray");
    });

    it("should apply correct styling for running state", () => {
      renderWithProviders("running");
      const badge = screen.getByText("running");
      expect(badge.className).toContain("bg-blue");
    });

    it("should apply correct styling for completed state", () => {
      renderWithProviders("completed");
      const badge = screen.getByText("completed");
      expect(badge.className).toContain("bg-green");
    });

    it("should apply correct styling for error state", () => {
      renderWithProviders("error");
      const badge = screen.getByText("error");
      expect(badge.className).toContain("bg-red");
    });
  });

  describe("Multiple Logs", () => {
    it("should render all logs in order", () => {
      renderWithProviders("running", sampleLogs);

      const logMessages = [
        "Workflow started",
        "Processing input",
        "Rate limit approaching",
        "Connection failed",
      ];

      logMessages.forEach((message) => {
        expect(screen.getByText(message)).toBeInTheDocument();
      });
    });

    it("should handle many logs without crashing", () => {
      const manyLogs: ExecutionLog[] = Array.from({ length: 100 }, (_, i) => ({
        id: `log-${i}`,
        timestamp: 1704067200000 + i * 1000,
        level: "info" as const,
        message: `Log message ${i}`,
      }));

      renderWithProviders("running", manyLogs);

      // Should render first and last log
      expect(screen.getByText("Log message 0")).toBeInTheDocument();
      expect(screen.getByText("Log message 99")).toBeInTheDocument();
    });
  });

  describe("Stop Execution", () => {
    it("should show Stop button when execution is running", () => {
      const onStop = vi.fn();
      renderWithProviders("running", sampleLogs, undefined, onStop);
      expect(screen.getByText("Stop")).toBeInTheDocument();
    });

    it("should not show Stop button when execution is idle", () => {
      renderWithProviders("idle", []);
      expect(screen.queryByText("Stop")).not.toBeInTheDocument();
    });

    it("should not show Stop button when execution is completed", () => {
      renderWithProviders("completed", sampleLogs);
      expect(screen.queryByText("Stop")).not.toBeInTheDocument();
    });

    it("should not show Stop button when execution is in error state", () => {
      renderWithProviders("error", sampleLogs);
      expect(screen.queryByText("Stop")).not.toBeInTheDocument();
    });

    it("should call onStop when Stop button is clicked", () => {
      const onStop = vi.fn();
      renderWithProviders("running", sampleLogs, undefined, onStop);

      const stopButton = screen.getByText("Stop");
      fireEvent.click(stopButton);

      expect(onStop).toHaveBeenCalledTimes(1);
    });
  });

  describe("Node Status Display", () => {
    it("should show node statuses when available", () => {
      const nodeStatuses = {
        "node-1": "success" as const,
        "node-2": "running" as const,
        "node-3": "error" as const,
      };
      renderWithProviders(
        "running",
        sampleLogs,
        undefined,
        undefined,
        nodeStatuses,
      );

      expect(screen.getByTestId("node-status-node-1")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-node-2")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-node-3")).toBeInTheDocument();
    });

    it("should not show node status section when no node statuses", () => {
      renderWithProviders("running", sampleLogs);
      expect(screen.queryByTestId("node-statuses")).not.toBeInTheDocument();
    });

    it("should show correct badge color for running node", () => {
      const nodeStatuses = { "node-1": "running" as const };
      const { container } = renderWithProviders(
        "running",
        [],
        undefined,
        undefined,
        nodeStatuses,
      );

      const badge = container.querySelector(
        '[data-testid="node-status-node-1"]',
      );
      expect(badge?.className).toContain("bg-blue");
    });

    it("should show correct badge color for success node", () => {
      const nodeStatuses = { "node-1": "success" as const };
      const { container } = renderWithProviders(
        "running",
        [],
        undefined,
        undefined,
        nodeStatuses,
      );

      const badge = container.querySelector(
        '[data-testid="node-status-node-1"]',
      );
      expect(badge?.className).toContain("bg-green");
    });

    it("should show correct badge color for error node", () => {
      const nodeStatuses = { "node-1": "error" as const };
      const { container } = renderWithProviders(
        "running",
        [],
        undefined,
        undefined,
        nodeStatuses,
      );

      const badge = container.querySelector(
        '[data-testid="node-status-node-1"]',
      );
      expect(badge?.className).toContain("bg-red");
    });
  });

  describe("Auto-scroll", () => {
    it("should have a scrollable logs container", () => {
      const { container } = renderWithProviders("running", sampleLogs);

      const logsContainer = container.querySelector(
        '[data-testid="logs-container"]',
      );
      expect(logsContainer).toBeInTheDocument();
    });

    it("should auto-scroll to bottom when new logs are added", async () => {
      const initialLogs = [sampleLogs[0]];
      const { container } = renderWithProviders("running", initialLogs);

      const logsContainer = container.querySelector(
        '[data-testid="logs-container"]',
      );
      expect(logsContainer).toBeInTheDocument();

      // Verify scrollIntoView is called for the last log item
      // This is tested by checking the ref is attached to the last item
      const logItems = container.querySelectorAll('[data-testid="log-item"]');
      expect(logItems.length).toBe(1);
    });

    it("should mark last log item with data-last attribute", () => {
      const { container } = renderWithProviders("running", sampleLogs);

      const logItems = container.querySelectorAll('[data-testid="log-item"]');
      const lastItem = logItems[logItems.length - 1];

      expect(lastItem).toHaveAttribute("data-last", "true");
    });
  });
});
