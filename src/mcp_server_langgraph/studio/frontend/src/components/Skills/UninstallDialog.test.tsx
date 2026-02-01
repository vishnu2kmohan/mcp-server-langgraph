/**
 * UninstallDialog Component Tests
 *
 * TDD test suite for the uninstall confirmation dialog.
 * Tests rendering, confirmation flow, and accessibility.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UninstallDialog } from "./UninstallDialog";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("UninstallDialog", () => {
  const defaultProps = {
    skillName: "web-research",
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    isUninstalling: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("should render dialog when open", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(screen.getByTestId("uninstall-dialog")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(<UninstallDialog {...defaultProps} isOpen={false} />);

      expect(screen.queryByTestId("uninstall-dialog")).not.toBeInTheDocument();
    });

    it("should not render when skillName is null", () => {
      render(<UninstallDialog {...defaultProps} skillName={null} />);

      expect(screen.queryByTestId("uninstall-dialog")).not.toBeInTheDocument();
    });

    it("should display dialog title", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(screen.getByText("Uninstall Skill")).toBeInTheDocument();
    });

    it("should display skill name in confirmation message", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(screen.getByText(/web-research/)).toBeInTheDocument();
    });

    it("should display warning about data loss", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(
        screen.getByText(/this action cannot be undone/i),
      ).toBeInTheDocument();
    });

    it("should have Cancel button", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("should have Uninstall button", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /uninstall/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // User Interaction Tests
  // ===========================================================================

  describe("User Interactions", () => {
    it("should call onClose when Cancel is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(<UninstallDialog {...defaultProps} onClose={onClose} />);

      await user.click(screen.getByRole("button", { name: /cancel/i }));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("should call onConfirm when Uninstall is clicked", async () => {
      const user = userEvent.setup();
      const onConfirm = vi.fn();

      render(<UninstallDialog {...defaultProps} onConfirm={onConfirm} />);

      await user.click(screen.getByRole("button", { name: /uninstall/i }));
      expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it("should call onClose when backdrop is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(<UninstallDialog {...defaultProps} onClose={onClose} />);

      // Click the backdrop (the outer div with onClick)
      const backdrop = screen.getByTestId("uninstall-dialog").parentElement;
      if (backdrop) {
        await user.click(backdrop);
        expect(onClose).toHaveBeenCalledTimes(1);
      }
    });

    it("should not close when dialog content is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(<UninstallDialog {...defaultProps} onClose={onClose} />);

      await user.click(screen.getByTestId("uninstall-dialog"));
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("Loading State", () => {
    it("should disable Cancel button when uninstalling", () => {
      render(<UninstallDialog {...defaultProps} isUninstalling={true} />);

      expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();
    });

    it("should disable Uninstall button when uninstalling", () => {
      render(<UninstallDialog {...defaultProps} isUninstalling={true} />);

      expect(screen.getByRole("button", { name: /uninstall/i })).toBeDisabled();
    });

    it("should show loading text on Uninstall button when uninstalling", () => {
      render(<UninstallDialog {...defaultProps} isUninstalling={true} />);

      expect(screen.getByText("Uninstalling...")).toBeInTheDocument();
    });

    it("should not call onConfirm when button clicked while uninstalling", async () => {
      const user = userEvent.setup();
      const onConfirm = vi.fn();

      render(
        <UninstallDialog
          {...defaultProps}
          onConfirm={onConfirm}
          isUninstalling={true}
        />,
      );

      const button = screen.getByRole("button", { name: /uninstall/i });
      await user.click(button);
      expect(onConfirm).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Keyboard Navigation Tests
  // ===========================================================================

  describe("Keyboard Navigation", () => {
    it("should close on Escape key when not uninstalling", async () => {
      const onClose = vi.fn();

      render(<UninstallDialog {...defaultProps} onClose={onClose} />);

      fireEvent.keyDown(document, { key: "Escape", code: "Escape" });

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });

    it("should not close on Escape key when uninstalling", async () => {
      const onClose = vi.fn();

      render(
        <UninstallDialog
          {...defaultProps}
          onClose={onClose}
          isUninstalling={true}
        />,
      );

      fireEvent.keyDown(document, { key: "Escape", code: "Escape" });

      await waitFor(() => {
        expect(onClose).not.toHaveBeenCalled();
      });
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    it("should have dialog role", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have aria-modal attribute", () => {
      render(<UninstallDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("should have accessible title via aria-labelledby", () => {
      render(<UninstallDialog {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");

      const labelId = dialog.getAttribute("aria-labelledby");
      expect(document.getElementById(labelId!)).toHaveTextContent(
        "Uninstall Skill",
      );
    });

    it("should have focusable buttons", () => {
      render(<UninstallDialog {...defaultProps} />);

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      const uninstallButton = screen.getByRole("button", {
        name: /uninstall/i,
      });

      expect(cancelButton).not.toBeDisabled();
      expect(uninstallButton).not.toBeDisabled();
    });
  });

  // ===========================================================================
  // Visual Styling Tests
  // ===========================================================================

  describe("Visual Styling", () => {
    it("should have danger styling on Uninstall button", () => {
      render(<UninstallDialog {...defaultProps} />);

      const uninstallButton = screen.getByRole("button", {
        name: /uninstall/i,
      });
      // Danger variant should have red styling
      expect(uninstallButton).toHaveClass("bg-danger-9");
    });
  });

  // ===========================================================================
  // Enhanced Loading State Tests
  // ===========================================================================

  describe("Enhanced Loading States", () => {
    it("should show progress indicator when uninstalling", () => {
      render(<UninstallDialog {...defaultProps} isUninstalling={true} />);
      expect(screen.getByTestId("uninstall-progress")).toBeInTheDocument();
    });

    it("should show progress message when uninstalling", () => {
      render(<UninstallDialog {...defaultProps} isUninstalling={true} />);
      expect(
        screen.getByTestId("uninstall-progress-message"),
      ).toBeInTheDocument();
    });

    it("should hide progress indicator when not uninstalling", () => {
      render(<UninstallDialog {...defaultProps} isUninstalling={false} />);
      expect(
        screen.queryByTestId("uninstall-progress"),
      ).not.toBeInTheDocument();
    });
  });
});
