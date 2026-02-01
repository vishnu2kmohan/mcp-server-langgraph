/**
 * AddMarketplaceDialog Component Tests
 *
 * TDD test suite for the add marketplace dialog.
 * Tests form rendering, validation, and submission.
 *
 * Following STYLE.md conventions:
 * - Accessible dialogs with proper ARIA attributes
 * - Button variants: secondary for Cancel, primary for Add
 * - Form validation with error messages
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AddMarketplaceDialog } from "./AddMarketplaceDialog";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AddMarketplaceDialog", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSubmit: vi.fn(),
    isSubmitting: false,
    error: null as string | null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("does not render when isOpen is false", () => {
      render(<AddMarketplaceDialog {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("renders dialog when isOpen is true", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has data-testid", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByTestId("add-marketplace-dialog")).toBeInTheDocument();
    });

    it("displays dialog title", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByRole("heading", { name: /add marketplace/i }),
      ).toBeInTheDocument();
    });

    it("renders name input field", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    });

    it("renders URI input field", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByLabelText(/uri/i)).toBeInTheDocument();
    });

    it("renders type select field", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByLabelText(/type/i)).toBeInTheDocument();
    });

    it("renders trusted checkbox", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByLabelText(/trusted/i)).toBeInTheDocument();
    });

    it("renders auto-sync checkbox", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByLabelText(/auto-sync/i)).toBeInTheDocument();
    });

    it("renders requires approval checkbox", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByLabelText(/requires approval/i)).toBeInTheDocument();
    });

    it("renders Cancel button", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("renders Add button", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /^add$/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Form Interaction Tests
  // ===========================================================================

  describe("Form Interaction", () => {
    it("allows typing in name field", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      const nameInput = screen.getByLabelText(/name/i);
      await user.type(nameInput, "my-marketplace");
      expect(nameInput).toHaveValue("my-marketplace");
    });

    it("allows typing in URI field", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      const uriInput = screen.getByLabelText(/uri/i);
      await user.type(uriInput, "https://github.com/test/skills");
      expect(uriInput).toHaveValue("https://github.com/test/skills");
    });

    it("allows changing type selection", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      const typeSelect = screen.getByLabelText(/type/i);
      await user.selectOptions(typeSelect, "oci");
      expect(typeSelect).toHaveValue("oci");
    });

    it("allows toggling trusted checkbox", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      const trustedCheckbox = screen.getByLabelText(/trusted/i);
      expect(trustedCheckbox).not.toBeChecked();

      await user.click(trustedCheckbox);
      expect(trustedCheckbox).toBeChecked();
    });

    it("allows toggling auto-sync checkbox", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      const autoSyncCheckbox = screen.getByLabelText(/auto-sync/i);
      expect(autoSyncCheckbox).not.toBeChecked();

      await user.click(autoSyncCheckbox);
      expect(autoSyncCheckbox).toBeChecked();
    });

    it("has requires approval checked by default", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      const requiresApprovalCheckbox =
        screen.getByLabelText(/requires approval/i);
      expect(requiresApprovalCheckbox).toBeChecked();
    });
  });

  // ===========================================================================
  // Form Submission Tests
  // ===========================================================================

  describe("Form Submission", () => {
    it("calls onSubmit with form data when Add clicked", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      await user.type(screen.getByLabelText(/name/i), "test-marketplace");
      await user.type(
        screen.getByLabelText(/uri/i),
        "https://github.com/test/skills",
      );
      await user.click(screen.getByRole("button", { name: /^add$/i }));

      expect(defaultProps.onSubmit).toHaveBeenCalledWith({
        name: "test-marketplace",
        uri: "https://github.com/test/skills",
        type: "github",
        trusted: false,
        autoSync: false,
        requiresApproval: true,
      });
    });

    it("calls onClose when Cancel clicked", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });

    it("does not call onSubmit when name is empty", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      await user.type(
        screen.getByLabelText(/uri/i),
        "https://github.com/test/skills",
      );
      await user.click(screen.getByRole("button", { name: /^add$/i }));

      expect(defaultProps.onSubmit).not.toHaveBeenCalled();
    });

    it("does not call onSubmit when URI is empty", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      await user.type(screen.getByLabelText(/name/i), "test-marketplace");
      await user.click(screen.getByRole("button", { name: /^add$/i }));

      expect(defaultProps.onSubmit).not.toHaveBeenCalled();
    });

    it("shows validation error for empty name", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      await user.type(
        screen.getByLabelText(/uri/i),
        "https://github.com/test/skills",
      );
      await user.click(screen.getByRole("button", { name: /^add$/i }));

      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    });

    it("shows validation error for empty URI", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      await user.type(screen.getByLabelText(/name/i), "test-marketplace");
      await user.click(screen.getByRole("button", { name: /^add$/i }));

      expect(screen.getByText(/uri is required/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("Loading State", () => {
    it("disables Add button when submitting", () => {
      render(<AddMarketplaceDialog {...defaultProps} isSubmitting={true} />);
      expect(screen.getByRole("button", { name: /adding/i })).toBeDisabled();
    });

    it("shows loading spinner when submitting", () => {
      render(<AddMarketplaceDialog {...defaultProps} isSubmitting={true} />);
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("disables form fields when submitting", () => {
      render(<AddMarketplaceDialog {...defaultProps} isSubmitting={true} />);
      expect(screen.getByLabelText(/name/i)).toBeDisabled();
      expect(screen.getByLabelText(/uri/i)).toBeDisabled();
    });
  });

  // ===========================================================================
  // Error State Tests
  // ===========================================================================

  describe("Error State", () => {
    it("displays error message when error prop provided", () => {
      render(
        <AddMarketplaceDialog
          {...defaultProps}
          error="Marketplace already exists"
        />,
      );
      expect(
        screen.getByText(/marketplace already exists/i),
      ).toBeInTheDocument();
    });

    it("shows error with alert role", () => {
      render(
        <AddMarketplaceDialog
          {...defaultProps}
          error="Marketplace already exists"
        />,
      );
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    it("has accessible dialog", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);
      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("has labels for all form fields", () => {
      render(<AddMarketplaceDialog {...defaultProps} />);

      // All inputs should have associated labels
      expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/uri/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/trusted/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/auto-sync/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/requires approval/i)).toBeInTheDocument();
    });

    it("closes on Escape key", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      await user.keyboard("{Escape}");
      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it("has focusable elements in dialog", async () => {
      const user = userEvent.setup();
      render(<AddMarketplaceDialog {...defaultProps} />);

      // Tab to first focusable element (close button or form field)
      await user.tab();
      // Active element should be within the dialog
      const dialog = screen.getByRole("dialog");
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
  });

  // ===========================================================================
  // Form Reset Tests
  // ===========================================================================

  describe("Form Reset", () => {
    it("clears form when dialog closes and reopens", async () => {
      const user = userEvent.setup();
      const { rerender } = render(<AddMarketplaceDialog {...defaultProps} />);

      // Fill in the form
      await user.type(screen.getByLabelText(/name/i), "test-marketplace");

      // Close dialog
      rerender(<AddMarketplaceDialog {...defaultProps} isOpen={false} />);

      // Reopen dialog
      rerender(<AddMarketplaceDialog {...defaultProps} isOpen={true} />);

      // Form should be cleared
      await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toHaveValue("");
      });
    });
  });
});
