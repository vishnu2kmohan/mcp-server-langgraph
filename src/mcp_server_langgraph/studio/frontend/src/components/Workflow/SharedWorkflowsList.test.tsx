/**
 * SharedWorkflowsList Tests
 *
 * TDD tests for the shared workflows list component.
 * Tests cover:
 * - Shared workflows display
 * - Permission levels
 * - Actions (view, execute)
 * - Loading and error states
 * - Empty state
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react";
import { BrowserRouter } from "react-router";
import { SharedWorkflowsList } from "./SharedWorkflowsList";

// Wrapper for routing
const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      {ui}
    </BrowserRouter>,
  );
};

describe("SharedWorkflowsList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  describe("Header", () => {
    it("should display title", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [] }),
      });

      await act(async () => {
        renderWithRouter(<SharedWorkflowsList />);
      });

      expect(screen.getByText("Shared With Me")).toBeInTheDocument();
    });

    it("should display description", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [] }),
      });

      await act(async () => {
        renderWithRouter(<SharedWorkflowsList />);
      });

      expect(
        screen.getByText(/Workflows shared by other users/),
      ).toBeInTheDocument();
    });

    it("should have refresh button", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [] }),
      });

      await act(async () => {
        renderWithRouter(<SharedWorkflowsList />);
      });

      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading state initially", () => {
      global.fetch = vi.fn().mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      renderWithRouter(<SharedWorkflowsList />);

      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should display empty state when no workflows are shared", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [] }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByText(/No workflows shared with you/),
        ).toBeInTheDocument();
      });
    });

    it("should show helpful message in empty state", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [] }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByText(/Ask a colleague to share/),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Error State", () => {
    it("should display error message on API failure", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: "Failed to fetch shared workflows" }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to fetch shared workflows/),
        ).toBeInTheDocument();
      });
    });

    it("should have retry button on error", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: "Failed" }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /retry/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Workflow List", () => {
    const mockWorkflows = [
      {
        id: "wf-1",
        name: "Customer Support Agent",
        description: "Handles customer inquiries",
        shared_by: "alice@example.com",
        permission: "viewer",
        shared_at: "2024-01-15T10:30:00Z",
      },
      {
        id: "wf-2",
        name: "Data Processing Pipeline",
        description: "Processes incoming data",
        shared_by: "charlie@example.com",
        permission: "executor",
        shared_at: "2024-01-16T14:00:00Z",
      },
      {
        id: "wf-3",
        name: "Report Generator",
        description: "Generates weekly reports",
        shared_by: "alice@example.com",
        permission: "editor",
        shared_at: "2024-01-17T09:00:00Z",
      },
    ];

    it("should display list of shared workflows", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
        expect(
          screen.getByText("Data Processing Pipeline"),
        ).toBeInTheDocument();
        expect(screen.getByText("Report Generator")).toBeInTheDocument();
      });
    });

    it("should display workflow descriptions", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByText("Handles customer inquiries"),
        ).toBeInTheDocument();
      });
    });

    it("should display who shared the workflow", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        // alice@example.com appears in 2 workflows + 1 filter dropdown = 3 total
        const aliceElements = screen.getAllByText(/alice@example.com/);
        expect(aliceElements.length).toBe(3);
        // charlie@example.com appears in 1 workflow + 1 filter dropdown = 2 total
        const charlieElements = screen.getAllByText(/charlie@example.com/);
        expect(charlieElements.length).toBe(2);
      });
    });

    it("should display permission level badges", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        // Each permission appears in workflow badge + filter dropdown option
        // Use getAllByText since they appear multiple times
        expect(screen.getAllByText("Viewer").length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText("Executor").length).toBeGreaterThanOrEqual(
          1,
        );
        expect(screen.getAllByText("Editor").length).toBeGreaterThanOrEqual(1);
      });
    });

    it("should have view button for all workflows", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        const viewButtons = screen.getAllByRole("button", { name: /view/i });
        expect(viewButtons.length).toBe(3);
      });
    });

    it("should have execute button for executor and editor permissions", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        const executeButtons = screen.getAllByRole("button", {
          name: /execute/i,
        });
        // Only executor and editor should have execute button
        expect(executeButtons.length).toBe(2);
      });
    });

    it("should not show execute button for viewer permission", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          workflows: [mockWorkflows[0]], // Only viewer workflow
        }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      // Viewer should not have execute button
      expect(
        screen.queryByRole("button", { name: /execute/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    const mockWorkflow = {
      id: "wf-1",
      name: "Test Workflow",
      description: "Test description",
      shared_by: "alice@example.com",
      permission: "executor",
      shared_at: "2024-01-15T10:30:00Z",
    };

    it("should call onView when view button is clicked", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [mockWorkflow] }),
      });

      const onView = vi.fn();
      renderWithRouter(<SharedWorkflowsList onView={onView} />);

      await waitFor(() => {
        expect(screen.getByText("Test Workflow")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /view/i }));

      expect(onView).toHaveBeenCalledWith("wf-1");
    });

    it("should call onExecute when execute button is clicked", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [mockWorkflow] }),
      });

      const onExecute = vi.fn();
      renderWithRouter(<SharedWorkflowsList onExecute={onExecute} />);

      await waitFor(() => {
        expect(screen.getByText("Test Workflow")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /execute/i }));

      expect(onExecute).toHaveBeenCalledWith("wf-1");
    });

    it("should refresh list when refresh button is clicked", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: [mockWorkflow] }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Test Workflow")).toBeInTheDocument();
      });

      // Clear the mock call count
      vi.mocked(global.fetch).mockClear();

      fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          "/api/v1/workflows/shared",
          expect.any(Object),
        );
      });
    });
  });

  describe("Permission Badge Styling", () => {
    it("should have correct styling for viewer badge", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          workflows: [
            {
              id: "wf-1",
              name: "Test",
              description: "Test",
              shared_by: "test@example.com",
              permission: "viewer",
              shared_at: "2024-01-15T10:30:00Z",
            },
          ],
        }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        // Get all Viewer elements (badge + dropdown option) and check the badge
        const badges = screen.getAllByText("Viewer");
        // The first one should be the badge with styling
        const badge = badges.find((el) => el.classList.contains("bg-gray-100"));
        expect(badge).toBeTruthy();
      });
    });

    it("should have correct styling for executor badge", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          workflows: [
            {
              id: "wf-1",
              name: "Test",
              description: "Test",
              shared_by: "test@example.com",
              permission: "executor",
              shared_at: "2024-01-15T10:30:00Z",
            },
          ],
        }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        // Get all Executor elements (badge + dropdown option) and check the badge
        const badges = screen.getAllByText("Executor");
        // Find the one with badge styling
        const badge = badges.find((el) => el.classList.contains("bg-blue-100"));
        expect(badge).toBeTruthy();
      });
    });

    it("should have correct styling for editor badge", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          workflows: [
            {
              id: "wf-1",
              name: "Test",
              description: "Test",
              shared_by: "test@example.com",
              permission: "editor",
              shared_at: "2024-01-15T10:30:00Z",
            },
          ],
        }),
      });

      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        // Get all Editor elements (badge + dropdown option) and check the badge
        const badges = screen.getAllByText("Editor");
        // Find the one with badge styling
        const badge = badges.find((el) =>
          el.classList.contains("bg-green-100"),
        );
        expect(badge).toBeTruthy();
      });
    });
  });

  // =========================================================================
  // Filter Tests
  // =========================================================================

  describe("Filters", () => {
    const mockWorkflows = [
      {
        id: "wf-1",
        name: "Customer Support Agent",
        description: "Handles customer inquiries",
        shared_by: "alice@example.com",
        permission: "viewer",
        shared_at: "2024-01-15T10:30:00Z",
      },
      {
        id: "wf-2",
        name: "Data Processing Pipeline",
        description: "Processes incoming data",
        shared_by: "charlie@example.com",
        permission: "executor",
        shared_at: "2024-01-16T14:00:00Z",
      },
      {
        id: "wf-3",
        name: "Report Generator",
        description: "Generates weekly reports",
        shared_by: "alice@example.com",
        permission: "editor",
        shared_at: "2024-01-17T09:00:00Z",
      },
    ];

    beforeEach(() => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ workflows: mockWorkflows }),
      });
    });

    it("should have search input", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/Search workflows/i),
        ).toBeInTheDocument();
      });
    });

    it("should have permission filter dropdown", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/Filter by permission/i),
        ).toBeInTheDocument();
      });
    });

    it("should have shared by filter dropdown", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/Filter by shared by/i),
        ).toBeInTheDocument();
      });
    });

    it("should filter by search text", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search workflows/i);
      fireEvent.change(searchInput, { target: { value: "Report" } });

      await waitFor(() => {
        expect(
          screen.queryByText("Customer Support Agent"),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByText("Data Processing Pipeline"),
        ).not.toBeInTheDocument();
        expect(screen.getByText("Report Generator")).toBeInTheDocument();
      });
    });

    it("should filter by permission", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      const permissionFilter = screen.getByLabelText(/Filter by permission/i);
      fireEvent.change(permissionFilter, { target: { value: "executor" } });

      await waitFor(() => {
        expect(
          screen.queryByText("Customer Support Agent"),
        ).not.toBeInTheDocument();
        expect(
          screen.getByText("Data Processing Pipeline"),
        ).toBeInTheDocument();
        expect(screen.queryByText("Report Generator")).not.toBeInTheDocument();
      });
    });

    it("should filter by shared by", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      const sharedByFilter = screen.getByLabelText(/Filter by shared by/i);
      fireEvent.change(sharedByFilter, {
        target: { value: "charlie@example.com" },
      });

      await waitFor(() => {
        expect(
          screen.queryByText("Customer Support Agent"),
        ).not.toBeInTheDocument();
        expect(
          screen.getByText("Data Processing Pipeline"),
        ).toBeInTheDocument();
        expect(screen.queryByText("Report Generator")).not.toBeInTheDocument();
      });
    });

    it("should combine multiple filters", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      // Filter by Alice's workflows
      const sharedByFilter = screen.getByLabelText(/Filter by shared by/i);
      fireEvent.change(sharedByFilter, {
        target: { value: "alice@example.com" },
      });

      // And filter for editor permission
      const permissionFilter = screen.getByLabelText(/Filter by permission/i);
      fireEvent.change(permissionFilter, { target: { value: "editor" } });

      await waitFor(() => {
        // Only Report Generator matches (alice + editor)
        expect(
          screen.queryByText("Customer Support Agent"),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByText("Data Processing Pipeline"),
        ).not.toBeInTheDocument();
        expect(screen.getByText("Report Generator")).toBeInTheDocument();
      });
    });

    it("should show no results message when filters match nothing", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/Search workflows/i);
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      await waitFor(() => {
        expect(screen.getByText(/No workflows match/i)).toBeInTheDocument();
      });
    });

    it("should have clear filters button", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      // Apply a filter first
      const searchInput = screen.getByPlaceholderText(/Search workflows/i);
      fireEvent.change(searchInput, { target: { value: "Report" } });

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Clear filters/i }),
        ).toBeInTheDocument();
      });
    });

    it("should clear all filters when clear button is clicked", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      // Apply filters
      const searchInput = screen.getByPlaceholderText(/Search workflows/i);
      fireEvent.change(searchInput, { target: { value: "Report" } });

      const permissionFilter = screen.getByLabelText(/Filter by permission/i);
      fireEvent.change(permissionFilter, { target: { value: "editor" } });

      await waitFor(() => {
        expect(screen.getByText("Report Generator")).toBeInTheDocument();
        expect(
          screen.queryByText("Customer Support Agent"),
        ).not.toBeInTheDocument();
      });

      // Click clear filters
      fireEvent.click(screen.getByRole("button", { name: /Clear filters/i }));

      await waitFor(() => {
        // All workflows should be visible again
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
        expect(
          screen.getByText("Data Processing Pipeline"),
        ).toBeInTheDocument();
        expect(screen.getByText("Report Generator")).toBeInTheDocument();
      });
    });

    it("should populate shared by dropdown with unique users", async () => {
      renderWithRouter(<SharedWorkflowsList />);

      await waitFor(() => {
        expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
      });

      const sharedByFilter = screen.getByLabelText(/Filter by shared by/i);

      // Should have the All option plus unique users
      const options = sharedByFilter.querySelectorAll("option");
      expect(options.length).toBe(3); // All + alice + charlie
    });
  });
});
