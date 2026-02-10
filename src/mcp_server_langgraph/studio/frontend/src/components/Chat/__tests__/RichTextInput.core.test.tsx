/**
 * RichTextInput Core Tests
 *
 * Tests cover:
 * - Basic rendering
 * - Text input
 * - Text formatting (bold, italic, code)
 * - Keyboard shortcuts for formatting
 * - Submit handling
 * - Disabled state
 * - maxLength
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TestProvider } from "@/test-utils";
import { RichTextInput } from "../RichTextInput";

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
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should render placeholder text", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            placeholder="Type a message..."
          />
        </TestProvider>,
      );
      expect(
        screen.getByPlaceholderText("Type a message..."),
      ).toBeInTheDocument();
    });

    it("should render formatting toolbar when expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("formatting-toolbar")).toBeInTheDocument();
    });

    it("should render bold button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();
    });

    it("should render italic button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /italic/i }),
      ).toBeInTheDocument();
    });

    it("should render code button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /^code$/i }),
      ).toBeInTheDocument();
    });
  });

  describe("text input", () => {
    it("should accept text input", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} onChange={mockOnChange} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "Hello world");

      expect(mockOnChange).toHaveBeenCalled();
    });

    it("should display entered text", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "Test message");

      expect(input).toHaveValue("Test message");
    });

    it("should support controlled value", () => {
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} value="Controlled value" />
        </TestProvider>,
      );
      expect(screen.getByRole("textbox")).toHaveValue("Controlled value");
    });
  });

  describe("text formatting", () => {
    it("should wrap selected text with bold markers", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
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
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
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
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
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
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "test");
      input.setSelectionRange(0, 4);

      await user.keyboard("{Control>}b{/Control}");

      expect(input.value).toContain("**test**");
    });

    it("should apply italic with Cmd/Ctrl+I", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "test");
      input.setSelectionRange(0, 4);

      await user.keyboard("{Control>}i{/Control}");

      expect(input.value).toContain("*test*");
    });

    it("should apply code with Cmd/Ctrl+`", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "test");
      input.setSelectionRange(0, 4);

      await user.keyboard("{Control>}`{/Control}");

      expect(input.value).toContain("`test`");
    });
  });

  describe("submit handling", () => {
    describe("submitOnEnter=true (default, ChatGPT-style)", () => {
      it("should submit on Enter", async () => {
        const user = userEvent.setup();
        render(
          <TestProvider>
            <RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />
          </TestProvider>,
        );

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Enter}");

        expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
      });

      it("should not submit on Shift+Enter (allows newline)", async () => {
        const user = userEvent.setup();
        render(
          <TestProvider>
            <RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />
          </TestProvider>,
        );

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Shift>}{Enter}{/Shift}");

        expect(mockOnSubmit).not.toHaveBeenCalled();
      });

      it("should clear input after successful submit", async () => {
        const user = userEvent.setup();
        render(
          <TestProvider>
            <RichTextInput onSubmit={mockOnSubmit} submitOnEnter={true} />
          </TestProvider>,
        );

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Enter}");

        expect(input).toHaveValue("");
      });
    });

    describe("submitOnEnter=false (legacy, Ctrl+Enter style)", () => {
      it("should submit on Ctrl+Enter", async () => {
        const user = userEvent.setup();
        render(
          <TestProvider>
            <RichTextInput onSubmit={mockOnSubmit} submitOnEnter={false} />
          </TestProvider>,
        );

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Control>}{Enter}{/Control}");

        expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
      });

      it("should not submit on Enter alone", async () => {
        const user = userEvent.setup();
        render(
          <TestProvider>
            <RichTextInput onSubmit={mockOnSubmit} submitOnEnter={false} />
          </TestProvider>,
        );

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Enter}");

        expect(mockOnSubmit).not.toHaveBeenCalled();
      });

      it("should clear input after successful submit", async () => {
        const user = userEvent.setup();
        render(
          <TestProvider>
            <RichTextInput onSubmit={mockOnSubmit} submitOnEnter={false} />
          </TestProvider>,
        );

        const input = screen.getByRole("textbox");
        await user.type(input, "Test message");
        await user.keyboard("{Control>}{Enter}{/Control}");

        expect(input).toHaveValue("");
      });
    });

    it("should not submit empty input", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      input.focus();
      await user.keyboard("{Enter}");

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe("disabled state", () => {
    it("should disable input when disabled prop is true", () => {
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} disabled />
        </TestProvider>,
      );
      expect(screen.getByRole("textbox")).toBeDisabled();
    });

    it("should disable formatting buttons when disabled and toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            disabled
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /bold/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /italic/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /^code$/i })).toBeDisabled();
    });
  });

  describe("maxLength", () => {
    it("should respect maxLength prop", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} maxLength={10} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "This is a very long message");

      expect(input).toHaveValue("This is a ");
    });

    it("should show character count when maxLength is set", () => {
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} maxLength={100} />
        </TestProvider>,
      );
      expect(screen.getByText("0 / 100")).toBeInTheDocument();
    });

    it("should update character count as user types", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} maxLength={100} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "Hello");

      expect(screen.getByText("5 / 100")).toBeInTheDocument();
    });
  });
});
