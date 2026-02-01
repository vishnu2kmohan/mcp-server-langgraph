/**
 * RemoveMarketplaceDialog Component Tests
 *
 * TDD test suite for the remove marketplace confirmation dialog.
 * Tests rendering, user interactions, and accessibility.
 *
 * Following STYLE.md conventions:
 * - Accessible dialogs with proper ARIA attributes
 * - Button variants: secondary for Cancel, danger for Remove
 * - Focus-visible rings for keyboard navigation
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RemoveMarketplaceDialog } from "./RemoveMarketplaceDialog";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RemoveMarketplaceDialog", () => {
  const defaultProps = {
    marketplaceName: "community",
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    isRemoving: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("does not render when isOpen is false", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("renders dialog when isOpen is true", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has data-testid", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByTestId("remove-marketplace-dialog"),
      ).toBeInTheDocument();
    });

    it("displays dialog title", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByRole("heading", { name: /remove marketplace/i }),
      ).toBeInTheDocument();
    });

    it("displays marketplace name in confirmation message", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(screen.getByText(/community/)).toBeInTheDocument();
    });

    it("displays warning message", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByText(/are you sure you want to remove/i),
      ).toBeInTheDocument();
    });

    it("displays consequences warning", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByText(/skills from this marketplace will no longer/i),
      ).toBeInTheDocument();
    });

    it("renders Cancel button", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("renders Remove button", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /^remove$/i }),
      ).toBeInTheDocument();
    });

    it("does not render when marketplaceName is null", () => {
      render(
        <RemoveMarketplaceDialog {...defaultProps} marketplaceName={null} />,
      );
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // User Interaction Tests
  // ===========================================================================

  describe("User Interactions", () => {
    it("calls onClose when Cancel clicked", async () => {
      const user = userEvent.setup();
      render(<RemoveMarketplaceDialog {...defaultProps} />);

      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onConfirm when Remove clicked", async () => {
      const user = userEvent.setup();
      render(<RemoveMarketplaceDialog {...defaultProps} />);

      await user.click(screen.getByRole("button", { name: /^remove$/i }));
      expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
    });

    it("closes dialog on Escape key", async () => {
      const user = userEvent.setup();
      render(<RemoveMarketplaceDialog {...defaultProps} />);

      await user.keyboard("{Escape}");
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it("closes dialog when clicking backdrop", async () => {
      const user = userEvent.setup();
      render(<RemoveMarketplaceDialog {...defaultProps} />);

      // Click on the backdrop (the outer container)
      const backdrop = screen.getByTestId("remove-marketplace-dialog-backdrop");
      await user.click(backdrop);
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("Loading State", () => {
    it("disables Remove button when removing", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} isRemoving={true} />);
      expect(screen.getByRole("button", { name: /removing/i })).toBeDisabled();
    });

    it("disables Cancel button when removing", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} isRemoving={true} />);
      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
    });

    it("shows loading spinner when removing", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} isRemoving={true} />);
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("shows 'Removing...' text when removing", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} isRemoving={true} />);
      expect(screen.getByText(/removing/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    it("has accessible dialog with aria-modal", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("has aria-labelledby pointing to title", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");
    });

    it("Remove button has danger styling indication", () => {
      render(<RemoveMarketplaceDialog {...defaultProps} />);
      const removeButton = screen.getByRole("button", { name: /^remove$/i });
      // Check for danger-related classes (error semantic color)
      expect(removeButton.className).toMatch(/error|red|danger/i);
    });

    it("focus is trapped in dialog", async () => {
      const user = userEvent.setup();
      render(<RemoveMarketplaceDialog {...defaultProps} />);

      // Tab through the dialog
      await user.tab();

      // Active element should be within the dialog
      const dialog = screen.getByRole("dialog");
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe("Edge Cases", () => {
    it("handles long marketplace names gracefully", () => {
      render(
        <RemoveMarketplaceDialog
          {...defaultProps}
          marketplaceName="very-long-marketplace-name-that-might-overflow"
        />,
      );
      expect(
        screen.getByText(/very-long-marketplace-name-that-might-overflow/),
      ).toBeInTheDocument();
    });

    it("handles special characters in marketplace name", () => {
      render(
        <RemoveMarketplaceDialog
          {...defaultProps}
          marketplaceName="my-org/skills-repo"
        />,
      );
      expect(screen.getByText(/my-org\/skills-repo/)).toBeInTheDocument();
    });
  });
});
