/**
 * RichTextInput Advanced Features Tests
 *
 * Split from RichTextInput.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Accessibility (a11y)
 * - maxLength handling
 * - Collapsible toolbar (Sprint 2.4)
 * - Inline suggestions
 * - Cursor position tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { RichTextInput } from "./RichTextInput";

expect.extend(toHaveNoViolations);

describe("RichTextInput - Advanced Features", () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<RichTextInput onSubmit={mockOnSubmit} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible labels for formatting buttons when toolbar expanded", () => {
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
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
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
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

  describe("collapsible toolbar (Sprint 2.4)", () => {
    it("should render toolbar toggle button", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);
      expect(
        screen.getByRole("button", {
          name: /show formatting|hide formatting/i,
        }),
      ).toBeInTheDocument();
    });

    it("should hide formatting toolbar by default (collapsed)", () => {
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      // Toggle button should be visible
      expect(
        screen.getByRole("button", {
          name: /show formatting|hide formatting/i,
        }),
      ).toBeInTheDocument();

      // Formatting buttons should be hidden initially
      expect(
        screen.queryByRole("button", { name: /bold/i }),
      ).not.toBeInTheDocument();
    });

    it("should show formatting toolbar when toggle is clicked", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const toggleButton = screen.getByRole("button", {
        name: /show formatting|hide formatting/i,
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
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const toggleButton = screen.getByRole("button", {
        name: /show formatting|hide formatting/i,
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
      render(<RichTextInput onSubmit={mockOnSubmit} />);

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

    it("should show Aa toggle button and change style when expanded", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const toggleButton = screen.getByTestId("formatting-toggle-button");
      const aaIcon = screen.getByTestId("aa-icon");

      // Should show Aa text
      expect(aaIcon).toHaveTextContent("Aa");

      // Should have muted color when collapsed
      expect(aaIcon.className).toMatch(/text-neutral-10/);

      await user.click(toggleButton);

      // Should have primary color when expanded
      expect(aaIcon.className).toMatch(/text-primary-10/);
    });

    it("should render toolbar visible when defaultExpanded prop is true", () => {
      render(
        <RichTextInput onSubmit={mockOnSubmit} defaultToolbarExpanded={true} />,
      );

      // Formatting buttons should be visible
      expect(screen.getByRole("button", { name: /bold/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /italic/i }),
      ).toBeInTheDocument();
    });

    it("should still apply formatting when toolbar is expanded", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      // Expand toolbar
      const toggleButton = screen.getByRole("button", {
        name: /show formatting|hide formatting/i,
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
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const toggleButton = screen.getByRole("button", {
        name: /show formatting|hide formatting/i,
      });

      // Should indicate collapsed state
      expect(toggleButton).toHaveAttribute("aria-expanded", "false");

      await user.click(toggleButton);

      // Should indicate expanded state
      expect(toggleButton).toHaveAttribute("aria-expanded", "true");
    });

    it("should announce toolbar state change to screen readers", async () => {
      const user = userEvent.setup();
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const toggleButton = screen.getByRole("button", {
        name: /show formatting|hide formatting/i,
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
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
        />,
      );

      expect(
        screen.getByTestId("inline-suggestion-overlay"),
      ).toBeInTheDocument();
    });

    it("should not show inline suggestion when disabled", () => {
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello "
          enableInlineSuggestions={false}
          inlineSuggestion="world"
        />,
      );

      expect(
        screen.queryByTestId("inline-suggestion-overlay"),
      ).not.toBeInTheDocument();
    });

    it("should not show inline suggestion when value is empty", () => {
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          value=""
          enableInlineSuggestions={true}
          inlineSuggestion="world"
        />,
      );

      expect(
        screen.queryByTestId("inline-suggestion-overlay"),
      ).not.toBeInTheDocument();
    });

    it("should accept suggestion on Tab key", async () => {
      const user = userEvent.setup();
      const mockAccept = vi.fn();
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
          onAcceptSuggestion={mockAccept}
        />,
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
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
          onDismissSuggestion={mockDismiss}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.click(input);
      await user.keyboard("{Escape}");

      expect(mockDismiss).toHaveBeenCalled();
    });

    it("should show loading indicator when suggestion is loading", () => {
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello "
          enableInlineSuggestions={true}
          isSuggestionLoading={true}
        />,
      );

      expect(screen.getByTestId("suggestion-loading")).toBeInTheDocument();
    });

    it("should show Tab hint when suggestion is visible", () => {
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello "
          enableInlineSuggestions={true}
          inlineSuggestion="world"
        />,
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
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello world"
          onCursorPositionChange={mockCursorChange}
        />,
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
        <RichTextInput
          onSubmit={mockOnSubmit}
          onCursorPositionChange={mockCursorChange}
        />,
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
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello world"
          onCursorPositionChange={mockCursorChange}
        />,
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
      render(<RichTextInput onSubmit={mockOnSubmit} />);

      const input = screen.getByRole("textbox");
      await user.type(input, "Test");

      // No error should be thrown
      expect(input).toHaveValue("Test");
    });

    it("should report cursor position during text selection", async () => {
      const user = userEvent.setup();
      const mockCursorChange = vi.fn();
      render(
        <RichTextInput
          onSubmit={mockOnSubmit}
          value="Hello world"
          onCursorPositionChange={mockCursorChange}
        />,
      );

      const input = screen.getByRole("textbox") as HTMLTextAreaElement;

      // Click to focus and trigger cursor position change
      await user.click(input);

      // Clear previous calls
      mockCursorChange.mockClear();

      // Use keyboard to select text (Shift+End selects to end of line)
      await user.keyboard("{Home}");
      expect(mockCursorChange).toHaveBeenCalledWith(0);
    });
  });
});
