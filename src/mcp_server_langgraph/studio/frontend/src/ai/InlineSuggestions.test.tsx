/**
 * InlineSuggestions Tests
 *
 * Phase 4: AI-Native Features
 * Tests for inline AI suggestions component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { InlineSuggestions, type Suggestion } from "./InlineSuggestions";

import { TestProvider } from "@/test-utils";

describe("InlineSuggestions", () => {
  const mockSuggestions: Suggestion[] = [
    {
      id: "sug-1",
      type: "completion",
      content: "Add error handling",
      confidence: 0.95,
    },
    {
      id: "sug-2",
      type: "refactor",
      content: "Extract to separate function",
      confidence: 0.85,
    },
    {
      id: "sug-3",
      type: "fix",
      content: "Fix potential null reference",
      confidence: 0.72,
    },
  ];

  const mockOnAccept = vi.fn();
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders the suggestions container", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={mockSuggestions}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("inline-suggestions")).toBeInTheDocument();
    });

    it("renders all suggestions", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={mockSuggestions}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Add error handling")).toBeInTheDocument();
      expect(
        screen.getByText("Extract to separate function"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Fix potential null reference"),
      ).toBeInTheDocument();
    });

    it("shows empty state when no suggestions", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[]}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/no suggestions/i)).toBeInTheDocument();
    });

    it("shows loading state when isLoading is true", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[]}
            isLoading={true}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/generating suggestions/i)).toBeInTheDocument();
    });
  });

  describe("Suggestion Types", () => {
    it("renders correct icon for completion type", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[mockSuggestions[0]]}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      // Check that completion suggestion is labeled correctly
      expect(screen.getByText("completion")).toBeInTheDocument();
    });

    it("renders correct icon for refactor type", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[mockSuggestions[1]]}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      expect(screen.getByText("refactor")).toBeInTheDocument();
    });

    it("renders correct icon for fix type", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[mockSuggestions[2]]}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      expect(screen.getByText("fix")).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("calls onAccept when accept button is clicked", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={mockSuggestions}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      // Find the first accept button
      const acceptButtons = screen.getAllByLabelText(/accept/i);
      fireEvent.click(acceptButtons[0]);

      expect(mockOnAccept).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("calls onDismiss when dismiss button is clicked", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={mockSuggestions}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      // Find the first dismiss button
      const dismissButtons = screen.getAllByLabelText(/dismiss/i);
      fireEvent.click(dismissButtons[0]);

      expect(mockOnDismiss).toHaveBeenCalledWith(mockSuggestions[0]);
    });
  });

  describe("Confidence Indicator", () => {
    it("displays confidence as percentage", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[mockSuggestions[0]]}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/95%/)).toBeInTheDocument();
    });

    it("applies high confidence styling for >= 0.9", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[mockSuggestions[0]]} // 0.95 confidence
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      const confidenceBadge = screen.getByText(/95%/).closest("span");
      expect(confidenceBadge).toHaveClass("text-success-10");
    });

    it("applies medium confidence styling for >= 0.7 and < 0.9", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={[mockSuggestions[2]]} // 0.72 confidence
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      const confidenceBadge = screen.getByText(/72%/).closest("span");
      expect(confidenceBadge).toHaveClass("text-warning-9");
    });
  });

  describe("Accessibility - Touch Targets (WCAG 2.5.8)", () => {
    it("accept button meets minimum 24x24px touch target", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={mockSuggestions}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      const acceptButtons = screen.getAllByLabelText(/accept/i);
      // All accept buttons should meet 24px minimum
      acceptButtons.forEach((button) => {
        expect(button.className).toMatch(/min-h-6|h-6/);
        expect(button.className).toMatch(/min-w-6|w-6/);
      });
    });

    it("dismiss button meets minimum 24x24px touch target", () => {
      render(
        <TestProvider>
          <InlineSuggestions
            suggestions={mockSuggestions}
            onAccept={mockOnAccept}
            onDismiss={mockOnDismiss}
          />
        </TestProvider>,
      );

      const dismissButtons = screen.getAllByLabelText(/dismiss/i);
      // All dismiss buttons should meet 24px minimum
      dismissButtons.forEach((button) => {
        expect(button.className).toMatch(/min-h-6|h-6/);
        expect(button.className).toMatch(/min-w-6|w-6/);
      });
    });
  });
});
