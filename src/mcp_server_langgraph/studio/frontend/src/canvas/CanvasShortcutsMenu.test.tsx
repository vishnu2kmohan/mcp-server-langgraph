/**
 * CanvasShortcutsMenu Tests
 *
 * TDD tests for the Canvas Shortcuts Menu component (Sprint 6).
 * Tests menu toggle, action selection, keyboard shortcuts, and loading states.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  CanvasShortcutsMenu,
  type CanvasShortcutAction,
} from "./CanvasShortcutsMenu";

import { TestProvider } from "@/test-utils";

describe("CanvasShortcutsMenu", () => {
  let onAction: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onAction = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("renders the floating action button", () => {
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("canvas-shortcuts-trigger");
      expect(trigger).toBeInTheDocument();
      expect(trigger).toHaveAttribute("aria-label", "Open shortcuts menu");
      expect(trigger).toHaveAttribute("aria-expanded", "false");
    });

    it("menu panel is hidden by default", () => {
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("canvas-shortcuts-panel"),
      ).not.toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} className="custom-class" />
        </TestProvider>,
      );

      const container = screen.getByTestId("canvas-shortcuts-menu");
      expect(container).toHaveClass("custom-class");
    });
  });

  describe("Menu Toggle", () => {
    it("opens menu when trigger is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("canvas-shortcuts-trigger");
      await user.click(trigger);

      const panel = screen.getByTestId("canvas-shortcuts-panel");
      expect(panel).toBeInTheDocument();
      expect(trigger).toHaveAttribute("aria-expanded", "true");
      expect(trigger).toHaveAttribute("aria-label", "Close shortcuts menu");
    });

    it("closes menu when trigger is clicked again", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("canvas-shortcuts-trigger");
      await user.click(trigger);
      expect(screen.getByTestId("canvas-shortcuts-panel")).toBeInTheDocument();

      await user.click(trigger);
      expect(
        screen.queryByTestId("canvas-shortcuts-panel"),
      ).not.toBeInTheDocument();
      expect(trigger).toHaveAttribute("aria-expanded", "false");
    });

    it("rotates trigger button when menu is open", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("canvas-shortcuts-trigger");
      expect(trigger).not.toHaveClass("rotate-45");

      await user.click(trigger);
      expect(trigger).toHaveClass("rotate-45");
    });
  });

  describe("Menu Actions", () => {
    const actions: CanvasShortcutAction[] = [
      "review",
      "comments",
      "logging",
      "fix",
      "port",
      "tests",
      "explain",
    ];

    it.each(actions)("displays %s action in menu", async (action) => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      const actionButton = screen.getByTestId(`shortcut-${action}`);
      expect(actionButton).toBeInTheDocument();
      expect(actionButton).toHaveAttribute("role", "menuitem");
    });

    it.each(actions)(
      "calls onAction with '%s' when clicked",
      async (action) => {
        const user = userEvent.setup();
        render(
          <TestProvider>
            <CanvasShortcutsMenu onAction={onAction} />
          </TestProvider>,
        );

        await user.click(screen.getByTestId("canvas-shortcuts-trigger"));
        await user.click(screen.getByTestId(`shortcut-${action}`));

        expect(onAction).toHaveBeenCalledWith(action);
        expect(onAction).toHaveBeenCalledTimes(1);
      },
    );

    it("closes menu after action is selected", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));
      await user.click(screen.getByTestId("shortcut-review"));

      expect(
        screen.queryByTestId("canvas-shortcuts-panel"),
      ).not.toBeInTheDocument();
    });

    it("shows custom description for port action with language", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} language="TypeScript" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      const portButton = screen.getByTestId("shortcut-port");
      expect(portButton).toHaveTextContent("Convert from TypeScript");
    });
  });

  describe("Loading State", () => {
    it("disables trigger button when loading", () => {
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} isLoading={true} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("canvas-shortcuts-trigger");
      expect(trigger).toBeDisabled();
      expect(trigger).toHaveClass("opacity-50", "cursor-not-allowed");
    });

    it("shows loading spinner when loading", () => {
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} isLoading={true} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("canvas-shortcuts-trigger");
      const spinner = trigger.querySelector(".animate-spin");
      expect(spinner).toBeInTheDocument();
    });

    it("disables action buttons when loading", async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} isLoading={false} />
        </TestProvider>,
      );

      // Open menu first
      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      // Now set loading state (must keep TestProvider wrapper)
      rerender(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} isLoading={true} />
        </TestProvider>,
      );

      const reviewButton = screen.getByTestId("shortcut-review");
      expect(reviewButton).toBeDisabled();
      expect(reviewButton).toHaveClass("opacity-50", "cursor-not-allowed");
    });

    it("does not call onAction when loading", async () => {
      const user = userEvent.setup();
      const { rerender } = render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} isLoading={false} />
        </TestProvider>,
      );

      // Open menu first
      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      // Now set loading state (must keep TestProvider wrapper)
      rerender(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} isLoading={true} />
        </TestProvider>,
      );

      // Try to click action
      await user.click(screen.getByTestId("shortcut-review"));
      expect(onAction).not.toHaveBeenCalled();
    });
  });

  describe("Keyboard Navigation", () => {
    it("closes menu on Escape key", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));
      expect(screen.getByTestId("canvas-shortcuts-panel")).toBeInTheDocument();

      await user.keyboard("{Escape}");
      expect(
        screen.queryByTestId("canvas-shortcuts-panel"),
      ).not.toBeInTheDocument();
    });

    it("does not close menu on Escape when already closed", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      // Menu is closed
      expect(
        screen.queryByTestId("canvas-shortcuts-panel"),
      ).not.toBeInTheDocument();

      // Press Escape
      await user.keyboard("{Escape}");

      // Still closed (no errors)
      expect(
        screen.queryByTestId("canvas-shortcuts-panel"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Click Outside", () => {
    it("closes menu when clicking outside", async () => {
      render(
        <TestProvider>
          <div>
            <div data-testid="outside-element">Outside</div>
            <CanvasShortcutsMenu onAction={onAction} />
          </div>
        </TestProvider>,
      );

      // Open menu
      fireEvent.click(screen.getByTestId("canvas-shortcuts-trigger"));
      expect(screen.getByTestId("canvas-shortcuts-panel")).toBeInTheDocument();

      // Click outside
      fireEvent.mouseDown(screen.getByTestId("outside-element"));
      expect(
        screen.queryByTestId("canvas-shortcuts-panel"),
      ).not.toBeInTheDocument();
    });

    it("does not close menu when clicking inside", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));
      const panel = screen.getByTestId("canvas-shortcuts-panel");

      // Click inside the panel (not on an action)
      fireEvent.mouseDown(panel);
      expect(screen.getByTestId("canvas-shortcuts-panel")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA attributes on trigger", () => {
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("canvas-shortcuts-trigger");
      expect(trigger).toHaveAttribute("aria-label");
      expect(trigger).toHaveAttribute("aria-expanded", "false");
    });

    it("has proper role on menu panel", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      const panel = screen.getByTestId("canvas-shortcuts-panel");
      expect(panel).toHaveAttribute("role", "menu");
      expect(panel).toHaveAttribute("aria-label", "Canvas shortcuts");
    });

    it("has proper role on action buttons", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      const reviewButton = screen.getByTestId("shortcut-review");
      expect(reviewButton).toHaveAttribute("role", "menuitem");
    });
  });

  describe("Menu Content", () => {
    it("displays header with title", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      expect(screen.getByText("Quick Actions")).toBeInTheDocument();
      expect(
        screen.getByText("AI-powered code transformations"),
      ).toBeInTheDocument();
    });

    it("displays footer tip", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      expect(
        screen.getByText("Actions apply to selected artifact"),
      ).toBeInTheDocument();
    });

    it("displays keyboard shortcuts for some actions", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <CanvasShortcutsMenu onAction={onAction} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("canvas-shortcuts-trigger"));

      // Check for keyboard shortcuts (some actions have them)
      expect(screen.getByText("⌘R")).toBeInTheDocument(); // Review
      expect(screen.getByText("⌘F")).toBeInTheDocument(); // Fix
      expect(screen.getByText("⌘T")).toBeInTheDocument(); // Tests
      expect(screen.getByText("⌘E")).toBeInTheDocument(); // Explain
    });
  });
});
