/**
 * CodePreviewToggle Component Tests
 *
 * TDD: Tests written FIRST (RED phase)
 *
 * The CodePreviewToggle component should:
 * 1. Display Code and Preview buttons
 * 2. Indicate the currently active mode
 * 3. Call onModeChange when mode is switched
 * 4. Disable Preview when not supported
 */

import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, it, expect, vi } from "vitest";

import { CodePreviewToggle } from "./CodePreviewToggle";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("CodePreviewToggle", () => {
  describe("Display", () => {
    it("renders Code and Preview buttons", () => {
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="code" onModeChange={onModeChange} />);

      expect(screen.getByRole("button", { name: /code/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /preview/i }),
      ).toBeInTheDocument();
    });

    it("indicates active mode with aria-pressed", () => {
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="code" onModeChange={onModeChange} />);

      expect(screen.getByRole("button", { name: /code/i })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(screen.getByRole("button", { name: /preview/i })).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });

    it("shows preview as active when mode is preview", () => {
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="preview" onModeChange={onModeChange} />);

      expect(screen.getByRole("button", { name: /code/i })).toHaveAttribute(
        "aria-pressed",
        "false",
      );
      expect(screen.getByRole("button", { name: /preview/i })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });
  });

  describe("Mode Switching", () => {
    it("calls onModeChange with 'preview' when Preview is clicked", async () => {
      const _user = userEvent.setup();
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="code" onModeChange={onModeChange} />);

      await user.click(screen.getByRole("button", { name: /preview/i }));

      expect(onModeChange).toHaveBeenCalledWith("preview");
    });

    it("calls onModeChange with 'code' when Code is clicked", async () => {
      const _user = userEvent.setup();
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="preview" onModeChange={onModeChange} />);

      await user.click(screen.getByRole("button", { name: /code/i }));

      expect(onModeChange).toHaveBeenCalledWith("code");
    });

    it("does not call onModeChange when clicking already active mode", async () => {
      const _user = userEvent.setup();
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="code" onModeChange={onModeChange} />);

      await user.click(screen.getByRole("button", { name: /code/i }));

      expect(onModeChange).not.toHaveBeenCalled();
    });
  });

  describe("Preview Support", () => {
    it("disables Preview button when previewSupported is false", () => {
      const onModeChange = vi.fn();
      render(
        <CodePreviewToggle
          mode="code"
          onModeChange={onModeChange}
          previewSupported={false}
        />,
      );

      expect(screen.getByRole("button", { name: /preview/i })).toBeDisabled();
    });

    it("enables Preview button when previewSupported is true", () => {
      const onModeChange = vi.fn();
      render(
        <CodePreviewToggle
          mode="code"
          onModeChange={onModeChange}
          previewSupported={true}
        />,
      );

      expect(
        screen.getByRole("button", { name: /preview/i }),
      ).not.toBeDisabled();
    });

    it("shows tooltip on disabled Preview button", async () => {
      const _user = userEvent.setup();
      const onModeChange = vi.fn();
      render(
        <CodePreviewToggle
          mode="code"
          onModeChange={onModeChange}
          previewSupported={false}
        />,
      );

      const previewButton = screen.getByRole("button", { name: /preview/i });
      expect(previewButton).toHaveAttribute("title", "Preview not available");
    });
  });

  describe("Styling", () => {
    it("applies active styles to selected button", () => {
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="code" onModeChange={onModeChange} />);

      const codeButton = screen.getByRole("button", { name: /code/i });
      expect(codeButton).toHaveClass("bg-primary-500");
    });

    it("applies custom className", () => {
      const onModeChange = vi.fn();
      render(
        <CodePreviewToggle
          mode="code"
          onModeChange={onModeChange}
          className="custom-class"
          data-testid="toggle-group"
        />,
      );

      expect(screen.getByTestId("toggle-group")).toHaveClass("custom-class");
    });
  });

  describe("Accessibility", () => {
    it("uses role group with accessible name", () => {
      const onModeChange = vi.fn();
      render(
        <CodePreviewToggle
          mode="code"
          onModeChange={onModeChange}
          aria-label="View mode"
        />,
      );

      expect(screen.getByRole("group")).toHaveAccessibleName("View mode");
    });

    it("supports keyboard navigation", async () => {
      const _user = userEvent.setup();
      const onModeChange = vi.fn();
      render(<CodePreviewToggle mode="code" onModeChange={onModeChange} />);

      // Tab to first button
      await user.tab();
      expect(screen.getByRole("button", { name: /code/i })).toHaveFocus();

      // Tab to second button
      await user.tab();
      expect(screen.getByRole("button", { name: /preview/i })).toHaveFocus();

      // Activate with Enter
      await user.keyboard("{Enter}");
      expect(onModeChange).toHaveBeenCalledWith("preview");
    });
  });
});
