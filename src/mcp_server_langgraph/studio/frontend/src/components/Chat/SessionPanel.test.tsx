/**
 * SessionPanel Tests
 *
 * TDD tests for the collapsible session panel in ChatPage.
 * Tests cover:
 * - Session list display
 * - New session creation
 * - Session selection
 * - Collapsible behavior
 * - Empty state
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  waitFor,
} from "@testing-library/react";
import { SessionPanel } from "./SessionPanel";

// Mock session data
const mockSessions = [
  {
    id: "session-1",
    name: "Chat 1",
    createdAt: "2024-01-01T10:00:00Z",
    updatedAt: "2024-01-01T12:00:00Z",
    messageCount: 5,
  },
  {
    id: "session-2",
    name: "Chat 2",
    createdAt: "2024-01-02T10:00:00Z",
    updatedAt: "2024-01-02T11:00:00Z",
    messageCount: 3,
  },
  {
    id: "session-3",
    name: "Chat 3",
    createdAt: "2024-01-03T10:00:00Z",
    updatedAt: "2024-01-03T10:30:00Z",
    messageCount: 0,
  },
];

describe("SessionPanel", () => {
  const mockOnSessionSelect = vi.fn();
  const mockOnNewSession = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Session List Display", () => {
    it("should render session list", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.getByText("Chat 1")).toBeInTheDocument();
      expect(screen.getByText("Chat 2")).toBeInTheDocument();
      expect(screen.getByText("Chat 3")).toBeInTheDocument();
    });

    it("should highlight current session", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      // Find the session item container (div) that has the bg-blue class
      const session1Button = screen.getByText("Chat 1").closest("button");
      const session1Container = session1Button?.parentElement;
      expect(session1Container?.className).toMatch(/bg-blue/);
    });

    it("should show message count for each session", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.getByText("5 messages")).toBeInTheDocument();
      expect(screen.getByText("3 messages")).toBeInTheDocument();
      expect(screen.getByText("0 messages")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no sessions", () => {
      render(
        <SessionPanel
          sessions={[]}
          currentSessionId={null}
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.getByText("No sessions yet")).toBeInTheDocument();
    });

    it("should show New Session button in empty state", () => {
      render(
        <SessionPanel
          sessions={[]}
          currentSessionId={null}
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.getByText("New Session")).toBeInTheDocument();
    });
  });

  describe("Session Creation", () => {
    it("should render New Session button", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.getByText("New")).toBeInTheDocument();
    });

    it("should call onNewSession when New button is clicked", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      fireEvent.click(screen.getByText("New"));
      expect(mockOnNewSession).toHaveBeenCalled();
    });
  });

  describe("Session Selection", () => {
    it("should call onSessionSelect when session is clicked", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      fireEvent.click(screen.getByText("Chat 2"));
      expect(mockOnSessionSelect).toHaveBeenCalledWith("session-2");
    });

    it("should not call onSessionSelect when clicking current session", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      fireEvent.click(screen.getByText("Chat 1"));
      expect(mockOnSessionSelect).not.toHaveBeenCalled();
    });
  });

  describe("Collapsible Behavior", () => {
    it("should show collapse toggle button", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      // Look for chevron icon or collapse button
      const collapseButton = screen.getByRole("button", { name: /collapse/i });
      expect(collapseButton).toBeInTheDocument();
    });

    it("should collapse panel when toggle is clicked", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      const collapseButton = screen.getByRole("button", { name: /collapse/i });
      fireEvent.click(collapseButton);

      // Session names should be hidden when collapsed
      expect(screen.queryByText("Chat 2")).not.toBeInTheDocument();
      expect(screen.queryByText("Chat 3")).not.toBeInTheDocument();
    });

    it("should expand panel when toggle is clicked again", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      const collapseButton = screen.getByRole("button", { name: /collapse/i });

      // Collapse
      fireEvent.click(collapseButton);
      expect(screen.queryByText("Chat 2")).not.toBeInTheDocument();

      // Find expand button and click it
      const expandButton = screen.getByRole("button", { name: /expand/i });
      fireEvent.click(expandButton);

      // Wait for component to re-render, then check again
      expect(screen.queryByText("Chat 2")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading skeletons when loading", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          isLoading={true}
        />,
      );

      // Should show skeleton placeholders
      expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
    });

    it("should show multiple skeleton items when loading", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          isLoading={true}
        />,
      );

      // Should have multiple skeleton items
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(1);
    });

    it("should not show session list when loading", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          isLoading={true}
        />,
      );

      expect(screen.queryByText("Chat 1")).not.toBeInTheDocument();
    });
  });

  describe("Recent Sessions Limit", () => {
    it("should show only 5 most recent sessions by default", () => {
      const manySessions = Array.from({ length: 10 }, (_, i) => ({
        id: `session-${i}`,
        name: `Chat ${i}`,
        createdAt: `2024-01-0${i + 1}T10:00:00Z`,
        updatedAt: `2024-01-0${i + 1}T10:00:00Z`,
        messageCount: i,
      }));

      render(
        <SessionPanel
          sessions={manySessions}
          currentSessionId="session-0"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      // Should show 5 sessions + "See All" link
      expect(screen.getByText(/See All/)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA labels for buttons", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.getByRole("button", { name: /new/i })).toBeInTheDocument();
    });

    it("should have navigation role for panel", () => {
      const { container } = render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(
        container.querySelector('[role="navigation"]'),
      ).toBeInTheDocument();
    });
  });

  describe("Search Functionality", () => {
    it("should render search input when enableSearch is true", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableSearch={true}
        />,
      );

      expect(screen.getByRole("searchbox")).toBeInTheDocument();
    });

    it("should have search placeholder text", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableSearch={true}
        />,
      );

      const searchInput = screen.getByRole("searchbox");
      expect(searchInput).toHaveAttribute("placeholder");
      expect(searchInput.getAttribute("placeholder")).toMatch(/search/i);
    });

    it("should call onSearch callback when typing", () => {
      const mockOnSearch = vi.fn();
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableSearch={true}
          onSearch={mockOnSearch}
        />,
      );

      const searchInput = screen.getByRole("searchbox");
      fireEvent.change(searchInput, { target: { value: "test query" } });

      expect(searchInput).toHaveValue("test query");
      expect(mockOnSearch).toHaveBeenCalledWith("test query");
    });

    it("should not render search input by default", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    });
  });

  describe("Status Filter", () => {
    it("should render status filter when enableStatusFilter is true", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableStatusFilter={true}
        />,
      );

      expect(
        screen.getByRole("button", { name: /^all$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^active$/i }),
      ).toBeInTheDocument();
    });

    it('should have "All" button selected by default', () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableStatusFilter={true}
        />,
      );

      const allButton = screen.getByRole("button", { name: /^all$/i });
      expect(allButton).toHaveAttribute("aria-pressed", "true");
    });

    it("should call onStatusChange callback when status is changed", () => {
      const mockOnStatusChange = vi.fn();
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableStatusFilter={true}
          onStatusChange={mockOnStatusChange}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /^active$/i }));

      expect(mockOnStatusChange).toHaveBeenCalledWith("active");
    });

    it("should not render status filter by default", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(
        screen.queryByRole("button", { name: /^all$/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Cursor Pagination", () => {
    it("should render Load More button when hasMore is true", () => {
      const mockOnLoadMore = vi.fn();
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          hasMore={true}
          onLoadMore={mockOnLoadMore}
        />,
      );

      expect(
        screen.getByRole("button", { name: /load more/i }),
      ).toBeInTheDocument();
    });

    it("should call onLoadMore callback when Load More is clicked", () => {
      const mockOnLoadMore = vi.fn();
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          hasMore={true}
          onLoadMore={mockOnLoadMore}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /load more/i }));

      expect(mockOnLoadMore).toHaveBeenCalled();
    });

    it("should show loading state on Load More button when loadingMore is true", () => {
      const mockOnLoadMore = vi.fn();
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          hasMore={true}
          loadingMore={true}
          onLoadMore={mockOnLoadMore}
        />,
      );

      const loadMoreButton = screen.getByRole("button", { name: /loading/i });
      expect(loadMoreButton).toBeDisabled();
    });

    it("should not render Load More button when hasMore is false", () => {
      const mockOnLoadMore = vi.fn();
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          hasMore={false}
          onLoadMore={mockOnLoadMore}
        />,
      );

      expect(
        screen.queryByRole("button", { name: /load more/i }),
      ).not.toBeInTheDocument();
    });

    it("should show session count when using pagination", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          totalCount={50}
          hasMore={true}
        />,
      );

      expect(screen.getByText(/3 of 50/i)).toBeInTheDocument();
    });
  });

  describe("Bulk Selection", () => {
    const mockOnBulkDelete = vi.fn();

    it("should render checkboxes when enableBulkSelect is true", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // 3 session checkboxes + 1 select all
      expect(checkboxes.length).toBe(4);
    });

    it("should not render checkboxes by default", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
        />,
      );

      expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    });

    it("should show select all checkbox", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      expect(screen.getByLabelText(/select all/i)).toBeInTheDocument();
    });

    it("should select session when checkbox is clicked", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // Click the first session checkbox (skip select all)
      fireEvent.click(checkboxes[1]);

      expect(checkboxes[1]).toBeChecked();
    });

    it("should select all when select all checkbox is clicked", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      const selectAllCheckbox = screen.getByLabelText(/select all/i);
      fireEvent.click(selectAllCheckbox);

      const checkboxes = screen.getAllByRole("checkbox");
      // All checkboxes should be checked
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeChecked();
      });
    });

    it("should show bulk action bar when sessions are selected", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      // Select a session
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);

      expect(
        screen.getByRole("toolbar", { name: /bulk actions/i }),
      ).toBeInTheDocument();
      expect(screen.getByText(/1 selected/i)).toBeInTheDocument();
    });

    it("should update selected count as sessions are selected", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);
      fireEvent.click(checkboxes[2]);

      expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
    });

    it("should clear selection when clear button is clicked", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      // Select sessions
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);
      fireEvent.click(checkboxes[2]);

      // Click clear selection
      fireEvent.click(screen.getByLabelText(/clear selection/i));

      // No sessions should be selected
      expect(screen.queryByText(/selected/i)).not.toBeInTheDocument();
    });

    it("should call onBulkDelete when delete is confirmed", async () => {
      // Create a resolving mock for the async delete operation
      mockOnBulkDelete.mockResolvedValue(undefined);

      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      // Select sessions
      const checkboxes = screen.getAllByRole("checkbox");
      await act(async () => {
        fireEvent.click(checkboxes[1]);
      });
      await act(async () => {
        fireEvent.click(checkboxes[2]);
      });

      // Click delete
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      });

      // Confirm - this triggers an async operation
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
      });

      // Wait for async operation to complete and state to update
      await waitFor(() => {
        expect(mockOnBulkDelete).toHaveBeenCalledWith([
          "session-3",
          "session-2",
        ]);
      });
    });

    it("should hide bulk action bar when no sessions selected", () => {
      render(
        <SessionPanel
          sessions={mockSessions}
          currentSessionId="session-1"
          onSessionSelect={mockOnSessionSelect}
          onNewSession={mockOnNewSession}
          enableBulkSelect={true}
          onBulkDelete={mockOnBulkDelete}
        />,
      );

      // No selections initially
      expect(
        screen.queryByRole("toolbar", { name: /bulk actions/i }),
      ).not.toBeInTheDocument();
    });
  });
});
