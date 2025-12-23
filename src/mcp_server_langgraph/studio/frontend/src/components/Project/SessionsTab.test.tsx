/**
 * SessionsTab Component Tests
 *
 * TDD tests for the project sessions tab component.
 * Features:
 * - Session list display
 * - Create session dialog
 * - Remove session
 * - Bulk selection with BulkActionBar
 * - Navigation to chat
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { SessionsTab } from "./SessionsTab";

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock fetch
const mockFetch = vi.fn();

// Mock session data
const mockSessions = [
  {
    id: "sess-1",
    name: "Session One",
    message_count: 10,
    created_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "sess-2",
    name: "Session Two",
    message_count: 5,
    created_at: "2025-01-02T00:00:00Z",
  },
  { id: "sess-3", name: "Session Three", message_count: 0, created_at: null },
];

describe("SessionsTab", () => {
  const mockOnRefresh = vi.fn();
  const defaultProps = {
    sessions: mockSessions,
    projectId: "project-123",
    onRefresh: mockOnRefresh,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    // Default mock: return ok for all requests
    // First call (create session) returns session object, rest return ok: true
    mockFetch.mockImplementation((url: string) => {
      if (url === "/api/v1/sessions") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              session_id: "new-session-id",
              name: "New Test Session",
            }),
        });
      }
      return Promise.resolve({ ok: true });
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Session List Display", () => {
    it("should render session list", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      expect(screen.getByText("Session One")).toBeInTheDocument();
      expect(screen.getByText("Session Two")).toBeInTheDocument();
      expect(screen.getByText("Session Three")).toBeInTheDocument();
    });

    it("should show message count for each session", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      expect(screen.getByText("10 messages")).toBeInTheDocument();
      expect(screen.getByText("5 messages")).toBeInTheDocument();
      expect(screen.getByText("0 messages")).toBeInTheDocument();
    });

    it("should show empty state when no sessions", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} sessions={[]} />
        </MemoryRouter>,
      );

      expect(screen.getByText(/no sessions yet/i)).toBeInTheDocument();
    });

    it("should have New Session button", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      expect(
        screen.getByRole("button", { name: /new session/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Navigation", () => {
    it("should navigate to chat when session is clicked", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      fireEvent.click(screen.getByText("Session One"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/chat?session=sess-1");
    });
  });

  describe("Create Session", () => {
    it("should open dialog when New Session is clicked", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      fireEvent.click(screen.getByRole("button", { name: /new session/i }));

      expect(screen.getByText("Create New Session")).toBeInTheDocument();
    });

    it("should call API and refresh when session is created", async () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      fireEvent.click(screen.getByRole("button", { name: /new session/i }));

      const input = screen.getByLabelText("Session Name");
      fireEvent.change(input, { target: { value: "New Test Session" } });

      fireEvent.click(screen.getByRole("button", { name: /^create$/i }));

      // Step 1: Create session globally first
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/sessions",
          expect.objectContaining({
            method: "POST",
            body: JSON.stringify({ name: "New Test Session" }),
          }),
        );
      });

      // Step 2: Add session to project
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/projects/project-123/sessions"),
          expect.objectContaining({ method: "POST" }),
        );
      });

      await waitFor(() => {
        expect(mockOnRefresh).toHaveBeenCalled();
      });
    });
  });

  describe("Remove Session", () => {
    it("should have remove button for each session", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      const removeButtons = screen.getAllByRole("button", {
        name: /remove session/i,
      });
      expect(removeButtons).toHaveLength(3);
    });

    it("should call API and refresh when session is removed", async () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      const removeButtons = screen.getAllByRole("button", {
        name: /remove session/i,
      });
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/projects/project-123/sessions/sess-1",
          expect.objectContaining({ method: "DELETE" }),
        );
      });

      await waitFor(() => {
        expect(mockOnRefresh).toHaveBeenCalled();
      });
    });

    it("should not navigate when remove button is clicked", async () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      const removeButtons = screen.getAllByRole("button", {
        name: /remove session/i,
      });
      fireEvent.click(removeButtons[0]);

      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe("Bulk Selection", () => {
    it("should render checkboxes for each session", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // 3 session checkboxes + 1 select all
      expect(checkboxes.length).toBe(4);
    });

    it("should have select all checkbox", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      expect(screen.getByLabelText(/select all/i)).toBeInTheDocument();
    });

    it("should select all when select all is clicked", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      const selectAllCheckbox = screen.getByLabelText(/select all/i);
      fireEvent.click(selectAllCheckbox);

      const checkboxes = screen.getAllByRole("checkbox");
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeChecked();
      });
    });

    it("should show bulk action bar when sessions are selected", () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]); // First session checkbox

      expect(
        screen.getByRole("toolbar", { name: /bulk actions/i }),
      ).toBeInTheDocument();
      expect(screen.getByText(/1 selected/i)).toBeInTheDocument();
    });

    it("should bulk delete sessions when confirmed", async () => {
      render(
        <MemoryRouter>
          <SessionsTab {...defaultProps} />
        </MemoryRouter>,
      );

      // Select two sessions
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);
      fireEvent.click(checkboxes[2]);

      // Click delete
      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      // Confirm
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      await waitFor(() => {
        expect(mockOnRefresh).toHaveBeenCalled();
      });
    });
  });
});
