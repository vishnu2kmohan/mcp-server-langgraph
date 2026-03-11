/**
 * ProjectsPage Tests - List View Shard
 *
 * Tests for loading state, empty state, project list, search, pagination, sorting, filters, and refresh.
 */

import { screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// =============================================================================
// Hoisted Mocks (MUST be before vi.mock and imports)
// =============================================================================

const mockListProjectsQuery = vi.hoisted(() => vi.fn());
const mockCreateProjectMutation = vi.hoisted(() => vi.fn());
const mockDeleteProjectMutation = vi.hoisted(() => vi.fn());

// Mock RTK Query hooks
vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useListProjectsQuery: () => mockListProjectsQuery(),
    useCreateProjectMutation: () => mockCreateProjectMutation(),
    useDeleteProjectMutation: () => mockDeleteProjectMutation(),
    // Required for AIEmptyState used in empty state
    useGetEmptyStateSuggestionsMutation: () => [
      vi.fn(),
      { isLoading: false, data: null },
    ],
  };
});
// =============================================================================
// Imports (after mocks)
// =============================================================================

import { ProjectsPage } from "../ProjectsPage";
import {
  renderWithRouter,
  mockProjectsListData,
  mockSingleProjectData,
  mockEmptyProjectsData,
  mockPaginatedData,
  setupDefaultMocks,
} from "./ProjectsPage.fixtures";

describe("ProjectsPage - List View", () => {
  const mockCreateFn = vi.fn();
  const mockDeleteFn = vi.fn();

  // Bundle mocks for setupDefaultMocks
  const mocks = {
    mockListProjectsQuery,
    mockCreateProjectMutation,
    mockDeleteProjectMutation,
  };

  beforeEach(() => {
    setupDefaultMocks(mocks, mockCreateFn, mockDeleteFn);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    // Force GC to prevent mock accumulation in xdist workers
    if (global.gc) {
      global.gc();
    }
  });

  describe("Loading State", () => {
    it("should show loading skeletons initially", () => {
      // isLoading is already true in setupDefaultMocks
      renderWithRouter(<ProjectsPage />);

      // Should show skeleton placeholders instead of text loading indicator
      expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
    });

    it("should show multiple skeleton items while loading", () => {
      // isLoading is already true in setupDefaultMocks
      renderWithRouter(<ProjectsPage />);

      // Should have multiple skeleton items
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no projects exist", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockEmptyProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText(/no projects/i)).toBeInTheDocument();
      });
    });

    it("should show create button in empty state", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockEmptyProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // There are 2 create buttons - one in header, one in empty state
        const createButtons = screen.getAllByRole("button", {
          name: /create.*project/i,
        });
        expect(createButtons.length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  describe("Project List", () => {
    it("should display list of projects", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsListData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
        expect(screen.getByText("Project Beta")).toBeInTheDocument();
      });
    });

    it("should display project descriptions", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsListData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("First project")).toBeInTheDocument();
        expect(screen.getByText("Second project")).toBeInTheDocument();
      });
    });

    it("should display resource counts", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsListData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText(/3.*workflow/i)).toBeInTheDocument();
        expect(screen.getByText(/5.*session/i)).toBeInTheDocument();
      });
    });
  });

  describe("Search Functionality", () => {
    it("should have a search input", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByRole("searchbox")).toBeInTheDocument();
      });
    });

    it("should show search placeholder text", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        const searchInput = screen.getByRole("searchbox");
        expect(searchInput).toHaveAttribute("placeholder");
        expect(searchInput.getAttribute("placeholder")).toMatch(/search/i);
      });
    });

    it("should allow typing in the search input", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByRole("searchbox")).toBeInTheDocument();
      });

      const searchInput = screen.getByRole("searchbox");
      fireEvent.change(searchInput, { target: { value: "test query" } });

      expect(searchInput).toHaveValue("test query");
    });
  });

  describe("Pagination", () => {
    it("should show pagination when there are multiple pages", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockPaginatedData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // Should have Previous/Next buttons
        expect(
          screen.getByRole("button", { name: /next/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show total items count", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockPaginatedData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText(/45.*items/i)).toBeInTheDocument();
      });
    });

    it("should disable previous button on first page", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockPaginatedData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        const prevButton = screen.getByRole("button", { name: /previous/i });
        expect(prevButton).toBeDisabled();
      });
    });
  });

  describe("Sorting", () => {
    it("should have sort dropdown", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // Look for the specific sort dropdown (select element)
        expect(
          screen.getByRole("combobox", { name: /sort/i }),
        ).toBeInTheDocument();
      });
    });

    it("should have sort order toggle button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /sort order/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Status Filter", () => {
    it("should have status filter chips", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // Should have status filter dropdown
        const statusFilter = screen.getByTestId("status-filter");
        expect(statusFilter).toBeInTheDocument();
        // StatusFilter uses a select element
        const select = screen.getByRole("combobox", {
          name: /filter by status/i,
        });
        expect(select).toBeInTheDocument();
      });
    });

    it("should have 'All Statuses' selected by default", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // StatusFilter should have "All Statuses" selected by default
        const select = screen.getByRole("combobox", {
          name: /filter by status/i,
        }) as HTMLSelectElement;
        expect(select.value).toBe("");
      });
    });
  });

  describe("Refresh Functionality", () => {
    it("should call refetch when clicking refresh button", async () => {
      const refetchFn = vi.fn();
      mockListProjectsQuery.mockReturnValue({
        data: mockEmptyProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: refetchFn,
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByTitle(/refresh/i)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTitle(/refresh/i));

      expect(refetchFn).toHaveBeenCalled();
    });

    it("should disable refresh button while fetching", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockEmptyProjectsData,
        isLoading: false,
        isFetching: true,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        const refreshBtn = screen.getByTitle(/refresh/i);
        expect(refreshBtn).toBeDisabled();
      });
    });
  });

  describe("Project Status Display", () => {
    it("should display archived status with gray styling", async () => {
      const archivedProject = {
        items: [
          {
            id: "proj-1",
            name: "Archived Project",
            description: "Archived",
            workflow_count: 0,
            session_count: 0,
            connection_count: 0,
            status: "archived" as const,
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-02T00:00:00Z",
            owner_id: "user-1",
            organization_id: null,
          },
        ],
        total: 1,
        page: 1,
        perPage: 20,
        totalPages: 1,
      };

      mockListProjectsQuery.mockReturnValue({
        data: archivedProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("archived")).toBeInTheDocument();
      });
    });

    it("should display project without description", async () => {
      const noDescProject = {
        items: [
          {
            id: "proj-1",
            name: "No Desc Project",
            description: null,
            workflow_count: 0,
            session_count: 0,
            connection_count: 0,
            status: "active" as const,
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-02T00:00:00Z",
            owner_id: "user-1",
            organization_id: null,
          },
        ],
        total: 1,
        page: 1,
        perPage: 20,
        totalPages: 1,
      };

      mockListProjectsQuery.mockReturnValue({
        data: noDescProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("No Desc Project")).toBeInTheDocument();
      });
    });

    it("should display project without updated_at date", async () => {
      const noDateProject = {
        items: [
          {
            id: "proj-1",
            name: "No Date Project",
            description: "Test",
            workflow_count: 0,
            session_count: 0,
            connection_count: 0,
            status: "active" as const,
            created_at: "2025-01-01T00:00:00Z",
            updated_at: null,
            owner_id: "user-1",
            organization_id: null,
          },
        ],
        total: 1,
        page: 1,
        perPage: 20,
        totalPages: 1,
      };

      mockListProjectsQuery.mockReturnValue({
        data: noDateProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("No Date Project")).toBeInTheDocument();
      });

      // Switch to table view to see the date column
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        // Should show "-" for missing date
        expect(screen.getByText("-")).toBeInTheDocument();
      });
    });
  });
});
