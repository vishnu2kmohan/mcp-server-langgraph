/**
 * ConditionNode Tests
 *
 * TDD tests for Conditional branching node component.
 * Tests cover:
 * - Rendering with proper label
 * - True/False labels
 * - Status visualization (idle, running, success, error)
 * - Selection state
 * - Connection handles (1 target, 2 source for true/false)
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { ConditionNode } from "./ConditionNode";
import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "../../../types/workflow";

// Helper to render nodes with ReactFlow context
const renderNode = (node: JSX.Element) => {
  return render(<ReactFlowProvider>{node}</ReactFlowProvider>);
};

describe("ConditionNode", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const createNodeProps = (
    data: Partial<WorkflowNodeData> = {},
    selected = false,
  ): NodeProps<WorkflowNodeData> => ({
    id: "condition-1",
    data: {
      label: "Check Result",
      nodeType: "condition",
      config: {},
      status: "idle",
      ...data,
    },
    selected,
    type: "condition",
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    isConnectable: true,
    dragging: false,
  });

  describe("Rendering", () => {
    it("should render with label", () => {
      renderNode(<ConditionNode {...createNodeProps()} />);
      expect(screen.getByText("Check Result")).toBeInTheDocument();
    });

    it("should render True and False labels", () => {
      renderNode(<ConditionNode {...createNodeProps()} />);
      expect(screen.getByText("True")).toBeInTheDocument();
      expect(screen.getByText("False")).toBeInTheDocument();
    });

    it("should render with GitBranch icon", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps()} />,
      );
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });
  });

  describe("Status Visualization", () => {
    it("should show idle state with gray border", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps({ status: "idle" })} />,
      );
      const node = container.querySelector('[data-status="idle"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-neutral-300");
    });

    it("should show running state with blue border and animation", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps({ status: "running" })} />,
      );
      const node = container.querySelector('[data-status="running"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-primary-500");
      expect(node).toHaveClass("animate-pulse");
    });

    it("should show success state with green border", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps({ status: "success" })} />,
      );
      const node = container.querySelector('[data-status="success"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-success-500");
    });

    it("should show error state with red border", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps({ status: "error" })} />,
      );
      const node = container.querySelector('[data-status="error"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-error-500");
    });
  });

  describe("Selection State", () => {
    it("should highlight when selected", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps({}, true)} />,
      );
      const node = container.querySelector('[data-selected="true"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-primary-500");
    });

    it("should not highlight when not selected", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps({}, false)} />,
      );
      const node = container.querySelector('[data-selected="false"]');
      expect(node).toBeInTheDocument();
    });
  });

  describe("Connection Handles", () => {
    it("should have target handle on left", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps()} />,
      );
      const targetHandle = container.querySelector('[data-handlepos="left"]');
      expect(targetHandle).toBeInTheDocument();
    });

    it("should have two source handles on right for true/false branches", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps()} />,
      );
      const sourceHandles = container.querySelectorAll(
        '[data-handlepos="right"]',
      );
      expect(sourceHandles.length).toBe(2);
    });

    it("should have true branch handle with id", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps()} />,
      );
      const trueHandle = container.querySelector('[data-handleid="true"]');
      expect(trueHandle).toBeInTheDocument();
    });

    it("should have false branch handle with id", () => {
      const { container } = renderNode(
        <ConditionNode {...createNodeProps()} />,
      );
      const falseHandle = container.querySelector('[data-handleid="false"]');
      expect(falseHandle).toBeInTheDocument();
    });
  });
});
