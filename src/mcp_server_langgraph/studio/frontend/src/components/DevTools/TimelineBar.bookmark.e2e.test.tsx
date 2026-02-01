/**
 * TimelineBar Bookmark Management E2E Integration Tests
 *
 * End-to-end tests for the complete bookmark workflow:
 * - Add bookmark -> Verify in list -> Jump to bookmark -> Remove bookmark
 * - Persistence callbacks integration
 * - Keyboard navigation support
 *
 * These tests verify the full user flow across components.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { TimelineBar } from "./TimelineBar";
import { DevToolsTimelineProvider } from "./context/DevToolsTimelineProvider";

// =============================================================================
// Test Utilities
// =============================================================================

interface RenderOptions {
  initialEvents?: Array<{
    id: string;
    type: string;
    timestamp: number;
    data: unknown;
  }>;
  onBookmarkAdd?: (bookmark: {
    id: string;
    time: number;
    label: string;
  }) => void;
  onBookmarkRemove?: (id: string) => void;
}

function renderTimelineBar(options: RenderOptions = {}) {
  const {
    initialEvents = [
      { id: "e1", type: "console", timestamp: Date.now() - 5000, data: {} },
      { id: "e2", type: "network", timestamp: Date.now() - 3000, data: {} },
      { id: "e3", type: "console", timestamp: Date.now() - 1000, data: {} },
    ],
    onBookmarkAdd = vi.fn(),
    onBookmarkRemove = vi.fn(),
  } = options;

  return {
    ...render(
      <DevToolsTimelineProvider initialEvents={initialEvents}>
        <TimelineBar
          showBookmarkButton={true}
          onBookmarkAdd={onBookmarkAdd}
          onBookmarkRemove={onBookmarkRemove}
        />
      </DevToolsTimelineProvider>,
    ),
    onBookmarkAdd,
    onBookmarkRemove,
  };
}

// =============================================================================
// E2E Tests
// =============================================================================

describe("TimelineBar Bookmark Management E2E", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("complete bookmark workflow", () => {
    it("should complete full flow: add bookmark -> verify in list -> jump to bookmark -> remove", async () => {
      const user = userEvent.setup();
      const { onBookmarkAdd, onBookmarkRemove } = renderTimelineBar();

      // Step 1: Open bookmark menu
      const bookmarkButton = screen.getByRole("button", {
        name: /add bookmark/i,
      });
      await user.click(bookmarkButton);

      // Step 2: Verify empty state
      expect(screen.getByText(/no bookmarks yet/i)).toBeInTheDocument();

      // Step 3: Add a bookmark
      await user.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Step 4: Verify callback was called
      expect(onBookmarkAdd).toHaveBeenCalledWith(
        expect.objectContaining({
          label: "Bookmark 1",
          time: expect.any(Number),
        }),
      );

      // Step 5: Reopen menu and verify bookmark appears
      await user.click(bookmarkButton);
      expect(screen.queryByText(/no bookmarks yet/i)).not.toBeInTheDocument();
      expect(screen.getByTestId("bookmark-item")).toBeInTheDocument();

      // Step 6: Click on bookmark to jump
      await user.click(
        screen.getByRole("button", { name: /jump to bookmark 1/i }),
      );
      // Menu should close after jump (wait for AnimatePresence exit animation)
      await waitFor(() => {
        expect(screen.queryByTestId("bookmark-menu")).not.toBeInTheDocument();
      });

      // Step 7: Reopen menu and remove bookmark
      await user.click(bookmarkButton);
      const removeButton = screen.getByRole("button", {
        name: /remove bookmark 1/i,
      });
      await user.click(removeButton);

      // Step 8: Verify removal callback
      expect(onBookmarkRemove).toHaveBeenCalledWith(expect.any(String));
    });

    it("should display bookmark count badge when bookmarks exist", async () => {
      const user = userEvent.setup();
      renderTimelineBar();

      // Initially no count shown
      const bookmarkButton = screen.getByRole("button", {
        name: /add bookmark/i,
      });
      expect(bookmarkButton).not.toHaveTextContent(/\d+/);

      // Add first bookmark
      await user.click(bookmarkButton);
      await user.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Reopen to check count
      await user.click(bookmarkButton);

      // Button should now show count
      expect(bookmarkButton).toHaveTextContent("1");
    });

    it("should add multiple bookmarks sequentially", async () => {
      const user = userEvent.setup();
      const { onBookmarkAdd } = renderTimelineBar();

      const bookmarkButton = screen.getByRole("button", {
        name: /add bookmark/i,
      });

      // Add first bookmark
      await user.click(bookmarkButton);
      await user.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Add second bookmark
      await user.click(bookmarkButton);
      await user.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Verify both callbacks called with sequential labels
      expect(onBookmarkAdd).toHaveBeenCalledTimes(2);
      expect(onBookmarkAdd).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({ label: "Bookmark 1" }),
      );
      expect(onBookmarkAdd).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({ label: "Bookmark 2" }),
      );

      // Verify count in button
      expect(bookmarkButton).toHaveTextContent("2");
    });
  });

  describe("bookmark persistence integration", () => {
    it("should trigger persistence callback on add", async () => {
      const user = userEvent.setup();
      const persistBookmark = vi.fn();
      renderTimelineBar({ onBookmarkAdd: persistBookmark });

      await user.click(screen.getByRole("button", { name: /add bookmark/i }));
      await user.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      expect(persistBookmark).toHaveBeenCalledWith({
        id: expect.stringMatching(/^\d+-[a-z0-9]+$/),
        time: expect.any(Number),
        label: "Bookmark 1",
      });
    });

    it("should trigger persistence callback on remove", async () => {
      const user = userEvent.setup();
      const removeBookmarkCallback = vi.fn();
      renderTimelineBar({ onBookmarkRemove: removeBookmarkCallback });

      // Add a bookmark first
      await user.click(screen.getByRole("button", { name: /add bookmark/i }));
      await user.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Remove it
      await user.click(screen.getByRole("button", { name: /add bookmark/i }));
      await user.click(
        screen.getByRole("button", { name: /remove bookmark 1/i }),
      );

      expect(removeBookmarkCallback).toHaveBeenCalledWith(expect.any(String));
    });
  });

  describe("accessibility", () => {
    it("should be fully keyboard navigable", async () => {
      const user = userEvent.setup();
      renderTimelineBar();

      // Tab to bookmark button and activate with Enter
      const bookmarkButton = screen.getByRole("button", {
        name: /add bookmark/i,
      });
      bookmarkButton.focus();
      await user.keyboard("{Enter}");

      // Menu should open
      expect(screen.getByTestId("bookmark-menu")).toBeInTheDocument();

      // Menu items should have proper role
      expect(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      ).toBeInTheDocument();
    });

    it("should have proper ARIA attributes on bookmark button", () => {
      renderTimelineBar();

      const button = screen.getByRole("button", { name: /add bookmark/i });
      expect(button).toHaveAttribute("aria-haspopup", "menu");
      expect(button).toHaveAttribute("aria-expanded", "false");
    });

    it("should update aria-expanded when menu opens", async () => {
      const user = userEvent.setup();
      renderTimelineBar();

      const button = screen.getByRole("button", { name: /add bookmark/i });
      expect(button).toHaveAttribute("aria-expanded", "false");

      await user.click(button);
      expect(button).toHaveAttribute("aria-expanded", "true");
    });
  });

  describe("edge cases", () => {
    it("should disable bookmark button when no events", () => {
      render(
        <DevToolsTimelineProvider initialEvents={[]}>
          <TimelineBar showBookmarkButton={true} />
        </DevToolsTimelineProvider>,
      );

      const button = screen.getByRole("button", { name: /add bookmark/i });
      expect(button).toBeDisabled();
    });

    it("should support adding and removing a bookmark", async () => {
      const user = userEvent.setup();
      const { onBookmarkAdd, onBookmarkRemove } = renderTimelineBar();

      const bookmarkButton = screen.getByRole("button", {
        name: /add bookmark/i,
      });

      // Add a bookmark
      await user.click(bookmarkButton);
      await user.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      expect(onBookmarkAdd).toHaveBeenCalledTimes(1);

      // Open menu and verify bookmark exists
      await user.click(bookmarkButton);
      expect(screen.getByTestId("bookmark-item")).toBeInTheDocument();

      // Remove the bookmark
      const removeButton = screen.getByRole("button", {
        name: /remove bookmark 1/i,
      });
      await user.click(removeButton);

      expect(onBookmarkRemove).toHaveBeenCalledTimes(1);
    });
  });
});
