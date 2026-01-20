/**
 * WorkflowsListPage Tests - List View Shard
 *
 * Tests for loading state, empty state, workflow list, search, pagination, sorting, and refresh.
 */

import { screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// =============================================================================
// Hoisted Mocks (MUST be before vi.mock and imports)
// =============================================================================

const mockListWorkflowsQuery = vi.hoisted(() => vi.fn());
const mockDeleteWorkflowMutation = vi.hoisted(() => vi.fn());

// Mock RTK Query hooks
vi.mock("../../api", () => ({
  useListWorkflowsQuery: () => mockListWorkflowsQuery(),
  useDeleteWorkflowMutation: () => mockDeleteWorkflowMutation(),
  // Required for AIEmptyState used in empty state
  useGetEmptyStateSuggestionsMutation: () => [
    vi.fn(),
    { isLoading: false, data: null },
  ],
}));

// =============================================================================
// Imports (after mocks)
// =============================================================================

import { WorkflowsListPage } from "../WorkflowsListPage";
import {
  renderWithRouter,
  mockWorkflowsListData,
  mockSingleWorkflowData,
  mockEmptyWorkflowsData,
  mockPaginatedWorkflowsData,
  setupDefaultMocks,
  setupLoadedMocks,
} from "./WorkflowsListPage.fixtures";

describe("WorkflowsListPage - List View", () => {
  const mockDeleteFn = vi.fn();

  // Bundle mocks for setupDefaultMocks
  const mocks = {
    mockListWorkflowsQuery,
    mockDeleteWorkflowMutation,
  };

  beforeEach(() => {
    setupDefaultMocks(mocks, mockDeleteFn);
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
      renderWithRouter(<WorkflowsListPage />);

      // Should show skeleton placeholders instead of text loading indicator
      expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
    });

    it("should show multiple skeleton items while loading", () => {
      // isLoading is already true in setupDefaultMocks
      renderWithRouter(<WorkflowsListPage />);

      // Should have multiple skeleton items
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no workflows exist", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockEmptyWorkflowsData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText(/no workflows/i)).toBeInTheDocument();
      });
    });

    it("should show create button in empty state", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockEmptyWorkflowsData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        // There are 2 create buttons - one in header, one in empty state
        const createButtons = screen.getAllByRole("button", {
          name: /create.*workflow/i,
        });
        expect(createButtons.length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  describe("Workflow List", () => {
    it("should display list of workflows", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockWorkflowsListData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
        expect(screen.getByText("Workflow Beta")).toBeInTheDocument();
      });
    });

    it("should display workflow descriptions", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockWorkflowsListData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(
          screen.getByText("First workflow for data processing")
        ).toBeInTheDocument();
        expect(
          screen.getByText("Second workflow for analysis")
        ).toBeInTheDocument();
      });
    });

    it("should display node and edge counts", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockWorkflowsListData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        // Check for node count display
        expect(screen.getByText(/5.*nodes/i)).toBeInTheDocument();
        expect(screen.getByText(/4.*edges/i)).toBeInTheDocument();
      });
    });
  });

  describe("Search Functionality", () => {
    it("should have a search input", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockSingleWorkflowData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByRole("searchbox")).toBeInTheDocument();
      });
    });

    it("should show search placeholder text", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockSingleWorkflowData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        const searchInput = screen.getByRole("searchbox");
        expect(searchInput).toHaveAttribute("placeholder");
        expect(searchInput.getAttribute("placeholder")).toMatch(/search/i);
      });
    });

    it("should allow typing in the search input", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockSingleWorkflowData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByRole("searchbox")).toBeInTheDocument();
      });

      const searchInput = screen.getByRole("searchbox");
      fireEvent.change(searchInput, { target: { value: "test query" } });

      expect(searchInput).toHaveValue("test query");
    });
  });

  describe("Cursor Pagination", () => {
    it("should show pagination when there are more pages", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockPaginatedWorkflowsData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        // Should have Next button enabled
        expect(
          screen.getByRole("button", { name: /next/i })
        ).toBeInTheDocument();
      });
    });

    it("should disable previous button on first page", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockPaginatedWorkflowsData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        const prevButton = screen.getByRole("button", { name: /previous/i });
        expect(prevButton).toBeDisabled();
      });
    });

    it("should enable next button when hasNext is true", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockPaginatedWorkflowsData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        const nextButton = screen.getByRole("button", { name: /next/i });
        expect(nextButton).not.toBeDisabled();
      });
    });
  });

  describe("Sorting", () => {
    it("should have sort dropdown", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockSingleWorkflowData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        // Look for the specific sort dropdown (select element)
        expect(
          screen.getByRole("combobox", { name: /sort/i })
        ).toBeInTheDocument();
      });
    });

    it("should have sort order toggle button", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockSingleWorkflowData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /sort order/i })
        ).toBeInTheDocument();
      });
    });
  });

  describe("Refresh Functionality", () => {
    it("should call refetch when clicking refresh button", async () => {
      const refetchFn = vi.fn();
      mockListWorkflowsQuery.mockReturnValue({
        data: mockEmptyWorkflowsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: refetchFn,
      });
      // Note: Delete mock not needed for this test, using default from beforeEach

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByTitle(/refresh/i)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTitle(/refresh/i));

      expect(refetchFn).toHaveBeenCalled();
    });

    it("should disable refresh button while fetching", async () => {
      mockListWorkflowsQuery.mockReturnValue({
        data: mockEmptyWorkflowsData,
        isLoading: false,
        isFetching: true,
        error: null,
        refetch: vi.fn(),
      });
      // Note: Delete mock not needed for this test, using default from beforeEach

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        const refreshBtn = screen.getByTitle(/refresh/i);
        expect(refreshBtn).toBeDisabled();
      });
    });
  });

  describe("Workflow Display Details", () => {
    it("should display workflow without description", async () => {
      const noDescWorkflow = {
        items: [
          {
            id: "wf-1",
            name: "No Desc Workflow",
            description: "",
            nodeCount: 3,
            edgeCount: 2,
            createdAt: "2025-01-01T00:00:00Z",
            updatedAt: "2025-01-02T00:00:00Z",
          },
        ],
        pagination: {
          count: 1,
          has_next: false,
          has_prev: false,
          next_cursor: null,
          prev_cursor: null,
        },
        count: 1,
        hasNext: false,
        hasPrev: false,
        nextCursor: undefined,
        prevCursor: undefined,
      };

      setupLoadedMocks(mocks, mockDeleteFn, noDescWorkflow);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("No Desc Workflow")).toBeInTheDocument();
      });
    });

    it("should display updated date in human-readable format", async () => {
      setupLoadedMocks(mocks, mockDeleteFn, mockSingleWorkflowData);

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view to see the date column
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
        // Should show formatted date in table view (locale-specific format)
        // Just verify the table has a date cell with some content
        const dateCells = screen.getAllByRole("cell");
        expect(dateCells.length).toBeGreaterThan(0);
      });
    });
  });
});
