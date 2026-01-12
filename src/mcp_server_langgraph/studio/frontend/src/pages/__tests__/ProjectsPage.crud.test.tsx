/**
 * ProjectsPage Tests - CRUD Operations Shard
 *
 * Tests for create project, delete confirmation, error handling, and dialog edge cases.
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
  mockEmptyProjectsData,
  setupDefaultMocks,
} from "./ProjectsPage.fixtures";

describe("ProjectsPage - CRUD Operations", () => {
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

  describe("Create Project", () => {
    it("should open create dialog when clicking create button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockEmptyProjectsData,
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
        data: mockEmptyProjectsData,
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
        data: mockEmptyProjectsData,
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
            status: "active" as const,
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
        data: mockEmptyProjectsData,
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
        data: mockEmptyProjectsData,
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
        data: mockEmptyProjectsData,
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
        'button[class*="hover:text-neutral-600"]',
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
        data: mockEmptyProjectsData,
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

  describe("Delete Confirmation Dialog", () => {
    it("should show delete confirmation dialog when clicking delete", async () => {
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

  describe("Create Dialog Cancel Button", () => {
    it("should close create dialog when clicking Cancel button", async () => {
      mockListProjectsQuery.mockReturnValue({
        data: mockEmptyProjectsData,
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
