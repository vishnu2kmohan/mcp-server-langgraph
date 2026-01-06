/**
 * ProjectDetailPage Cost Tests
 *
 * Tests for Cost Tab display, real data, and error handling.
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
  mockCostSummaryData as _mockCostSummaryData,
  mockCostByModelData as _mockCostByModelData,
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

describe("ProjectDetailPage - Cost", () => {
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
  // COST TAB LINKS
  // ===========================================================================

  describe("Cost Tab Links", () => {
    it("should have link to full cost page", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        // Component shows "View detailed cost breakdown →"
        const viewFullLink = screen.getByText(/View detailed cost breakdown/i);
        expect(viewFullLink).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // COST TAB REAL DATA
  // ===========================================================================

  describe("CostTab Real Data", () => {
    it("should display total cost from RTK Query", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText(/\$25\.50/)).toBeInTheDocument();
      });
    });

    it("should display token counts from RTK Query", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        // Component shows total tokens (prompt_tokens + completion_tokens = 15,000)
        expect(screen.getByText(/15,000/)).toBeInTheDocument();
      });
    });

    it("should display session count in cost summary", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        // Component shows session count as just a number (15)
        // "Sessions" appears in both tab and card, so we just verify the count
        expect(screen.getByText("15")).toBeInTheDocument();
      });
    });

    it("should display cost by model breakdown", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("gpt-4")).toBeInTheDocument();
        expect(screen.getByText("gpt-3.5-turbo")).toBeInTheDocument();
      });
    });

    it("should display cost amounts per model", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText(/\$20\.00/)).toBeInTheDocument(); // gpt-4 cost
        expect(screen.getByText(/\$5\.50/)).toBeInTheDocument(); // gpt-3.5-turbo cost
      });
    });

    it("should display token counts per model", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText(/12,000/)).toBeInTheDocument(); // gpt-4 tokens
        expect(screen.getByText(/8,000/)).toBeInTheDocument(); // gpt-3.5-turbo tokens
      });
    });
  });

  // ===========================================================================
  // COST TAB ERROR HANDLING
  // ===========================================================================

  describe("CostTab Error Handling", () => {
    it("should show error message when RTK Query returns error", async () => {
      mockUseGetProjectCostSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });

    it("should show retry button when RTK Query returns error", async () => {
      mockUseGetProjectCostSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });
    });

    it("should refetch when retry button is clicked", async () => {
      const mockCostRefetch = vi.fn();

      mockUseGetProjectCostSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: mockCostRefetch,
      });

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Retry/i }));

      expect(mockCostRefetch).toHaveBeenCalled();
    });
  });
});
