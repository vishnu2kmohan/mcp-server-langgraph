/**
 * NodePalette Tests
 *
 * Tests for the node palette sidebar component with drag-and-drop functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { NodePalette } from "./NodePalette";

import { TestProvider } from "@/test-utils";

describe("NodePalette", () => {
  const defaultProps = {
    onAddNode: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the node palette", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Node Types")).toBeInTheDocument();
    });

    it("should render all node type buttons", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Start")).toBeInTheDocument();
      expect(screen.getByText("End")).toBeInTheDocument();
      expect(screen.getByText("LLM")).toBeInTheDocument();
      expect(screen.getByText("Tool")).toBeInTheDocument();
      expect(screen.getByText("Conditional")).toBeInTheDocument();
      expect(screen.getByText("Approval")).toBeInTheDocument();
      expect(screen.getByText("Custom")).toBeInTheDocument();
    });

    it("should render category headers", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Flow Control")).toBeInTheDocument();
      expect(screen.getByText("Processing")).toBeInTheDocument();
      expect(screen.getByText("Control")).toBeInTheDocument();
      expect(screen.getByText("Advanced")).toBeInTheDocument();
    });

    it("should render search input", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText("Search nodes..."),
      ).toBeInTheDocument();
    });

    it("should render footer hint", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/Drag nodes to canvas/)).toBeInTheDocument();
    });

    it("should have data-testid on palette", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("node-palette")).toBeInTheDocument();
    });
  });

  describe("Node Type Selection (Click to Add)", () => {
    it('should call onAddNode with "start" when Start is clicked', () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("node-start"));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith("start");
    });

    it('should call onAddNode with "llm" when LLM is clicked', () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("node-llm"));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith("llm");
    });

    it('should call onAddNode with "tool" when Tool is clicked', () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("node-tool"));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith("tool");
    });

    it('should call onAddNode with "conditional" when Conditional is clicked', () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("node-conditional"));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith("conditional");
    });

    it('should call onAddNode with "end" when End is clicked', () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("node-end"));
      expect(defaultProps.onAddNode).toHaveBeenCalledWith("end");
    });
  });

  describe("Search Functionality", () => {
    it("should filter nodes when searching", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText("Search nodes...");
      fireEvent.change(searchInput, { target: { value: "LLM" } });

      expect(screen.getByText("LLM")).toBeInTheDocument();
      expect(screen.queryByText("Start")).not.toBeInTheDocument();
      expect(screen.queryByText("Tool")).not.toBeInTheDocument();
    });

    it("should show message when no nodes match search", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText("Search nodes...");
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      expect(
        screen.getByText("No nodes match your search"),
      ).toBeInTheDocument();
    });

    it("should search by description", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText("Search nodes...");
      fireEvent.change(searchInput, { target: { value: "language model" } });

      expect(screen.getByText("LLM")).toBeInTheDocument();
    });
  });

  describe("Collapsed Mode", () => {
    it("should render collapsed view when isCollapsed is true", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} isCollapsed={true} />
        </TestProvider>,
      );

      // Should not show search or category headers
      expect(
        screen.queryByPlaceholderText("Search nodes..."),
      ).not.toBeInTheDocument();
      expect(screen.queryByText("Flow Control")).not.toBeInTheDocument();
    });

    it("should still have buttons in collapsed mode", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} isCollapsed={true} />
        </TestProvider>,
      );

      // Buttons should still be clickable
      expect(
        screen.getByRole("button", { name: /Add Start node/ }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Add LLM node/ }),
      ).toBeInTheDocument();
    });
  });

  describe("Drag and Drop", () => {
    it("should have draggable attribute on node elements", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      const startNode = screen.getByTestId("node-start");
      expect(startNode).toHaveAttribute("draggable", "true");
    });

    it("should set data transfer on drag start", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      const startNode = screen.getByTestId("node-start");
      const dataTransfer = {
        setData: vi.fn(),
        effectAllowed: "",
      };

      fireEvent.dragStart(startNode, { dataTransfer });

      expect(dataTransfer.setData).toHaveBeenCalledWith(
        "application/reactflow",
        "start",
      );
    });
  });

  describe("Accessibility", () => {
    it("should have proper aria-labels on nodes", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: "Add Start node" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Add LLM node" }),
      ).toBeInTheDocument();
    });

    it("should have aria-label on search input", () => {
      render(
        <TestProvider>
          <NodePalette {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("textbox", { name: "Search node types" }),
      ).toBeInTheDocument();
    });
  });
});
