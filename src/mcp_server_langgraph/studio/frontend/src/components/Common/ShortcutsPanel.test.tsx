/**
 * ShortcutsPanel Tests
 *
 * TDD tests for the Keyboard Shortcuts Panel component.
 * Tests cover:
 * - Panel rendering
 * - Shortcut grouping by category
 * - Search/filter shortcuts
 * - Keyboard navigation
 * - WCAG 2.1 AA accessibility requirements
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ShortcutsPanel } from "./ShortcutsPanel";

expect.extend(toHaveNoViolations);

const mockShortcuts = [
  {
    action: "new-session",
    keys: "Cmd+N",
    label: "New Session",
    category: "Navigation",
  },
  {
    action: "search",
    keys: "Cmd+K",
    label: "Quick Search",
    category: "Navigation",
  },
  {
    action: "send-message",
    keys: "Cmd+Enter",
    label: "Send Message",
    category: "Chat",
  },
  {
    action: "toggle-sidebar",
    keys: "Cmd+B",
    label: "Toggle Sidebar",
    category: "Layout",
  },
  {
    action: "show-shortcuts",
    keys: "Cmd+/",
    label: "Show Shortcuts",
    category: "Help",
  },
];

describe("ShortcutsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the shortcuts panel when open", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(
        <ShortcutsPanel
          isOpen={false}
          shortcuts={mockShortcuts}
          onClose={() => {}}
        />,
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render panel title", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      expect(screen.getByText(/keyboard shortcuts/i)).toBeInTheDocument();
    });

    it("should render all shortcuts", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      expect(screen.getByText("New Session")).toBeInTheDocument();
      expect(screen.getByText("Quick Search")).toBeInTheDocument();
      expect(screen.getByText("Send Message")).toBeInTheDocument();
    });

    it("should render shortcut keys", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      expect(screen.getByText("Cmd+N")).toBeInTheDocument();
      expect(screen.getByText("Cmd+K")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Category Grouping Tests
  // ===========================================================================

  describe("category grouping", () => {
    it("should group shortcuts by category", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      expect(screen.getByText("Navigation")).toBeInTheDocument();
      expect(screen.getByText("Chat")).toBeInTheDocument();
      expect(screen.getByText("Layout")).toBeInTheDocument();
    });

    it("should show category headings", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      const headings = screen.getAllByRole("heading", { level: 3 });
      expect(headings.length).toBeGreaterThan(0);
    });
  });

  // ===========================================================================
  // Search/Filter Tests
  // ===========================================================================

  describe("search functionality", () => {
    it("should render search input", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      expect(
        screen.getByPlaceholderText(/search shortcuts/i),
      ).toBeInTheDocument();
    });

    it("should filter shortcuts by search query", async () => {
      const user = userEvent.setup();
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      const searchInput = screen.getByPlaceholderText(/search shortcuts/i);
      await user.type(searchInput, "session");

      expect(screen.getByText("New Session")).toBeInTheDocument();
      expect(screen.queryByText("Quick Search")).not.toBeInTheDocument();
    });

    it("should show no results message when search has no matches", async () => {
      const user = userEvent.setup();
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      const searchInput = screen.getByPlaceholderText(/search shortcuts/i);
      await user.type(searchInput, "nonexistent");

      expect(screen.getByText(/no shortcuts found/i)).toBeInTheDocument();
    });

    it("should clear search when clear button is clicked", async () => {
      const user = userEvent.setup();
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      const searchInput = screen.getByPlaceholderText(/search shortcuts/i);
      await user.type(searchInput, "session");

      const clearButton = screen.getByRole("button", { name: /clear search/i });
      await user.click(clearButton);

      expect(searchInput).toHaveValue("");
      expect(screen.getByText("Quick Search")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Close Action Tests
  // ===========================================================================

  describe("close actions", () => {
    it("should call onClose when close button is clicked", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={onClose} />,
      );

      await user.click(screen.getByRole("button", { name: /close/i }));

      expect(onClose).toHaveBeenCalled();
    });

    it("should close on Escape key", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={onClose} />,
      );

      await user.keyboard("{Escape}");

      expect(onClose).toHaveBeenCalled();
    });

    it("should close on backdrop click", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={onClose} />,
      );

      await user.click(screen.getByTestId("panel-backdrop"));

      expect(onClose).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper dialog role", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have proper aria-labelledby", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");
    });

    it("should focus search input on open", async () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search shortcuts/i)).toHaveFocus();
      });
    });

    it("should use kbd element for shortcut keys", () => {
      render(
        <ShortcutsPanel isOpen shortcuts={mockShortcuts} onClose={() => {}} />,
      );

      const kbdElements = document.querySelectorAll("kbd");
      expect(kbdElements.length).toBeGreaterThan(0);
    });
  });
});
