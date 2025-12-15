/**
 * ProjectsPage Tests
 *
 * TDD: Tests written FIRST for the ProjectsPage component.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
});
