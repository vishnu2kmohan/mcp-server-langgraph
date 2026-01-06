/**
 * ProjectDetailPage Members Tests
 *
 * Tests for Members Tab display, Add Member button, and Remove Member.
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

describe("ProjectDetailPage - Members", () => {
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
  // MEMBERS TAB
  // ===========================================================================

  describe("Members Tab", () => {
    it("should switch to members tab when clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-1")).toBeInTheDocument();
        expect(screen.getByText("user-2")).toBeInTheDocument();
        expect(screen.getByText("user-3")).toBeInTheDocument();
      });
    });

    it("should display member roles", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("owner")).toBeInTheDocument();
        expect(screen.getByText("editor")).toBeInTheDocument();
        expect(screen.getByText("viewer")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // MEMBERS EMPTY STATE
  // ===========================================================================

  describe("Members Empty State", () => {
    it("should show empty message when no members", async () => {
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

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText(/No members/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // ADD MEMBER BUTTON
  // ===========================================================================

  describe("Add Member Button", () => {
    it("should open dialog when clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Member")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Member"));

      await waitFor(() => {
        expect(screen.getByText("Add Team Member")).toBeInTheDocument();
        expect(screen.getByLabelText("User ID")).toBeInTheDocument();
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });
    });

    it("should add member when dialog is submitted", async () => {
      // Configure the mock for this specific test
      const mockAddMemberFn = vi
        .fn()
        .mockReturnValue({ unwrap: () => Promise.resolve() });
      mockUseAddProjectMemberMutation.mockReturnValue([
        mockAddMemberFn,
        { isLoading: false },
      ]);

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Member")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Member"));

      await waitFor(() => {
        expect(screen.getByLabelText("User ID")).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-new" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "editor" },
      });
      fireEvent.click(screen.getByText("Add"));

      await waitFor(() => {
        expect(mockAddMemberFn).toHaveBeenCalledWith(
          expect.objectContaining({
            project_id: "project-123",
            user_id: "user-new",
            role: "editor",
          }),
        );
      });
    });

    it("should show role options: editor, viewer, executor", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Member")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Member"));

      await waitFor(() => {
        const roleSelect = screen.getByLabelText("Role");
        expect(roleSelect).toBeInTheDocument();
        expect(
          screen.getByRole("option", { name: "Editor" }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("option", { name: "Viewer" }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("option", { name: "Executor" }),
        ).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // REMOVE MEMBER
  // ===========================================================================

  describe("Remove Member", () => {
    it("should have remove button on non-owner members", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-1")).toBeInTheDocument();
      });

      // Should have remove buttons for non-owner members (2 out of 3)
      const removeButtons = screen.getAllByLabelText(/remove member/i);
      expect(removeButtons.length).toBe(2);
    });

    it("should call RTK Query mutation when remove button is clicked", async () => {
      // Configure the mock for this specific test
      const mockRemoveMemberFn = vi
        .fn()
        .mockReturnValue({ unwrap: () => Promise.resolve() });
      mockUseRemoveProjectMemberMutation.mockReturnValue([
        mockRemoveMemberFn,
        { isLoading: false },
      ]);

      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-2")).toBeInTheDocument();
      });

      // Click remove button (first non-owner member)
      const removeButtons = screen.getAllByLabelText(/remove member/i);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(mockRemoveMemberFn).toHaveBeenCalledWith(
          expect.objectContaining({
            project_id: "project-123",
            user_id: "user-2",
          }),
        );
      });
    });

    it("should not show remove button for owner", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-1")).toBeInTheDocument();
        expect(screen.getByText("owner")).toBeInTheDocument();
      });

      // Owner row should not have remove button
      const ownerRow = screen
        .getByText("user-1")
        .closest('div[class*="rounded-lg"]');
      expect(ownerRow?.querySelector('[aria-label*="remove"]')).toBeNull();
    });
  });
});
