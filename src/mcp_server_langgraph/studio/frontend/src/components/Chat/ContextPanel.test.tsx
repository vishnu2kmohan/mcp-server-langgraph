/**
 * ContextPanel Tests
 *
 * Tests for the right sidebar context panel showing tools, activity, and cost.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ContextPanel, ContextPanelProps } from "./ContextPanel";

const defaultProps: ContextPanelProps = {
  tools: [
    { name: "calculator", description: "Perform calculations" },
    { name: "web_search", description: "Search the web" },
    { name: "read_file", description: "Read files from disk" },
  ],
  activities: [
    {
      timestamp: Date.now() - 1000,
      action: "tool called",
      details: "calculator",
    },
    {
      timestamp: Date.now() - 60000,
      action: "message received",
      details: "assistant response",
    },
    { timestamp: Date.now() - 120000, action: "session started", details: "" },
  ],
  sessionCost: {
    tokens: 4521,
    cost: 0.0045,
    model: "gemini-2.5-flash",
  },
};

describe("ContextPanel", () => {
  describe("Tools Section", () => {
    it("should render tools section header", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText("TOOLS")).toBeInTheDocument();
    });

    it("should render all tools", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("web_search")).toBeInTheDocument();
      expect(screen.getByText("read_file")).toBeInTheDocument();
    });

    it("should show tool count", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText(/3 available/)).toBeInTheDocument();
    });

    it("should show empty state when no tools", () => {
      render(<ContextPanel {...defaultProps} tools={[]} />);
      expect(screen.getByText(/no tools available/i)).toBeInTheDocument();
    });

    it("should render refresh button", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /refresh tools/i }),
      ).toBeInTheDocument();
    });

    it("should call onRefreshTools when refresh clicked", () => {
      const onRefreshTools = vi.fn();
      render(
        <ContextPanel {...defaultProps} onRefreshTools={onRefreshTools} />,
      );
      fireEvent.click(screen.getByRole("button", { name: /refresh tools/i }));
      expect(onRefreshTools).toHaveBeenCalled();
    });
  });

  describe("Activity Section", () => {
    it("should render activity section header", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText("ACTIVITY")).toBeInTheDocument();
    });

    it("should render activities", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText(/tool called/i)).toBeInTheDocument();
      expect(screen.getByText(/message received/i)).toBeInTheDocument();
      expect(screen.getByText(/session started/i)).toBeInTheDocument();
    });

    it("should show empty state when no activities", () => {
      render(<ContextPanel {...defaultProps} activities={[]} />);
      expect(screen.getByText(/no activity yet/i)).toBeInTheDocument();
    });
  });

  describe("Session Cost Section", () => {
    it("should render cost section header", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText("SESSION COST")).toBeInTheDocument();
    });

    it("should show token count", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText(/4,521/)).toBeInTheDocument();
    });

    it("should show cost amount", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText(/\$0\.0045/)).toBeInTheDocument();
    });

    it("should show model name", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByText("gemini-2.5-flash")).toBeInTheDocument();
    });

    it("should handle missing cost data", () => {
      render(<ContextPanel {...defaultProps} sessionCost={undefined} />);
      expect(screen.getByText(/no cost data/i)).toBeInTheDocument();
    });
  });

  describe("Collapse/Expand", () => {
    it("should be collapsible", () => {
      render(<ContextPanel {...defaultProps} />);
      const collapseButton = screen.getByRole("button", { name: /collapse/i });
      expect(collapseButton).toBeInTheDocument();
    });

    it("should collapse when collapse button clicked", () => {
      render(<ContextPanel {...defaultProps} />);
      const collapseButton = screen.getByRole("button", { name: /collapse/i });
      fireEvent.click(collapseButton);
      expect(screen.queryByText("TOOLS")).not.toBeInTheDocument();
    });

    it("should expand when expand button clicked", () => {
      render(<ContextPanel {...defaultProps} />);
      const collapseButton = screen.getByRole("button", { name: /collapse/i });
      fireEvent.click(collapseButton);
      const expandButton = screen.getByRole("button", { name: /expand/i });
      fireEvent.click(expandButton);
      expect(screen.getByText("TOOLS")).toBeInTheDocument();
    });
  });

  describe("Layout", () => {
    it("should have proper test id", () => {
      render(<ContextPanel {...defaultProps} />);
      expect(screen.getByTestId("context-panel")).toBeInTheDocument();
    });
  });
});
