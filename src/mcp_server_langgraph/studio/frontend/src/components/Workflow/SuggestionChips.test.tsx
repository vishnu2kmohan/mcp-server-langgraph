/**
 * SuggestionChips Tests
 *
 * Tests for the AI suggestion chips component.
 * Features:
 * - Display AI suggestions as interactive chips
 * - Loading state
 * - Error handling
 * - Apply suggestion callback
 * - Dismiss suggestion callback
 * - Confidence indicators
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SuggestionChips } from "./SuggestionChips";
import type { AISuggestion } from "../../types/api";

// Mock suggestions
const mockSuggestions: AISuggestion[] = [
  {
    type: "add_node",
    description: "Add a retry mechanism to handle failures",
    confidence: 0.92,
    metadata: { node_type: "retry", position: { x: 100, y: 200 } },
  },
  {
    type: "optimize",
    description: "Consider parallel execution for independent steps",
    confidence: 0.85,
    metadata: { affected_nodes: ["node1", "node2"] },
  },
  {
    type: "warning",
    description: "Missing error handling in transform node",
    confidence: 0.78,
    metadata: { node_id: "transform-1" },
  },
];

const defaultProps = {
  suggestions: mockSuggestions,
  isLoading: false,
  error: null,
  onApply: vi.fn(),
  onDismiss: vi.fn(),
  onRefresh: vi.fn(),
};

describe("SuggestionChips", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render suggestion chips when suggestions exist", () => {
      render(<SuggestionChips {...defaultProps} />);

      expect(
        screen.getByText("Add a retry mechanism to handle failures"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Consider parallel execution for independent steps"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Missing error handling in transform node"),
      ).toBeInTheDocument();
    });

    it("should render empty state when no suggestions", () => {
      render(<SuggestionChips {...defaultProps} suggestions={[]} />);

      expect(screen.getByText(/no suggestions/i)).toBeInTheDocument();
    });

    it("should show loading state", () => {
      render(
        <SuggestionChips {...defaultProps} isLoading={true} suggestions={[]} />,
      );

      expect(screen.getByText(/analyzing workflow/i)).toBeInTheDocument();
    });

    it("should show error state", () => {
      render(
        <SuggestionChips
          {...defaultProps}
          error="Failed to fetch suggestions"
        />,
      );

      expect(
        screen.getByText(/failed to fetch suggestions/i),
      ).toBeInTheDocument();
    });

    it("should display AI label in header", () => {
      render(<SuggestionChips {...defaultProps} />);

      expect(screen.getByText(/ai suggestions/i)).toBeInTheDocument();
    });
  });

  describe("Confidence Indicators", () => {
    it("should show high confidence indicator for confidence >= 0.9", () => {
      render(<SuggestionChips {...defaultProps} />);

      // The first suggestion has 0.92 confidence
      const chips = screen.getAllByTestId("suggestion-chip");
      expect(chips[0]).toHaveAttribute("data-confidence", "high");
    });

    it("should show medium confidence indicator for confidence 0.7-0.9", () => {
      render(<SuggestionChips {...defaultProps} />);

      // The second suggestion has 0.85 confidence
      const chips = screen.getAllByTestId("suggestion-chip");
      expect(chips[1]).toHaveAttribute("data-confidence", "medium");
    });

    it("should show low confidence indicator for confidence < 0.7", () => {
      const lowConfidenceSuggestion: AISuggestion = {
        type: "hint",
        description: "Consider adding documentation",
        confidence: 0.55,
        metadata: {},
      };

      render(
        <SuggestionChips
          {...defaultProps}
          suggestions={[lowConfidenceSuggestion]}
        />,
      );

      const chips = screen.getAllByTestId("suggestion-chip");
      expect(chips[0]).toHaveAttribute("data-confidence", "low");
    });
  });

  describe("Suggestion Types", () => {
    it("should display icon for add_node type", () => {
      render(<SuggestionChips {...defaultProps} />);

      const chips = screen.getAllByTestId("suggestion-chip");
      expect(chips[0].querySelector('[data-icon="add"]')).toBeInTheDocument();
    });

    it("should display icon for optimize type", () => {
      render(<SuggestionChips {...defaultProps} />);

      const chips = screen.getAllByTestId("suggestion-chip");
      expect(
        chips[1].querySelector('[data-icon="optimize"]'),
      ).toBeInTheDocument();
    });

    it("should display icon for warning type", () => {
      render(<SuggestionChips {...defaultProps} />);

      const chips = screen.getAllByTestId("suggestion-chip");
      expect(
        chips[2].querySelector('[data-icon="warning"]'),
      ).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onApply when apply button is clicked", () => {
      const onApply = vi.fn();
      render(<SuggestionChips {...defaultProps} onApply={onApply} />);

      const applyButtons = screen.getAllByRole("button", { name: /apply/i });
      fireEvent.click(applyButtons[0]);

      expect(onApply).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      const onDismiss = vi.fn();
      render(<SuggestionChips {...defaultProps} onDismiss={onDismiss} />);

      const dismissButtons = screen.getAllByRole("button", {
        name: /dismiss/i,
      });
      fireEvent.click(dismissButtons[0]);

      expect(onDismiss).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("should call onRefresh when refresh button is clicked", () => {
      const onRefresh = vi.fn();
      render(<SuggestionChips {...defaultProps} onRefresh={onRefresh} />);

      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      fireEvent.click(refreshButton);

      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe("Collapsible Behavior", () => {
    it("should be expanded by default", () => {
      render(<SuggestionChips {...defaultProps} />);

      expect(screen.getByTestId("suggestions-container")).toHaveAttribute(
        "data-expanded",
        "true",
      );
    });

    it("should collapse when collapse button is clicked", () => {
      render(<SuggestionChips {...defaultProps} />);

      const collapseButton = screen.getByRole("button", { name: /collapse/i });
      fireEvent.click(collapseButton);

      expect(screen.getByTestId("suggestions-container")).toHaveAttribute(
        "data-expanded",
        "false",
      );
    });

    it("should show count badge when collapsed", () => {
      render(<SuggestionChips {...defaultProps} />);

      const collapseButton = screen.getByRole("button", { name: /collapse/i });
      fireEvent.click(collapseButton);

      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible labels for action buttons", () => {
      render(<SuggestionChips {...defaultProps} />);

      const applyButtons = screen.getAllByRole("button", { name: /apply/i });
      const dismissButtons = screen.getAllByRole("button", {
        name: /dismiss/i,
      });

      expect(applyButtons[0]).toHaveAccessibleName();
      expect(dismissButtons[0]).toHaveAccessibleName();
    });

    it('should have role="list" for suggestions container', () => {
      render(<SuggestionChips {...defaultProps} />);

      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it('should have role="listitem" for each suggestion', () => {
      render(<SuggestionChips {...defaultProps} />);

      const listitems = screen.getAllByRole("listitem");
      expect(listitems).toHaveLength(3);
    });
  });

  describe("Maximum Suggestions", () => {
    it("should limit displayed suggestions to maxVisible prop", () => {
      const manySuggestions: AISuggestion[] = Array.from(
        { length: 10 },
        (_, i) => ({
          type: "hint",
          description: `Suggestion ${i + 1}`,
          confidence: 0.8,
          metadata: {},
        }),
      );

      render(
        <SuggestionChips
          {...defaultProps}
          suggestions={manySuggestions}
          maxVisible={5}
        />,
      );

      const chips = screen.getAllByTestId("suggestion-chip");
      expect(chips).toHaveLength(5);
    });

    it('should show "show more" button when suggestions exceed maxVisible', () => {
      const manySuggestions: AISuggestion[] = Array.from(
        { length: 10 },
        (_, i) => ({
          type: "hint",
          description: `Suggestion ${i + 1}`,
          confidence: 0.8,
          metadata: {},
        }),
      );

      render(
        <SuggestionChips
          {...defaultProps}
          suggestions={manySuggestions}
          maxVisible={5}
        />,
      );

      expect(screen.getByText(/show 5 more/i)).toBeInTheDocument();
    });
  });
});
