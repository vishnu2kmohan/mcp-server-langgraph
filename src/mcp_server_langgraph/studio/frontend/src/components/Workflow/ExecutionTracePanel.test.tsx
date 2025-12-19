/**
 * ExecutionTracePanel Tests
 *
 * TDD tests for LangGraph execution trace visualization.
 * Tests the real-time display of execution events, node highlighting,
 * and execution state management.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ExecutionTracePanel } from "./ExecutionTracePanel";
import workflowReducer, {
  initialWorkflowState,
} from "../../store/slices/workflowSlice";
import type { ExecutionLog } from "../../types/workflow";

// Mock execution logs for testing
const mockExecutionLogs: ExecutionLog[] = [
  {
    id: "log-1",
    timestamp: Date.now() - 5000,
    level: "info",
    message: "Starting workflow execution",
    nodeId: undefined,
  },
  {
    id: "log-2",
    timestamp: Date.now() - 4000,
    level: "info",
    message: "Executing node: start",
    nodeId: "node-start",
  },
  {
    id: "log-3",
    timestamp: Date.now() - 3000,
    level: "info",
    message: "Executing node: llm",
    nodeId: "node-llm",
  },
  {
    id: "log-4",
    timestamp: Date.now() - 2000,
    level: "warning",
    message: "Rate limit approaching",
    nodeId: "node-llm",
  },
  {
    id: "log-5",
    timestamp: Date.now() - 1000,
    level: "error",
    message: "API call failed",
    nodeId: "node-tool",
  },
];

function createMockStore(overrides: Partial<typeof initialWorkflowState> = {}) {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
    },
    preloadedState: {
      workflow: {
        ...initialWorkflowState,
        ...overrides,
      },
    },
  });
}

function renderWithStore(
  ui: React.ReactElement,
  overrides: Partial<typeof initialWorkflowState> = {},
) {
  const store = createMockStore(overrides);
  return {
    ...render(<Provider store={store}>{ui}</Provider>),
    store,
  };
}

describe("ExecutionTracePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render the panel with header", () => {
      renderWithStore(<ExecutionTracePanel />);
      expect(screen.getByText(/execution trace/i)).toBeInTheDocument();
    });

    it("should display empty state when no logs", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: [],
        executionState: "idle",
      });
      expect(screen.getByText(/no execution events yet/i)).toBeInTheDocument();
    });

    it("should display execution logs", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });
      expect(
        screen.getByText(/starting workflow execution/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/executing node: llm/i)).toBeInTheDocument();
    });

    it("should show different log levels with appropriate styling", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });

      // Should have info, warning, and error logs
      const infoLog = screen.getByText(/executing node: start/i);
      const warningLog = screen.getByText(/rate limit approaching/i);
      const errorLog = screen.getByText(/api call failed/i);

      expect(infoLog).toBeInTheDocument();
      expect(warningLog).toBeInTheDocument();
      expect(errorLog).toBeInTheDocument();
    });
  });

  describe("execution state indicators", () => {
    it("should show idle indicator when not executing", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionState: "idle",
      });
      expect(screen.getByText(/idle/i)).toBeInTheDocument();
    });

    it("should show running indicator with spinner", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionState: "running",
      });
      expect(screen.getByText(/running/i)).toBeInTheDocument();
      expect(screen.getByTestId("execution-spinner")).toBeInTheDocument();
    });

    it("should show completed indicator", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionState: "completed",
      });
      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    });

    it("should show error indicator", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionState: "error",
      });
      // Look for exact "Error" text (not "Errors" button)
      expect(screen.getByText("Error")).toBeInTheDocument();
    });
  });

  describe("log filtering", () => {
    it("should filter logs by level when filter is applied", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });

      // Click error filter
      const errorFilter = screen.getByRole("button", { name: /errors/i });
      fireEvent.click(errorFilter);

      // Should only show error logs
      expect(screen.getByText(/api call failed/i)).toBeInTheDocument();
      expect(
        screen.queryByText(/starting workflow execution/i),
      ).not.toBeInTheDocument();
    });

    it("should filter logs by node ID when node filter is applied", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });

      // Click on node filter input
      const nodeFilter = screen.getByPlaceholderText(/filter by node/i);
      fireEvent.change(nodeFilter, { target: { value: "llm" } });

      // Should only show logs for node-llm
      expect(screen.getByText(/executing node: llm/i)).toBeInTheDocument();
      expect(screen.getByText(/rate limit approaching/i)).toBeInTheDocument();
      expect(
        screen.queryByText(/starting workflow execution/i),
      ).not.toBeInTheDocument();
    });
  });

  describe("clear logs", () => {
    it("should clear logs when clear button is clicked", () => {
      const { store } = renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });

      const clearButton = screen.getByRole("button", { name: /clear/i });
      fireEvent.click(clearButton);

      // Store should have empty logs
      expect(store.getState().workflow.executionLogs).toHaveLength(0);
    });
  });

  describe("auto-scroll", () => {
    it("should auto-scroll to new logs by default", () => {
      const scrollIntoViewMock = vi.fn();
      Element.prototype.scrollIntoView = scrollIntoViewMock;

      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });

      // Should have called scrollIntoView for the last log
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });

    it("should toggle auto-scroll when button is clicked", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });

      const autoScrollToggle = screen.getByRole("button", {
        name: /auto-scroll/i,
      });
      expect(autoScrollToggle).toHaveAttribute("aria-pressed", "true");

      fireEvent.click(autoScrollToggle);
      expect(autoScrollToggle).toHaveAttribute("aria-pressed", "false");
    });
  });

  describe("log details", () => {
    it("should expand log details when clicked", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: [
          {
            id: "log-detail",
            timestamp: Date.now(),
            level: "info",
            message: "Node output",
            nodeId: "node-llm",
            data: { output: "Hello, world!", tokens: 50 },
          },
        ],
      });

      const logEntry = screen.getByText(/node output/i);
      fireEvent.click(logEntry);

      // Should show details
      expect(screen.getByText(/hello, world!/i)).toBeInTheDocument();
      expect(screen.getByText(/tokens: 50/i)).toBeInTheDocument();
    });
  });

  describe("timestamp formatting", () => {
    it("should display relative timestamps", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: [
          {
            id: "log-time",
            timestamp: Date.now() - 30000, // 30 seconds ago
            level: "info",
            message: "Test event",
          },
        ],
      });

      expect(screen.getByText(/30s ago/i)).toBeInTheDocument();
    });
  });

  describe("node highlighting", () => {
    it("should call onNodeHighlight when log with nodeId is hovered", () => {
      const onNodeHighlight = vi.fn();
      renderWithStore(
        <ExecutionTracePanel onNodeHighlight={onNodeHighlight} />,
        {
          executionLogs: mockExecutionLogs,
        },
      );

      const logWithNode = screen.getByText(/executing node: llm/i);
      fireEvent.mouseEnter(logWithNode.closest("[data-node-id]")!);

      expect(onNodeHighlight).toHaveBeenCalledWith("node-llm");
    });

    it("should clear highlight on mouse leave", () => {
      const onNodeHighlight = vi.fn();
      renderWithStore(
        <ExecutionTracePanel onNodeHighlight={onNodeHighlight} />,
        {
          executionLogs: mockExecutionLogs,
        },
      );

      const logWithNode = screen.getByText(/executing node: llm/i);
      const logElement = logWithNode.closest("[data-node-id]")!;
      fireEvent.mouseEnter(logElement);
      fireEvent.mouseLeave(logElement);

      expect(onNodeHighlight).toHaveBeenLastCalledWith(null);
    });
  });

  describe("accessibility", () => {
    it("should have accessible heading", () => {
      renderWithStore(<ExecutionTracePanel />);
      expect(
        screen.getByRole("heading", { name: /execution trace/i }),
      ).toBeInTheDocument();
    });

    it("should have accessible log list", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });
      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should announce new logs to screen readers", () => {
      renderWithStore(<ExecutionTracePanel />, {
        executionLogs: mockExecutionLogs,
      });

      const liveRegion = screen.getByRole("log");
      expect(liveRegion).toHaveAttribute("aria-live", "polite");
    });
  });
});
