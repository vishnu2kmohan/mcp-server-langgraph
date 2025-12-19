/**
 * SessionList Tests
 *
 * TDD tests for the Session List sidebar component.
 * Tests cover:
 * - Session list rendering
 * - Session search/filter
 * - Session actions (pin, delete, rename)
 * - Keyboard navigation
 * - Loading and empty states
 * - WCAG 2.1 AA accessibility requirements
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { SessionList } from "./SessionList";
import { PreferencesProvider } from "../../contexts/PreferencesContext";
import type { SessionSummary } from "../../types/session";

expect.extend(toHaveNoViolations);

// Mock session data
const mockSessions: SessionSummary[] = [
  {
    id: "session-1",
    name: "First Session",
    createdAt: Date.now() - 3600000,
    updatedAt: Date.now() - 1800000,
    messageCount: 5,
  },
  {
    id: "session-2",
    name: "Second Session",
    createdAt: Date.now() - 7200000,
    updatedAt: Date.now() - 3600000,
    messageCount: 12,
  },
  {
    id: "session-3",
    name: "Third Session",
    createdAt: Date.now() - 86400000,
    updatedAt: Date.now() - 86400000,
    messageCount: 0,
  },
];

// Helper to create wrapper with preferences provider
const renderWithProvider = (
  ui: React.ReactElement,
  { pinnedSessions = [] }: { pinnedSessions?: string[] } = {},
) => {
  // Set up localStorage with pinned sessions
  if (pinnedSessions.length > 0) {
    localStorage.setItem(
      "mcp_studio_preferences",
      JSON.stringify({
        session: { pinnedSessions, recentSessions: [], maxRecentSessions: 10 },
      }),
    );
  }
  return render(<PreferencesProvider>{ui}</PreferencesProvider>);
};

describe("SessionList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the session list", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />);

      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it("should render all sessions", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />);

      expect(screen.getByText("First Session")).toBeInTheDocument();
      expect(screen.getByText("Second Session")).toBeInTheDocument();
      expect(screen.getByText("Third Session")).toBeInTheDocument();
    });

    it("should render session message count", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />);

      expect(screen.getByText(/5 messages/i)).toBeInTheDocument();
      expect(screen.getByText(/12 messages/i)).toBeInTheDocument();
    });

    it("should render search input", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />);

      expect(
        screen.getByPlaceholderText(/search sessions/i),
      ).toBeInTheDocument();
    });

    it("should render create new session button when onCreate is provided", () => {
      renderWithProvider(
        <SessionList sessions={mockSessions} onCreate={() => {}} />,
      );

      expect(
        screen.getByRole("button", { name: /new session/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should show loading skeleton when isLoading is true", () => {
      renderWithProvider(<SessionList sessions={[]} isLoading />);

      expect(screen.getByTestId("session-list-loading")).toBeInTheDocument();
    });

    it("should not show sessions when loading", () => {
      renderWithProvider(<SessionList sessions={mockSessions} isLoading />);

      expect(screen.queryByText("First Session")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Empty State Tests
  // ===========================================================================

  describe("empty state", () => {
    it("should show empty message when no sessions exist", () => {
      renderWithProvider(<SessionList sessions={[]} />);

      expect(screen.getByText(/no sessions yet/i)).toBeInTheDocument();
    });

    it("should show create session prompt in empty state", () => {
      renderWithProvider(<SessionList sessions={[]} />);

      expect(screen.getByText(/start a new conversation/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Search/Filter Tests
  // ===========================================================================

  describe("search functionality", () => {
    it("should filter sessions by search query", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SessionList sessions={mockSessions} />);

      const searchInput = screen.getByPlaceholderText(/search sessions/i);
      await user.type(searchInput, "First");

      expect(screen.getByText("First Session")).toBeInTheDocument();
      expect(screen.queryByText("Second Session")).not.toBeInTheDocument();
    });

    it("should show no results message when search has no matches", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SessionList sessions={mockSessions} />);

      const searchInput = screen.getByPlaceholderText(/search sessions/i);
      await user.type(searchInput, "nonexistent");

      expect(screen.getByText(/no sessions found/i)).toBeInTheDocument();
    });

    it("should clear search when clear button is clicked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SessionList sessions={mockSessions} />);

      const searchInput = screen.getByPlaceholderText(/search sessions/i);
      await user.type(searchInput, "First");

      const clearButton = screen.getByRole("button", { name: /clear search/i });
      await user.click(clearButton);

      expect(searchInput).toHaveValue("");
      expect(screen.getByText("Second Session")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Session Selection Tests
  // ===========================================================================

  describe("session selection", () => {
    it("should call onSelect when session is clicked", async () => {
      const onSelect = vi.fn();
      const user = userEvent.setup();
      renderWithProvider(
        <SessionList sessions={mockSessions} onSelect={onSelect} />,
      );

      await user.click(screen.getByText("First Session"));

      expect(onSelect).toHaveBeenCalledWith("session-1");
    });

    it("should highlight selected session", () => {
      renderWithProvider(
        <SessionList sessions={mockSessions} selectedId="session-2" />,
      );

      const selectedItem = screen.getByText("Second Session").closest("li");
      expect(selectedItem).toHaveAttribute("aria-current", "true");
    });
  });

  // ===========================================================================
  // Session Actions Tests
  // ===========================================================================

  describe("session actions", () => {
    it("should show actions menu on hover", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SessionList sessions={mockSessions} />);

      const sessionItem = screen.getByText("First Session").closest("li")!;
      await user.hover(sessionItem);

      expect(
        within(sessionItem).getByRole("button", { name: /session actions/i }),
      ).toBeInTheDocument();
    });

    it("should call onDelete when delete action is clicked", async () => {
      const onDelete = vi.fn();
      const user = userEvent.setup();
      renderWithProvider(
        <SessionList sessions={mockSessions} onDelete={onDelete} />,
      );

      const sessionItem = screen.getByText("First Session").closest("li")!;
      await user.hover(sessionItem);

      const actionsButton = within(sessionItem).getByRole("button", {
        name: /session actions/i,
      });
      await user.click(actionsButton);

      const deleteOption = screen.getByRole("menuitem", { name: /delete/i });
      await user.click(deleteOption);

      expect(onDelete).toHaveBeenCalledWith("session-1");
    });

    it("should call onRename when rename action is triggered", async () => {
      const onRename = vi.fn();
      const user = userEvent.setup();
      renderWithProvider(
        <SessionList sessions={mockSessions} onRename={onRename} />,
      );

      const sessionItem = screen.getByText("First Session").closest("li")!;
      await user.hover(sessionItem);

      const actionsButton = within(sessionItem).getByRole("button", {
        name: /session actions/i,
      });
      await user.click(actionsButton);

      const renameOption = screen.getByRole("menuitem", { name: /rename/i });
      await user.click(renameOption);

      // Enter new name - search input is visible, so get the one inside the session item
      const inputs = screen.getAllByRole("textbox");
      const renameInput = inputs.find(
        (input) => !input.hasAttribute("placeholder"),
      );
      await user.clear(renameInput!);
      await user.type(renameInput!, "New Name");
      await user.keyboard("{Enter}");

      expect(onRename).toHaveBeenCalledWith("session-1", "New Name");
    });
  });

  // ===========================================================================
  // Pin/Unpin Tests
  // ===========================================================================

  describe("pin functionality", () => {
    it("should show pin option in actions menu", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SessionList sessions={mockSessions} />);

      const sessionItem = screen.getByText("First Session").closest("li")!;
      await user.hover(sessionItem);

      const actionsButton = within(sessionItem).getByRole("button", {
        name: /session actions/i,
      });
      await user.click(actionsButton);

      expect(
        screen.getByRole("menuitem", { name: /pin/i }),
      ).toBeInTheDocument();
    });

    it("should show pinned sessions at top", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />, {
        pinnedSessions: ["session-3"],
      });

      const listItems = screen.getAllByRole("listitem");
      const firstItemText = listItems[0].textContent;
      expect(firstItemText).toContain("Third Session");
    });

    it("should show unpin option for pinned sessions", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SessionList sessions={mockSessions} />, {
        pinnedSessions: ["session-1"],
      });

      const sessionItem = screen.getByText("First Session").closest("li")!;
      await user.hover(sessionItem);

      const actionsButton = within(sessionItem).getByRole("button", {
        name: /session actions/i,
      });
      await user.click(actionsButton);

      expect(
        screen.getByRole("menuitem", { name: /unpin/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Keyboard Navigation Tests
  // ===========================================================================

  describe("keyboard navigation", () => {
    it("should navigate to next session with ArrowDown", async () => {
      const onSelect = vi.fn();
      const user = userEvent.setup();
      renderWithProvider(
        <SessionList
          sessions={mockSessions}
          selectedId="session-1"
          onSelect={onSelect}
        />,
      );

      const list = screen.getByRole("list");
      list.focus();

      await user.keyboard("{ArrowDown}");

      expect(onSelect).toHaveBeenCalledWith("session-2");
    });

    it("should navigate to previous session with ArrowUp", async () => {
      const onSelect = vi.fn();
      const user = userEvent.setup();
      renderWithProvider(
        <SessionList
          sessions={mockSessions}
          selectedId="session-2"
          onSelect={onSelect}
        />,
      );

      const list = screen.getByRole("list");
      list.focus();

      await user.keyboard("{ArrowUp}");

      expect(onSelect).toHaveBeenCalledWith("session-1");
    });

    it("should focus search with Cmd+K", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SessionList sessions={mockSessions} />);

      await user.keyboard("{Meta>}k{/Meta}");

      expect(screen.getByPlaceholderText(/search sessions/i)).toHaveFocus();
    });
  });

  // ===========================================================================
  // Create Session Tests
  // ===========================================================================

  describe("create session", () => {
    it("should call onCreate when new session button is clicked", async () => {
      const onCreate = vi.fn();
      const user = userEvent.setup();
      renderWithProvider(
        <SessionList sessions={mockSessions} onCreate={onCreate} />,
      );

      await user.click(screen.getByRole("button", { name: /new session/i }));

      expect(onCreate).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = renderWithProvider(
        <SessionList sessions={mockSessions} />,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper list role", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />);

      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it("should have proper listitem roles", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />);

      expect(screen.getAllByRole("listitem")).toHaveLength(3);
    });

    it("should have accessible search input", () => {
      renderWithProvider(<SessionList sessions={mockSessions} />);

      const searchInput = screen.getByPlaceholderText(/search sessions/i);
      expect(searchInput).toHaveAttribute("aria-label");
    });
  });
});
