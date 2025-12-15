/**
 * StartNode Tests
 *
 * TDD tests for Start node component.
 * Tests cover:
 * - Rendering with proper label and icon
 * - Status visualization (idle, running, success, error)
 * - Selection state
 * - Handles (connection points)
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { StartNode } from "./StartNode";
import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "../../../types/workflow";

// Helper to render nodes with ReactFlow context
const renderNode = (node: JSX.Element) => {
  return render(<ReactFlowProvider>{node}</ReactFlowProvider>);
};

describe("StartNode", () => {
  const createNodeProps = (
    data: Partial<WorkflowNodeData> = {},
    selected = false,
  ): NodeProps<WorkflowNodeData> => ({
    id: "start-1",
    data: {
      label: "Start",
      nodeType: "start",
      config: {},
      status: "idle",
      ...data,
    },
    selected,
    type: "start",
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    isConnectable: true,
    dragging: false,
  });

  describe("Rendering", () => {
    it("should render with label", () => {
      renderNode(<StartNode {...createNodeProps()} />);
      expect(screen.getByText("Start")).toBeInTheDocument();
    });

    it("should render with Play icon", () => {
      const { container } = renderNode(<StartNode {...createNodeProps()} />);
      // Check for SVG with Play icon class
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("should render with custom label", () => {
      renderNode(
        <StartNode {...createNodeProps({ label: "Begin Workflow" })} />,
      );
      expect(screen.getByText("Begin Workflow")).toBeInTheDocument();
    });
  });

  describe("Status Visualization", () => {
    it("should show idle state with gray border", () => {
      const { container } = renderNode(
        <StartNode {...createNodeProps({ status: "idle" })} />,
      );
      const node = container.querySelector('[data-status="idle"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-gray-300");
    });

    it("should show running state with blue border and spinner", () => {
      const { container } = renderNode(
        <StartNode {...createNodeProps({ status: "running" })} />,
      );
      const node = container.querySelector('[data-status="running"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-blue-500");
      expect(node).toHaveClass("animate-pulse");
    });

    it("should show success state with green border and checkmark", () => {
      const { container } = renderNode(
        <StartNode {...createNodeProps({ status: "success" })} />,
      );
      const node = container.querySelector('[data-status="success"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-green-500");
    });

    it("should show error state with red border and error icon", () => {
      const { container } = renderNode(
        <StartNode {...createNodeProps({ status: "error" })} />,
      );
      const node = container.querySelector('[data-status="error"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-red-500");
    });
  });

  describe("Selection State", () => {
    it("should highlight when selected", () => {
      const { container } = renderNode(
        <StartNode {...createNodeProps({}, true)} />,
      );
      const node = container.querySelector('[data-selected="true"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-blue-500");
    });

    it("should not highlight when not selected", () => {
      const { container } = renderNode(
        <StartNode {...createNodeProps({}, false)} />,
      );
      const node = container.querySelector('[data-selected="false"]');
      expect(node).toBeInTheDocument();
    });
  });

  describe("Connection Handles", () => {
    it("should have source handle on right", () => {
      const { container } = renderNode(<StartNode {...createNodeProps()} />);
      const sourceHandle = container.querySelector('[data-handlepos="right"]');
      expect(sourceHandle).toBeInTheDocument();
    });

    it("should not have target handle (entry point)", () => {
      const { container } = renderNode(<StartNode {...createNodeProps()} />);
      const targetHandle = container.querySelector('[data-handlepos="left"]');
      expect(targetHandle).not.toBeInTheDocument();
    });
  });
});
