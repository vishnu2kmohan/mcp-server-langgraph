/**
 * LLMNode Tests
 *
 * TDD tests for LLM completion node component.
 * Tests cover:
 * - Rendering with proper label and model
 * - Status visualization (idle, running, success, error)
 * - Selection state
 * - Connection handles (target and source)
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { LLMNode } from "./LLMNode";
import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "../../../types/workflow";

// Helper to render nodes with ReactFlow context
const renderNode = (node: JSX.Element) => {
  return render(<ReactFlowProvider>{node}</ReactFlowProvider>);
};

describe("LLMNode", () => {
  const createNodeProps = (
    data: Partial<WorkflowNodeData> = {},
    selected = false,
  ): NodeProps<WorkflowNodeData> => ({
    id: "llm-1",
    data: {
      label: "Analyze Data",
      nodeType: "llm",
      config: { model: "gpt-4" },
      status: "idle",
      ...data,
    },
    selected,
    type: "llm",
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    isConnectable: true,
    dragging: false,
  });

  describe("Rendering", () => {
    it("should render with label", () => {
      renderNode(<LLMNode {...createNodeProps()} />);
      expect(screen.getByText("Analyze Data")).toBeInTheDocument();
    });

    it("should render with model name", () => {
      renderNode(<LLMNode {...createNodeProps()} />);
      expect(screen.getByText("gpt-4")).toBeInTheDocument();
    });

    it("should render default model when not specified", () => {
      renderNode(<LLMNode {...createNodeProps({ config: {} })} />);
      expect(screen.getByText("gemini-2.5-flash")).toBeInTheDocument();
    });

    it("should render with Brain icon", () => {
      const { container } = renderNode(<LLMNode {...createNodeProps()} />);
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });
  });

  describe("Status Visualization", () => {
    it("should show idle state with gray border", () => {
      const { container } = renderNode(
        <LLMNode {...createNodeProps({ status: "idle" })} />,
      );
      const node = container.querySelector('[data-status="idle"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-gray-300");
    });

    it("should show running state with blue border and animation", () => {
      const { container } = renderNode(
        <LLMNode {...createNodeProps({ status: "running" })} />,
      );
      const node = container.querySelector('[data-status="running"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-blue-500");
      expect(node).toHaveClass("animate-pulse");
    });

    it("should show success state with green border", () => {
      const { container } = renderNode(
        <LLMNode {...createNodeProps({ status: "success" })} />,
      );
      const node = container.querySelector('[data-status="success"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-green-500");
    });

    it("should show error state with red border", () => {
      const { container } = renderNode(
        <LLMNode {...createNodeProps({ status: "error" })} />,
      );
      const node = container.querySelector('[data-status="error"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-red-500");
    });
  });

  describe("Selection State", () => {
    it("should highlight when selected", () => {
      const { container } = renderNode(
        <LLMNode {...createNodeProps({}, true)} />,
      );
      const node = container.querySelector('[data-selected="true"]');
      expect(node).toBeInTheDocument();
      expect(node).toHaveClass("border-blue-500");
    });

    it("should not highlight when not selected", () => {
      const { container } = renderNode(
        <LLMNode {...createNodeProps({}, false)} />,
      );
      const node = container.querySelector('[data-selected="false"]');
      expect(node).toBeInTheDocument();
    });
  });

  describe("Connection Handles", () => {
    it("should have target handle on left", () => {
      const { container } = renderNode(<LLMNode {...createNodeProps()} />);
      const targetHandle = container.querySelector('[data-handlepos="left"]');
      expect(targetHandle).toBeInTheDocument();
    });

    it("should have source handle on right", () => {
      const { container } = renderNode(<LLMNode {...createNodeProps()} />);
      const sourceHandle = container.querySelector('[data-handlepos="right"]');
      expect(sourceHandle).toBeInTheDocument();
    });
  });
});
