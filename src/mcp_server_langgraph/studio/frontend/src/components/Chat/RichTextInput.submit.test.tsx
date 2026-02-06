/**
 * RichTextInput Submit Handling Tests
 *
 * Split from RichTextInput.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Submit on Enter (ChatGPT-style)
 * - Submit on Ctrl+Enter (legacy style)
 * - Auto-continue lists on Enter (Slack-style)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RichTextInput } from "./RichTextInput";

describe("RichTextInput - Submit Handling", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("submit handling", () => {
    describe("submitOnEnter=true (default, ChatGPT-style)", () => {
      it("should submit on Enter", async () => {
        const user = userEvent.setup();
        render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Enter}");

        expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
      });

      it("should not submit on Shift+Enter (allows newline)", async () => {
        const user = userEvent.setup();
        render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Shift>}{Enter}{/Shift}");

        expect(mockOnSubmit).not.toHaveBeenCalled();
      });

      it("should clear input after successful submit", async () => {
        const user = userEvent.setup();
        render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Enter}");

        expect(input).toHaveValue("");
      });
    });

    describe("submitOnEnter=false (legacy, Ctrl+Enter style)", () => {
      it("should submit on Ctrl+Enter", async () => {
        const user = userEvent.setup();
        render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={false} />);

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Control>}{Enter}{/Control}");

        expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
      });

      it("should not submit on Enter alone", async () => {
        const user = userEvent.setup();
        render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={false} />);

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Enter}");

        expect(mockOnSubmit).not.toHaveBeenCalled();
      });

      it("should clear input after successful submit", async () => {
        const user = userEvent.setup();
        render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={false} />);

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Control>}{Enter}{/Control}");

        expect(input).toHaveValue("");
      });
    });

    it("should not submit empty input", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox");
      input.focus();
      await user.keyboard("{Enter}");

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe("auto-continue lists on Enter (Slack-style)", () => {
    it("should auto-continue ordered list when pressing Shift+Enter after numbered item", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "1. First item");

      // Shift+Enter for newline (doesn't submit)
      await user.keyboard("{Shift>}{Enter}{/Shift}");

      // Should auto-insert "2. " on new line
      expect(input.value).toBe("1. First item\n2. ");
    });

    it("should auto-continue bullet list when pressing Shift+Enter after bullet item", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "- First item");

      await user.keyboard("{Shift>}{Enter}{/Shift}");

      expect(input.value).toBe("- First item\n- ");
    });

    it("should auto-continue quote when pressing Shift+Enter after quote line", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "> First line");

      await user.keyboard("{Shift>}{Enter}{/Shift}");

      expect(input.value).toBe("> First line\n> ");
    });

    it("should increment ordered list number", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "5. Item five");

      await user.keyboard("{Shift>}{Enter}{/Shift}");

      expect(input.value).toBe("5. Item five\n6. ");
    });

    it("should exit list mode on empty list item (double Enter)", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "- Item");
      await user.keyboard("{Shift>}{Enter}{/Shift}");

      // Now we have "- Item\n- "
      // If we press Enter again without typing, it should remove the "- " and just add newline
      await user.keyboard("{Shift>}{Enter}{/Shift}");

      expect(input.value).toBe("- Item\n\n");
    });

    it("should work with submitOnEnter=false (Enter for newline)", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} submitOnEnter={false} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "1. First item");

      // With submitOnEnter=false, plain Enter creates newline
      await user.keyboard("{Enter}");

      expect(input.value).toBe("1. First item\n2. ");
    });
  });
});
