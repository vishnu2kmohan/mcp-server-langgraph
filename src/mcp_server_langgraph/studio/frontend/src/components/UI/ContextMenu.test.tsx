/**
 * ContextMenu Component Tests
 *
 * TDD: Tests written FIRST (RED phase)
 *
 * The ContextMenu component should:
 * 1. Open on right-click
 * 2. Show menu items
 * 3. Execute action on item click
 * 4. Close on outside click
 * 5. Support keyboard navigation
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

import { ContextMenu, ContextMenuItem } from "./ContextMenu";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("ContextMenu", () => {
  const defaultItems: ContextMenuItem[] = [
    { id: "rename", label: "Rename", action: vi.fn() },
    { id: "delete", label: "Delete", action: vi.fn() },
    { id: "duplicate", label: "Duplicate", action: vi.fn() },
  ];

  describe("Trigger", () => {
    it("renders children normally", () => {
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      expect(screen.getByTestId("trigger")).toBeInTheDocument();
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("opens menu on right-click", async () => {
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      expect(screen.getByRole("menu")).toBeInTheDocument();
    });

    it("positions menu at cursor location", async () => {
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"), {
        clientX: 100,
        clientY: 200,
      });

      const menu = screen.getByRole("menu");
      expect(menu).toHaveStyle({ left: "100px", top: "200px" });
    });
  });

  describe("Menu Items", () => {
    it("renders all menu items", async () => {
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      expect(
        screen.getByRole("menuitem", { name: "Rename" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("menuitem", { name: "Delete" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("menuitem", { name: "Duplicate" }),
      ).toBeInTheDocument();
    });

    it("executes action when item is clicked", async () => {
      const user = userEvent.setup();
      const renameAction = vi.fn();
      const items: ContextMenuItem[] = [
        { id: "rename", label: "Rename", action: renameAction },
      ];

      render(
        <TestProvider>
          <ContextMenu items={items}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));
      await user.click(screen.getByRole("menuitem", { name: "Rename" }));

      expect(renameAction).toHaveBeenCalled();
    });

    it("closes menu after action", async () => {
      const user = userEvent.setup();
      const items: ContextMenuItem[] = [
        { id: "rename", label: "Rename", action: vi.fn() },
      ];

      render(
        <TestProvider>
          <ContextMenu items={items}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));
      await user.click(screen.getByRole("menuitem", { name: "Rename" }));

      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("supports disabled items", async () => {
      const user = userEvent.setup();
      const deleteAction = vi.fn();
      const items: ContextMenuItem[] = [
        { id: "delete", label: "Delete", action: deleteAction, disabled: true },
      ];

      render(
        <TestProvider>
          <ContextMenu items={items}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));
      const menuItem = screen.getByRole("menuitem", { name: "Delete" });

      expect(menuItem).toHaveAttribute("aria-disabled", "true");
      await user.click(menuItem);

      expect(deleteAction).not.toHaveBeenCalled();
    });

    it("supports dividers between items", async () => {
      const items: ContextMenuItem[] = [
        { id: "rename", label: "Rename", action: vi.fn() },
        { id: "divider-1", type: "divider" },
        { id: "delete", label: "Delete", action: vi.fn() },
      ];

      render(
        <TestProvider>
          <ContextMenu items={items}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      expect(screen.getByRole("separator")).toBeInTheDocument();
    });

    it("supports icons in items", async () => {
      const items: ContextMenuItem[] = [
        {
          id: "rename",
          label: "Rename",
          action: vi.fn(),
          icon: <span data-testid="rename-icon">✏️</span>,
        },
      ];

      render(
        <TestProvider>
          <ContextMenu items={items}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      expect(screen.getByTestId("rename-icon")).toBeInTheDocument();
    });
  });

  describe("Closing", () => {
    it("closes on outside click", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <>
            <ContextMenu items={defaultItems}>
              <div data-testid="trigger">Right-click me</div>
            </ContextMenu>
            <button data-testid="outside">Outside</button>
          </>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));
      expect(screen.getByRole("menu")).toBeInTheDocument();

      await user.click(screen.getByTestId("outside"));

      await waitFor(() => {
        expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      });
    });

    it("closes on Escape key", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));
      expect(screen.getByRole("menu")).toBeInTheDocument();

      await user.keyboard("{Escape}");

      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("focuses first item when opened", async () => {
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      await waitFor(() => {
        expect(screen.getByRole("menuitem", { name: "Rename" })).toHaveFocus();
      });
    });

    it("navigates with arrow keys", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      await waitFor(() => {
        expect(screen.getByRole("menuitem", { name: "Rename" })).toHaveFocus();
      });

      await user.keyboard("{ArrowDown}");
      expect(screen.getByRole("menuitem", { name: "Delete" })).toHaveFocus();

      await user.keyboard("{ArrowDown}");
      expect(screen.getByRole("menuitem", { name: "Duplicate" })).toHaveFocus();

      await user.keyboard("{ArrowUp}");
      expect(screen.getByRole("menuitem", { name: "Delete" })).toHaveFocus();
    });

    it("executes action on Enter", async () => {
      const user = userEvent.setup();
      const renameAction = vi.fn();
      const items: ContextMenuItem[] = [
        { id: "rename", label: "Rename", action: renameAction },
      ];

      render(
        <TestProvider>
          <ContextMenu items={items}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      await waitFor(() => {
        expect(screen.getByRole("menuitem", { name: "Rename" })).toHaveFocus();
      });

      await user.keyboard("{Enter}");

      expect(renameAction).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA roles", async () => {
      render(
        <TestProvider>
          <ContextMenu items={defaultItems}>
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      expect(screen.getByRole("menu")).toBeInTheDocument();
      expect(screen.getAllByRole("menuitem")).toHaveLength(3);
    });

    it("supports aria-label on menu", async () => {
      render(
        <TestProvider>
          <ContextMenu items={defaultItems} aria-label="Session actions">
            <div data-testid="trigger">Right-click me</div>
          </ContextMenu>
        </TestProvider>,
      );

      fireEvent.contextMenu(screen.getByTestId("trigger"));

      expect(screen.getByRole("menu")).toHaveAccessibleName("Session actions");
    });
  });
});
