/**
 * LangGraphNodeVisualization Component Test Suite
 *
 * TDD tests for LangGraph workflow visualization component.
 * Extracted from ChatMessages.tsx for reusability.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import {
  LangGraphNodeVisualization,
  getNodeTypeIcon,
  getNodeStatusIndicator,
  getNodeColor,
} from "./LangGraphNodeVisualization";
import type { LangGraphNode, LangGraphEdge } from "../../types/chat";

import { TestProvider } from "@/test-utils";

describe("LangGraphNodeVisualization", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  describe("component rendering", () => {
    it("should render the visualization container", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
      ];

      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={nodes} />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("langgraph-node-visualization"),
      ).toBeInTheDocument();
    });

    it("should render all nodes", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
        { id: "2", name: "Process", type: "agent", status: "running" },
        { id: "3", name: "End", type: "end", status: "pending" },
      ];

      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={nodes} />
        </TestProvider>,
      );

      expect(screen.getByTestId("node-1")).toBeInTheDocument();
      expect(screen.getByTestId("node-2")).toBeInTheDocument();
      expect(screen.getByTestId("node-3")).toBeInTheDocument();
    });

    it("should display node names", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "My Custom Node", type: "agent", status: "completed" },
      ];

      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={nodes} />
        </TestProvider>,
      );

      expect(screen.getByText("My Custom Node")).toBeInTheDocument();
    });

    it("should display node duration when provided", () => {
      const nodes: LangGraphNode[] = [
        {
          id: "1",
          name: "Fast Node",
          type: "tool",
          status: "completed",
          duration: 150,
        },
      ];

      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={nodes} />
        </TestProvider>,
      );

      expect(screen.getByText("150ms")).toBeInTheDocument();
    });

    it("should highlight the current active node", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
        { id: "2", name: "Active", type: "agent", status: "running" },
      ];

      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={nodes} currentNode="2" />
        </TestProvider>,
      );

      const activeNode = screen.getByTestId("node-2");
      expect(activeNode.className).toContain("ring-2");
    });

    it("should render edges between nodes", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
        { id: "2", name: "End", type: "end", status: "pending" },
      ];
      const edges: LangGraphEdge[] = [{ from: "1", to: "2" }];

      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={nodes} edges={edges} />
        </TestProvider>,
      );

      expect(screen.getByTestId("edge-1-to-2")).toBeInTheDocument();
    });

    it("should display edge conditions when provided", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Decision", type: "conditional", status: "completed" },
        { id: "2", name: "Path A", type: "agent", status: "pending" },
      ];
      const edges: LangGraphEdge[] = [
        { from: "1", to: "2", condition: "success" },
      ];

      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={nodes} edges={edges} />
        </TestProvider>,
      );

      expect(screen.getByText("success")).toBeInTheDocument();
    });

    it("should handle empty nodes array", () => {
      render(
        <TestProvider>
          <LangGraphNodeVisualization nodes={[]} />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("langgraph-node-visualization"),
      ).toBeInTheDocument();
    });
  });

  describe("getNodeTypeIcon", () => {
    it("should return correct icon for start type", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeTypeIcon("start")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-type-start"]'),
      ).toBeInTheDocument();
    });

    it("should return correct icon for end type", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeTypeIcon("end")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-type-end"]'),
      ).toBeInTheDocument();
    });

    it("should return correct icon for tool type", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeTypeIcon("tool")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-type-tool"]'),
      ).toBeInTheDocument();
    });

    it("should return correct icon for conditional type", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeTypeIcon("conditional")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-type-conditional"]'),
      ).toBeInTheDocument();
    });

    it("should return correct icon for agent type", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeTypeIcon("agent")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-type-agent"]'),
      ).toBeInTheDocument();
    });

    it("should return default icon for unknown type", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeTypeIcon("default")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-type-default"]'),
      ).toBeInTheDocument();
    });

    it("should respect custom size parameter", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeTypeIcon("start", 20)}</>
        </TestProvider>,
      );
      const icon = container.querySelector('[data-testid="node-type-start"]');
      expect(icon).toHaveAttribute("width", "20");
      expect(icon).toHaveAttribute("height", "20");
    });
  });

  describe("getNodeStatusIndicator", () => {
    it("should return completed indicator", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeStatusIndicator("completed")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-status-completed"]'),
      ).toBeInTheDocument();
    });

    it("should return running indicator with animation", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeStatusIndicator("running")}</>
        </TestProvider>,
      );
      const indicator = container.querySelector(
        '[data-testid="node-status-running"]',
      );
      expect(indicator).toBeInTheDocument();
      // SVG elements use classList in jsdom
      expect(indicator).toHaveClass("animate-spin");
    });

    it("should return error indicator", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeStatusIndicator("error")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-status-error"]'),
      ).toBeInTheDocument();
    });

    it("should return pending indicator", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeStatusIndicator("pending")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-status-pending"]'),
      ).toBeInTheDocument();
    });

    it("should return skipped indicator", () => {
      const { container } = render(
        <TestProvider>
          <>{getNodeStatusIndicator("skipped")}</>
        </TestProvider>,
      );
      expect(
        container.querySelector('[data-testid="node-status-skipped"]'),
      ).toBeInTheDocument();
    });
  });

  describe("getNodeColor", () => {
    it("should return error colors for error status", () => {
      const color = getNodeColor("agent", "error");
      // Uses Radix semantic color scale
      expect(color).toContain("error");
    });

    it("should return running colors for running status", () => {
      const color = getNodeColor("agent", "running");
      // Uses primary color for running state
      expect(color).toContain("primary");
    });

    it("should return completed colors for completed status", () => {
      const color = getNodeColor("agent", "completed");
      // Uses success color for completed state
      expect(color).toContain("success");
    });

    it("should return start node colors", () => {
      const color = getNodeColor("start", "pending");
      // Start nodes use success color
      expect(color).toContain("success");
    });

    it("should return end node colors", () => {
      const color = getNodeColor("end", "pending");
      // End nodes use neutral color
      expect(color).toContain("neutral");
    });

    it("should return conditional node colors", () => {
      const color = getNodeColor("conditional", "pending");
      // Conditional nodes use warning/amber color
      expect(color).toContain("warning");
    });

    it("should return tool node colors", () => {
      const color = getNodeColor("tool", "pending");
      // Tool nodes use insight color
      expect(color).toContain("insight");
    });

    it("should return agent node colors", () => {
      const color = getNodeColor("agent", "pending");
      // Agent nodes use primary color
      expect(color).toContain("primary");
    });

    it("should return default colors for unknown type", () => {
      const color = getNodeColor("default", "pending");
      // Default uses neutral color
      expect(color).toContain("neutral");
    });
  });
});
