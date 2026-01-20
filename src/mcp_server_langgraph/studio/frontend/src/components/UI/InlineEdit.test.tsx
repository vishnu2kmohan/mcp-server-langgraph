/**
 * InlineEdit Component Tests
 *
 * TDD: Tests written FIRST (RED phase)
 *
 * The InlineEdit component should:
 * 1. Display the current value as text when not editing
 * 2. Switch to edit mode on click (or double-click)
 * 3. Save on Enter key
 * 4. Cancel on Escape key
 * 5. Support validation
 * 6. Handle blur events appropriately
 */

import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, it, expect, vi } from "vitest";

import { InlineEdit } from "./InlineEdit";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("InlineEdit", () => {
  describe("Display Mode", () => {
    it("renders the value as text when not editing", () => {
      const onSave = vi.fn();
      render(<InlineEdit value="Test Value" onSave={onSave} />);

      expect(screen.getByText("Test Value")).toBeInTheDocument();
    });

    it("shows placeholder when value is empty", () => {
      const onSave = vi.fn();
      render(
        <InlineEdit value="" onSave={onSave} placeholder="Click to edit" />,
      );

      expect(screen.getByText("Click to edit")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const onSave = vi.fn();
      render(
        <InlineEdit
          value="Test"
          onSave={onSave}
          className="custom-class"
          data-testid="inline-edit"
        />,
      );

      const container = screen.getByTestId("inline-edit");
      expect(container).toHaveClass("custom-class");
    });
  });

  describe("Edit Mode Activation", () => {
    it("switches to edit mode on click", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Test Value" onSave={onSave} />);

      await user.click(screen.getByText("Test Value"));

      const input = screen.getByRole("textbox");
      expect(input).toBeInTheDocument();
      expect(input).toHaveValue("Test Value");
    });

    it("focuses the input when entering edit mode", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Test Value" onSave={onSave} />);

      await user.click(screen.getByText("Test Value"));

      const input = screen.getByRole("textbox");
      expect(input).toHaveFocus();
    });

    it("selects all text when entering edit mode", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Test Value" onSave={onSave} />);

      await user.click(screen.getByText("Test Value"));

      const input = screen.getByRole("textbox") as HTMLInputElement;
      expect(input.selectionStart).toBe(0);
      expect(input.selectionEnd).toBe("Test Value".length);
    });
  });

  describe("Saving", () => {
    it("calls onSave with new value on Enter key", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Original" onSave={onSave} />);

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");

      await user.clear(input);
      await user.type(input, "Updated{Enter}");

      expect(onSave).toHaveBeenCalledWith("Updated");
    });

    it("exits edit mode after saving", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Original" onSave={onSave} />);

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.type(input, "{Enter}");

      expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    });

    it("saves on blur by default", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Original" onSave={onSave} />);

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "Updated");
      fireEvent.blur(input);

      expect(onSave).toHaveBeenCalledWith("Updated");
    });

    it("does not call onSave if value unchanged", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Original" onSave={onSave} />);

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.type(input, "{Enter}");

      expect(onSave).not.toHaveBeenCalled();
    });
  });

  describe("Cancellation", () => {
    it("cancels and reverts on Escape key", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      const onCancel = vi.fn();
      render(
        <InlineEdit value="Original" onSave={onSave} onCancel={onCancel} />,
      );

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "Changed{Escape}");

      expect(screen.getByText("Original")).toBeInTheDocument();
      expect(onSave).not.toHaveBeenCalled();
      expect(onCancel).toHaveBeenCalled();
    });

    it("exits edit mode on cancel", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Original" onSave={onSave} />);

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.type(input, "{Escape}");

      expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    });
  });

  describe("Validation", () => {
    it("does not save if validation fails", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      const validate = vi.fn().mockReturnValue(false);
      render(
        <InlineEdit value="Original" onSave={onSave} validate={validate} />,
      );

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "Invalid{Enter}");

      expect(validate).toHaveBeenCalledWith("Invalid");
      expect(onSave).not.toHaveBeenCalled();
    });

    it("saves if validation passes", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      const validate = vi.fn().mockReturnValue(true);
      render(
        <InlineEdit value="Original" onSave={onSave} validate={validate} />,
      );

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "Valid{Enter}");

      expect(validate).toHaveBeenCalledWith("Valid");
      expect(onSave).toHaveBeenCalledWith("Valid");
    });

    it("shows error styling when validation fails", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      const validate = vi.fn().mockReturnValue(false);
      render(
        <InlineEdit
          value="Original"
          onSave={onSave}
          validate={validate}
          data-testid="inline-edit"
        />,
      );

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "Invalid{Enter}");

      // Input should still be visible (not saved) and have error styling
      expect(input).toBeInTheDocument();
      expect(input).toHaveClass("border-error-9");
    });
  });

  describe("Disabled State", () => {
    it("does not enter edit mode when disabled", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<InlineEdit value="Test" onSave={onSave} disabled />);

      await user.click(screen.getByText("Test"));

      expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    });

    it("shows disabled styling", () => {
      const onSave = vi.fn();
      render(
        <InlineEdit
          value="Test"
          onSave={onSave}
          disabled
          data-testid="inline-edit"
        />,
      );

      const container = screen.getByTestId("inline-edit");
      expect(container).toHaveClass("cursor-not-allowed");
    });
  });

  describe("Loading State", () => {
    it("shows loading indicator when saving", async () => {
      const user = userEvent.setup();
      // Create a promise that we can resolve manually
      let resolvePromise: (value: void) => void;
      const savePromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });
      const onSave = vi.fn().mockImplementation(() => savePromise);

      render(<InlineEdit value="Original" onSave={onSave} />);

      await user.click(screen.getByText("Original"));
      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "Updated{Enter}");

      // Should show loading state while save is pending
      expect(screen.getByTestId("inline-edit-loading")).toBeInTheDocument();

      // Resolve and verify loading disappears
      resolvePromise!();
      await waitFor(() => {
        expect(
          screen.queryByTestId("inline-edit-loading"),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Accessibility", () => {
    it("has appropriate aria-label", () => {
      const onSave = vi.fn();
      render(
        <InlineEdit
          value="Test"
          onSave={onSave}
          aria-label="Edit session name"
        />,
      );

      const button = screen.getByRole("button", { name: /edit session name/i });
      expect(button).toBeInTheDocument();
    });

    it("input has accessible name when editing", async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(
        <InlineEdit
          value="Test"
          onSave={onSave}
          aria-label="Edit session name"
        />,
      );

      await user.click(screen.getByRole("button"));
      const input = screen.getByRole("textbox");

      expect(input).toHaveAccessibleName("Edit session name");
    });
  });
});
