/**
 * ProjectDetailPage Workflows Tests
 *
 * Tests for Workflows Tab display, New Workflow button, and Remove Workflow.
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

describe("ProjectDetailPage - Workflows", () => {
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
  // WORKFLOWS TAB
  // ===========================================================================

  describe("Workflows Tab", () => {
    it("should switch to workflows tab when clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("Workflow One")).toBeInTheDocument();
        expect(screen.getByText("Workflow Two")).toBeInTheDocument();
      });
    });

    it("should navigate to workflow when clicked", async () => {
      renderWithRouter("project-123", {}, mockUseGetFeatureFlagsQuery);

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("Workflow One")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Workflow One"));

      await waitFor(() => {
        expect(screen.getByText("Workflows Page")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // WORKFLOWS EMPTY STATE
  // ===========================================================================

  describe("Workflows Empty State", () => {
    it("should show empty message when no workflows", async () => {
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

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText(/No workflows yet/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // NEW WORKFLOW BUTTON
  // ===========================================================================

  describe("New Workflow Button", () => {
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
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("New Workflow")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("New Workflow"));

      await waitFor(() => {
        expect(screen.getByText("Create New Workflow")).toBeInTheDocument();
        expect(screen.getByLabelText("Workflow Name")).toBeInTheDocument();
      });
    });

    it("should create workflow when dialog is submitted", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "POST" && url.includes("/workflows")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                workflow_count: 3,
                workflows: [
                  ...mockProject.workflows,
                  { id: "wf-new", name: "New Test Workflow", created_at: null },
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
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("New Workflow")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("New Workflow"));

      await waitFor(() => {
        expect(screen.getByLabelText("Workflow Name")).toBeInTheDocument();
      });

      fireEvent.change(screen.getByLabelText("Workflow Name"), {
        target: { value: "New Test Workflow" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/projects/project-123/workflows"),
          expect.objectContaining({
            method: "POST",
          }),
        );
      });
    });
  });

  // ===========================================================================
  // REMOVE WORKFLOW
  // ===========================================================================

  describe("Remove Workflow", () => {
    it("should have remove button on each workflow", async () => {
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
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("Workflow One")).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByLabelText(/remove workflow/i);
      expect(removeButtons.length).toBe(2);
    });

    it("should call DELETE API when remove button is clicked", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "DELETE" && url.includes("/workflows/wf-1")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                workflow_count: 1,
                workflows: mockProject.workflows.filter((w) => w.id !== "wf-1"),
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
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("Workflow One")).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByLabelText(/remove workflow/i);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining(
            "/api/v1/projects/project-123/workflows/wf-1",
          ),
          expect.objectContaining({
            method: "DELETE",
          }),
        );
      });
    });
  });
});
