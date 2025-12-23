/**
 * ApprovalNode Tests
 *
 * TDD tests for the human-in-the-loop approval node.
 * Tests cover:
 * - Rendering with label
 * - Status visualization (idle, running, success, error)
 * - Selection states
 * - Handle connections
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ReactFlowProvider } from "reactflow";
import { ApprovalNode } from "./ApprovalNode";
import type { NodeProps } from "reactflow";
import type { WorkflowNodeData } from "../../../types/workflow";

// Helper to render node with ReactFlow context
const renderWithProvider = (
  props: Partial<NodeProps<WorkflowNodeData>> = {},
) => {
  const defaultProps: NodeProps<WorkflowNodeData> = {
    id: "test-node",
    type: "approval",
    data: {
      label: "Approval",
      nodeType: "approval",
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
      <ApprovalNode {...defaultProps} />
    </ReactFlowProvider>,
  );
};

describe("ApprovalNode", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the node label", () => {
      renderWithProvider({
        data: {
          label: "Human Review",
          nodeType: "approval",
          config: {},
        },
      });

      expect(screen.getByText("Human Review")).toBeInTheDocument();
    });

    it("should display UserCheck icon", () => {
      renderWithProvider();

      // UserCheck icon should be present (lucide-react renders SVG)
      const icon = document.querySelector(".lucide-user-check");
      expect(icon).toBeInTheDocument();
    });

    it("should show Approved label", () => {
      renderWithProvider();

      expect(screen.getByText("Approved")).toBeInTheDocument();
    });

    it("should show Rejected label", () => {
      renderWithProvider();

      expect(screen.getByText("Rejected")).toBeInTheDocument();
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
          label: "Approval",
          nodeType: "approval",
          config: {},
          status: "running",
        },
      });

      const node = document.querySelector('[data-status="running"]');
      expect(node).toBeInTheDocument();

      // Check for spinning loader icon (Lucide uses animate-spin class)
      const loader = document.querySelector(".animate-spin");
      expect(loader).toBeInTheDocument();
    });

    it("should show success status with check icon", () => {
      renderWithProvider({
        data: {
          label: "Approval",
          nodeType: "approval",
          config: {},
          status: "success",
        },
      });

      const node = document.querySelector('[data-status="success"]');
      expect(node).toBeInTheDocument();

      // Check for green status icon (CheckCircle has text-green-500 class)
      const checkIcon = document.querySelector(".text-green-500");
      expect(checkIcon).toBeInTheDocument();
    });

    it("should show error status with X icon", () => {
      renderWithProvider({
        data: {
          label: "Approval",
          nodeType: "approval",
          config: {},
          status: "error",
        },
      });

      const node = document.querySelector('[data-status="error"]');
      expect(node).toBeInTheDocument();

      // Check for red status icon (XCircle has text-red-500 class)
      const xIcon = document.querySelector(".text-red-500");
      expect(xIcon).toBeInTheDocument();
    });

    it("should not show status icon when idle", () => {
      renderWithProvider({
        data: {
          label: "Approval",
          nodeType: "approval",
          config: {},
          status: "idle",
        },
      });

      // No animate-spin (loader), no text-green-500 (success), no text-red-500 (error) status icons
      // Note: text-blue-500 exists for the UserCheck icon, so we check specifically for status icons
      expect(document.querySelector(".animate-spin")).not.toBeInTheDocument();
    });
  });

  describe("Border Colors", () => {
    it("should have blue border when selected and idle", () => {
      renderWithProvider({
        selected: true,
        data: {
          label: "Approval",
          nodeType: "approval",
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
          label: "Approval",
          nodeType: "approval",
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
          label: "Approval",
          nodeType: "approval",
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
          label: "Approval",
          nodeType: "approval",
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
          label: "Approval",
          nodeType: "approval",
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

      // ReactFlow adds handles as divs with specific classes
      const handles = document.querySelectorAll(".react-flow__handle");
      expect(handles.length).toBeGreaterThanOrEqual(1);

      // Check for target handle
      const targetHandle = document.querySelector(".react-flow__handle-left");
      expect(targetHandle).toBeInTheDocument();
    });

    it("should have approved source handle", () => {
      renderWithProvider();

      const approvedHandle = document.querySelector(
        '[data-handleid="approved"]',
      );
      expect(approvedHandle).toBeInTheDocument();
    });

    it("should have rejected source handle", () => {
      renderWithProvider();

      const rejectedHandle = document.querySelector(
        '[data-handleid="rejected"]',
      );
      expect(rejectedHandle).toBeInTheDocument();
    });

    it("should have 3 handles total (1 target, 2 source)", () => {
      renderWithProvider();

      const handles = document.querySelectorAll(".react-flow__handle");
      expect(handles.length).toBe(3);
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
      expect(ApprovalNode.displayName).toBe("ApprovalNode");
    });

    it("should render with different labels", () => {
      renderWithProvider({
        data: {
          label: "Manager Approval Required",
          nodeType: "approval",
          config: {},
        },
      });

      expect(screen.getByText("Manager Approval Required")).toBeInTheDocument();
    });

    it("should handle undefined status gracefully", () => {
      renderWithProvider({
        data: {
          label: "Approval",
          nodeType: "approval",
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
});
