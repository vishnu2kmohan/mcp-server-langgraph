/**
 * LangGraphNodeVisualization Component Test Suite
 *
 * TDD tests for LangGraph workflow visualization component.
 * Extracted from ChatMessages.tsx for reusability.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  LangGraphNodeVisualization,
  getNodeTypeIcon,
  getNodeStatusIndicator,
  getNodeColor,
} from "./LangGraphNodeVisualization";
import type { LangGraphNode, LangGraphEdge } from "../../types/chat";

describe("LangGraphNodeVisualization", () => {
  describe("component rendering", () => {
    it("should render the visualization container", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
      ];

      render(<LangGraphNodeVisualization nodes={nodes} />);

      expect(
        screen.getByTestId("langgraph-node-visualization")
      ).toBeInTheDocument();
    });

    it("should render all nodes", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
        { id: "2", name: "Process", type: "agent", status: "running" },
        { id: "3", name: "End", type: "end", status: "pending" },
      ];

      render(<LangGraphNodeVisualization nodes={nodes} />);

      expect(screen.getByTestId("node-1")).toBeInTheDocument();
      expect(screen.getByTestId("node-2")).toBeInTheDocument();
      expect(screen.getByTestId("node-3")).toBeInTheDocument();
    });

    it("should display node names", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "My Custom Node", type: "agent", status: "completed" },
      ];

      render(<LangGraphNodeVisualization nodes={nodes} />);

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

      render(<LangGraphNodeVisualization nodes={nodes} />);

      expect(screen.getByText("150ms")).toBeInTheDocument();
    });

    it("should highlight the current active node", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
        { id: "2", name: "Active", type: "agent", status: "running" },
      ];

      render(<LangGraphNodeVisualization nodes={nodes} currentNode="2" />);

      const activeNode = screen.getByTestId("node-2");
      expect(activeNode.className).toContain("ring-2");
    });

    it("should render edges between nodes", () => {
      const nodes: LangGraphNode[] = [
        { id: "1", name: "Start", type: "start", status: "completed" },
        { id: "2", name: "End", type: "end", status: "pending" },
      ];
      const edges: LangGraphEdge[] = [{ from: "1", to: "2" }];

      render(<LangGraphNodeVisualization nodes={nodes} edges={edges} />);

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

      render(<LangGraphNodeVisualization nodes={nodes} edges={edges} />);

      expect(screen.getByText("success")).toBeInTheDocument();
    });

    it("should handle empty nodes array", () => {
      render(<LangGraphNodeVisualization nodes={[]} />);

      expect(
        screen.getByTestId("langgraph-node-visualization")
      ).toBeInTheDocument();
    });
  });

  describe("getNodeTypeIcon", () => {
    it("should return correct icon for start type", () => {
      const { container } = render(<>{getNodeTypeIcon("start")}</>);
      expect(container.querySelector('[data-testid="node-type-start"]')).toBeInTheDocument();
    });

    it("should return correct icon for end type", () => {
      const { container } = render(<>{getNodeTypeIcon("end")}</>);
      expect(container.querySelector('[data-testid="node-type-end"]')).toBeInTheDocument();
    });

    it("should return correct icon for tool type", () => {
      const { container } = render(<>{getNodeTypeIcon("tool")}</>);
      expect(container.querySelector('[data-testid="node-type-tool"]')).toBeInTheDocument();
    });

    it("should return correct icon for conditional type", () => {
      const { container } = render(<>{getNodeTypeIcon("conditional")}</>);
      expect(container.querySelector('[data-testid="node-type-conditional"]')).toBeInTheDocument();
    });

    it("should return correct icon for agent type", () => {
      const { container } = render(<>{getNodeTypeIcon("agent")}</>);
      expect(container.querySelector('[data-testid="node-type-agent"]')).toBeInTheDocument();
    });

    it("should return default icon for unknown type", () => {
      const { container } = render(<>{getNodeTypeIcon("default")}</>);
      expect(container.querySelector('[data-testid="node-type-default"]')).toBeInTheDocument();
    });

    it("should respect custom size parameter", () => {
      const { container } = render(<>{getNodeTypeIcon("start", 20)}</>);
      const icon = container.querySelector('[data-testid="node-type-start"]');
      expect(icon).toHaveAttribute("width", "20");
      expect(icon).toHaveAttribute("height", "20");
    });
  });

  describe("getNodeStatusIndicator", () => {
    it("should return completed indicator", () => {
      const { container } = render(<>{getNodeStatusIndicator("completed")}</>);
      expect(container.querySelector('[data-testid="node-status-completed"]')).toBeInTheDocument();
    });

    it("should return running indicator with animation", () => {
      const { container } = render(<>{getNodeStatusIndicator("running")}</>);
      const indicator = container.querySelector('[data-testid="node-status-running"]');
      expect(indicator).toBeInTheDocument();
      // SVG elements use classList in jsdom
      expect(indicator).toHaveClass("animate-spin");
    });

    it("should return error indicator", () => {
      const { container } = render(<>{getNodeStatusIndicator("error")}</>);
      expect(container.querySelector('[data-testid="node-status-error"]')).toBeInTheDocument();
    });

    it("should return pending indicator", () => {
      const { container } = render(<>{getNodeStatusIndicator("pending")}</>);
      expect(container.querySelector('[data-testid="node-status-pending"]')).toBeInTheDocument();
    });

    it("should return skipped indicator", () => {
      const { container } = render(<>{getNodeStatusIndicator("skipped")}</>);
      expect(container.querySelector('[data-testid="node-status-skipped"]')).toBeInTheDocument();
    });
  });

  describe("getNodeColor", () => {
    it("should return error colors for error status", () => {
      const color = getNodeColor("agent", "error");
      expect(color).toContain("red");
    });

    it("should return running colors for running status", () => {
      const color = getNodeColor("agent", "running");
      expect(color).toContain("blue");
    });

    it("should return completed colors for completed status", () => {
      const color = getNodeColor("agent", "completed");
      expect(color).toContain("green");
    });

    it("should return start node colors", () => {
      const color = getNodeColor("start", "pending");
      expect(color).toContain("emerald");
    });

    it("should return end node colors", () => {
      const color = getNodeColor("end", "pending");
      expect(color).toContain("slate");
    });

    it("should return conditional node colors", () => {
      const color = getNodeColor("conditional", "pending");
      expect(color).toContain("amber");
    });

    it("should return tool node colors", () => {
      const color = getNodeColor("tool", "pending");
      expect(color).toContain("purple");
    });

    it("should return agent node colors", () => {
      const color = getNodeColor("agent", "pending");
      expect(color).toContain("indigo");
    });

    it("should return default colors for unknown type", () => {
      const color = getNodeColor("default", "pending");
      expect(color).toContain("gray");
    });
  });
});
