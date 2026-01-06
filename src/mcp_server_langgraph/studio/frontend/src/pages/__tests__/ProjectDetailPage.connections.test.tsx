/**
 * ProjectDetailPage Connections Tests
 *
 * Tests for Connections Tab display and Add Connection button.
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
  mockEmptyProject,
  mockAddConnection as _mockAddConnection,
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

describe("ProjectDetailPage - Connections", () => {
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
  // CONNECTIONS TAB
  // ===========================================================================

  describe("Connections Tab", () => {
    it("should switch to connections tab when clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("MCP Server")).toBeInTheDocument();
      });
    });

    it("should display connection status", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("active")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // CONNECTIONS EMPTY STATE
  // ===========================================================================

  describe("Connections Empty State", () => {
    it("should show empty message when no connections", async () => {
      mockUseGetProjectQuery.mockReturnValue({
        data: mockEmptyProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText(/No connections yet/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // ADD CONNECTION BUTTON
  // ===========================================================================

  describe("Add Connection Button", () => {
    it("should open dialog when clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Connection")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Connection"));

      await waitFor(() => {
        expect(screen.getByText("Add New Connection")).toBeInTheDocument();
        expect(screen.getByLabelText("Connection Name")).toBeInTheDocument();
        expect(screen.getByLabelText("Connection Type")).toBeInTheDocument();
      });
    });

    it("should create connection when dialog is submitted", async () => {
      // Reset and configure the mock for this specific test
      const mockAddConnectionFn = vi
        .fn()
        .mockReturnValue({ unwrap: () => Promise.resolve() });
      mockUseAddProjectConnectionMutation.mockReturnValue([
        mockAddConnectionFn,
        { isLoading: false },
      ]);

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Connection")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Connection"));

      await waitFor(() => {
        expect(screen.getByLabelText("Connection Name")).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText("Connection Name"), {
        target: { value: "New MCP" },
      });
      fireEvent.change(screen.getByLabelText("Connection Type"), {
        target: { value: "mcp_server" },
      });
      fireEvent.click(screen.getByText("Add"));

      await waitFor(() => {
        expect(mockAddConnectionFn).toHaveBeenCalledWith(
          expect.objectContaining({
            project_id: "project-123",
            connection_type: "mcp_server",
            connection_name: "New MCP",
          }),
        );
      });
    });
  });
});
