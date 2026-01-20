/**
 * TraceNode Component Tests
 *
 * TDD tests for the trace node React Flow component.
 * Tests cover:
 * - Rendering with different statuses
 * - Duration display
 * - Selected state
 * - Accessibility
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import TraceNode from "./TraceNode";
import { ReactFlowProvider } from "reactflow";

// Wrapper component for React Flow context
const renderWithReactFlow = (component: React.ReactNode) => {
  return render(<ReactFlowProvider>{component}</ReactFlowProvider>);
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("TraceNode", () => {
  const defaultProps = {
    id: "test-node",
    type: "traceNode",
    data: {
      label: "Test Span",
      status: "OK" as const,
      statusColor: "#22c55e",
      duration: "100ms",
      attributes: {},
      traceId: "trace-123",
    },
    selected: false,
    isConnectable: true,
    xPos: 0,
    yPos: 0,
    zIndex: 0,
    dragging: false,
  };

  describe("Rendering", () => {
    it("should render the span name", () => {
      renderWithReactFlow(<TraceNode {...defaultProps} />);

      expect(screen.getByText("Test Span")).toBeInTheDocument();
    });

    it("should render the duration when provided", () => {
      renderWithReactFlow(<TraceNode {...defaultProps} />);

      expect(screen.getByText("100ms")).toBeInTheDocument();
    });

    it("should not render duration when empty", () => {
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, duration: "" },
      };

      const { container } = renderWithReactFlow(<TraceNode {...props} />);

      // Duration element should not be present
      const durationElements = container.querySelectorAll(
        ".text-xs.opacity-75",
      );
      expect(durationElements.length).toBe(0);
    });
  });

  describe("Status Styling", () => {
    it("should apply OK status styling", () => {
      const props = {
        ...defaultProps,
        data: {
          ...defaultProps.data,
          status: "OK" as const,
          statusColor: "#22c55e",
        },
      };

      const { container } = renderWithReactFlow(<TraceNode {...props} />);

      const nodeDiv = container.querySelector(".bg-success-2");
      expect(nodeDiv).toBeInTheDocument();
    });

    it("should apply ERROR status styling", () => {
      const props = {
        ...defaultProps,
        data: {
          ...defaultProps.data,
          status: "ERROR" as const,
          statusColor: "#ef4444",
        },
      };

      const { container } = renderWithReactFlow(<TraceNode {...props} />);

      const nodeDiv = container.querySelector(".bg-error-2");
      expect(nodeDiv).toBeInTheDocument();
    });

    it("should apply UNSET status styling", () => {
      const props = {
        ...defaultProps,
        data: {
          ...defaultProps.data,
          status: "UNSET" as const,
          statusColor: "#6366f1",
        },
      };

      const { container } = renderWithReactFlow(<TraceNode {...props} />);

      const nodeDiv = container.querySelector(".bg-primary-3");
      expect(nodeDiv).toBeInTheDocument();
    });
  });

  describe("Running State", () => {
    it("should show running indicator for UNSET status", () => {
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, status: "UNSET" as const },
      };

      renderWithReactFlow(<TraceNode {...props} />);

      expect(screen.getByText("Running...")).toBeInTheDocument();
    });

    it("should have animated pulse for running spans", () => {
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, status: "UNSET" as const },
      };

      const { container } = renderWithReactFlow(<TraceNode {...props} />);

      const pulseElement = container.querySelector(".animate-ping");
      expect(pulseElement).toBeInTheDocument();
    });

    it("should not show running indicator for OK status", () => {
      renderWithReactFlow(<TraceNode {...defaultProps} />);

      expect(screen.queryByText("Running...")).not.toBeInTheDocument();
    });

    it("should not show running indicator for ERROR status", () => {
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, status: "ERROR" as const },
      };

      renderWithReactFlow(<TraceNode {...props} />);

      expect(screen.queryByText("Running...")).not.toBeInTheDocument();
    });
  });

  describe("Selected State", () => {
    it("should have ring styling when selected", () => {
      const props = { ...defaultProps, selected: true };

      const { container } = renderWithReactFlow(<TraceNode {...props} />);

      const selectedElement = container.querySelector(".ring-2");
      expect(selectedElement).toBeInTheDocument();
    });

    it("should not have ring styling when not selected", () => {
      const { container } = renderWithReactFlow(
        <TraceNode {...defaultProps} />,
      );

      const selectedElement = container.querySelector(".ring-2");
      expect(selectedElement).not.toBeInTheDocument();
    });
  });

  describe("Handles", () => {
    it("should render target handle on the left", () => {
      const { container } = renderWithReactFlow(
        <TraceNode {...defaultProps} />,
      );

      // React Flow handles have specific classes
      const targetHandle = container.querySelector('[data-handlepos="left"]');
      expect(targetHandle).toBeInTheDocument();
    });

    it("should render source handle on the right", () => {
      const { container } = renderWithReactFlow(
        <TraceNode {...defaultProps} />,
      );

      const sourceHandle = container.querySelector('[data-handlepos="right"]');
      expect(sourceHandle).toBeInTheDocument();
    });
  });

  describe("Label Truncation", () => {
    it("should truncate long labels", () => {
      const longLabel =
        "This is a very long span name that should be truncated in the display";
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, label: longLabel },
      };

      const { container } = renderWithReactFlow(<TraceNode {...props} />);

      const labelElement = container.querySelector(".truncate");
      expect(labelElement).toBeInTheDocument();
    });

    it("should show full label on hover via title attribute", () => {
      const longLabel = "This is a very long span name";
      const props = {
        ...defaultProps,
        data: { ...defaultProps.data, label: longLabel },
      };

      renderWithReactFlow(<TraceNode {...props} />);

      const labelElement = screen.getByText(longLabel);
      expect(labelElement).toHaveAttribute("title", longLabel);
    });
  });

  describe("Accessibility", () => {
    it("should have minimum width for readability", () => {
      const { container } = renderWithReactFlow(
        <TraceNode {...defaultProps} />,
      );

      const nodeDiv = container.querySelector(".min-w-\\[180px\\]");
      expect(nodeDiv).toBeInTheDocument();
    });

    it("should have proper color contrast for text", () => {
      // OK status uses green text on green background
      const { container } = renderWithReactFlow(
        <TraceNode {...defaultProps} />,
      );

      const nodeDiv = container.querySelector(".text-success-11");
      expect(nodeDiv).toBeInTheDocument();
    });
  });

  describe("Transitions", () => {
    it("should have hover shadow transition", () => {
      const { container } = renderWithReactFlow(
        <TraceNode {...defaultProps} />,
      );

      const nodeDiv = container.querySelector(".hover\\:shadow-lg");
      expect(nodeDiv).toBeInTheDocument();
    });

    it("should have transition duration", () => {
      const { container } = renderWithReactFlow(
        <TraceNode {...defaultProps} />,
      );

      const nodeDiv = container.querySelector(".transition-all");
      expect(nodeDiv).toBeInTheDocument();
    });
  });
});
