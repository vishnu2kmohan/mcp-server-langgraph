/**
 * RichTextInput Rendering Tests
 *
 * Split from RichTextInput.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Basic rendering
 * - Text input behavior
 * - Text formatting (bold, italic, code)
 * - Keyboard shortcuts for formatting
 * - Disabled state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RichTextInput } from "./RichTextInput";

describe("RichTextInput - Rendering", () => {
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

    it("should render formatting toolbar when expanded", () => {
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );
      expect(screen.getByTestId("formatting-toolbar")).toBeInTheDocument();
    });

    it("should render bold button when toolbar expanded", () => {
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();
    });

    it("should render italic button when toolbar expanded", () => {
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );
      expect(
        screen.getByRole("button", { name: /italic/i }),
      ).toBeInTheDocument();
    });

    it("should render code button when toolbar expanded", () => {
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );
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
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );

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
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );

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
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );

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
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );

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

  describe("disabled state", () => {
    it("should disable input when disabled prop is true", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} disabled />);
      expect(screen.getByRole("textbox")).toBeDisabled();
    });

    it("should disable formatting buttons when disabled and toolbar expanded", () => {
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          disabled
          defaultToolbarExpanded={true}
        />,
      );
      expect(screen.getByRole("button", { name: /bold/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /italic/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /^code$/i })).toBeDisabled();
    });
  });
});
