/**
 * ContextualHelp Tests
 *
 * Phase 6: Help & Accessibility
 * Tests for context-aware help tips component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ContextualHelp, type HelpTip } from "./ContextualHelp";

describe("ContextualHelp", () => {
  const mockTips: HelpTip[] = [
    {
      id: "tip-1",
      title: "Quick Tip",
      content: "Use Cmd+K to open the command palette.",
      learnMoreUrl: "/docs/command-palette",
    },
    {
      id: "tip-2",
      title: "Pro Tip",
      content: "Tab to accept inline AI suggestions.",
    },
  ];

  const mockOnDismiss = vi.fn();
  const mockOnLearnMore = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders the contextual help container", () => {
      render(
        <ContextualHelp
          tips={mockTips}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );
      expect(screen.getByTestId("contextual-help")).toBeInTheDocument();
    });

    it("renders tip title", () => {
      render(
        <ContextualHelp
          tips={[mockTips[0]]}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );
      expect(screen.getByText("Quick Tip")).toBeInTheDocument();
    });

    it("renders tip content", () => {
      render(
        <ContextualHelp
          tips={[mockTips[0]]}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );
      expect(
        screen.getByText(/use cmd\+k to open the command palette/i),
      ).toBeInTheDocument();
    });

    it("shows empty state when no tips", () => {
      render(
        <ContextualHelp
          tips={[]}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );
      expect(screen.getByText(/no tips available/i)).toBeInTheDocument();
    });
  });

  describe("Learn More", () => {
    it("shows learn more button when url is provided", () => {
      render(
        <ContextualHelp
          tips={[mockTips[0]]}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );
      expect(screen.getByText(/learn more/i)).toBeInTheDocument();
    });

    it("hides learn more button when no url is provided", () => {
      render(
        <ContextualHelp
          tips={[mockTips[1]]}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );
      expect(screen.queryByText(/learn more/i)).not.toBeInTheDocument();
    });

    it("calls onLearnMore when learn more button is clicked", () => {
      render(
        <ContextualHelp
          tips={[mockTips[0]]}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );

      fireEvent.click(screen.getByText(/learn more/i));

      expect(mockOnLearnMore).toHaveBeenCalledWith(mockTips[0]);
    });
  });

  describe("Dismiss", () => {
    it("calls onDismiss when dismiss button is clicked", () => {
      render(
        <ContextualHelp
          tips={[mockTips[0]]}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );

      const dismissButton = screen.getByLabelText(/dismiss/i);
      fireEvent.click(dismissButton);

      expect(mockOnDismiss).toHaveBeenCalledWith(mockTips[0]);
    });
  });

  describe("Multiple Tips", () => {
    it("renders multiple tips", () => {
      render(
        <ContextualHelp
          tips={mockTips}
          onDismiss={mockOnDismiss}
          onLearnMore={mockOnLearnMore}
        />,
      );
      expect(screen.getByText("Quick Tip")).toBeInTheDocument();
      expect(screen.getByText("Pro Tip")).toBeInTheDocument();
    });
  });
});
