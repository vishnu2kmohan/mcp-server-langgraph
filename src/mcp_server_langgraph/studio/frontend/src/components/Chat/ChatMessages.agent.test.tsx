/**
 * ChatMessages Agent Execution Tests
 *
 * =============================================================================
 * DEPRECATED - SKIPPED DUE TO OOM/HANG ISSUES
 * =============================================================================
 *
 * These tests are DEPRECATED in favor of AgentExecutionTracePanel.test.tsx.
 * Reason: The lazy-loaded AgentExecutionTracePanel causes OOM hangs when
 * testing through ChatMessages integration, even with code splitting.
 *
 * COVERAGE: All 28 LangGraph visualization tests are in:
 *   src/components/Chat/AgentExecutionTracePanel.test.tsx
 *
 * This file is kept for reference but tests are skipped. If lazy-loading
 * stability improves in future Vitest versions, these can be re-enabled.
 *
 * Historical context:
 * - AgentExecutionTracePanel is lazy-loaded in ChatMessages.tsx
 * - Tests use async/await patterns to handle Suspense boundary loading
 * - Memory consumption was ~11GB causing worker OOM in fork pool
 *
 * =============================================================================
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ChatMessages } from "./ChatMessages";

// Mock the API module for AgentExecutionTrace tests (uses useStudioAnalyzeMutation)
vi.mock("../../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            trace_summarize: {
              summary: "Agent completed workflow",
              total_duration_ms: 1000,
              step_count: 3,
              tool_call_count: 1,
              success: true,
              key_actions: ["Processed request"],
            },
          },
          cross_insights: [],
          failed_analyses: [],
          total_cost: "0.001",
        }),
    })),
    { isLoading: false },
  ]),
}));

// Create test store for Redux Provider
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}
const ReduxWrapper = ({ children }: WrapperProps) => {
  const store = createTestStore();
  return <Provider store={store}>{children}</Provider>;
};

const renderWithProvider = (ui: React.ReactElement) => {
  return render(ui, { wrapper: ReduxWrapper });
};

// SKIPPED: Tests cause OOM/hang issues with lazy-loaded AgentExecutionTracePanel.
// See AgentExecutionTracePanel.test.tsx for comprehensive coverage (28 tests).
describe.skip("ChatMessages AgentExecutionTrace (DEPRECATED - see header)", () => {
  const mockMessagesForTrace = [
    {
      id: "msg-1",
      role: "user" as const,
      content: "Run the analysis workflow",
      timestamp: Date.now(),
    },
  ];

  // Cleanup after each test to prevent DOM leakage and state pollution
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should render agent execution trace panel when provided", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          steps: [{ name: "agent", status: "running" }],
          tokens: { input: 100, output: 50 },
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      expect(screen.getByText(/Execution Steps/i)).toBeInTheDocument();
    });
  });

  it("should display LangGraph nodes when provided in trace", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          nodes: [
            {
              id: "start",
              name: "Start",
              type: "start",
              status: "completed",
            },
            {
              id: "analyze",
              name: "Analyze Input",
              type: "tool",
              status: "running",
            },
            {
              id: "decide",
              name: "Route Decision",
              type: "conditional",
              status: "pending",
            },
            { id: "end", name: "End", type: "end", status: "pending" },
          ],
          edges: [
            { from: "start", to: "analyze" },
            { from: "analyze", to: "decide" },
            { from: "decide", to: "end", condition: "complete" },
          ],
          currentNode: "analyze",
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      expect(
        screen.getByTestId("langgraph-node-visualization"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Start")).toBeInTheDocument();
    expect(screen.getByText("Analyze Input")).toBeInTheDocument();
    expect(screen.getByText("Route Decision")).toBeInTheDocument();
  });

  it("should highlight the current active node", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          nodes: [
            {
              id: "start",
              name: "Start",
              type: "start",
              status: "completed",
            },
            {
              id: "process",
              name: "Process",
              type: "tool",
              status: "running",
            },
          ],
          currentNode: "process",
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      const activeNode = screen.getByTestId("node-process");
      expect(activeNode).toHaveClass("ring-2");
    });
  });

  it("should display different node type icons", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          nodes: [
            {
              id: "start",
              name: "Start",
              type: "start",
              status: "completed",
            },
            { id: "tool", name: "Search", type: "tool", status: "running" },
            {
              id: "conditional",
              name: "Check",
              type: "conditional",
              status: "pending",
            },
          ],
          currentNode: "tool",
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      expect(screen.getByTestId("node-type-start")).toBeInTheDocument();
    });
    expect(screen.getByTestId("node-type-tool")).toBeInTheDocument();
    expect(screen.getByTestId("node-type-conditional")).toBeInTheDocument();
  });

  it("should show node status indicators", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          nodes: [
            { id: "n1", name: "Step 1", type: "tool", status: "completed" },
            { id: "n2", name: "Step 2", type: "tool", status: "running" },
            { id: "n3", name: "Step 3", type: "tool", status: "error" },
            { id: "n4", name: "Step 4", type: "tool", status: "pending" },
          ],
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      expect(screen.getByTestId("node-status-completed")).toBeInTheDocument();
    });
    expect(screen.getByTestId("node-status-running")).toBeInTheDocument();
    expect(screen.getByTestId("node-status-error")).toBeInTheDocument();
    expect(screen.getByTestId("node-status-pending")).toBeInTheDocument();
  });

  it("should display edge connections between nodes", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          nodes: [
            { id: "a", name: "A", type: "start", status: "completed" },
            { id: "b", name: "B", type: "tool", status: "completed" },
          ],
          edges: [{ from: "a", to: "b" }],
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      expect(screen.getByTestId("edge-a-to-b")).toBeInTheDocument();
    });
  });

  it("should show conditional edge labels", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          nodes: [
            {
              id: "check",
              name: "Check",
              type: "conditional",
              status: "completed",
            },
            {
              id: "success",
              name: "Success",
              type: "tool",
              status: "running",
            },
            {
              id: "failure",
              name: "Failure",
              type: "tool",
              status: "pending",
            },
          ],
          edges: [
            { from: "check", to: "success", condition: "passed" },
            { from: "check", to: "failure", condition: "failed" },
          ],
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      expect(screen.getByText("passed")).toBeInTheDocument();
    });
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("should fallback to simple steps view when no nodes provided", async () => {
    renderWithProvider(
      <ChatMessages
        messages={mockMessagesForTrace}
        isStreaming={true}
        streamingContent=""
        agentExecutionTrace={{
          steps: [
            { name: "Processing", status: "running" },
            { name: "Completed", status: "success" },
          ],
          tokens: { input: 100, output: 200 },
        }}
      />,
    );

    const toggleButton = screen.getByLabelText("Toggle agent execution trace");
    fireEvent.click(toggleButton);

    // Wait for lazy-loaded component to render
    await waitFor(() => {
      expect(screen.getByText("Processing")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("langgraph-node-visualization"),
    ).not.toBeInTheDocument();
  });
});
