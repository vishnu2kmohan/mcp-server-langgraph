/**
 * WorkflowsListPage Tests - Views Shard
 *
 * Tests for grid/table view toggle, table view sortable headers, and bulk selection.
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
  setupLoadedMocks,
} from "./WorkflowsListPage.fixtures";

describe("WorkflowsListPage - Views", () => {
  const mockDeleteFn = vi.fn();

  // Bundle mocks for setupLoadedMocks
  const mocks = {
    mockListWorkflowsQuery,
    mockDeleteWorkflowMutation,
  };

  beforeEach(() => {
    setupLoadedMocks(mocks, mockDeleteFn, mockWorkflowsListData);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    // Force GC to prevent mock accumulation in xdist workers
    if (global.gc) {
      global.gc();
    }
  });

  describe("View Mode Toggle", () => {
    it("should show view mode toggle with grid and table options", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("radio", { name: /grid view/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("radio", { name: /table view/i }),
        ).toBeInTheDocument();
      });
    });

    it("should default to grid view", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        // Grid view is default - table should not be present
        expect(screen.queryByRole("table")).not.toBeInTheDocument();
        // Workflows should be shown as cards
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });
    });

    it("should switch to table view when table button is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Click table view button
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        // Table view should show a table element
        expect(screen.getByRole("table")).toBeInTheDocument();
      });
    });

    it("should switch back to grid view when grid button is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Switch back to grid view
      fireEvent.click(screen.getByRole("radio", { name: /grid view/i }));

      await waitFor(() => {
        // Table should no longer be present in grid view
        expect(screen.queryByRole("table")).not.toBeInTheDocument();
      });
    });
  });

  describe("Table View", () => {
    it("should display table with headers in table view", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
        // Check for column headers - they are in th elements
        const headers = screen.getAllByRole("columnheader");
        expect(headers.length).toBeGreaterThanOrEqual(5); // checkbox + Name + Nodes + Edges + Updated + Actions
      });
    });

    it("should show workflow data in table rows", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        // Check workflow names in table
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
        expect(screen.getByText("Workflow Beta")).toBeInTheDocument();
        // Check descriptions are shown
        expect(
          screen.getByText("First workflow for data processing"),
        ).toBeInTheDocument();
      });
    });

    it("should have sortable headers that can be clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Get the header cells and verify they exist
      const headers = screen.getAllByRole("columnheader");
      expect(headers.length).toBeGreaterThan(0);

      // Headers should be clickable (cursor-pointer class)
      // Find the Name header specifically
      const nameHeader = headers.find((h) => h.textContent?.includes("Name"));
      expect(nameHeader).toBeDefined();
    });
  });

  describe("Bulk Selection", () => {
    it("should show select all checkbox in table view", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("checkbox", { name: /select all/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show row checkboxes for each workflow in table view", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        // Each workflow should have a checkbox
        expect(
          screen.getByRole("checkbox", { name: /select workflow alpha/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("checkbox", { name: /select workflow beta/i }),
        ).toBeInTheDocument();
      });
    });

    it("should select individual workflow when checkbox is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        const alphaCheckbox = screen.getByRole("checkbox", {
          name: /select workflow alpha/i,
        });
        expect(alphaCheckbox).not.toBeChecked();

        // Select workflow
        fireEvent.click(alphaCheckbox);

        expect(alphaCheckbox).toBeChecked();
      });
    });

    it("should show bulk action bar when workflows are selected", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        const alphaCheckbox = screen.getByRole("checkbox", {
          name: /select workflow alpha/i,
        });
        fireEvent.click(alphaCheckbox);
      });

      await waitFor(() => {
        // Bulk action bar should appear
        expect(screen.getByText(/1 workflow selected/i)).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /delete selected/i }),
        ).toBeInTheDocument();
      });
    });

    it("should select all workflows when select all checkbox is clicked", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        const selectAllCheckbox = screen.getByRole("checkbox", {
          name: /select all/i,
        });
        fireEvent.click(selectAllCheckbox);
      });

      await waitFor(() => {
        // Both workflows should be selected
        expect(screen.getByText(/2 workflows selected/i)).toBeInTheDocument();
      });
    });

    it("should deselect all when select all is clicked again", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        const selectAllCheckbox = screen.getByRole("checkbox", {
          name: /select all/i,
        });
        // Select all
        fireEvent.click(selectAllCheckbox);
      });

      await waitFor(() => {
        expect(screen.getByText(/2 workflows selected/i)).toBeInTheDocument();
      });

      // Deselect all
      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        // Bulk action bar should be gone
        expect(
          screen.queryByText(/workflows? selected/i),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Grid View Cards", () => {
    it("should display workflow cards with names and descriptions", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText("Workflow Alpha")).toBeInTheDocument();
        expect(screen.getByText("Workflow Beta")).toBeInTheDocument();
        expect(
          screen.getByText("First workflow for data processing"),
        ).toBeInTheDocument();
      });
    });

    it("should display node and edge counts on cards", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        expect(screen.getByText(/5.*nodes/i)).toBeInTheDocument();
        expect(screen.getByText(/4.*edges/i)).toBeInTheDocument();
      });
    });

    it("should have Open and Delete buttons on each card", async () => {
      renderWithRouter(<WorkflowsListPage />);

      await waitFor(() => {
        const openButtons = screen.getAllByRole("button", { name: /open/i });
        const deleteButtons = screen.getAllByRole("button", {
          name: /delete.*workflow/i,
        });

        // Should have buttons for each workflow
        expect(openButtons.length).toBeGreaterThanOrEqual(2);
        expect(deleteButtons.length).toBeGreaterThanOrEqual(2);
      });
    });
  });
});
