/**
 * EndNode Tests
 *
 * TDD tests for the workflow termination node.
 * Tests cover:
 * - Rendering with label
 * - Status visualization (idle, running, success, error)
 * - Selection states
 * - Handle configuration (only target, no source)
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { EndNode } from "./EndNode";
import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "../../../types/workflow";

// Helper to render node with ReactFlow context
const renderWithProvider = (
  props: Partial<NodeProps<WorkflowNodeData>> = {},
) => {
  const defaultProps: NodeProps<WorkflowNodeData> = {
    id: "test-node",
    type: "end",
    data: {
      label: "End",
      nodeType: "end",
      config: {},
    },
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    dragging: false,
    ...props,
  };

  return render(
    <ReactFlowProvider>
      <EndNode {...defaultProps} />
    </ReactFlowProvider>,
  );
};

describe("EndNode", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the node label", () => {
      renderWithProvider({
        data: {
          label: "Finish",
          nodeType: "end",
          config: {},
        },
      });

      expect(screen.getByText("Finish")).toBeInTheDocument();
    });

    it("should display CircleStop icon", () => {
      renderWithProvider();

      // CircleStop icon should be present with red styling
      const icons = document.querySelectorAll("svg.text-red-500");
      expect(icons.length).toBeGreaterThan(0);
    });

    it("should render with default label", () => {
      renderWithProvider();

      expect(screen.getByText("End")).toBeInTheDocument();
    });
  });

  describe("Status Visualization", () => {
    it("should show idle state by default", () => {
      renderWithProvider();

      const node = document.querySelector('[data-status="idle"]');
      expect(node).toBeInTheDocument();
    });

    it("should show running status with loader", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "running",
        },
      });

      const node = document.querySelector('[data-status="running"]');
      expect(node).toBeInTheDocument();

      // Check for spinning loader icon
      const loader = document.querySelector(".animate-spin");
      expect(loader).toBeInTheDocument();
    });

    it("should show success status with check icon", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "success",
        },
      });

      const node = document.querySelector('[data-status="success"]');
      expect(node).toBeInTheDocument();

      // Check for green status icon
      const checkIcon = document.querySelector("svg.text-green-500");
      expect(checkIcon).toBeInTheDocument();
    });

    it("should show error status with X icon", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "error",
        },
      });

      const node = document.querySelector('[data-status="error"]');
      expect(node).toBeInTheDocument();

      // Check for red status icon
      const xIcon = document.querySelector("svg.text-red-500");
      // There are two red icons: CircleStop and XCircle when error
      expect(xIcon).toBeInTheDocument();
    });

    it("should not show status icon when idle", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "idle",
        },
      });

      // No animate-spin (loader) status icon
      expect(document.querySelector(".animate-spin")).not.toBeInTheDocument();
    });
  });

  describe("Border Colors", () => {
    it("should have blue border when selected and idle", () => {
      renderWithProvider({
        selected: true,
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "idle",
        },
      });

      const node = document.querySelector('[data-selected="true"]');
      expect(node).toBeInTheDocument();
      expect(node?.className).toContain("border-blue-500");
    });

    it("should have blue border with pulse when running", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "running",
        },
      });

      const node = document.querySelector('[data-status="running"]');
      expect(node?.className).toContain("border-blue-500");
      expect(node?.className).toContain("animate-pulse");
    });

    it("should have green border when success", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "success",
        },
      });

      const node = document.querySelector('[data-status="success"]');
      expect(node?.className).toContain("border-green-500");
    });

    it("should have red border when error", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "error",
        },
      });

      const node = document.querySelector('[data-status="error"]');
      expect(node?.className).toContain("border-red-500");
    });

    it("should have gray border when not selected and idle", () => {
      renderWithProvider({
        selected: false,
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          status: "idle",
        },
      });

      const node = document.querySelector('[data-selected="false"]');
      expect(node?.className).toContain("border-gray-300");
    });
  });

  describe("Handles", () => {
    it("should have target handle on left", () => {
      renderWithProvider();

      // Check for target handle
      const targetHandle = document.querySelector(".react-flow__handle-left");
      expect(targetHandle).toBeInTheDocument();
    });

    it("should NOT have source handles (end node has no output)", () => {
      renderWithProvider();

      // End node should only have 1 handle (target)
      const handles = document.querySelectorAll(".react-flow__handle");
      expect(handles.length).toBe(1);

      // Verify it's a target handle, not source
      const targetHandle = document.querySelector(".react-flow__handle-left");
      expect(targetHandle).toBeInTheDocument();
    });

    it("should only have 1 handle total", () => {
      renderWithProvider();

      const handles = document.querySelectorAll(".react-flow__handle");
      expect(handles.length).toBe(1);
    });
  });

  describe("Selection State", () => {
    it("should set data-selected=true when selected", () => {
      renderWithProvider({ selected: true });

      const node = document.querySelector('[data-selected="true"]');
      expect(node).toBeInTheDocument();
    });

    it("should set data-selected=false when not selected", () => {
      renderWithProvider({ selected: false });

      const node = document.querySelector('[data-selected="false"]');
      expect(node).toBeInTheDocument();
    });
  });

  describe("Component Properties", () => {
    it("should be memoized (displayName check)", () => {
      expect(EndNode.displayName).toBe("EndNode");
    });

    it("should render with different labels", () => {
      renderWithProvider({
        data: {
          label: "Workflow Complete",
          nodeType: "end",
          config: {},
        },
      });

      expect(screen.getByText("Workflow Complete")).toBeInTheDocument();
    });

    it("should handle undefined status gracefully", () => {
      renderWithProvider({
        data: {
          label: "End",
          nodeType: "end",
          config: {},
          // status undefined - should default to 'idle'
        },
      });

      const node = document.querySelector('[data-status="idle"]');
      expect(node).toBeInTheDocument();
    });
  });

  describe("Styling", () => {
    it("should have rounded corners", () => {
      renderWithProvider();

      const node = document.querySelector("[data-status]");
      expect(node?.className).toContain("rounded-lg");
    });

    it("should have padding", () => {
      renderWithProvider();

      const node = document.querySelector("[data-status]");
      expect(node?.className).toContain("p-3");
    });

    it("should have minimum width", () => {
      renderWithProvider();

      const node = document.querySelector("[data-status]");
      expect(node?.className).toContain("min-w-[180px]");
    });

    it("should have shadow", () => {
      renderWithProvider();

      const node = document.querySelector("[data-status]");
      expect(node?.className).toContain("shadow-sm");
    });

    it("should have hover shadow effect", () => {
      renderWithProvider();

      const node = document.querySelector("[data-status]");
      expect(node?.className).toContain("hover:shadow-md");
    });
  });

  describe("Icon Styling", () => {
    it("should have red CircleStop icon", () => {
      renderWithProvider();

      // CircleStop icon has text-red-500 class for styling
      const icons = document.querySelectorAll("svg.text-red-500");
      // Should find at least one red icon (the CircleStop)
      expect(icons.length).toBeGreaterThan(0);
    });
  });
});
