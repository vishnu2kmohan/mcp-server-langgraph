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

import { TestProvider } from "@/test-utils";

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
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
    });

    it("should render with data-testid", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toBeInTheDocument();
    });

    it("should render as a button element", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("should render with custom id", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} id="chip-1" />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveAttribute(
        "id",
        "chip-1",
      );
    });

    it("should accept custom className", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} className="custom-class" />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("custom-class");
    });
  });

  describe("Icons", () => {
    it("should render with icon when provided", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} icon="sparkles" />
        </TestProvider>,
      );

      expect(screen.getByTestId("chip-icon")).toBeInTheDocument();
    });

    it("should not render icon when not provided", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("chip-icon")).not.toBeInTheDocument();
    });

    it("should render different icon types", () => {
      const icons = ["sparkles", "lightbulb", "zap", "message-circle"] as const;

      icons.forEach((icon) => {
        const { unmount } = render(
          <TestProvider>
            <SuggestionChip {...defaultProps} icon={icon} />
          </TestProvider>,
        );
        expect(screen.getByTestId("chip-icon")).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe("Interactions", () => {
    it("should call onClick when clicked", async () => {
      const onClick = vi.fn();
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} onClick={onClick} />
        </TestProvider>,
      );

      await userEvent.click(screen.getByRole("button"));

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should call onClick with chip data when clicked", async () => {
      const onClick = vi.fn();
      render(
        <TestProvider>
          <SuggestionChip
            {...defaultProps}
            id="chip-1"
            text="Test suggestion"
            onClick={onClick}
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} onClick={onClick} />
        </TestProvider>,
      );

      const chip = screen.getByRole("button");
      chip.focus();
      await userEvent.keyboard("{Enter}");

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should call onClick on Space key press", async () => {
      const onClick = vi.fn();
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} onClick={onClick} />
        </TestProvider>,
      );

      const chip = screen.getByRole("button");
      chip.focus();
      await userEvent.keyboard(" ");

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should not call onClick when disabled", async () => {
      const onClick = vi.fn();
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} onClick={onClick} disabled />
        </TestProvider>,
      );

      await userEvent.click(screen.getByRole("button"));

      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe("Disabled State", () => {
    it("should have disabled attribute when disabled", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} disabled />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("should have disabled styles when disabled", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} disabled />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("opacity-50");
    });

    it("should not be focusable when disabled", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} disabled />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toHaveAttribute("tabIndex", "-1");
    });
  });

  describe("Confidence Indicator", () => {
    it("should show confidence badge when confidence is provided", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} confidence={0.95} />
        </TestProvider>,
      );

      expect(screen.getByTestId("confidence-badge")).toBeInTheDocument();
      expect(screen.getByText("95%")).toBeInTheDocument();
    });

    it("should not show confidence badge when not provided", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("confidence-badge")).not.toBeInTheDocument();
    });

    it("should show high confidence styling for >= 90%", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} confidence={0.92} />
        </TestProvider>,
      );

      expect(screen.getByTestId("confidence-badge")).toHaveClass("text-green");
    });

    it("should show medium confidence styling for 70-89%", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} confidence={0.75} />
        </TestProvider>,
      );

      expect(screen.getByTestId("confidence-badge")).toHaveClass("text-yellow");
    });

    it("should show low confidence styling for < 70%", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} confidence={0.55} />
        </TestProvider>,
      );

      expect(screen.getByTestId("confidence-badge")).toHaveClass("text-gray");
    });
  });

  describe("Variants", () => {
    it("should render default variant by default", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("bg-primary");
    });

    it("should render outline variant", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} variant="outline" />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("border");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass(
        "bg-transparent",
      );
    });

    it("should render subtle variant", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} variant="subtle" />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("bg-neutral-2");
    });
  });

  describe("Sizes", () => {
    it("should render medium size by default", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("px-3");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("py-1.5");
    });

    it("should render small size", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} size="sm" />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("px-2");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("py-1");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("text-xs");
    });

    it("should render large size", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} size="lg" />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-chip")).toHaveClass("px-4");
      expect(screen.getByTestId("suggestion-chip")).toHaveClass("py-2");
    });
  });

  describe("Truncation", () => {
    it("should truncate long text with ellipsis", () => {
      render(
        <TestProvider>
          <SuggestionChip
            {...defaultProps}
            text="This is a very long suggestion text that should be truncated"
            maxLength={20}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/This is a very long/)).toBeInTheDocument();
      expect(screen.getByText(/\.\.\./)).toBeInTheDocument();
    });

    it("should not truncate short text", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} text="Short text" maxLength={20} />
        </TestProvider>,
      );

      expect(screen.getByText("Short text")).toBeInTheDocument();
      expect(screen.queryByText(/\.\.\./)).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible name from text", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} text="Accept this suggestion" />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toHaveAccessibleName(
        "Accept this suggestion",
      );
    });

    it("should have accessible name with aria-label when provided", () => {
      render(
        <TestProvider>
          <SuggestionChip
            {...defaultProps}
            text="Suggest"
            ariaLabel="Apply suggestion to accept this change"
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toHaveAccessibleName(
        "Apply suggestion to accept this change",
      );
    });

    it("should be focusable", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      const chip = screen.getByRole("button");
      chip.focus();

      expect(document.activeElement).toBe(chip);
    });

    it("should have visible focus indicator", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} />
        </TestProvider>,
      );

      const chip = screen.getByTestId("suggestion-chip");
      expect(chip).toHaveClass("focus-visible:ring-2");
    });

    it("should have no accessibility violations when disabled", async () => {
      const { container } = render(
        <TestProvider>
          <SuggestionChip {...defaultProps} disabled />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations with confidence", async () => {
      const { container } = render(
        <TestProvider>
          <SuggestionChip {...defaultProps} confidence={0.85} />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when loading", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} isLoading />
        </TestProvider>,
      );

      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should disable interaction when loading", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} isLoading />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("should hide icon when loading", () => {
      render(
        <TestProvider>
          <SuggestionChip {...defaultProps} icon="sparkles" isLoading />
        </TestProvider>,
      );

      expect(screen.queryByTestId("chip-icon")).not.toBeInTheDocument();
    });
  });
});
