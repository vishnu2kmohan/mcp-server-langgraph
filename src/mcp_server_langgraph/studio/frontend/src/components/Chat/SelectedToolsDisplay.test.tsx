/**
 * Tests for SelectedToolsDisplay Component
 *
 * TDD tests for displaying semantically selected tools:
 * 1. Renders tool badges when tools are selected
 * 2. Shows selection scores as visual indicators
 * 3. Displays total available tools context
 * 4. Returns null when no tools selected
 * 5. Handles collapsible behavior
 */

import { render, screen, cleanup } from "@testing-library/react";
import { describe, expect, it, afterEach, vi } from "vitest";
import { SelectedToolsDisplay } from "./SelectedToolsDisplay";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("SelectedToolsDisplay", () => {
  describe("rendering", () => {
    it("renders tool names as badges", () => {
      render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator", "search", "translate"]}
            selectionScores={{}}
          />
        </TestProvider>,
      );

      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("search")).toBeInTheDocument();
      expect(screen.getByText("translate")).toBeInTheDocument();
    });

    it("returns null when no tools selected", () => {
      const { container } = render(
        <TestProvider>
          <SelectedToolsDisplay selectedTools={[]} selectionScores={{}} />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });

    it("shows header with tools icon", () => {
      render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator"]}
            selectionScores={{}}
          />
        </TestProvider>,
      );

      // Should show "Selected Tools" label or similar
      expect(screen.getByText(/selected tools/i)).toBeInTheDocument();
    });

    it("displays total available tools when provided", () => {
      render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator", "search"]}
            selectionScores={{}}
            totalAvailableTools={50}
          />
        </TestProvider>,
      );

      // Should show "2 of 50 tools" or similar
      expect(screen.getByText(/2/)).toBeInTheDocument();
      expect(screen.getByText(/50/)).toBeInTheDocument();
    });
  });

  describe("selection scores", () => {
    it("displays selection score when available", () => {
      render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator"]}
            selectionScores={{ calculator: 0.95 }}
          />
        </TestProvider>,
      );

      // Should show score (95% or 0.95)
      expect(screen.getByText(/95/)).toBeInTheDocument();
    });

    it("handles tools without scores gracefully", () => {
      render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator", "search"]}
            selectionScores={{ calculator: 0.9 }}
          />
        </TestProvider>,
      );

      // Should still render both tools
      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("search")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has accessible role for the tools list", () => {
      render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator"]}
            selectionScores={{}}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it("each tool badge has listitem role", () => {
      render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator", "search"]}
            selectionScores={{}}
          />
        </TestProvider>,
      );

      expect(screen.getAllByRole("listitem")).toHaveLength(2);
    });
  });

  describe("styling", () => {
    it("applies additional className when provided", () => {
      const { container } = render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator"]}
            selectionScores={{}}
            className="custom-class"
          />
        </TestProvider>,
      );

      expect(container.firstChild).toHaveClass("custom-class");
    });

    it("applies compact mode styling", () => {
      const { container } = render(
        <TestProvider>
          <SelectedToolsDisplay
            selectedTools={["calculator"]}
            selectionScores={{}}
            compact={true}
          />
        </TestProvider>,
      );

      // Check for compact-specific styles
      expect(container.firstChild).toHaveClass("text-xs");
    });
  });
});
