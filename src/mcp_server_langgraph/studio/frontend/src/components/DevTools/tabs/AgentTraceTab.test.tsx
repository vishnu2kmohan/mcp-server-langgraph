/**
 * AgentTraceTab Tests
 *
 * TDD tests for the Agent Trace tab in DevTools.
 * Displays LangGraph agent execution traces.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

import { AgentTraceTab } from "./AgentTraceTab";
import type { AgentExecutionTrace } from "../../../types/chat";

import { TestProvider } from "@/test-utils";

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

// Mock timeline context to avoid provider requirement
const mockTimelineContext = vi.fn().mockReturnValue({
  timeWindow: null,
  isLiveMode: true,
  currentTime: Date.now(),
  events: [],
  bookmarks: [],
});

vi.mock("../context/DevToolsTimelineProvider", () => ({
  useTimelineContext: () => mockTimelineContext(),
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
    // Reset timeline context to default (no filtering)
    mockTimelineContext.mockReturnValue({
      timeWindow: null,
      isLiveMode: true,
      currentTime: Date.now(),
      events: [],
      bookmarks: [],
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByTestId("agent-trace-tab")).toBeInTheDocument();
    });

    it("should display session ID", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByText("session-123")).toBeInTheDocument();
    });

    it("should show loading state", () => {
      mockUseAgentTrace.mockReturnValue({
        trace: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByTestId("agent-trace-loading")).toBeInTheDocument();
    });

    it("should show empty state when no trace data", () => {
      mockUseAgentTrace.mockReturnValue({
        trace: null,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByTestId("agent-trace-empty")).toBeInTheDocument();
      expect(screen.getByText(/no trace data/i)).toBeInTheDocument();
    });
  });

  describe("node visualization", () => {
    it("should display trace nodes", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByText("Agent")).toBeInTheDocument();
      expect(screen.getByText("Tool Call")).toBeInTheDocument();
      expect(screen.getByText("Response")).toBeInTheDocument();
    });

    it("should show node status indicators", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // Should have status indicators for nodes
      expect(screen.getByTestId("node-status-node-1")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-node-2")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-node-3")).toBeInTheDocument();
    });

    it("should show node duration", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // Completed nodes should show duration
      expect(screen.getByText("150ms")).toBeInTheDocument();
      expect(screen.getByText("50ms")).toBeInTheDocument();
    });
  });

  describe("node highlighting", () => {
    it("should call onNodeHighlight when node clicked", async () => {
      const handleNodeHighlight = vi.fn();

      render(
        <TestProvider>
          <AgentTraceTab
            sessionId="session-123"
            onNodeHighlight={handleNodeHighlight}
          />
        </TestProvider>,
      );

      const node = screen.getByTestId("trace-node-node-1");
      fireEvent.click(node);

      expect(handleNodeHighlight).toHaveBeenCalledWith("node-1");
    });

    it("should clear highlight when same node clicked again", async () => {
      const handleNodeHighlight = vi.fn();

      render(
        <TestProvider>
          <AgentTraceTab
            sessionId="session-123"
            onNodeHighlight={handleNodeHighlight}
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByTestId("token-input")).toHaveTextContent("100");
      expect(screen.getByTestId("token-output")).toHaveTextContent("50");
      expect(screen.getByTestId("token-total")).toHaveTextContent("150");
    });
  });

  describe("timeline view", () => {
    it("should show timeline view toggle", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByTestId("view-toggle")).toBeInTheDocument();
    });

    it("should switch between list and timeline views", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // Default is list view
      expect(screen.getByTestId("trace-list-view")).toBeInTheDocument();

      // Click timeline view
      await user.click(screen.getByTestId("view-timeline"));

      expect(screen.getByTestId("trace-timeline-view")).toBeInTheDocument();
    });
  });

  describe("refresh", () => {
    it("should have refresh button", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

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

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

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

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      expect(screen.getByTestId("agent-trace-error")).toBeInTheDocument();
      expect(screen.getByText(/failed to fetch/i)).toBeInTheDocument();
    });
  });

  describe("expand/collapse", () => {
    it("should expand node details on click", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      const expandButton = screen.getByTestId("expand-node-node-1");
      await user.click(expandButton);

      expect(screen.getByTestId("node-details-node-1")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have accessible structure", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // Should have proper heading
      expect(
        screen.getByRole("heading", { name: /trace/i }),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("timeline filtering with startTime", () => {
    it("should show all nodes when timeWindow is null", () => {
      // timeWindow is null by default from beforeEach
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // All 3 nodes should be visible
      expect(screen.getByText("Agent")).toBeInTheDocument();
      expect(screen.getByText("Tool Call")).toBeInTheDocument();
      expect(screen.getByText("Response")).toBeInTheDocument();
    });

    it("should filter nodes by timeline window when startTime is available", () => {
      // Mock timeline context with a time window that overlaps all nodes
      mockTimelineContext.mockReturnValue({
        timeWindow: {
          start: 1703000000100,
          end: 1703000000250,
        },
        isLiveMode: false,
        currentTime: 1703000000175,
        events: [],
        bookmarks: [],
      });

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // Only nodes overlapping with timeWindow should be visible
      // node-1: starts at 1703000000000, ends at 1703000000150 - overlaps (endTime > window.start)
      // node-2: starts at 1703000000150, ends at 1703000000200 - overlaps
      // node-3: starts at 1703000000200, no end (running) - overlaps (startTime < window.end)
      expect(screen.getByText("Agent")).toBeInTheDocument();
      expect(screen.getByText("Tool Call")).toBeInTheDocument();
      expect(screen.getByText("Response")).toBeInTheDocument();
    });

    it("should exclude nodes outside the timeline window", () => {
      // Mock timeline context with a narrow time window
      mockTimelineContext.mockReturnValue({
        timeWindow: {
          start: 1703000000160,
          end: 1703000000180,
        },
        isLiveMode: false,
        currentTime: 1703000000170,
        events: [],
        bookmarks: [],
      });

      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // node-1: ends at 1703000000150 - before window start (150 < 160), excluded
      // node-2: starts at 1703000000150, ends at 1703000000200 - overlaps (150 < 180 && 200 > 160)
      // node-3: starts at 1703000000200 - after window end (200 > 180), excluded
      expect(screen.queryByText("Agent")).not.toBeInTheDocument();
      expect(screen.getByText("Tool Call")).toBeInTheDocument();
      expect(screen.queryByText("Response")).not.toBeInTheDocument();
    });

    it("should show nodes with startTime for time-travel debugging", () => {
      render(
        <TestProvider>
          <AgentTraceTab sessionId="session-123" />
        </TestProvider>,
      );

      // Nodes with startTime should be rendered and have data-testid
      expect(screen.getByTestId("trace-node-node-1")).toBeInTheDocument();
      expect(screen.getByTestId("trace-node-node-2")).toBeInTheDocument();
      expect(screen.getByTestId("trace-node-node-3")).toBeInTheDocument();
    });
  });
});
