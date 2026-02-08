/**
 * WorkflowsTab Component Tests
 *
 * TDD tests for the project workflows tab component.
 * Features:
 * - Workflow list display
 * - Create workflow dialog
 * - Remove workflow
 * - Bulk selection with BulkActionBar
 * - Navigation to workflow builder
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
  cleanup,
} from "@testing-library/react";
import { WorkflowsTab } from "./WorkflowsTab";
import { TestProvider } from "@/test-utils";

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock fetch
const mockFetch = vi.fn();

// Mock workflow data (camelCase per ADR-0091 Phase 6)
const mockWorkflows = [
  { id: "wf-1", name: "Workflow One", createdAt: "2025-01-01T00:00:00Z" },
  { id: "wf-2", name: "Workflow Two", createdAt: "2025-01-02T00:00:00Z" },
  { id: "wf-3", name: "Workflow Three", createdAt: null },
];

describe("WorkflowsTab", () => {
  const mockOnRefresh = vi.fn();
  const defaultProps = {
    workflows: mockWorkflows,
    projectId: "project-123",
    onRefresh: mockOnRefresh,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    mockFetch.mockResolvedValue({ ok: true });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Workflow List Display", () => {
    it("should render workflow list", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Workflow One")).toBeInTheDocument();
      expect(screen.getByText("Workflow Two")).toBeInTheDocument();
      expect(screen.getByText("Workflow Three")).toBeInTheDocument();
    });

    it("should show created date for workflows with dates", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/Created 1\/1\/2025/)).toBeInTheDocument();
    });

    it("should show empty state when no workflows", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} workflows={[]} />
        </TestProvider>,
      );

      expect(screen.getByText(/no workflows yet/i)).toBeInTheDocument();
    });

    it("should have New Workflow button", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /new workflow/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Navigation", () => {
    it("should navigate to workflow builder when workflow is clicked", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Workflow One"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/workflows?id=wf-1");
    });
  });

  describe("Create Workflow", () => {
    it("should open dialog when New Workflow is clicked", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /new workflow/i }));

      expect(screen.getByText("Create New Workflow")).toBeInTheDocument();
    });

    it("should call API and refresh when workflow is created", async () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /new workflow/i }));

      const input = screen.getByLabelText("Workflow Name");
      fireEvent.change(input, { target: { value: "New Test Workflow" } });

      fireEvent.click(screen.getByRole("button", { name: /^create$/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/projects/project-123/workflows"),
          expect.objectContaining({ method: "POST" }),
        );
      });

      await waitFor(() => {
        expect(mockOnRefresh).toHaveBeenCalled();
      });
    });
  });

  describe("Remove Workflow", () => {
    it("should have remove button for each workflow", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      const removeButtons = screen.getAllByRole("button", {
        name: /remove workflow/i,
      });
      expect(removeButtons).toHaveLength(3);
    });

    it("should call API and refresh when workflow is removed", async () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      // Find "Workflow One" text element and get its parent row
      const workflowOneText = screen.getByText("Workflow One");
      // Navigate up to the main row div (cursor-pointer element)
      let workflowRow = workflowOneText.parentElement;
      while (workflowRow && !workflowRow.classList.contains("cursor-pointer")) {
        workflowRow = workflowRow.parentElement;
      }
      const removeButton = within(workflowRow!).getByRole("button", {
        name: /remove workflow/i,
      });
      fireEvent.click(removeButton);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/projects/project-123/workflows/wf-1",
          expect.objectContaining({ method: "DELETE" }),
        );
      });

      await waitFor(() => {
        expect(mockOnRefresh).toHaveBeenCalled();
      });
    });

    it("should not navigate when remove button is clicked", async () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      const removeButtons = screen.getAllByRole("button", {
        name: /remove workflow/i,
      });
      fireEvent.click(removeButtons[0]);

      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe("Search and Filter", () => {
    it("should render search input", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText(/search.*workflows/i),
      ).toBeInTheDocument();
    });

    it("should filter workflows by search query", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      // All workflows should be visible initially
      expect(screen.getByText("Workflow One")).toBeInTheDocument();
      expect(screen.getByText("Workflow Two")).toBeInTheDocument();
      expect(screen.getByText("Workflow Three")).toBeInTheDocument();

      // Type in search
      const searchInput = screen.getByPlaceholderText(/search.*workflows/i);
      fireEvent.change(searchInput, { target: { value: "One" } });

      // Only Workflow One should be visible
      expect(screen.getByText("Workflow One")).toBeInTheDocument();
      expect(screen.queryByText("Workflow Two")).not.toBeInTheDocument();
      expect(screen.queryByText("Workflow Three")).not.toBeInTheDocument();
    });

    it("should filter workflows case-insensitively", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText(/search.*workflows/i);
      fireEvent.change(searchInput, { target: { value: "one" } });

      // Workflow One should still be found with lowercase search
      expect(screen.getByText("Workflow One")).toBeInTheDocument();
    });

    it("should show empty message when no workflows match search", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      const searchInput = screen.getByPlaceholderText(/search.*workflows/i);
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      expect(screen.getByText(/no workflows match/i)).toBeInTheDocument();
    });

    it("should render sort dropdown", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByLabelText(/sort by/i)).toBeInTheDocument();
    });

    it("should sort workflows by name", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      // Change sort to name (ascending)
      const sortDropdown = screen.getByLabelText(/sort by/i);
      fireEvent.change(sortDropdown, { target: { value: "name" } });

      // After sorting by name: One, Three, Two (alphabetical)
      const workflowNames = screen.getAllByText(/Workflow (One|Two|Three)/);
      expect(workflowNames[0]).toHaveTextContent("Workflow One");
      expect(workflowNames[1]).toHaveTextContent("Workflow Three");
      expect(workflowNames[2]).toHaveTextContent("Workflow Two");
    });

    it("should sort workflows by date (default)", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      // Default is date descending, so workflows with dates come first (newest first)
      // wf-2 (Jan 2), wf-1 (Jan 1), wf-3 (null date last)
      const workflowNames = screen.getAllByText(/Workflow (One|Two|Three)/);
      expect(workflowNames[0]).toHaveTextContent("Workflow Two");
      expect(workflowNames[1]).toHaveTextContent("Workflow One");
      expect(workflowNames[2]).toHaveTextContent("Workflow Three");
    });
  });

  describe("Bulk Selection", () => {
    it("should render checkboxes for each workflow", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      const checkboxes = screen.getAllByRole("checkbox");
      // 3 workflow checkboxes + 1 select all
      expect(checkboxes.length).toBe(4);
    });

    it("should have select all checkbox", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByLabelText(/select all/i)).toBeInTheDocument();
    });

    it("should select all when select all is clicked", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      const selectAllCheckbox = screen.getByLabelText(/select all/i);
      fireEvent.click(selectAllCheckbox);

      const checkboxes = screen.getAllByRole("checkbox");
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toBeChecked();
      });
    });

    it("should show bulk action bar when workflows are selected", () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]); // First workflow checkbox

      expect(
        screen.getByRole("toolbar", { name: /bulk actions/i }),
      ).toBeInTheDocument();
      expect(screen.getByText(/1 selected/i)).toBeInTheDocument();
    });

    it("should bulk delete workflows when confirmed", async () => {
      render(
        <TestProvider>
          <WorkflowsTab {...defaultProps} />
        </TestProvider>,
      );

      // Select two workflows
      const checkboxes = screen.getAllByRole("checkbox");
      fireEvent.click(checkboxes[1]);
      fireEvent.click(checkboxes[2]);

      // Click delete
      fireEvent.click(screen.getByRole("button", { name: /delete/i }));

      // Confirm
      fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      await waitFor(() => {
        expect(mockOnRefresh).toHaveBeenCalled();
      });
    });
  });
});
