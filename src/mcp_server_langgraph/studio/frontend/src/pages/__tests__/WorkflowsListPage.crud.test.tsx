/**
 * WorkflowsListPage Tests - CRUD Shard
 *
 * Tests for delete confirmation, bulk delete, and error handling.
 */

import { screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// =============================================================================
// Hoisted Mocks (MUST be before vi.mock and imports)
// =============================================================================

const mockListWorkflowsQuery = vi.hoisted(() => vi.fn());
const mockDeleteWorkflowMutation = vi.hoisted(() => vi.fn());
const mockNavigate = vi.hoisted(() => vi.fn());

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

// Mock react-router navigate
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// =============================================================================
// Imports (after mocks)
// =============================================================================

import { WorkflowsListPage } from "../WorkflowsListPage";
import {
  renderWithRouter,
  mockWorkflowsListData,
  setupLoadedMocks,
} from "./WorkflowsListPage.fixtures";

describe("WorkflowsListPage - CRUD", () => {
  const mockDeleteFn = vi.fn();

  // Bundle mocks for setupLoadedMocks
  const mocks = {
    mockListWorkflowsQuery,
    mockDeleteWorkflowMutation,
  };

  beforeEach(() => {
    setupLoadedMocks(mocks, mockDeleteFn, mockWorkflowsListData);
    mockNavigate.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    // Force GC to prevent mock accumulation in xdist workers
    if (global.gc) {
      global.gc();
    }
  });

  describe("Navigation", () => {
    it("should navigate to builder when Create Workflow button is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      const createButton = screen.getByRole("button", {
        name: /create workflow/i,
      });
      fireEvent.click(createButton);

      expect(mockNavigate).toHaveBeenCalledWith("/studio/workflows/builder");
    });

    it("should navigate to workflow detail when Open is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      const openButtons = screen.getAllByRole("button", { name: /open/i });
      fireEvent.click(openButtons[0]); // Click first Open button

      expect(mockNavigate).toHaveBeenCalledWith("/studio/workflows/wf-1");
    });
  });

  describe("Delete Single Workflow", () => {
    it("should show confirmation dialog when delete button is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Click delete button on first workflow
      const deleteButtons = screen.getAllByRole("button", {
        name: /delete.*workflow/i,
      });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        // Confirmation dialog should appear
        expect(
          screen.getByText(/are you sure you want to delete/i),
        ).toBeInTheDocument();
        // Dialog should mention the workflow name in the message
        expect(
          screen.getByText(/are you sure you want to delete.*workflow alpha/i),
        ).toBeInTheDocument();
      });
    });

    it("should have Cancel and Delete buttons in confirmation dialog", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete.*workflow/i,
      });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /^cancel$/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /^delete$/i }),
        ).toBeInTheDocument();
      });
    });

    it("should close dialog when Cancel is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete.*workflow/i,
      });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /^cancel$/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /^cancel$/i }));

      await waitFor(() => {
        // Dialog should be closed - confirmation text should not be visible
        expect(
          screen.queryByText(/are you sure you want to delete/i),
        ).not.toBeInTheDocument();
      });
    });

    it("should call delete mutation when Delete is confirmed", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole("button", {
        name: /delete.*workflow/i,
      });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /^delete$/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

      await waitFor(() => {
        expect(mockDeleteFn).toHaveBeenCalledWith("wf-1");
      });
    });
  });

  describe("Bulk Delete", () => {
    it("should show confirmation dialog when Delete Selected is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Select all workflows
      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /delete selected/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /delete selected/i }));

      await waitFor(() => {
        // Dialog should appear asking to confirm deletion
        expect(
          screen.getByText(/are you sure you want to delete 2 workflow/i),
        ).toBeInTheDocument();
      });
    });

    it("should call delete for each selected workflow when bulk delete is confirmed", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Select all workflows
      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /delete selected/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /delete selected/i }));

      await waitFor(() => {
        // Dialog appears
        expect(
          screen.getByRole("button", { name: /delete 2 workflows/i }),
        ).toBeInTheDocument();
      });

      // Click the confirm button in the dialog
      fireEvent.click(
        screen.getByRole("button", { name: /delete 2 workflows/i }),
      );

      await waitFor(() => {
        // Should have called delete for both workflows
        expect(mockDeleteFn).toHaveBeenCalledTimes(2);
      });
    });

    it("should clear selection after successful bulk delete", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Select all workflows
      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /delete selected/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /delete selected/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /delete 2 workflows/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(
        screen.getByRole("button", { name: /delete 2 workflows/i }),
      );

      await waitFor(() => {
        // Selection should be cleared - no bulk action bar
        expect(
          screen.queryByText(/workflows? selected/i),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("should show error state when fetch fails", async () => {
      mockListWorkflowsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: "FETCH_ERROR" },
        refetch: vi.fn(),
      });

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/failed to load workflows/i),
        ).toBeInTheDocument();
      });
    });

    it("should show retry button on error", async () => {
      const refetchFn = vi.fn();
      mockListWorkflowsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: "FETCH_ERROR" },
        refetch: refetchFn,
      });

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /retry/i }),
        ).toBeInTheDocument();
      });
    });

    it("should call refetch when retry button is clicked", async () => {
      const refetchFn = vi.fn();
      mockListWorkflowsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: "FETCH_ERROR" },
        refetch: refetchFn,
      });

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /retry/i }),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /retry/i }));

      expect(refetchFn).toHaveBeenCalled();
    });

    it("should display network error message for connection issues", async () => {
      mockListWorkflowsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: "FETCH_ERROR" },
        refetch: vi.fn(),
      });

      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/unable to connect to the server/i),
        ).toBeInTheDocument();
      });
    });
  });
});
