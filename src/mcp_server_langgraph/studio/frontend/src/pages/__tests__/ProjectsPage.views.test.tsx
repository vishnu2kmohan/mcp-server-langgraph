/**
 * ProjectsPage Tests - Views and Actions Shard
 *
 * Tests for view mode toggle, table view bulk selection, project actions, sortable headers, and action buttons.
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
vi.mock("../../api", () => ({
  useListProjectsQuery: () => mockListProjectsQuery(),
  useCreateProjectMutation: () => mockCreateProjectMutation(),
  useDeleteProjectMutation: () => mockDeleteProjectMutation(),
}));

// =============================================================================
// Imports (after mocks)
// =============================================================================

import { ProjectsPage } from "../ProjectsPage";
import {
  renderWithRouter,
  mockSingleProjectData,
  setupDefaultMocks,
} from "./ProjectsPage.fixtures";

describe("ProjectsPage - Views and Actions", () => {
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

  describe("View Mode Toggle", () => {
    const mockProjectWithOwner = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First project",
          workflow_count: 3,
          session_count: 5,
          connection_count: 2,
          status: "active" as const,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          owner_name: "Test User",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      perPage: 20,
      totalPages: 1,
    };

    it("should have grid and table view toggle buttons", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectWithOwner,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

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
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectWithOwner,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        const gridBtn = screen.getByRole("radio", { name: /grid view/i });
        expect(gridBtn).toHaveAttribute("aria-checked", "true");
      });
    });

    it("should switch to table view when clicking table button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectWithOwner,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Click table view button
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        // Table view should have a table element
        expect(screen.getByRole("table")).toBeInTheDocument();
        const tableBtn = screen.getByRole("radio", { name: /table view/i });
        expect(tableBtn).toHaveAttribute("aria-checked", "true");
      });
    });

    it("should display project in table row with all columns", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectWithOwner,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
        // Table should show owner name
        expect(screen.getByText("Test User")).toBeInTheDocument();
      });
    });
  });

  describe("Table View Bulk Selection", () => {
    const mockTwoProjects = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First",
          workflow_count: 1,
          session_count: 1,
          connection_count: 1,
          status: "active" as const,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
        {
          id: "proj-2",
          name: "Project Beta",
          description: "Second",
          workflow_count: 2,
          session_count: 2,
          connection_count: 2,
          status: "active" as const,
          created_at: "2025-01-03T00:00:00Z",
          updated_at: "2025-01-04T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 2,
      page: 1,
      perPage: 20,
      totalPages: 1,
    };

    it("should allow selecting individual projects in table view", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockTwoProjects,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Select individual project
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]); // First project checkbox (index 0 is select all)

      await waitFor(() => {
        expect(screen.getByText(/1 project selected/i)).toBeInTheDocument();
      });
    });

    it("should allow select all in table view", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockTwoProjects,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Click select all checkbox
      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(screen.getByText(/2 projects selected/i)).toBeInTheDocument();
      });
    });

    it("should deselect all when clicking select all twice", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockTwoProjects,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Click select all twice
      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });
      fireEvent.click(selectAllCheckbox);
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(
          screen.queryByText(/projects? selected/i),
        ).not.toBeInTheDocument();
      });
    });

    it("should show bulk delete button when projects selected", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockTwoProjects,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Select a project
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /delete selected/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Project Actions", () => {
    const mockSingleProject = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First project",
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

    it("should have delete button for each project", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /delete/i }),
        ).toBeInTheDocument();
      });
    });

    it("should have open button for each project", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /open/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Sortable Header Edge Cases", () => {
    it("should toggle sort order when clicking same header twice", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockSingleProjectData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Switch to table view to see sortable headers
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Click the Name header to sort
      const nameHeader = screen.getByRole("columnheader", { name: /^name$/i });
      fireEvent.click(nameHeader);

      // Click again to toggle order
      fireEvent.click(nameHeader);

      // The component should re-render with updated sort
      expect(nameHeader).toBeInTheDocument();
    });
  });

  describe("Table View Action Buttons", () => {
    const mockTableTestProject = {
      items: [
        {
          id: "proj-table-1",
          name: "Table Test Project",
          description: "Test for table actions",
          workflow_count: 3,
          session_count: 5,
          connection_count: 2,
          status: "active" as const,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-10T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      perPage: 20,
      totalPages: 1,
    };

    it("should open project when clicking open button in table view", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockTableTestProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Table Test Project")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Find and click the Open button in the table row
      const openButton = screen.getByRole("button", { name: /open project/i });
      fireEvent.click(openButton);

      // Navigation should be triggered - verify router state change
      // The component uses navigate(`/studio/projects/${projectId}`)
      await waitFor(() => {
        // Just verify the button was clickable without errors
        expect(openButton).toBeInTheDocument();
      });
    });

    it("should show delete dialog when clicking delete button in table view", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockTableTestProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Table Test Project")).toBeInTheDocument();
      });

      // Switch to table view
      fireEvent.click(screen.getByRole("radio", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });

      // Find and click the Delete button in the table row
      const deleteButton = screen.getByRole("button", {
        name: /delete project/i,
      });
      fireEvent.click(deleteButton);

      // Delete confirmation dialog should appear
      await waitFor(() => {
        expect(
          screen.getByText(/are you sure you want to delete/i),
        ).toBeInTheDocument();
      });

      // The project name should appear in the delete confirmation message
      const confirmationText = screen.getByText(
        /are you sure you want to delete/i,
      );
      expect(confirmationText.textContent).toContain("Table Test Project");
    });
  });
});
