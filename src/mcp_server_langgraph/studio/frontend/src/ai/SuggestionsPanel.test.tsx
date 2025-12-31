/**
 * SuggestionsPanel Component Tests (TDD)
 *
 * Tests for the table-based suggestions panel component.
 * This component displays AI suggestions in a collapsible table format
 * instead of an overlay, giving users more control over when to view suggestions.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { SuggestionsPanel } from "./SuggestionsPanel";
import type { Suggestion } from "./InlineSuggestions";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("SuggestionsPanel", () => {
  const mockSuggestions: Suggestion[] = [
    {
      id: "1",
      type: "completion",
      content: "Add null check",
      confidence: 0.95,
    },
    { id: "2", type: "fix", content: "Fix type error", confidence: 0.85 },
    { id: "3", type: "refactor", content: "Extract function", confidence: 0.7 },
  ];

  const defaultProps = {
    suggestions: mockSuggestions,
    onAccept: vi.fn(),
    onDismiss: vi.fn(),
    onRefresh: vi.fn(),
    isLoading: false,
    isExpanded: true,
    onToggleExpand: vi.fn(),
  };

  describe("rendering", () => {
    it("renders the panel with suggestions table", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      expect(screen.getByTestId("suggestions-panel")).toBeInTheDocument();
      expect(screen.getByText("AI Suggestions")).toBeInTheDocument();
    });

    it("shows suggestion count in header", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("renders each suggestion row with type, content, and confidence", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      expect(screen.getByText("Add null check")).toBeInTheDocument();
      expect(screen.getByText("Fix type error")).toBeInTheDocument();
      expect(screen.getByText("Extract function")).toBeInTheDocument();

      // Check confidence percentages
      expect(screen.getByText("95%")).toBeInTheDocument();
      expect(screen.getByText("85%")).toBeInTheDocument();
      expect(screen.getByText("70%")).toBeInTheDocument();
    });

    it("renders type badges for each suggestion", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      expect(screen.getByText("completion")).toBeInTheDocument();
      expect(screen.getByText("fix")).toBeInTheDocument();
      expect(screen.getByText("refactor")).toBeInTheDocument();
    });
  });

  describe("actions", () => {
    it("calls onAccept when accept button is clicked", () => {
      const onAccept = vi.fn();
      render(<SuggestionsPanel {...defaultProps} onAccept={onAccept} />);

      const acceptButtons = screen.getAllByLabelText("Accept suggestion");
      fireEvent.click(acceptButtons[0]);

      expect(onAccept).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("calls onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      render(<SuggestionsPanel {...defaultProps} onDismiss={onDismiss} />);

      const dismissButtons = screen.getAllByLabelText("Dismiss suggestion");
      fireEvent.click(dismissButtons[1]);

      expect(onDismiss).toHaveBeenCalledWith(mockSuggestions[1]);
    });

    it("calls onRefresh when refresh button is clicked", () => {
      const onRefresh = vi.fn();
      render(<SuggestionsPanel {...defaultProps} onRefresh={onRefresh} />);

      const refreshButton = screen.getByLabelText("Refresh suggestions");
      fireEvent.click(refreshButton);

      expect(onRefresh).toHaveBeenCalled();
    });

    it("calls onToggleExpand when header is clicked", () => {
      const onToggleExpand = vi.fn();
      render(
        <SuggestionsPanel {...defaultProps} onToggleExpand={onToggleExpand} />,
      );

      const header = screen.getByRole("button", { name: /AI Suggestions/i });
      fireEvent.click(header);

      expect(onToggleExpand).toHaveBeenCalled();
    });
  });

  describe("collapsed state", () => {
    it("hides table when collapsed", () => {
      render(<SuggestionsPanel {...defaultProps} isExpanded={false} />);

      // Header should still be visible
      expect(screen.getByText("AI Suggestions")).toBeInTheDocument();

      // Table content should be hidden
      expect(screen.queryByText("Add null check")).not.toBeInTheDocument();
    });

    it("shows expand indicator when collapsed", () => {
      render(<SuggestionsPanel {...defaultProps} isExpanded={false} />);

      // Should show count even when collapsed
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("shows loading spinner when isLoading is true", () => {
      render(<SuggestionsPanel {...defaultProps} isLoading={true} />);

      expect(screen.getByTestId("suggestions-loading")).toBeInTheDocument();
    });

    it("disables refresh button when loading", () => {
      render(<SuggestionsPanel {...defaultProps} isLoading={true} />);

      const refreshButton = screen.getByLabelText("Refresh suggestions");
      expect(refreshButton).toBeDisabled();
    });
  });

  describe("empty state", () => {
    it("shows empty message when no suggestions", () => {
      render(<SuggestionsPanel {...defaultProps} suggestions={[]} />);

      expect(
        screen.getByText("No suggestions available. Click refresh to fetch."),
      ).toBeInTheDocument();
    });

    it("shows count of 0 when no suggestions", () => {
      render(<SuggestionsPanel {...defaultProps} suggestions={[]} />);

      expect(screen.getByText("0")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has accessible table structure", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      expect(screen.getByRole("table")).toBeInTheDocument();
      expect(screen.getAllByRole("row")).toHaveLength(4); // 1 header + 3 data rows
    });

    it("accept and dismiss buttons have accessible labels", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      expect(screen.getAllByLabelText("Accept suggestion")).toHaveLength(3);
      expect(screen.getAllByLabelText("Dismiss suggestion")).toHaveLength(3);
    });
  });

  describe("confidence colors", () => {
    it("uses green color for high confidence (>=90%)", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      // 95% confidence should have green styling
      const highConfidence = screen.getByText("95%");
      expect(highConfidence.className).toContain("green");
    });

    it("uses yellow color for medium confidence (70-89%)", () => {
      render(<SuggestionsPanel {...defaultProps} />);

      // 85% and 70% should have yellow styling
      const medConfidence = screen.getByText("85%");
      expect(medConfidence.className).toContain("yellow");
    });
  });
});
