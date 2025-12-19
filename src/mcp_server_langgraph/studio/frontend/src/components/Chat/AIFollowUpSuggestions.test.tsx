/**
 * AIFollowUpSuggestions Component Tests
 *
 * Tests for the AI-generated follow-up suggestions that appear
 * after AI responses to help users explore related topics.
 *
 * TDD RED Phase: Write failing tests first.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  AIFollowUpSuggestions,
  type AIFollowUpSuggestionsProps,
  type FollowUpSuggestion,
} from "./AIFollowUpSuggestions";

describe("AIFollowUpSuggestions", () => {
  const mockOnSelect = vi.fn();

  const defaultSuggestions: FollowUpSuggestion[] = [
    { id: "1", text: "Can you explain this in more detail?" },
    { id: "2", text: "What are the alternatives?" },
    { id: "3", text: "Show me an example" },
  ];

  const defaultProps: AIFollowUpSuggestionsProps = {
    suggestions: defaultSuggestions,
    onSelect: mockOnSelect,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render the suggestions container", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      expect(
        screen.getByTestId("follow-up-suggestions"),
      ).toBeInTheDocument();
    });

    it("should render all suggestions", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      expect(
        screen.getByText("Can you explain this in more detail?"),
      ).toBeInTheDocument();
      expect(screen.getByText("What are the alternatives?")).toBeInTheDocument();
      expect(screen.getByText("Show me an example")).toBeInTheDocument();
    });

    it("should not render when suggestions array is empty", () => {
      render(<AIFollowUpSuggestions suggestions={[]} onSelect={mockOnSelect} />);

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should render header text", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      expect(screen.getByText(/follow-up|related|explore/i)).toBeInTheDocument();
    });
  });

  describe("selection", () => {
    it("should call onSelect when a suggestion is clicked", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      fireEvent.click(screen.getByText("What are the alternatives?"));

      expect(mockOnSelect).toHaveBeenCalledWith(defaultSuggestions[1]);
    });

    it("should call onSelect with correct suggestion object", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      fireEvent.click(screen.getByText("Show me an example"));

      expect(mockOnSelect).toHaveBeenCalledWith({
        id: "3",
        text: "Show me an example",
      });
    });
  });

  describe("loading state", () => {
    it("should show loading state when isLoading is true", () => {
      render(
        <AIFollowUpSuggestions
          suggestions={[]}
          onSelect={mockOnSelect}
          isLoading
        />,
      );

      expect(screen.getByTestId("suggestions-loading")).toBeInTheDocument();
    });

    it("should show skeleton loaders during loading", () => {
      render(
        <AIFollowUpSuggestions
          suggestions={[]}
          onSelect={mockOnSelect}
          isLoading
        />,
      );

      expect(screen.getAllByTestId("skeleton-suggestion").length).toBeGreaterThan(
        0,
      );
    });

    it("should not show loading state when isLoading is false", () => {
      render(<AIFollowUpSuggestions {...defaultProps} isLoading={false} />);

      expect(
        screen.queryByTestId("suggestions-loading"),
      ).not.toBeInTheDocument();
    });
  });

  describe("disabled state", () => {
    it("should disable all suggestions when disabled is true", () => {
      render(<AIFollowUpSuggestions {...defaultProps} disabled />);

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it("should not call onSelect when disabled", () => {
      render(<AIFollowUpSuggestions {...defaultProps} disabled />);

      const button = screen.getByText("What are the alternatives?");
      fireEvent.click(button);

      expect(mockOnSelect).not.toHaveBeenCalled();
    });
  });

  describe("max suggestions", () => {
    it("should limit suggestions to maxSuggestions count", () => {
      const manySuggestions: FollowUpSuggestion[] = [
        { id: "1", text: "Question 1" },
        { id: "2", text: "Question 2" },
        { id: "3", text: "Question 3" },
        { id: "4", text: "Question 4" },
        { id: "5", text: "Question 5" },
      ];

      render(
        <AIFollowUpSuggestions
          suggestions={manySuggestions}
          onSelect={mockOnSelect}
          maxSuggestions={3}
        />,
      );

      expect(screen.getByText("Question 1")).toBeInTheDocument();
      expect(screen.getByText("Question 2")).toBeInTheDocument();
      expect(screen.getByText("Question 3")).toBeInTheDocument();
      expect(screen.queryByText("Question 4")).not.toBeInTheDocument();
      expect(screen.queryByText("Question 5")).not.toBeInTheDocument();
    });
  });

  describe("icons", () => {
    it("should show icon for each suggestion", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      const icons = screen.getAllByTestId("suggestion-icon");
      expect(icons).toHaveLength(defaultSuggestions.length);
    });
  });

  describe("accessibility", () => {
    it("should have role button for each suggestion", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(defaultSuggestions.length);
    });

    it("should be keyboard accessible", () => {
      render(<AIFollowUpSuggestions {...defaultProps} />);

      const firstButton = screen.getAllByRole("button")[0];
      firstButton.focus();
      fireEvent.keyDown(firstButton, { key: "Enter" });

      expect(mockOnSelect).toHaveBeenCalledWith(defaultSuggestions[0]);
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <AIFollowUpSuggestions {...defaultProps} className="custom-class" />,
      );

      expect(screen.getByTestId("follow-up-suggestions")).toHaveClass(
        "custom-class",
      );
    });
  });

  describe("compact mode", () => {
    it("should render in compact mode with smaller text", () => {
      render(<AIFollowUpSuggestions {...defaultProps} compact />);

      const container = screen.getByTestId("follow-up-suggestions");
      expect(container).toHaveClass("text-xs");
    });
  });

  describe("suggestion categories", () => {
    it("should render category label when suggestion has category", () => {
      const categorizedSuggestions: FollowUpSuggestion[] = [
        { id: "1", text: "What is X?", category: "clarify" },
        { id: "2", text: "How does Y work?", category: "explain" },
      ];

      render(
        <AIFollowUpSuggestions
          suggestions={categorizedSuggestions}
          onSelect={mockOnSelect}
          showCategories
        />,
      );

      expect(screen.getByText(/clarify/i)).toBeInTheDocument();
      expect(screen.getByText(/explain/i)).toBeInTheDocument();
    });
  });
});
