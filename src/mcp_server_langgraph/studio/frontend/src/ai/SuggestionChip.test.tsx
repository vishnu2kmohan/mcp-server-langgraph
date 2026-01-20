/**
 * SuggestionChip Tests
 *
 * TDD tests for the atomic SuggestionChip component.
 * SuggestionChip is a reusable component for displaying individual
 * AI suggestions as interactive chip elements.
 *
 * Features:
 * - Display suggestion text with optional icon
 * - Click handler for selection
 * - Keyboard accessibility (Enter/Space to select)
 * - Visual states (default, hover, active, disabled)
 * - Confidence indicator
 * - Multiple variants (default, outline, subtle)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { SuggestionChip } from "./SuggestionChip";

expect.extend(toHaveNoViolations);

// =============================================================================
// Test Data
// =============================================================================

const defaultProps = {
  text: "Tell me more about this",
  onClick: vi.fn(),
};

// =============================================================================
// Tests
// =============================================================================

describe("SuggestionChip", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the chip with text", () => {
      render(<SuggestionChip {...defaultProps} />);

      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
    });

    it("should render with data-testid", () => {
      render(<SuggestionChip {...defaultProps} />);

      expect(screen.getByTestId("suggestion-chip")).toBeInTheDocument();
    });

    it("should render as a button element", () => {
      render(<SuggestionChip {...defaultProps} />);

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("should render with custom id", () => {
      render(<SuggestionChip {...defaultProps} id="chip-1" />);

      expect(screen.getByTestId("suggestion-chip")).toHaveAttribute(
        "id",
        "chip-1",
      );
    });

    it("should accept custom className", () => {
      render(<SuggestionChip {...defaultProps} className="custom-class" />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("custom-class");
    });
  });

  describe("Icons", () => {
    it("should render with icon when provided", () => {
      render(<SuggestionChip {...defaultProps} icon="sparkles" />);

      expect(screen.getByTestId("chip-icon")).toBeInTheDocument();
    });

    it("should not render icon when not provided", () => {
      render(<SuggestionChip {...defaultProps} />);

      expect(screen.queryByTestId("chip-icon")).not.toBeInTheDocument();
    });

    it("should render different icon types", () => {
      const icons = ["sparkles", "lightbulb", "zap", "message-circle"] as const;

      icons.forEach((icon) => {
        const { unmount } = render(
          <SuggestionChip {...defaultProps} icon={icon} />,
        );
        expect(screen.getByTestId("chip-icon")).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe("Interactions", () => {
    it("should call onClick when clicked", async () => {
      const onClick = vi.fn();
      render(<SuggestionChip {...defaultProps} onClick={onClick} />);

      await userEvent.click(screen.getByRole("button"));

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should call onClick with chip data when clicked", async () => {
      const onClick = vi.fn();
      render(
        <SuggestionChip
          {...defaultProps}
          id="chip-1"
          text="Test suggestion"
          onClick={onClick}
        />,
      );

      await userEvent.click(screen.getByRole("button"));

      expect(onClick).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "chip-1",
          text: "Test suggestion",
        }),
      );
    });

    it("should call onClick on Enter key press", async () => {
      const onClick = vi.fn();
      render(<SuggestionChip {...defaultProps} onClick={onClick} />);

      const chip = screen.getByRole("button");
      chip.focus();
      await userEvent.keyboard("{Enter}");

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should call onClick on Space key press", async () => {
      const onClick = vi.fn();
      render(<SuggestionChip {...defaultProps} onClick={onClick} />);

      const chip = screen.getByRole("button");
      chip.focus();
      await userEvent.keyboard(" ");

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should not call onClick when disabled", async () => {
      const onClick = vi.fn();
      render(<SuggestionChip {...defaultProps} onClick={onClick} disabled />);

      await userEvent.click(screen.getByRole("button"));

      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe("Disabled State", () => {
    it("should have disabled attribute when disabled", () => {
      render(<SuggestionChip {...defaultProps} disabled />);

      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("should have disabled styles when disabled", () => {
      render(<SuggestionChip {...defaultProps} disabled />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("opacity-50");
    });

    it("should not be focusable when disabled", () => {
      render(<SuggestionChip {...defaultProps} disabled />);

      expect(screen.getByRole("button")).toHaveAttribute("tabIndex", "-1");
    });
  });

  describe("Confidence Indicator", () => {
    it("should show confidence badge when confidence is provided", () => {
      render(<SuggestionChip {...defaultProps} confidence={0.95} />);

      expect(screen.getByTestId("confidence-badge")).toBeInTheDocument();
      expect(screen.getByText("95%")).toBeInTheDocument();
    });

    it("should not show confidence badge when not provided", () => {
      render(<SuggestionChip {...defaultProps} />);

      expect(screen.queryByTestId("confidence-badge")).not.toBeInTheDocument();
    });

    it("should show high confidence styling for >= 90%", () => {
      render(<SuggestionChip {...defaultProps} confidence={0.92} />);

      expect(screen.getByTestId("confidence-badge")).toHaveClass("text-green");
    });

    it("should show medium confidence styling for 70-89%", () => {
      render(<SuggestionChip {...defaultProps} confidence={0.75} />);

      expect(screen.getByTestId("confidence-badge")).toHaveClass("text-yellow");
    });

    it("should show low confidence styling for < 70%", () => {
      render(<SuggestionChip {...defaultProps} confidence={0.55} />);

      expect(screen.getByTestId("confidence-badge")).toHaveClass("text-gray");
    });
  });

  describe("Variants", () => {
    it("should render default variant by default", () => {
      render(<SuggestionChip {...defaultProps} />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("bg-primary");
    });

    it("should render outline variant", () => {
      render(<SuggestionChip {...defaultProps} variant="outline" />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("border");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass(
        "bg-transparent",
      );
    });

    it("should render subtle variant", () => {
      render(<SuggestionChip {...defaultProps} variant="subtle" />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass(
        "bg-neutral-2",
      );
    });
  });

  describe("Sizes", () => {
    it("should render medium size by default", () => {
      render(<SuggestionChip {...defaultProps} />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("px-3");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("py-1.5");
    });

    it("should render small size", () => {
      render(<SuggestionChip {...defaultProps} size="sm" />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("px-2");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("py-1");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("text-xs");
    });

    it("should render large size", () => {
      render(<SuggestionChip {...defaultProps} size="lg" />);

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("px-4");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("py-2");
    });
  });

  describe("Truncation", () => {
    it("should truncate long text with ellipsis", () => {
      render(
        <SuggestionChip
          {...defaultProps}
          text="This is a very long suggestion text that should be truncated"
          maxLength={20}
        />,
      );

      expect(screen.getByText(/This is a very long/)).toBeInTheDocument();
      expect(screen.getByText(/\.\.\./)).toBeInTheDocument();
    });

    it("should not truncate short text", () => {
      render(
        <SuggestionChip {...defaultProps} text="Short text" maxLength={20} />,
      );

      expect(screen.getByText("Short text")).toBeInTheDocument();
      expect(screen.queryByText(/\.\.\./)).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<SuggestionChip {...defaultProps} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible name from text", () => {
      render(
        <SuggestionChip {...defaultProps} text="Accept this suggestion" />,
      );

      expect(screen.getByRole("button")).toHaveAccessibleName(
        "Accept this suggestion",
      );
    });

    it("should have accessible name with aria-label when provided", () => {
      render(
        <SuggestionChip
          {...defaultProps}
          text="Suggest"
          ariaLabel="Apply suggestion to accept this change"
        />,
      );

      expect(screen.getByRole("button")).toHaveAccessibleName(
        "Apply suggestion to accept this change",
      );
    });

    it("should be focusable", () => {
      render(<SuggestionChip {...defaultProps} />);

      const chip = screen.getByRole("button");
      chip.focus();

      expect(document.activeElement).toBe(chip);
    });

    it("should have visible focus indicator", () => {
      render(<SuggestionChip {...defaultProps} />);

      const chip = screen.getByTestId("suggestion-chip");
      expect(chip).toHaveClass("focus-visible:ring-2");
    });

    it("should have no accessibility violations when disabled", async () => {
      const { container } = render(
        <SuggestionChip {...defaultProps} disabled />,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations with confidence", async () => {
      const { container } = render(
        <SuggestionChip {...defaultProps} confidence={0.85} />,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when loading", () => {
      render(<SuggestionChip {...defaultProps} isLoading />);

      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should disable interaction when loading", () => {
      render(<SuggestionChip {...defaultProps} isLoading />);

      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("should hide icon when loading", () => {
      render(<SuggestionChip {...defaultProps} icon="sparkles" isLoading />);

      expect(screen.queryByTestId("chip-icon")).not.toBeInTheDocument();
    });
  });
});
