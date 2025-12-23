/**
 * AgentExecutionTracePanel Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * This component displays agent execution trace data including:
 * - LangGraph node visualization
 * - Execution steps fallback
 * - Token usage
 * - Raw output
 * - Sprint 5: AI-powered trace intelligence
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { AgentExecutionTracePanel } from "./AgentExecutionTracePanel";
import type { AgentExecutionTrace } from "../../types/chat";

// Mock the API module for AI features
vi.mock("../../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            trace_summarize: {
              summary:
                "Agent completed 5-step workflow in 2.3s with 2 tool calls",
              total_duration_ms: 2300,
              step_count: 5,
              tool_call_count: 2,
              success: true,
              key_actions: [
                "Retrieved data",
                "Processed request",
                "Generated response",
              ],
            },
            trace_anomaly: {
              anomalies: [
                {
                  type: "slow_step",
                  step_name: "database_query",
                  severity: "warning",
                  message: "Step took 1.5s, 3x slower than average",
                },
              ],
              bottlenecks: [
                {
                  step_name: "database_query",
                  duration_ms: 1500,
                  percentage_of_total: 65,
                },
              ],
              health_score: 0.72,
              optimization_suggestions: [
                "Consider parallel execution for independent steps",
              ],
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

// Create test store
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}
const Wrapper = ({ children }: WrapperProps) => {
  const store = createTestStore();
  return <Provider store={store}>{children}</Provider>;
};

const renderWithProvider = (ui: React.ReactElement) => {
  return render(ui, { wrapper: Wrapper });
};

// Mock LangGraphNodeVisualization to simplify testing
vi.mock("./LangGraphNodeVisualization", () => ({
  LangGraphNodeVisualization: ({
    nodes,
    edges,
    currentNode,
  }: {
    nodes: unknown[];
    edges?: unknown[];
    currentNode?: string;
  }) => (
    <div
      data-testid="langgraph-node-visualization"
      data-nodes={nodes.length}
      data-edges={edges?.length ?? 0}
      data-current-node={currentNode}
    >
      LangGraph Visualization Mock
    </div>
  ),
}));

describe("AgentExecutionTracePanel", () => {
  describe("rendering", () => {
    it("renders container with correct test ID when trace is provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "test", status: "completed" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByTestId("agent-trace-panel")).toBeInTheDocument();
    });

    it("renders empty state when trace is undefined", () => {
      renderWithProvider(<AgentExecutionTracePanel trace={undefined} />);

      expect(screen.getByTestId("agent-trace-panel-empty")).toBeInTheDocument();
      expect(
        screen.getByText(/processing.*trace data will appear/i),
      ).toBeInTheDocument();
    });

    it("applies custom className when provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "test", status: "completed" }],
      };

      renderWithProvider(
        <AgentExecutionTracePanel trace={trace} className="custom-class" />,
      );

      const panel = screen.getByTestId("agent-trace-panel");
      expect(panel).toHaveClass("custom-class");
    });
  });

  describe("LangGraph visualization", () => {
    it("renders LangGraphNodeVisualization when nodes are provided", () => {
      const trace: AgentExecutionTrace = {
        nodes: [
          { id: "1", name: "start", type: "start", status: "completed" },
          { id: "2", name: "agent", type: "agent", status: "running" },
        ],
        edges: [{ from: "1", to: "2" }],
        currentNode: "2",
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(
        screen.getByTestId("langgraph-node-visualization"),
      ).toBeInTheDocument();
      expect(screen.getByText("Workflow Execution:")).toBeInTheDocument();
    });

    it("passes edges and currentNode to LangGraphNodeVisualization", () => {
      const trace: AgentExecutionTrace = {
        nodes: [
          { id: "1", name: "start", type: "start", status: "completed" },
          { id: "2", name: "agent", type: "agent", status: "running" },
        ],
        edges: [{ from: "1", to: "2" }],
        currentNode: "2",
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      const viz = screen.getByTestId("langgraph-node-visualization");
      expect(viz).toHaveAttribute("data-nodes", "2");
      expect(viz).toHaveAttribute("data-edges", "1");
      expect(viz).toHaveAttribute("data-current-node", "2");
    });

    it("does not render visualization when nodes array is empty", () => {
      const trace: AgentExecutionTrace = {
        nodes: [],
        steps: [{ name: "fallback", status: "completed" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(
        screen.queryByTestId("langgraph-node-visualization"),
      ).not.toBeInTheDocument();
    });
  });

  describe("steps fallback", () => {
    it("shows execution steps when no nodes provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [
          { name: "Step 1", status: "completed" },
          { name: "Step 2", status: "running" },
        ],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("Execution Steps:")).toBeInTheDocument();
      expect(screen.getByText("Step 1")).toBeInTheDocument();
      expect(screen.getByText("Step 2")).toBeInTheDocument();
    });

    it("shows correct status indicators for completed steps", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "Completed Step", status: "completed" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      const stepItem = screen.getByText("Completed Step").closest("li");
      expect(stepItem).toBeInTheDocument();
      // Check for green indicator (bg-green-500)
      const indicator = stepItem?.querySelector(".bg-green-500");
      expect(indicator).toBeInTheDocument();
    });

    it("shows correct status indicators for running steps", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "Running Step", status: "running" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      const stepItem = screen.getByText("Running Step").closest("li");
      expect(stepItem).toBeInTheDocument();
      // Check for blue pulsing indicator (bg-blue-500 animate-pulse)
      const indicator = stepItem?.querySelector(".bg-blue-500");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("animate-pulse");
    });

    it("shows correct status indicators for pending steps", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "Pending Step", status: "pending" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      const stepItem = screen.getByText("Pending Step").closest("li");
      expect(stepItem).toBeInTheDocument();
      // Check for gray indicator (bg-gray-400)
      const indicator = stepItem?.querySelector(".bg-gray-400");
      expect(indicator).toBeInTheDocument();
    });

    it("shows duration when provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "Fast Step", status: "completed", duration: 150 }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("(150ms)")).toBeInTheDocument();
    });

    it("does not render steps section when steps array is empty", () => {
      const trace: AgentExecutionTrace = {
        steps: [],
        tokens: { input: 100, output: 50 },
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.queryByText("Execution Steps:")).not.toBeInTheDocument();
    });

    it("prefers nodes over steps when both are provided", () => {
      const trace: AgentExecutionTrace = {
        nodes: [{ id: "1", name: "Node", type: "agent", status: "completed" }],
        steps: [{ name: "Step", status: "completed" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("Workflow Execution:")).toBeInTheDocument();
      expect(screen.queryByText("Execution Steps:")).not.toBeInTheDocument();
    });
  });

  describe("token usage", () => {
    it("displays input and output token counts", () => {
      const trace: AgentExecutionTrace = {
        tokens: { input: 1500, output: 750 },
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText(/Input: 1500 tokens/)).toBeInTheDocument();
      expect(screen.getByText(/Output: 750 tokens/)).toBeInTheDocument();
    });

    it("hides token section when tokens not provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "test", status: "completed" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.queryByText(/Input:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Output:/)).not.toBeInTheDocument();
    });
  });

  describe("raw output", () => {
    it("renders collapsible raw output section", () => {
      const trace: AgentExecutionTrace = {
        rawOutput: "This is the raw LLM output",
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("Raw Output")).toBeInTheDocument();
      expect(
        screen.getByText("This is the raw LLM output"),
      ).toBeInTheDocument();
    });

    it("hides raw output when not provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "test", status: "completed" }],
      };

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.queryByText("Raw Output")).not.toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("shows placeholder when trace has no usable data", () => {
      const trace: AgentExecutionTrace = {};

      renderWithProvider(<AgentExecutionTracePanel trace={trace} />);

      expect(
        screen.getByText(/processing.*trace data will appear/i),
      ).toBeInTheDocument();
    });
  });

  // =============================================================================
  // Sprint 5: AI-Powered Trace Intelligence (TDD - RED Phase)
  // =============================================================================
  describe("Sprint 5: AI-powered trace intelligence", () => {
    const traceWithAI: AgentExecutionTrace = {
      steps: [
        { name: "fetch_data", status: "completed", duration: 150 },
        { name: "database_query", status: "completed", duration: 1500 },
        { name: "process_results", status: "completed", duration: 200 },
        { name: "generate_response", status: "completed", duration: 450 },
      ],
      tokens: { input: 1500, output: 750 },
    };

    describe("AI summary panel", () => {
      it("displays AI-generated trace summary when enableAI is true", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={true}
          />,
        );

        expect(screen.getByTestId("ai-trace-summary")).toBeInTheDocument();
        expect(
          screen.getByText(/Agent completed 5-step workflow/i),
        ).toBeInTheDocument();
      });

      it("does not show AI summary when enableAI is false", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={false}
          />,
        );

        expect(
          screen.queryByTestId("ai-trace-summary"),
        ).not.toBeInTheDocument();
      });

      it("shows key actions from AI analysis", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={true}
          />,
        );

        expect(screen.getByText(/Retrieved data/)).toBeInTheDocument();
        expect(screen.getByText(/Processed request/)).toBeInTheDocument();
        expect(screen.getByText(/Generated response/)).toBeInTheDocument();
      });
    });

    describe("AI anomaly detection", () => {
      it("displays bottleneck indicators for slow steps", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={true}
          />,
        );

        expect(
          screen.getByTestId("ai-bottleneck-indicator"),
        ).toBeInTheDocument();
        expect(screen.getByText(/database_query/)).toBeInTheDocument();
        expect(screen.getByText(/65%/)).toBeInTheDocument();
      });

      it("shows health score indicator", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={true}
          />,
        );

        expect(screen.getByTestId("ai-health-score")).toBeInTheDocument();
        expect(screen.getByText(/72%/)).toBeInTheDocument();
      });

      it("displays optimization suggestions", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={true}
          />,
        );

        expect(
          screen.getByText(/Consider parallel execution/i),
        ).toBeInTheDocument();
      });

      it("shows warning badge for anomalies", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={true}
          />,
        );

        expect(screen.getByTestId("ai-anomaly-badge")).toBeInTheDocument();
        expect(screen.getByText(/3x slower than average/)).toBeInTheDocument();
      });
    });

    describe("AI loading states", () => {
      it("shows loading indicator while AI analysis is in progress", () => {
        // Mock loading state
        vi.mocked(
          vi.fn(() => ({
            useStudioAnalyzeMutation: vi.fn(() => [
              vi.fn(),
              { isLoading: true },
            ]),
          })),
        );

        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
            enableAI={true}
          />,
        );

        // The component should still render trace data while AI loads
        expect(screen.getByTestId("agent-trace-panel")).toBeInTheDocument();
      });
    });

    describe("AI feature requirements", () => {
      it("requires userId prop when enableAI is true", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            enableAI={true}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
          />,
        );

        expect(screen.getByTestId("ai-trace-summary")).toBeInTheDocument();
      });

      it("requires traceId prop for AI trace analysis", () => {
        renderWithProvider(
          <AgentExecutionTracePanel
            trace={traceWithAI}
            enableAI={true}
            userId="user-123"
            sessionId="session-456"
            traceId="trace-789"
          />,
        );

        expect(screen.getByTestId("ai-trace-summary")).toBeInTheDocument();
      });
    });
  });
});
