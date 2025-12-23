/**
 * RichTextInput Tests
 *
 * TDD tests for the rich text input component.
 * Tests cover:
 * - Basic rendering
 * - Text formatting (bold, italic, code)
 * - Keyboard shortcuts for formatting
 * - Mention system (@model, @file)
 * - Code block syntax highlighting
 * - Submit handling
 * - Accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { RichTextInput } from "./RichTextInput";

expect.extend(toHaveNoViolations);

describe("RichTextInput", () => {
  const mockOnSubmit = vi.fn();
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render the text input area", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should render placeholder text", () => {
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          placeholder="Type a message..."
        />,
      );
      expect(
        screen.getByPlaceholderText("Type a message..."),
      ).toBeInTheDocument();
    });

    it("should render formatting toolbar", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);
      expect(screen.getByTestId("formatting-toolbar")).toBeInTheDocument();
    });

    it("should render bold button", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();
    });

    it("should render italic button", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);
      expect(
        screen.getByRole("button", { name: /italic/i }),
      ).toBeInTheDocument();
    });

    it("should render code button", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);
      expect(
        screen.getByRole("button", { name: /^code$/i }),
      ).toBeInTheDocument();
    });
  });

  describe("text input", () => {
    it("should accept text input", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} onChange={mockOnChange} />);

      const input = screen.getByRole("textbox");
      await user.type(input, "Hello world");

      expect(mockOnChange).toHaveBeenCalled();
    });

    it("should display entered text", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox");
      await user.type(input, "Test message");

      expect(input).toHaveValue("Test message");
    });

    it("should support controlled value", () => {
      render(
        <RichTextInput onSubmit={mockOnSubmit} value="Controlled value" />,
      );
      expect(screen.getByRole("textbox")).toHaveValue("Controlled value");
    });
  });

  describe("text formatting", () => {
    it("should wrap selected text with bold markers", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "Hello world");

      // Select "world"
      input.setSelectionRange(6, 11);

      const boldButton = screen.getByRole("button", { name: /bold/i });
      await user.click(boldButton);

      expect(input.value).toContain("**world**");
    });

    it("should wrap selected text with italic markers", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "Hello world");

      // Select "world"
      input.setSelectionRange(6, 11);

      const italicButton = screen.getByRole("button", { name: /italic/i });
      await user.click(italicButton);

      expect(input.value).toContain("*world*");
    });

    it("should wrap selected text with inline code markers", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "Use the function test");

      // Select "test"
      input.setSelectionRange(17, 21);

      const codeButton = screen.getByRole("button", { name: /^code$/i });
      await user.click(codeButton);

      expect(input.value).toContain("`test`");
    });

    it("should insert markers at cursor when no text selected", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      input.focus();

      const boldButton = screen.getByRole("button", { name: /bold/i });
      await user.click(boldButton);

      expect(input.value).toBe("****");
    });
  });

  describe("keyboard shortcuts", () => {
    it("should apply bold with Cmd/Ctrl+B", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "test");
      input.setSelectionRange(0, 4);

      await user.keyboard("{Control>}b{/Control}");

      expect(input.value).toContain("**test**");
    });

    it("should apply italic with Cmd/Ctrl+I", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "test");
      input.setSelectionRange(0, 4);

      await user.keyboard("{Control>}i{/Control}");

      expect(input.value).toContain("*test*");
    });

    it("should apply code with Cmd/Ctrl+`", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "test");
      input.setSelectionRange(0, 4);

      await user.keyboard("{Control>}`{/Control}");

      expect(input.value).toContain("`test`");
    });
  });

  describe("submit handling", () => {
    it("should submit on Cmd/Ctrl+Enter", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox");
      await user.type(input, "Test message");
      await user.keyboard("{Control>}{Enter}{/Control}");

      expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
    });

    it("should not submit empty input", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox");
      input.focus();
      await user.keyboard("{Control>}{Enter}{/Control}");

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("should clear input after successful submit", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox");
      await user.type(input, "Test message");
      await user.keyboard("{Control>}{Enter}{/Control}");

      expect(input).toHaveValue("");
    });
  });

  describe("mention system", () => {
    it("should show mention suggestions when @ is typed", async () => {
      const user = userEvent.setup();
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          mentionOptions={[
            { type: "model", value: "claude" },
            { type: "model", value: "gpt-4" },
          ]}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "@");

      await waitFor(() => {
        expect(screen.getByTestId("mention-suggestions")).toBeInTheDocument();
      });
    });

    it("should filter mention suggestions based on input", async () => {
      const user = userEvent.setup();
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          mentionOptions={[
            { type: "model", value: "claude" },
            { type: "model", value: "gpt-4" },
          ]}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "@cl");

      await waitFor(() => {
        expect(screen.getByText("claude")).toBeInTheDocument();
        expect(screen.queryByText("gpt-4")).not.toBeInTheDocument();
      });
    });

    it("should insert mention when suggestion is selected", async () => {
      const user = userEvent.setup();
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          mentionOptions={[{ type: "model", value: "claude" }]}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "@");

      await waitFor(() => {
        expect(screen.getByTestId("mention-suggestions")).toBeInTheDocument();
      });

      const suggestion = screen.getByText("claude");
      await user.click(suggestion);

      expect(input).toHaveValue("@claude ");
    });

    it("should close suggestions on escape", async () => {
      const user = userEvent.setup();
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          mentionOptions={[{ type: "model", value: "claude" }]}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "@");

      await waitFor(() => {
        expect(screen.getByTestId("mention-suggestions")).toBeInTheDocument();
      });

      await user.keyboard("{Escape}");

      expect(
        screen.queryByTestId("mention-suggestions"),
      ).not.toBeInTheDocument();
    });
  });

  describe("code block", () => {
    it("should render code block button", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);
      expect(
        screen.getByRole("button", { name: /code block/i }),
      ).toBeInTheDocument();
    });

    it("should insert code block template", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const codeBlockButton = screen.getByRole("button", {
        name: /code block/i,
      });
      await user.click(codeBlockButton);

      const input = screen.getByRole("textbox");
      expect(input).toHaveValue("```\n\n```");
    });

    it("should wrap selected text in code block", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "const x = 1;");
      input.setSelectionRange(0, 12);

      const codeBlockButton = screen.getByRole("button", {
        name: /code block/i,
      });
      await user.click(codeBlockButton);

      expect(input.value).toContain("```\nconst x = 1;\n```");
    });
  });

  describe("disabled state", () => {
    it("should disable input when disabled prop is true", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} disabled />);
      expect(screen.getByRole("textbox")).toBeDisabled();
    });

    it("should disable formatting buttons when disabled", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} disabled />);
      expect(screen.getByRole("button", { name: /bold/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /italic/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /^code$/i })).toBeDisabled();
    });
  });

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<RichTextInput onSubmit={mockOnSubmit} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible labels for formatting buttons", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      expect(
        screen.getByRole("button", { name: /bold/i }),
      ).toHaveAccessibleName();
      expect(
        screen.getByRole("button", { name: /italic/i }),
      ).toHaveAccessibleName();
      expect(
        screen.getByRole("button", { name: /^code$/i }),
      ).toHaveAccessibleName();
    });

    it("should support keyboard navigation in toolbar", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const boldButton = screen.getByRole("button", { name: /bold/i });
      boldButton.focus();

      expect(document.activeElement).toBe(boldButton);

      await user.keyboard("{Tab}");
      expect(document.activeElement).toBe(
        screen.getByRole("button", { name: /italic/i }),
      );
    });

    it("should announce mention suggestions to screen readers", async () => {
      const user = userEvent.setup();
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          mentionOptions={[{ type: "model", value: "claude" }]}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "@");

      await waitFor(() => {
        const suggestions = screen.getByTestId("mention-suggestions");
        expect(suggestions).toHaveAttribute("role", "listbox");
        expect(suggestions).toHaveAttribute("aria-label");
      });
    });
  });

  describe("maxLength", () => {
    it("should respect maxLength prop", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} maxLength={10} />);

      const input = screen.getByRole("textbox");
      await user.type(input, "This is a very long message");

      expect(input).toHaveValue("This is a ");
    });

    it("should show character count when maxLength is set", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} maxLength={100} />);
      expect(screen.getByText("0 / 100")).toBeInTheDocument();
    });

    it("should update character count as user types", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} maxLength={100} />);

      const input = screen.getByRole("textbox");
      await user.type(input, "Hello");

      expect(screen.getByText("5 / 100")).toBeInTheDocument();
    });
  });
});
