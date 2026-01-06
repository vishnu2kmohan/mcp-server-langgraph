/**
 * ProjectDetailPage Sessions Tests
 *
 * Tests for Sessions Tab display, empty states, New Session button, and Remove Session.
 * Split from ProjectDetailPage.test.tsx for memory optimization.
 *
 * @see ProjectDetailPage.setup.ts for shared mocks and utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, waitFor, cleanup } from "@testing-library/react";

// Import shared setup
import {
  resetAllMocks,
  setupDefaultMocks,
  mockRefetch,
  mockProject,
  mockEmptyProject,
  renderWithRouter,
} from "./ProjectDetailPage.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetFeatureFlagsQuery: vi.fn(),
    useGetProjectQuery: vi.fn(),
    useGetProjectObservabilityQuery: vi.fn(),
    useGetProjectLogsQuery: vi.fn(),
    useGetProjectAlertsQuery: vi.fn(),
    useGetProjectCostSummaryQuery: vi.fn(),
    useGetProjectCostByModelQuery: vi.fn(),
    useAddProjectMemberMutation: vi.fn(),
    useRemoveProjectMemberMutation: vi.fn(),
    useAddProjectConnectionMutation: vi.fn(),
  };
});

// Import mocked hooks
import {
  useGetFeatureFlagsQuery,
  useGetProjectQuery,
  useGetProjectObservabilityQuery,
  useGetProjectLogsQuery,
  useGetProjectAlertsQuery,
  useGetProjectCostSummaryQuery,
  useGetProjectCostByModelQuery,
  useAddProjectMemberMutation,
  useRemoveProjectMemberMutation,
  useAddProjectConnectionMutation,
} from "../../api";

// Cast for type safety
const mockUseGetFeatureFlagsQuery = useGetFeatureFlagsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectQuery = useGetProjectQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectObservabilityQuery =
  useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectLogsQuery = useGetProjectLogsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectAlertsQuery = useGetProjectAlertsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseGetProjectCostSummaryQuery =
  useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>;
const mockUseGetProjectCostByModelQuery =
  useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>;
const mockUseAddProjectMemberMutation =
  useAddProjectMemberMutation as ReturnType<typeof vi.fn>;
const mockUseRemoveProjectMemberMutation =
  useRemoveProjectMemberMutation as ReturnType<typeof vi.fn>;
const mockUseAddProjectConnectionMutation =
  useAddProjectConnectionMutation as ReturnType<typeof vi.fn>;

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("ProjectDetailPage - Sessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
    setupDefaultMocks({
      useGetFeatureFlagsQuery: mockUseGetFeatureFlagsQuery,
      useGetProjectQuery: mockUseGetProjectQuery,
      useGetProjectObservabilityQuery: mockUseGetProjectObservabilityQuery,
      useGetProjectLogsQuery: mockUseGetProjectLogsQuery,
      useGetProjectAlertsQuery: mockUseGetProjectAlertsQuery,
      useGetProjectCostSummaryQuery: mockUseGetProjectCostSummaryQuery,
      useGetProjectCostByModelQuery: mockUseGetProjectCostByModelQuery,
      useAddProjectMemberMutation: mockUseAddProjectMemberMutation,
      useRemoveProjectMemberMutation: mockUseRemoveProjectMemberMutation,
      useAddProjectConnectionMutation: mockUseAddProjectConnectionMutation,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // SESSIONS TAB
  // ===========================================================================

  describe("Sessions Tab", () => {
    it("should display sessions list", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Session One")).toBeInTheDocument();
        expect(screen.getByText("Session Two")).toBeInTheDocument();
        expect(screen.getByText("Session Three")).toBeInTheDocument();
      });
    });

    it("should display message count for sessions", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText(/10 messages/i)).toBeInTheDocument();
        expect(screen.getByText(/5 messages/i)).toBeInTheDocument();
      });
    });

    it("should navigate to session when clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Session One")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Session One"));

      await waitFor(() => {
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // EMPTY STATES
  // ===========================================================================

  describe("Sessions Empty State", () => {
    it("should show empty message when no sessions", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: mockEmptyProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText(/No sessions yet/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // NEW SESSION BUTTON
  // ===========================================================================

  describe("New Session Button", () => {
    it("should open dialog when clicked", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("New Session"));

      await waitFor(() => {
        expect(screen.getByText("Create New Session")).toBeInTheDocument();
        expect(screen.getByLabelText("Session Name")).toBeInTheDocument();
      });
    });

    it("should create session when dialog is submitted", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "POST" && url.includes("/sessions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                session_count: 4,
                sessions: [
                  ...mockProject.sessions,
                  {
                    id: "sess-new",
                    name: "New Test Session",
                    message_count: 0,
                  },
                ],
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProject),
        });
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("New Session"));

      await waitFor(() => {
        expect(screen.getByLabelText("Session Name")).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText("Session Name"), {
        target: { value: "New Test Session" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/projects/project-123/sessions"),
          expect.objectContaining({
            method: "POST",
          }),
        );
      });
    });

    it("should close dialog when cancel is clicked", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("New Session"));

      await waitFor(() => {
        expect(screen.getByText("Create New Session")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Cancel"));

      await waitFor(() => {
        expect(
          screen.queryByText("Create New Session"),
        ).not.toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // REMOVE SESSION
  // ===========================================================================

  describe("Remove Session", () => {
    it("should have remove button on each session", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Session One")).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByLabelText(/remove session/i);
      expect(removeButtons.length).toBe(3);
    });

    it("should call DELETE API when remove button is clicked", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "DELETE" && url.includes("/sessions/sess-1")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                session_count: 2,
                sessions: mockProject.sessions.filter((s) => s.id !== "sess-1"),
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProject),
        });
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Session One")).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByLabelText(/remove session/i);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining(
            "/api/v1/projects/project-123/sessions/sess-1",
          ),
          expect.objectContaining({
            method: "DELETE",
          }),
        );
      });
    });
  });
});
