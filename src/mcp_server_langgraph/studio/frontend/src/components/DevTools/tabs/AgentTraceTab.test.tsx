/**
 * AgentTraceTab Tests
 *
 * TDD tests for the Agent Trace tab in DevTools.
 * Displays LangGraph agent execution traces.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

import { AgentTraceTab } from "./AgentTraceTab";
import type { AgentExecutionTrace } from "../../../types/chat";

// =============================================================================
// Mock Data
// =============================================================================

const mockTrace: AgentExecutionTrace = {
  nodes: [
    {
      id: "node-1",
      name: "Agent",
      status: "completed",
      duration: 150,
      startTime: 1703000000000,
      endTime: 1703000000150,
    },
    {
      id: "node-2",
      name: "Tool Call",
      status: "completed",
      duration: 50,
      startTime: 1703000000150,
      endTime: 1703000000200,
    },
    {
      id: "node-3",
      name: "Response",
      status: "running",
      duration: 0,
      startTime: 1703000000200,
    },
  ],
  steps: [],
  tokens: {
    input: 100,
    output: 50,
    total: 150,
  },
  rawOutput: "Agent completed successfully",
};

// =============================================================================
// Mock Hooks
// =============================================================================

const mockUseAgentTrace = vi.fn().mockReturnValue({
  trace: mockTrace,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
});

vi.mock("../hooks/useAgentTrace", () => ({
  useAgentTrace: () => mockUseAgentTrace(),
}));

// =============================================================================
// Tests
// =============================================================================

describe("AgentTraceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAgentTrace.mockReturnValue({
      trace: mockTrace,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByTestId("agent-trace-tab")).toBeInTheDocument();
    });

    it("should display session ID", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByText("session-123")).toBeInTheDocument();
    });

    it("should show loading state", () => {
      mockUseAgentTrace.mockReturnValue({
        trace: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByTestId("agent-trace-loading")).toBeInTheDocument();
    });

    it("should show empty state when no trace data", () => {
      mockUseAgentTrace.mockReturnValue({
        trace: null,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByTestId("agent-trace-empty")).toBeInTheDocument();
      expect(screen.getByText(/no trace data/i)).toBeInTheDocument();
    });
  });

  describe("node visualization", () => {
    it("should display trace nodes", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByText("Agent")).toBeInTheDocument();
      expect(screen.getByText("Tool Call")).toBeInTheDocument();
      expect(screen.getByText("Response")).toBeInTheDocument();
    });

    it("should show node status indicators", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      // Should have status indicators for nodes
      expect(screen.getByTestId("node-status-node-1")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-node-2")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-node-3")).toBeInTheDocument();
    });

    it("should show node duration", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      // Completed nodes should show duration
      expect(screen.getByText("150ms")).toBeInTheDocument();
      expect(screen.getByText("50ms")).toBeInTheDocument();
    });
  });

  describe("node highlighting", () => {
    it("should call onNodeHighlight when node clicked", async () => {
      const handleNodeHighlight = vi.fn();

      render(
        <AgentTraceTab
          sessionId="session-123"
          onNodeHighlight={handleNodeHighlight}
        />
      );

      const node = screen.getByTestId("trace-node-node-1");
      fireEvent.click(node);

      expect(handleNodeHighlight).toHaveBeenCalledWith("node-1");
    });

    it("should clear highlight when same node clicked again", async () => {
      const handleNodeHighlight = vi.fn();

      render(
        <AgentTraceTab
          sessionId="session-123"
          onNodeHighlight={handleNodeHighlight}
        />
      );

      const node = screen.getByTestId("trace-node-node-1");

      fireEvent.click(node);
      expect(handleNodeHighlight).toHaveBeenCalledWith("node-1");

      fireEvent.click(node);
      expect(handleNodeHighlight).toHaveBeenCalledWith(null);
    });
  });

  describe("token usage", () => {
    it("should display token counts", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByTestId("token-input")).toHaveTextContent("100");
      expect(screen.getByTestId("token-output")).toHaveTextContent("50");
      expect(screen.getByTestId("token-total")).toHaveTextContent("150");
    });
  });

  describe("timeline view", () => {
    it("should show timeline view toggle", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByTestId("view-toggle")).toBeInTheDocument();
    });

    it("should switch between list and timeline views", async () => {
      const user = userEvent.setup();

      render(<AgentTraceTab sessionId="session-123" />);

      // Default is list view
      expect(screen.getByTestId("trace-list-view")).toBeInTheDocument();

      // Click timeline view
      await user.click(screen.getByTestId("view-timeline"));

      expect(screen.getByTestId("trace-timeline-view")).toBeInTheDocument();
    });
  });

  describe("refresh", () => {
    it("should have refresh button", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByTestId("refresh-trace-button")).toBeInTheDocument();
    });

    it("should call refetch when refresh clicked", async () => {
      const user = userEvent.setup();
      const mockRefetch = vi.fn();

      mockUseAgentTrace.mockReturnValue({
        trace: mockTrace,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(<AgentTraceTab sessionId="session-123" />);

      await user.click(screen.getByTestId("refresh-trace-button"));

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("should display error message when fetch fails", () => {
      mockUseAgentTrace.mockReturnValue({
        trace: null,
        isLoading: false,
        error: new Error("Failed to fetch trace"),
        refetch: vi.fn(),
      });

      render(<AgentTraceTab sessionId="session-123" />);

      expect(screen.getByTestId("agent-trace-error")).toBeInTheDocument();
      expect(screen.getByText(/failed to fetch/i)).toBeInTheDocument();
    });
  });

  describe("expand/collapse", () => {
    it("should expand node details on click", async () => {
      const user = userEvent.setup();

      render(<AgentTraceTab sessionId="session-123" />);

      const expandButton = screen.getByTestId("expand-node-node-1");
      await user.click(expandButton);

      expect(screen.getByTestId("node-details-node-1")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have accessible structure", () => {
      render(<AgentTraceTab sessionId="session-123" />);

      // Should have proper heading
      expect(
        screen.getByRole("heading", { name: /trace/i })
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(<AgentTraceTab sessionId="session-123" />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
