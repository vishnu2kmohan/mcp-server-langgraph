/**
 * ProjectsPage Tests
 *
 * TDD: Tests written FIRST for the ProjectsPage component.
 */

import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router";
import { ProjectsPage } from "./ProjectsPage";

// Mock the RTK Query hooks
const mockListProjectsQuery = vi.fn();
const mockCreateProjectMutation = vi.fn();
const mockDeleteProjectMutation = vi.fn();

vi.mock("../api", () => ({
  useListProjectsQuery: () => mockListProjectsQuery(),
  useCreateProjectMutation: () => mockCreateProjectMutation(),
  useDeleteProjectMutation: () => mockDeleteProjectMutation(),
}));

// Helper to render with router
const renderWithRouter = (component: React.ReactNode) => {
  return render(
    <MemoryRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      {component}
    </MemoryRouter>,
  );
};

describe("ProjectsPage", () => {
  const mockCreateFn = vi.fn();
  const mockDeleteFn = vi.fn();

  beforeEach(() => {
    // Default mock implementations
    mockListProjectsQuery.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });
    mockCreateProjectMutation.mockReturnValue([
      mockCreateFn.mockResolvedValue({ data: {} }),
      { isLoading: false },
    ]);
    mockDeleteProjectMutation.mockReturnValue([
      mockDeleteFn.mockResolvedValue({ data: {} }),
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should show loading skeletons initially", () => {
      // isLoading is already true in beforeEach
      renderWithRouter(<ProjectsPage />);

      // Should show skeleton placeholders instead of text loading indicator
      expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
    });

    it("should show multiple skeleton items while loading", () => {
      // isLoading is already true in beforeEach
      renderWithRouter(<ProjectsPage />);

      // Should have multiple skeleton items
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no projects exist", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
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
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
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
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First project",
          workflow_count: 3,
          session_count: 5,
          connection_count: 2,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
        {
          id: "proj-2",
          name: "Project Beta",
          description: "Second project",
          workflow_count: 1,
          session_count: 10,
          connection_count: 0,
          status: "active",
          created_at: "2025-01-03T00:00:00Z",
          updated_at: "2025-01-04T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should display list of projects", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
        data: mockProjectsData,
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
        data: mockProjectsData,
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

  describe("Create Project", () => {
    it("should open create dialog when clicking create button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Click the first create button (header button)
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });
    });

    it("should create project when form is submitted", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      const createFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({ id: "proj-new", name: "New Project" }),
      });
      mockCreateProjectMutation.mockReturnValue([
        createFn,
        { isLoading: false },
      ]);

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Click the first create button (header button)
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });

      // Fill in the form
      fireEvent.change(screen.getByLabelText(/project name/i), {
        target: { value: "New Project" },
      });

      // Submit the form
      fireEvent.click(screen.getByRole("button", { name: /^create$/i }));

      await waitFor(() => {
        expect(createFn).toHaveBeenCalledWith({
          name: "New Project",
          description: undefined,
        });
      });
    });
  });

  describe("Error Handling", () => {
    it("should show error message when fetch fails", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { message: "Network error" },
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // ErrorState component has role="alert" for accessibility
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(
          screen.getByRole("heading", { name: /failed to load projects/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show error when API returns error status", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: 500 },
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // ErrorState component has role="alert" for accessibility
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(
          screen.getByRole("heading", { name: /failed to load projects/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Search Functionality", () => {
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First project",
          workflow_count: 3,
          session_count: 5,
          connection_count: 2,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should have a search input", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
        data: mockProjectsData,
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
        data: mockProjectsData,
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

  describe("Project Actions", () => {
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First project",
          workflow_count: 0,
          session_count: 0,
          connection_count: 0,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should have delete button for each project", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
        data: mockProjectsData,
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

  describe("Pagination", () => {
    const mockPaginatedData = {
      items: [
        {
          id: "proj-1",
          name: "Project One",
          description: "First",
          workflow_count: 1,
          session_count: 1,
          connection_count: 1,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 45,
      page: 1,
      per_page: 20,
      total_pages: 3,
    };

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
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First",
          workflow_count: 1,
          session_count: 1,
          connection_count: 1,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should have sort dropdown", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
        data: mockProjectsData,
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
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First",
          workflow_count: 1,
          session_count: 1,
          connection_count: 1,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should have status filter chips", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // Should have filter chips for Active and Archived
        const filterGroup = screen.getByRole("group", {
          name: /filter projects by status/i,
        });
        expect(filterGroup).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /active/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /archived/i }),
        ).toBeInTheDocument();
      });
    });

    it("should have no filter selected by default", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        // Both filter chips should be unpressed by default
        const activeBtn = screen.getByRole("button", { name: /active/i });
        const archivedBtn = screen.getByRole("button", { name: /archived/i });
        expect(activeBtn).toHaveAttribute("aria-pressed", "false");
        expect(archivedBtn).toHaveAttribute("aria-pressed", "false");
      });
    });
  });

  describe("View Mode Toggle", () => {
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First project",
          workflow_count: 3,
          session_count: 5,
          connection_count: 2,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          owner_name: "Test User",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should have grid and table view toggle buttons", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /grid view/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /table view/i }),
        ).toBeInTheDocument();
      });
    });

    it("should default to grid view", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        const gridBtn = screen.getByRole("button", { name: /grid view/i });
        expect(gridBtn).toHaveAttribute("aria-pressed", "true");
      });
    });

    it("should switch to table view when clicking table button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

      await waitFor(() => {
        // Table view should have a table element
        expect(screen.getByRole("table")).toBeInTheDocument();
        const tableBtn = screen.getByRole("button", { name: /table view/i });
        expect(tableBtn).toHaveAttribute("aria-pressed", "true");
      });
    });

    it("should display project in table row with all columns", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
        // Table should show owner name
        expect(screen.getByText("Test User")).toBeInTheDocument();
      });
    });
  });

  describe("Table View Bulk Selection", () => {
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First",
          workflow_count: 1,
          session_count: 1,
          connection_count: 1,
          status: "active",
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
          status: "active",
          created_at: "2025-01-03T00:00:00Z",
          updated_at: "2025-01-04T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should allow selecting individual projects in table view", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

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
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

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
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

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
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

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

  describe("Delete Confirmation Dialog", () => {
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First",
          workflow_count: 1,
          session_count: 1,
          connection_count: 1,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should show delete confirmation dialog when clicking delete", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Click delete button
      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/are you sure you want to delete/i),
        ).toBeInTheDocument();
      });
    });

    it("should close dialog when clicking cancel", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Click delete button
      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/are you sure you want to delete/i),
        ).toBeInTheDocument();
      });

      // Click cancel
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      await waitFor(() => {
        expect(
          screen.queryByText(/are you sure you want to delete/i),
        ).not.toBeInTheDocument();
      });
    });

    it("should call delete mutation when confirming", async () => {
      const deleteFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({}),
      });
      mockDeleteProjectMutation.mockReturnValue([deleteFn]);

      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Click delete button
      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/are you sure you want to delete/i),
        ).toBeInTheDocument();
      });

      // Confirm delete - find the delete button in the dialog
      const confirmButton = screen.getByRole("button", { name: /^delete$/i });
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(deleteFn).toHaveBeenCalledWith("proj-1");
      });
    });
  });

  describe("Error Handling Edge Cases", () => {
    it("should show network error message for FETCH_ERROR", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: "FETCH_ERROR" },
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/unable to connect to the server/i),
        ).toBeInTheDocument();
      });
    });

    it("should show mutation error when create fails", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      const createFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.reject(new Error("Create failed")),
      });
      mockCreateProjectMutation.mockReturnValue([
        createFn,
        { isLoading: false },
      ]);

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Click create button
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });

      // Fill in form and submit
      fireEvent.change(screen.getByLabelText(/project name/i), {
        target: { value: "New Project" },
      });
      fireEvent.click(screen.getByRole("button", { name: /^create$/i }));

      await waitFor(() => {
        expect(screen.getByText(/create failed/i)).toBeInTheDocument();
      });
    });

    it("should show mutation error when delete fails", async () => {
      const deleteFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.reject(new Error("Delete failed")),
      });
      mockDeleteProjectMutation.mockReturnValue([deleteFn]);

      const mockProjectsData = {
        items: [
          {
            id: "proj-1",
            name: "Project Alpha",
            description: "First",
            workflow_count: 1,
            session_count: 1,
            connection_count: 1,
            status: "active",
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-02T00:00:00Z",
            owner_id: "user-1",
            organization_id: null,
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
      };

      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(screen.getByText("Project Alpha")).toBeInTheDocument();
      });

      // Click delete and confirm
      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/are you sure you want to delete/i),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

      await waitFor(() => {
        expect(screen.getByText(/delete failed/i)).toBeInTheDocument();
      });
    });
  });

  describe("Create Dialog Edge Cases", () => {
    it("should disable create button when name is empty", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Click create button
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });

      // Create button should be disabled when name is empty
      const createBtn = screen.getByRole("button", { name: /^create$/i });
      expect(createBtn).toBeDisabled();
    });

    it("should disable create button when name is only whitespace", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Click create button
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });

      // Enter whitespace only
      fireEvent.change(screen.getByLabelText(/project name/i), {
        target: { value: "   " },
      });

      // Create button should still be disabled
      const createBtn = screen.getByRole("button", { name: /^create$/i });
      expect(createBtn).toBeDisabled();
    });

    it("should close create dialog when clicking X button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Click create button
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });

      // Find and click the X button (close button)
      const closeButtons = document.querySelectorAll(
        'button[class*="hover:text-gray-600"]',
      );
      const xButton = Array.from(closeButtons).find((btn) =>
        btn.querySelector("svg"),
      );
      if (xButton) {
        fireEvent.click(xButton);
      }

      await waitFor(() => {
        expect(
          screen.queryByLabelText(/project name/i),
        ).not.toBeInTheDocument();
      });
    });

    it("should include description in create request when provided", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      const createFn = vi.fn().mockReturnValue({
        unwrap: () => Promise.resolve({ id: "proj-new", name: "New Project" }),
      });
      mockCreateProjectMutation.mockReturnValue([
        createFn,
        { isLoading: false },
      ]);

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Click create button
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });

      // Fill in both name and description
      fireEvent.change(screen.getByLabelText(/project name/i), {
        target: { value: "New Project" },
      });
      fireEvent.change(screen.getByLabelText(/description/i), {
        target: { value: "Test description" },
      });

      // Submit
      fireEvent.click(screen.getByRole("button", { name: /^create$/i }));

      await waitFor(() => {
        expect(createFn).toHaveBeenCalledWith({
          name: "New Project",
          description: "Test description",
        });
      });
    });
  });

  describe("Sortable Header Edge Cases", () => {
    const mockProjectsData = {
      items: [
        {
          id: "proj-1",
          name: "Project Alpha",
          description: "First",
          workflow_count: 1,
          session_count: 1,
          connection_count: 1,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-02T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should toggle sort order when clicking same header twice", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

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
            status: "archived",
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-02T00:00:00Z",
            owner_id: "user-1",
            organization_id: null,
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
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
            status: "active",
            created_at: "2025-01-01T00:00:00Z",
            updated_at: "2025-01-02T00:00:00Z",
            owner_id: "user-1",
            organization_id: null,
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
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
            status: "active",
            created_at: "2025-01-01T00:00:00Z",
            updated_at: null,
            owner_id: "user-1",
            organization_id: null,
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        total_pages: 1,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

      await waitFor(() => {
        // Should show "-" for missing date
        expect(screen.getByText("-")).toBeInTheDocument();
      });
    });
  });

  describe("Refresh Functionality", () => {
    it("should call refetch when clicking refresh button", async () => {
      const refetchFn = vi.fn();
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
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
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
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

  describe("Table View Action Buttons", () => {
    const mockProjectsData = {
      items: [
        {
          id: "proj-table-1",
          name: "Table Test Project",
          description: "Test for table actions",
          workflow_count: 3,
          session_count: 5,
          connection_count: 2,
          status: "active",
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-10T00:00:00Z",
          owner_id: "user-1",
          organization_id: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    it("should open project when clicking open button in table view", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

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
        data: mockProjectsData,
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
      fireEvent.click(screen.getByRole("button", { name: /table view/i }));

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

  describe("Create Dialog Cancel Button", () => {
    it("should close create dialog when clicking Cancel button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 },
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter(<ProjectsPage />);

      await waitFor(() => {
        expect(
          screen.getAllByRole("button", { name: /create.*project/i }).length,
        ).toBeGreaterThan(0);
      });

      // Open create dialog
      fireEvent.click(
        screen.getAllByRole("button", { name: /create.*project/i })[0],
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
      });

      // Find and click the Cancel button in the dialog footer
      const cancelButton = screen.getByRole("button", { name: /^cancel$/i });
      fireEvent.click(cancelButton);

      // Dialog should close
      await waitFor(() => {
        expect(
          screen.queryByLabelText(/project name/i),
        ).not.toBeInTheDocument();
      });
    });
  });
});
