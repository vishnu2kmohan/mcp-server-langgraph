/**
 * ProjectDetailPage Core Tests
 *
 * Tests for Loading, Error, Project Details display, Tab Navigation, and RTK Query integration.
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

describe("ProjectDetailPage - Core", () => {
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
  // LOADING STATE
  // ===========================================================================

  describe("Loading State", () => {
    it("should show loading spinner while fetching project", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: null,
        isLoading: true,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      expect(screen.getByText("Loading project...")).toBeInTheDocument();
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // ERROR STATE
  // ===========================================================================

  describe("Error State", () => {
    it("should show error message when fetch fails", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 500, data: "Internal Server Error" },
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
      });
    });

    it("should show 'project not found' for 404 errors", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 404, data: "Not Found" },
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
      });
    });

    it("should have back to projects button on error", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 500, data: "Internal Server Error" },
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Back to Projects")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // PROJECT DETAILS DISPLAY
  // ===========================================================================

  describe("Project Details Display", () => {
    it("should display project name", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });
    });

    it("should display project description", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByText("A test project for testing"),
        ).toBeInTheDocument();
      });
    });

    it("should display all tabs with correct counts", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        // Use getAllByText since tabs and content both show these labels
        expect(screen.getAllByText("Sessions").length).toBeGreaterThanOrEqual(
          1,
        );
        expect(screen.getAllByText("Workflows").length).toBeGreaterThanOrEqual(
          1,
        );
        expect(
          screen.getAllByText("Connections").length,
        ).toBeGreaterThanOrEqual(1);
        expect(screen.getByText("Observability")).toBeInTheDocument();
        expect(screen.getByText("Cost")).toBeInTheDocument();
        expect(screen.getByText("Members")).toBeInTheDocument();
      });

      // Check counts are displayed (may appear multiple times for sessions/members)
      expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1); // session_count & members count
      expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1); // workflow_count
      expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1); // connection_count
    });

    it("should have refresh button", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByTestId("project-refresh-button"),
        ).toBeInTheDocument();
      });
    });

    it("should have settings button", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByTitle("Settings")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // TAB NAVIGATION
  // ===========================================================================

  describe("Tab Navigation", () => {
    it("should show Sessions tab by default", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Sessions/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show Workflows tab", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Workflows/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show Connections tab", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Connections/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show Observability tab", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Observability/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show Cost tab", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Cost/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show Members tab", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Members/i }),
        ).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // BACK NAVIGATION
  // ===========================================================================

  describe("Back Navigation", () => {
    it("should navigate back to projects list", async () => {
      // Mock error state to show "Back to Projects" button
      mockUseGetProjectQuery.mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 500, data: "Error" },
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Back to Projects")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Back to Projects"));

      await waitFor(() => {
        expect(screen.getByText("Projects List")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // RTK QUERY INTEGRATION
  // ===========================================================================

  describe("RTK Query Integration", () => {
    it("should call useGetProjectQuery with project ID", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(mockUseGetProjectQuery).toHaveBeenCalledWith(
          "project-123",
          expect.any(Object),
        );
      });
    });

    it("should show loading state from RTK Query", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: null,
        isLoading: true,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      expect(screen.getByText("Loading project...")).toBeInTheDocument();
    });

    it("should show error state from RTK Query", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 500, data: "Internal Server Error" },
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
        expect(screen.getByText("Back to Projects")).toBeInTheDocument();
      });
    });

    it("should call refetch when refresh button is clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("project-refresh-button"));

      expect(mockRefetch).toHaveBeenCalled();
    });

    it("should show loading indicator when refetching", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: mockProject,
        isLoading: false,
        isFetching: true,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      const refreshButton = screen.getByTestId("project-refresh-button");
      expect(refreshButton.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should display project data from RTK Query", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
        expect(
          screen.getByText("A test project for testing"),
        ).toBeInTheDocument();
      });
    });
  });
});
