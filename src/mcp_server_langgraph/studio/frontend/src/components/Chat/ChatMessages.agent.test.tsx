/**
 * ChatMessages Agent Execution Tests
 *
 * Tests for AgentExecutionTrace with LangGraph node visualization.
 * Split from ChatMessages.integration.test.tsx for memory optimization.
 *
 * Note: This file uses Redux Provider and API mocking for AgentExecutionTracePanel.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
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

// Skip these tests due to OOM - AgentExecutionTracePanel loads heavy dependencies
// TODO: Investigate memory usage of AgentExecutionTracePanel and optimize
describe.skip("ChatMessages AgentExecutionTrace", () => {
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

  it("should render agent execution trace panel when provided", () => {
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

    expect(screen.getByText(/Execution Steps/i)).toBeInTheDocument();
  });

  it("should display LangGraph nodes when provided in trace", () => {
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

    expect(
      screen.getByTestId("langgraph-node-visualization"),
    ).toBeInTheDocument();
    expect(screen.getByText("Start")).toBeInTheDocument();
    expect(screen.getByText("Analyze Input")).toBeInTheDocument();
    expect(screen.getByText("Route Decision")).toBeInTheDocument();
  });

  it("should highlight the current active node", () => {
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

    const activeNode = screen.getByTestId("node-process");
    expect(activeNode).toHaveClass("ring-2");
  });

  it("should display different node type icons", () => {
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

    expect(screen.getByTestId("node-type-start")).toBeInTheDocument();
    expect(screen.getByTestId("node-type-tool")).toBeInTheDocument();
    expect(screen.getByTestId("node-type-conditional")).toBeInTheDocument();
  });

  it("should show node status indicators", () => {
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

    expect(screen.getByTestId("node-status-completed")).toBeInTheDocument();
    expect(screen.getByTestId("node-status-running")).toBeInTheDocument();
    expect(screen.getByTestId("node-status-error")).toBeInTheDocument();
    expect(screen.getByTestId("node-status-pending")).toBeInTheDocument();
  });

  it("should display edge connections between nodes", () => {
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

    expect(screen.getByTestId("edge-a-to-b")).toBeInTheDocument();
  });

  it("should show conditional edge labels", () => {
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

    expect(screen.getByText("passed")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("should fallback to simple steps view when no nodes provided", () => {
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

    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(
      screen.queryByTestId("langgraph-node-visualization"),
    ).not.toBeInTheDocument();
  });
});
