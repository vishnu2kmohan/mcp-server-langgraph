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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ConfirmationDialog } from "./ConfirmationDialog";

import { TestProvider } from "@/test-utils";

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

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the dialog when open", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} isOpen={false} />
        </TestProvider>,
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render the title", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Confirm Action")).toBeInTheDocument();
    });

    it("should render the message", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByText("Are you sure you want to proceed?"),
      ).toBeInTheDocument();
    });

    it("should render confirm and cancel buttons", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /confirm/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("should render custom button labels", () => {
      render(
        <TestProvider>
          <ConfirmationDialog
            {...defaultProps}
            confirmLabel="Delete"
            cancelLabel="Keep"
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /delete/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /keep/i })).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Severity Levels Tests
  // ===========================================================================

  describe("severity levels", () => {
    it("should render info severity by default", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("data-severity", "info");
    });

    it("should render warning severity", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} severity="warning" />
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("data-severity", "warning");
    });

    it("should render danger severity", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} severity="danger" />
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("data-severity", "danger");
    });

    it("should show warning icon for warning severity", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} severity="warning" />
        </TestProvider>,
      );

      expect(screen.getByTestId("warning-icon")).toBeInTheDocument();
    });

    it("should show danger icon for danger severity", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} severity="danger" />
        </TestProvider>,
      );

      expect(screen.getByTestId("danger-icon")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Type-to-Confirm Tests
  // ===========================================================================

  describe("type-to-confirm", () => {
    it("should show type confirmation input for danger severity with confirmText", () => {
      render(
        <TestProvider>
          <ConfirmationDialog
            {...defaultProps}
            severity="danger"
            confirmText="DELETE"
          />
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText(/type DELETE to confirm/i),
      ).toBeInTheDocument();
    });

    it("should disable confirm button until correct text is entered", () => {
      render(
        <TestProvider>
          <ConfirmationDialog
            {...defaultProps}
            severity="danger"
            confirmText="DELETE"
          />
        </TestProvider>,
      );

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      expect(confirmButton).toBeDisabled();
    });

    it("should enable confirm button when correct text is entered", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ConfirmationDialog
            {...defaultProps}
            severity="danger"
            confirmText="DELETE"
          />
        </TestProvider>,
      );

      const input = screen.getByPlaceholderText(/type DELETE to confirm/i);
      await user.type(input, "DELETE");

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      expect(confirmButton).not.toBeDisabled();
    });

    it("should be case-sensitive for confirmation text", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ConfirmationDialog
            {...defaultProps}
            severity="danger"
            confirmText="DELETE"
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} onConfirm={onConfirm} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /confirm/i }));

      expect(onConfirm).toHaveBeenCalled();
    });

    it("should call onCancel when cancel button is clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} onCancel={onCancel} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /cancel/i }));

      expect(onCancel).toHaveBeenCalled();
    });

    it("should call onCancel when backdrop is clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} onCancel={onCancel} />
        </TestProvider>,
      );

      const backdrop = screen.getByTestId("dialog-backdrop");
      await user.click(backdrop);

      expect(onCancel).toHaveBeenCalled();
    });

    it("should not close when dialog content is clicked", async () => {
      const onCancel = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} onCancel={onCancel} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} onCancel={onCancel} />
        </TestProvider>,
      );

      await user.keyboard("{Escape}");

      expect(onCancel).toHaveBeenCalled();
    });

    it("should focus confirm button on open", async () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /confirm/i })).toHaveFocus();
      });
    });

    it("should trap focus within dialog", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} isLoading />
        </TestProvider>,
      );

      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      expect(confirmButton).toBeDisabled();
      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should disable cancel button when loading", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} isLoading />
        </TestProvider>,
      );

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      expect(cancelButton).toBeDisabled();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper dialog role", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have proper aria-labelledby", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");
    });

    it("should have proper aria-describedby", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-describedby");
    });

    it("should have proper aria-modal", () => {
      render(
        <TestProvider>
          <ConfirmationDialog {...defaultProps} />
        </TestProvider>,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });
  });
});
