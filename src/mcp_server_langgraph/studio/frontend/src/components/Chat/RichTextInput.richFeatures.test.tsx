/**
 * RichTextInput Rich Features Tests
 *
 * Split from RichTextInput.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Mention system (@model, @file)
 * - Code block insertion
 * - Strikethrough formatting
 * - List formatting (ordered and bullet)
 * - Quote formatting
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RichTextInput } from "./RichTextInput";

import { TestProvider } from "@/test-utils";

describe("RichTextInput - Rich Features", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("mention system", () => {
    it("should show mention suggestions when @ is typed", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            mentionOptions={[
              { type: "model", value: "claude" },
              { type: "model", value: "gpt-4" },
            ]}
          />
        </TestProvider>,
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
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            mentionOptions={[
              { type: "model", value: "claude" },
              { type: "model", value: "gpt-4" },
            ]}
          />
        </TestProvider>,
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
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            mentionOptions={[{ type: "model", value: "claude" }]}
          />
        </TestProvider>,
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
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            mentionOptions={[{ type: "model", value: "claude" }]}
          />
        </TestProvider>,
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
    it("should render code block button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /code block/i }),
      ).toBeInTheDocument();
    });

    it("should insert code block template", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );

      const codeBlockButton = screen.getByRole("button", {
        name: /code block/i,
      });
      await user.click(codeBlockButton);

      const input = screen.getByRole("textbox");
      expect(input).toHaveValue("```\n\n```");
    });

    it("should wrap selected text in code block", async () => {
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
      await user.type(input, "const x = 1;");
      input.setSelectionRange(0, 12);

      const codeBlockButton = screen.getByRole("button", {
        name: /code block/i,
      });
      await user.click(codeBlockButton);

      expect(input.value).toContain("```\nconst x = 1;\n```");
    });
  });

  describe("strikethrough formatting", () => {
    it("should render strikethrough button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /strikethrough/i }),
      ).toBeInTheDocument();
    });

    it("should wrap selected text with strikethrough markers", async () => {
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

      const strikeButton = screen.getByRole("button", {
        name: /strikethrough/i,
      });
      await user.click(strikeButton);

      expect(input.value).toContain("~~world~~");
    });

    it("should apply strikethrough with Ctrl+Shift+X shortcut", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "test");
      input.setSelectionRange(0, 4);

      await user.keyboard("{Control>}{Shift>}x{/Shift}{/Control}");

      expect(input.value).toContain("~~test~~");
    });
  });

  describe("list formatting", () => {
    it("should render ordered list button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /ordered list/i }),
      ).toBeInTheDocument();
    });

    it("should render bullet list button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /bullet list/i }),
      ).toBeInTheDocument();
    });

    it("should insert ordered list prefix at line start", async () => {
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
      await user.type(input, "First item");

      const listButton = screen.getByRole("button", { name: /ordered list/i });
      await user.click(listButton);

      expect(input.value).toBe("1. First item");
    });

    it("should insert bullet list prefix at line start", async () => {
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
      await user.type(input, "List item");

      const listButton = screen.getByRole("button", { name: /bullet list/i });
      await user.click(listButton);

      expect(input.value).toBe("- List item");
    });

    it("should insert ordered list on empty input", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );

      const listButton = screen.getByRole("button", { name: /ordered list/i });
      await user.click(listButton);

      const input = screen.getByRole("textbox");
      expect(input).toHaveValue("1. ");
    });

    it("should insert bullet list on empty input", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );

      const listButton = screen.getByRole("button", { name: /bullet list/i });
      await user.click(listButton);

      const input = screen.getByRole("textbox");
      expect(input).toHaveValue("- ");
    });
  });

  describe("quote formatting", () => {
    it("should render quote button when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /quote/i }),
      ).toBeInTheDocument();
    });

    it("should insert quote prefix at line start", async () => {
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
      await user.type(input, "Famous quote");

      const quoteButton = screen.getByRole("button", { name: /quote/i });
      await user.click(quoteButton);

      expect(input.value).toBe("> Famous quote");
    });

    it("should insert quote prefix on empty input", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );

      const quoteButton = screen.getByRole("button", { name: /quote/i });
      await user.click(quoteButton);

      const input = screen.getByRole("textbox");
      expect(input).toHaveValue("> ");
    });
  });
});
