/**
 * ToolNode Tests
 *
 * TDD tests for Tool execution node component.
 * Tests cover:
 * - Rendering with proper label and tool name
 * - Status visualization (idle, running, success, error)
 * - Selection state
 * - Connection handles (target and source)
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { ToolNode } from "./ToolNode";
import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "../../../types/workflow";

// Helper to render nodes with ReactFlow context
const renderNode = (node: JSX.Element) => {
  return render(<ReactFlowProvider>{node}</ReactFlowProvider>);
};

describe("ToolNode", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const createNodeProps = (
    data: Partial<WorkflowNodeData> = {},
    selected = false,
  ): NodeProps<WorkflowNodeData> => ({
    id: "tool-1",
    data: {
      label: "Web Search",
      nodeType: "tool",
      config: { toolName: "web_search" },
      status: "idle",
      ...data,
    },
    selected,
    type: "tool",
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    isConnectable: true,
    dragging: false,
  });

  describe("Rendering", () => {
    it("should render with label", () => {
      renderNode(<ToolNode {...createNodeProps()} />);
      expect(screen.getByText("Web Search")).toBeInTheDocument();
    });

    it("should render with tool name", () => {
      renderNode(<ToolNode {...createNodeProps()} />);
      expect(screen.getByText("web_search")).toBeInTheDocument();
    });

    it("should render default tool name when not specified", () => {
      renderNode(<ToolNode {...createNodeProps({ config: {} })} />);
      expect(screen.getByText("Unknown Tool")).toBeInTheDocument();
    });

    it("should render with Wrench icon", () => {
      const { container } = renderNode(<ToolNode {...createNodeProps()} />);
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });
  });

  describe("Status Visualization", () => {
    it("should show idle state with gray border", () => {
      const { container } = renderNode(
        <ToolNode {...createNodeProps({ status: "idle" })} />,
      );
      const node = container.querySelector('[data-status="idle"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-neutral-5");
    });

    it("should show running state with blue border and animation", () => {
      const { container } = renderNode(
        <ToolNode {...createNodeProps({ status: "running" })} />,
      );
      const node = container.querySelector('[data-status="running"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-primary-9");
      expect(node).toHaveClass("animate-pulse");
    });

    it("should show success state with green border", () => {
      const { container } = renderNode(
        <ToolNode {...createNodeProps({ status: "success" })} />,
      );
      const node = container.querySelector('[data-status="success"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-success-9");
    });

    it("should show error state with red border", () => {
      const { container } = renderNode(
        <ToolNode {...createNodeProps({ status: "error" })} />,
      );
      const node = container.querySelector('[data-status="error"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-error-9");
    });
  });

  describe("Selection State", () => {
    it("should highlight when selected", () => {
      const { container } = renderNode(
        <ToolNode {...createNodeProps({}, true)} />,
      );
      const node = container.querySelector('[data-selected="true"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-primary-9");
    });

    it("should not highlight when not selected", () => {
      const { container } = renderNode(
        <ToolNode {...createNodeProps({}, false)} />,
      );
      const node = container.querySelector('[data-selected="false"]');
      expect(node).toBeInTheDocument();
    });
  });

  describe("Connection Handles", () => {
    it("should have target handle on left", () => {
      const { container } = renderNode(<ToolNode {...createNodeProps()} />);
      const targetHandle = container.querySelector('[data-handlepos="left"]');
      expect(targetHandle).toBeInTheDocument();
    });

    it("should have source handle on right", () => {
      const { container } = renderNode(<ToolNode {...createNodeProps()} />);
      const sourceHandle = container.querySelector('[data-handlepos="right"]');
      expect(sourceHandle).toBeInTheDocument();
    });
  });
});
