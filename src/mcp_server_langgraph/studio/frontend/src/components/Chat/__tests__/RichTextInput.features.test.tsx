/**
 * RichTextInput Feature Tests
 *
 * Tests cover:
 * - Mention system (@model, @file)
 * - Code block syntax highlighting
 * - Accessibility
 * - Collapsible toolbar (Sprint 2.4)
 * - Inline suggestions
 * - Cursor position tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  cleanup,
  fireEvent,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { TestProvider } from "@/test-utils";
import { RichTextInput } from "../RichTextInput";

expect.extend(toHaveNoViolations);

describe("RichTextInput", () => {
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

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible labels for formatting buttons when toolbar expanded", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );

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

    it("should support keyboard navigation in toolbar when expanded", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );

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
        const suggestions = screen.getByTestId("mention-suggestions");
        expect(suggestions).toHaveAttribute("role", "listbox");
        expect(suggestions).toHaveAttribute("aria-label");
      });
    });
  });

  describe("collapsible toolbar (Sprint 2.4)", () => {
    it("should render toolbar toggle button", () => {
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /toggle formatting/i }),
      ).toBeInTheDocument();
    });

    it("should hide formatting toolbar by default (collapsed)", () => {
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      // Toggle button should be visible
      expect(
        screen.getByRole("button", { name: /toggle formatting/i }),
      ).toBeInTheDocument();

      // Formatting buttons should be hidden initially
      expect(
        screen.queryByRole("button", { name: /bold/i }),
      ).not.toBeInTheDocument();
    });

    it("should show formatting toolbar when toggle is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const toggleButton = screen.getByRole("button", {
        name: /toggle formatting/i,
      });
      await user.click(toggleButton);

      // Formatting toolbar should now be visible
      expect(screen.getByTestId("formatting-toolbar")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /italic/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^code$/i }),
      ).toBeInTheDocument();
    });

    it("should hide formatting toolbar when toggle is clicked again", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const toggleButton = screen.getByRole("button", {
        name: /toggle formatting/i,
      });

      // Open toolbar
      await user.click(toggleButton);
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();

      // Close toolbar
      await user.click(toggleButton);
      expect(
        screen.queryByRole("button", { name: /bold/i }),
      ).not.toBeInTheDocument();
    });

    it("should toggle toolbar with Ctrl+Shift+F keyboard shortcut", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      input.focus();

      // Initially collapsed
      expect(
        screen.queryByRole("button", { name: /bold/i }),
      ).not.toBeInTheDocument();

      // Press Ctrl+Shift+F to expand
      await user.keyboard("{Control>}{Shift>}f{/Shift}{/Control}");
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();

      // Press Ctrl+Shift+F again to collapse
      await user.keyboard("{Control>}{Shift>}f{/Shift}{/Control}");
      expect(
        screen.queryByRole("button", { name: /bold/i }),
      ).not.toBeInTheDocument();
    });

    it("should show + icon when collapsed and - icon when expanded", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const toggleButton = screen.getByRole("button", {
        name: /toggle formatting/i,
      });

      // Should show plus icon when collapsed
      expect(
        toggleButton.querySelector("[data-testid='plus-icon']"),
      ).toBeInTheDocument();

      await user.click(toggleButton);

      // Should show minus icon when expanded
      expect(
        toggleButton.querySelector("[data-testid='minus-icon']"),
      ).toBeInTheDocument();
    });

    it("should render toolbar visible when defaultExpanded prop is true", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            defaultToolbarExpanded={true}
          />
        </TestProvider>,
      );

      // Formatting buttons should be visible
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /italic/i }),
      ).toBeInTheDocument();
    });

    it("should still apply formatting when toolbar is expanded", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      // Expand toolbar
      const toggleButton = screen.getByRole("button", {
        name: /toggle formatting/i,
      });
      await user.click(toggleButton);

      // Type and select text
      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.type(input, "Hello world");
      input.setSelectionRange(6, 11);

      // Click bold
      const boldButton = screen.getByRole("button", { name: /bold/i });
      await user.click(boldButton);

      expect(input.value).toContain("**world**");
    });

    it("should have accessible toggle button with aria-expanded", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const toggleButton = screen.getByRole("button", {
        name: /toggle formatting/i,
      });

      // Should indicate collapsed state
      expect(toggleButton).toHaveAttribute("aria-expanded", "false");

      await user.click(toggleButton);

      // Should indicate expanded state
      expect(toggleButton).toHaveAttribute("aria-expanded", "true");
    });

    it("should announce toolbar state change to screen readers", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const toggleButton = screen.getByRole("button", {
        name: /toggle formatting/i,
      });

      // Check for live region
      await user.click(toggleButton);

      // Look for the status announcement
      const liveRegion = document.querySelector('[role="status"]');
      expect(liveRegion).toBeInTheDocument();
    });
  });

  describe("inline suggestions", () => {
    it("should render inline suggestion overlay when provided", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello "
            enableInlineSuggestions={true}
            inlineSuggestion="world"
          />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("inline-suggestion-overlay"),
      ).toBeInTheDocument();
    });

    it("should not show inline suggestion when disabled", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello "
            enableInlineSuggestions={false}
            inlineSuggestion="world"
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("inline-suggestion-overlay"),
      ).not.toBeInTheDocument();
    });

    it("should not show inline suggestion when value is empty", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value=""
            enableInlineSuggestions={true}
            inlineSuggestion="world"
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("inline-suggestion-overlay"),
      ).not.toBeInTheDocument();
    });

    it("should accept suggestion on Tab key", async () => {
      const user = userEvent.setup();
      const mockAccept = vi.fn();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello "
            enableInlineSuggestions={true}
            inlineSuggestion="world"
            onAcceptSuggestion={mockAccept}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.click(input);
      await user.keyboard("{Tab}");

      expect(mockAccept).toHaveBeenCalledWith("world");
    });

    it("should dismiss suggestion on Escape key", async () => {
      const user = userEvent.setup();
      const mockDismiss = vi.fn();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello "
            enableInlineSuggestions={true}
            inlineSuggestion="world"
            onDismissSuggestion={mockDismiss}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.click(input);
      await user.keyboard("{Escape}");

      expect(mockDismiss).toHaveBeenCalled();
    });

    it("should show loading indicator when suggestion is loading", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello "
            enableInlineSuggestions={true}
            isSuggestionLoading={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-loading")).toBeInTheDocument();
    });

    it("should show Tab hint when suggestion is visible", () => {
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello "
            enableInlineSuggestions={true}
            inlineSuggestion="world"
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-hint")).toBeInTheDocument();
      expect(screen.getByText(/tab/i)).toBeInTheDocument();
    });
  });

  describe("cursor position tracking", () => {
    it("should call onCursorPositionChange when cursor moves via click", async () => {
      const user = userEvent.setup();
      const mockCursorChange = vi.fn();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello world"
            onCursorPositionChange={mockCursorChange}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.click(input);

      // Click should trigger cursor position change
      expect(mockCursorChange).toHaveBeenCalled();
    });

    it("should call onCursorPositionChange with correct position after typing", async () => {
      const user = userEvent.setup();
      const mockCursorChange = vi.fn();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            onCursorPositionChange={mockCursorChange}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "Hello");

      // After typing "Hello", cursor should be at position 5
      expect(mockCursorChange).toHaveBeenLastCalledWith(5);
    });

    it("should call onCursorPositionChange when using keyboard navigation", async () => {
      const user = userEvent.setup();
      const mockCursorChange = vi.fn();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello world"
            onCursorPositionChange={mockCursorChange}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;
      await user.click(input);

      // Clear previous calls from click
      mockCursorChange.mockClear();

      // Use arrow keys to move cursor
      await user.keyboard("{Home}");
      expect(mockCursorChange).toHaveBeenCalledWith(0);

      await user.keyboard("{End}");
      expect(mockCursorChange).toHaveBeenCalledWith(11); // "Hello world".length
    });

    it("should not throw when onCursorPositionChange is not provided", async () => {
      const user = userEvent.setup();

      // Should render without errors
      render(
        <TestProvider>
          <RichTextInput onSubmit={mockOnSubmit} />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "Test");

      // No error should be thrown
      expect(input).toHaveValue("Test");
    });

    it("should report cursor position during text selection", () => {
      const mockCursorChange = vi.fn();
      render(
        <TestProvider>
          <RichTextInput
            onSubmit={mockOnSubmit}
            value="Hello world"
            onCursorPositionChange={mockCursorChange}
          />
        </TestProvider>,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;

      // Focus and set selection range
      input.focus();
      input.setSelectionRange(6, 11); // Select "world"

      // Use fireEvent.select to trigger React's onSelect handler
      fireEvent.select(input);

      // Should report the start of selection
      expect(mockCursorChange).toHaveBeenCalledWith(6);
    });
  });
});
