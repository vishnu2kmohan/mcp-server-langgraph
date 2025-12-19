/**
 * ConfirmationDialog Tests
 *
 * TDD tests for the Confirmation Dialog component.
 * Tests cover:
 * - Dialog rendering with different severity levels
 * - Confirm and cancel actions
 * - Keyboard navigation (Escape to close)
 * - Focus trap within dialog
 * - Type-to-confirm for dangerous actions
 * - WCAG 2.1 AA accessibility requirements
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ConfirmationDialog } from "./ConfirmationDialog";

expect.extend(toHaveNoViolations);

describe("ConfirmationDialog", () => {
  const defaultProps = {
    isOpen: true,
    title: "Confirm Action",
    message: "Are you sure you want to proceed?",
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the dialog when open", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(<ConfirmationDialog {...defaultProps} isOpen={false} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render the title", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      expect(screen.getByText("Confirm Action")).toBeInTheDocument();
    });

    it("should render the message", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      expect(screen.getByText("Are you sure you want to proceed?")).toBeInTheDocument();
    });

    it("should render confirm and cancel buttons", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    });

    it("should render custom button labels", () => {
      render(
        <ConfirmationDialog
          {...defaultProps}
          confirmLabel="Delete"
          cancelLabel="Keep"
        />,
      );

      expect(screen.getByRole("button", { name: /delete/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /keep/i })).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Severity Levels Tests
  // ===========================================================================

  describe("severity levels", () => {
    it("should render info severity by default", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("data-severity", "info");
    });

    it("should render warning severity", () => {
      render(<ConfirmationDialog {...defaultProps} severity="warning" />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("data-severity", "warning");
    });

    it("should render danger severity", () => {
      render(<ConfirmationDialog {...defaultProps} severity="danger" />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("data-severity", "danger");
    });

    it("should show warning icon for warning severity", () => {
      render(<ConfirmationDialog {...defaultProps} severity="warning" />);

      expect(screen.getByTestId("warning-icon")).toBeInTheDocument();
    });

    it("should show danger icon for danger severity", () => {
      render(<ConfirmationDialog {...defaultProps} severity="danger" />);

      expect(screen.getByTestId("danger-icon")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Type-to-Confirm Tests
  // ===========================================================================

  describe("type-to-confirm", () => {
    it("should show type confirmation input for danger severity with confirmText", () => {
      render(
        <ConfirmationDialog
          {...defaultProps}
          severity="danger"
          confirmText="DELETE"
        />,
      );

      expect(screen.getByPlaceholderText(/type DELETE to confirm/i)).toBeInTheDocument();
    });

    it("should disable confirm button until correct text is entered", () => {
      render(
        <ConfirmationDialog
          {...defaultProps}
          severity="danger"
          confirmText="DELETE"
        />,
      );

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      expect(confirmButton).toBeDisabled();
    });

    it("should enable confirm button when correct text is entered", async () => {
      const user = userEvent.setup();
      render(
        <ConfirmationDialog
          {...defaultProps}
          severity="danger"
          confirmText="DELETE"
        />,
      );

      const input = screen.getByPlaceholderText(/type DELETE to confirm/i);
      await user.type(input, "DELETE");

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      expect(confirmButton).not.toBeDisabled();
    });

    it("should be case-sensitive for confirmation text", async () => {
      const user = userEvent.setup();
      render(
        <ConfirmationDialog
          {...defaultProps}
          severity="danger"
          confirmText="DELETE"
        />,
      );

      const input = screen.getByPlaceholderText(/type DELETE to confirm/i);
      await user.type(input, "delete");

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      expect(confirmButton).toBeDisabled();
    });
  });

  // ===========================================================================
  // Action Tests
  // ===========================================================================

  describe("actions", () => {
    it("should call onConfirm when confirm button is clicked", async () => {
      const onConfirm = vi.fn();
      const user = userEvent.setup();
      render(<ConfirmationDialog {...defaultProps} onConfirm={onConfirm} />);

      await user.click(screen.getByRole("button", { name: /confirm/i }));

      expect(onConfirm).toHaveBeenCalled();
    });

    it("should call onCancel when cancel button is clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(<ConfirmationDialog {...defaultProps} onCancel={onCancel} />);

      await user.click(screen.getByRole("button", { name: /cancel/i }));

      expect(onCancel).toHaveBeenCalled();
    });

    it("should call onCancel when backdrop is clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(<ConfirmationDialog {...defaultProps} onCancel={onCancel} />);

      const backdrop = screen.getByTestId("dialog-backdrop");
      await user.click(backdrop);

      expect(onCancel).toHaveBeenCalled();
    });

    it("should not close when dialog content is clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(<ConfirmationDialog {...defaultProps} onCancel={onCancel} />);

      const dialogContent = screen.getByRole("dialog");
      await user.click(dialogContent);

      expect(onCancel).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Keyboard Navigation Tests
  // ===========================================================================

  describe("keyboard navigation", () => {
    it("should close on Escape key", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(<ConfirmationDialog {...defaultProps} onCancel={onCancel} />);

      await user.keyboard("{Escape}");

      expect(onCancel).toHaveBeenCalled();
    });

    it("should focus confirm button on open", async () => {
      render(<ConfirmationDialog {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /confirm/i })).toHaveFocus();
      });
    });

    it("should trap focus within dialog", async () => {
      const user = userEvent.setup();
      render(<ConfirmationDialog {...defaultProps} />);

      // Tab through the dialog elements
      await user.tab(); // Cancel button
      await user.tab(); // Should wrap back to confirm or within dialog

      // Focus should still be within the dialog
      const dialog = screen.getByRole("dialog");
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should show loading state on confirm button when loading", () => {
      render(<ConfirmationDialog {...defaultProps} isLoading />);

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      expect(confirmButton).toBeDisabled();
      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should disable cancel button when loading", () => {
      render(<ConfirmationDialog {...defaultProps} isLoading />);

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      expect(cancelButton).toBeDisabled();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<ConfirmationDialog {...defaultProps} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper dialog role", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have proper aria-labelledby", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");
    });

    it("should have proper aria-describedby", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-describedby");
    });

    it("should have proper aria-modal", () => {
      render(<ConfirmationDialog {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });
  });
});
