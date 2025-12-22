/**
 * AgentExecutionTracePanel Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * This component displays agent execution trace data including:
 * - LangGraph node visualization
 * - Execution steps fallback
 * - Token usage
 * - Raw output
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AgentExecutionTracePanel } from "./AgentExecutionTracePanel";
import type { AgentExecutionTrace } from "../../types/chat";

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

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByTestId("agent-trace-panel")).toBeInTheDocument();
    });

    it("renders empty state when trace is undefined", () => {
      render(<AgentExecutionTracePanel trace={undefined} />);

      expect(
        screen.getByTestId("agent-trace-panel-empty")
      ).toBeInTheDocument();
      expect(
        screen.getByText(/processing.*trace data will appear/i)
      ).toBeInTheDocument();
    });

    it("applies custom className when provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "test", status: "completed" }],
      };

      render(
        <AgentExecutionTracePanel trace={trace} className="custom-class" />
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

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(
        screen.getByTestId("langgraph-node-visualization")
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

      render(<AgentExecutionTracePanel trace={trace} />);

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

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(
        screen.queryByTestId("langgraph-node-visualization")
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

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("Execution Steps:")).toBeInTheDocument();
      expect(screen.getByText("Step 1")).toBeInTheDocument();
      expect(screen.getByText("Step 2")).toBeInTheDocument();
    });

    it("shows correct status indicators for completed steps", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "Completed Step", status: "completed" }],
      };

      render(<AgentExecutionTracePanel trace={trace} />);

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

      render(<AgentExecutionTracePanel trace={trace} />);

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

      render(<AgentExecutionTracePanel trace={trace} />);

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

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("(150ms)")).toBeInTheDocument();
    });

    it("does not render steps section when steps array is empty", () => {
      const trace: AgentExecutionTrace = {
        steps: [],
        tokens: { input: 100, output: 50 },
      };

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.queryByText("Execution Steps:")).not.toBeInTheDocument();
    });

    it("prefers nodes over steps when both are provided", () => {
      const trace: AgentExecutionTrace = {
        nodes: [{ id: "1", name: "Node", type: "agent", status: "completed" }],
        steps: [{ name: "Step", status: "completed" }],
      };

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("Workflow Execution:")).toBeInTheDocument();
      expect(screen.queryByText("Execution Steps:")).not.toBeInTheDocument();
    });
  });

  describe("token usage", () => {
    it("displays input and output token counts", () => {
      const trace: AgentExecutionTrace = {
        tokens: { input: 1500, output: 750 },
      };

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText(/Input: 1500 tokens/)).toBeInTheDocument();
      expect(screen.getByText(/Output: 750 tokens/)).toBeInTheDocument();
    });

    it("hides token section when tokens not provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "test", status: "completed" }],
      };

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.queryByText(/Input:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Output:/)).not.toBeInTheDocument();
    });
  });

  describe("raw output", () => {
    it("renders collapsible raw output section", () => {
      const trace: AgentExecutionTrace = {
        rawOutput: "This is the raw LLM output",
      };

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.getByText("Raw Output")).toBeInTheDocument();
      expect(
        screen.getByText("This is the raw LLM output")
      ).toBeInTheDocument();
    });

    it("hides raw output when not provided", () => {
      const trace: AgentExecutionTrace = {
        steps: [{ name: "test", status: "completed" }],
      };

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(screen.queryByText("Raw Output")).not.toBeInTheDocument();
    });
  });

  describe("empty state", () => {
    it("shows placeholder when trace has no usable data", () => {
      const trace: AgentExecutionTrace = {};

      render(<AgentExecutionTracePanel trace={trace} />);

      expect(
        screen.getByText(/processing.*trace data will appear/i)
      ).toBeInTheDocument();
    });
  });
});
