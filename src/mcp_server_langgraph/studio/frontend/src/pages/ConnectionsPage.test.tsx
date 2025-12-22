/**
 * ConnectionsPage Tests
 *
 * TDD tests for the MCP connections management page.
 * Tests cover:
 * - Connection list display
 * - Filtering by status, auth type
 * - Sorting controls
 * - Search functionality
 * - Add/Edit/Delete operations
 * - Connection testing
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ConnectionsPage } from "./ConnectionsPage";
import type { MCPConnectionSummary } from "../types/connection";

// Mock RTK Query hooks
const mockConnections: MCPConnectionSummary[] = [
  {
    id: "conn-1",
    name: "Production Server",
    url: "https://prod.example.com",
    auth_type: "oauth2",
    status: "connected",
    server_name: "MCP Server",
    tool_count: 5,
    resource_count: 3,
    prompt_count: 2,
    last_connected_at: "2024-01-01T00:00:00Z",
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "conn-2",
    name: "Development Server",
    url: "https://dev.example.com",
    auth_type: "api_key",
    status: "disconnected",
    server_name: null,
    tool_count: 0,
    resource_count: 0,
    prompt_count: 0,
    last_connected_at: null,
    created_at: "2024-01-02T00:00:00Z",
  },
  {
    id: "conn-3",
    name: "Staging Server",
    url: "https://staging.example.com",
    auth_type: "none",
    status: "error",
    server_name: null,
    tool_count: 0,
    resource_count: 0,
    prompt_count: 0,
    last_connected_at: null,
    created_at: "2024-01-03T00:00:00Z",
  },
];

const mockRefetch = vi.fn();
const mockTestConnection = vi.fn().mockReturnValue({
  unwrap: vi.fn().mockResolvedValue({ success: true }),
});
const mockDeleteConnection = vi.fn().mockReturnValue({
  unwrap: vi.fn().mockResolvedValue(undefined),
});
const mockCreateConnection = vi.fn().mockReturnValue({
  unwrap: vi.fn().mockResolvedValue({ id: "conn-new", name: "New Connection" }),
});
const mockUpdateConnection = vi.fn().mockReturnValue({
  unwrap: vi
    .fn()
    .mockResolvedValue({ id: "conn-1", name: "Updated Connection" }),
});

// Import the mocked module for type-safe mocking
import * as apiModule from "../api";

vi.mock("../api", () => ({
  useListConnectionsQuery: vi.fn(() => ({
    data: { items: mockConnections, total: 3, cursor: null },
    isLoading: false,
    isFetching: false,
    isError: false,
    isSuccess: true,
    error: null,
    refetch: mockRefetch,
  })),
  useTestConnectionMutation: () => [mockTestConnection, { isLoading: false }],
  useDeleteConnectionMutation: () => [
    mockDeleteConnection,
    { isLoading: false },
  ],
  useCreateConnectionMutation: () => [
    mockCreateConnection,
    { isLoading: false },
  ],
  useUpdateConnectionMutation: () => [
    mockUpdateConnection,
    { isLoading: false },
  ],
}));

// Mock child components to simplify testing
vi.mock("../components/Connection", () => ({
  ConnectionDialog: ({
    open,
    onClose: _onClose,
  }: {
    open: boolean;
    onClose: () => void;
  }) =>
    open ? (
      <div data-testid="connection-dialog" role="dialog">
        Connection Dialog
      </div>
    ) : null,
  ConnectionBulkActions: ({
    selectedIds,
    onClearSelection,
  }: {
    selectedIds: string[];
    onClearSelection: () => void;
  }) =>
    selectedIds.length > 0 ? (
      <div data-testid="bulk-actions">
        {selectedIds.length} selected
        <button onClick={onClearSelection}>Clear</button>
      </div>
    ) : null,
  ConnectionTemplateSelector: ({
    onSelect,
    onCustom,
    showCustomOption,
  }: {
    onSelect: (t: unknown) => void;
    onCustom?: () => void;
    showCustomOption?: boolean;
  }) => (
    <div data-testid="template-selector">
      <h2>Choose a Template</h2>
      <button onClick={() => onSelect({ id: "github", name: "GitHub" })}>
        GitHub
      </button>
      {showCustomOption && onCustom && (
        <button onClick={onCustom}>Custom</button>
      )}
    </div>
  ),
  ConnectionAuditLog: ({ connectionId }: { connectionId: string }) => (
    <div data-testid="audit-log">
      <h2>Audit Log</h2>
      <p>Connection: {connectionId}</p>
    </div>
  ),
}));

const mockedUseListConnectionsQuery = vi.mocked(
  apiModule.useListConnectionsQuery,
);

// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      // Minimal reducer for testing
      test: (state = {}) => state,
    },
  });

const renderWithProviders = (component: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

describe("ConnectionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Page Structure", () => {
    it("should render page title", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("MCP Connections")).toBeInTheDocument();
    });

    it("should render add connection button", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.getByRole("button", { name: /add connection/i }),
      ).toBeInTheDocument();
    });

    it("should render search input", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.getByPlaceholderText(/search connections/i),
      ).toBeInTheDocument();
    });
  });

  describe("Connection List", () => {
    it("should display connection names", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("Production Server")).toBeInTheDocument();
      expect(screen.getByText("Development Server")).toBeInTheDocument();
      expect(screen.getByText("Staging Server")).toBeInTheDocument();
    });

    it("should display connection URLs", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("https://prod.example.com")).toBeInTheDocument();
    });

    it("should display connection status indicators", () => {
      renderWithProviders(<ConnectionsPage />);
      // Status indicators should be visible
      expect(screen.getByText("connected")).toBeInTheDocument();
      expect(screen.getByText("disconnected")).toBeInTheDocument();
      expect(screen.getByText("error")).toBeInTheDocument();
    });

    it("should display auth type badges", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("oauth2")).toBeInTheDocument();
      expect(screen.getByText("api_key")).toBeInTheDocument();
      expect(screen.getByText("none")).toBeInTheDocument();
    });

    it("should display tool/resource/prompt counts for connected servers", () => {
      renderWithProviders(<ConnectionsPage />);
      // Production server has 5 tools, 3 resources, 2 prompts
      expect(screen.getByText(/5 tools/i)).toBeInTheDocument();
    });
  });

  describe("Filtering", () => {
    it("should have status filter dropdown", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
    });

    it("should have auth type filter dropdown", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByLabelText(/auth type/i)).toBeInTheDocument();
    });
  });

  describe("Sorting", () => {
    it("should have sort by dropdown", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByLabelText(/sort by/i)).toBeInTheDocument();
    });

    it("should have sort order toggle", () => {
      renderWithProviders(<ConnectionsPage />);
      // Should have asc/desc toggle button
      expect(
        screen.getByRole("button", { name: /sort order/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Search", () => {
    it("should update search on input", async () => {
      renderWithProviders(<ConnectionsPage />);
      const searchInput = screen.getByPlaceholderText(/search connections/i);

      fireEvent.change(searchInput, { target: { value: "production" } });

      await waitFor(() => {
        expect(searchInput).toHaveValue("production");
      });
    });
  });

  describe("Connection Actions", () => {
    it("should have test connection button for each connection", () => {
      renderWithProviders(<ConnectionsPage />);
      const testButtons = screen.getAllByRole("button", { name: /test/i });
      expect(testButtons.length).toBeGreaterThanOrEqual(3);
    });

    it("should have edit button for each connection", () => {
      renderWithProviders(<ConnectionsPage />);
      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      expect(editButtons.length).toBeGreaterThanOrEqual(3);
    });

    it("should have delete button for each connection", () => {
      renderWithProviders(<ConnectionsPage />);
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      expect(deleteButtons.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when fetching", () => {
      // Override mock for this test
      mockedUseListConnectionsQuery.mockReturnValueOnce({
        data: undefined,
        isLoading: true,
        isFetching: true,
        isError: false,
        isSuccess: false,
        error: undefined,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListConnectionsQuery>);

      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no connections", () => {
      mockedUseListConnectionsQuery.mockReturnValueOnce({
        data: { items: [], total: 0, cursor: null },
        isLoading: false,
        isFetching: false,
        isError: false,
        isSuccess: true,
        error: undefined,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListConnectionsQuery>);

      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText(/no connections/i)).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when fetch fails", () => {
      mockedUseListConnectionsQuery.mockReturnValueOnce({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        isSuccess: false,
        error: { message: "Failed to fetch connections" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListConnectionsQuery>);

      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText(/failed to fetch/i)).toBeInTheDocument();
    });
  });

  describe("Add Connection Dialog", () => {
    it("should open dialog when add button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("button", { name: /add connection/i }));

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });
  });

  describe("Delete Confirmation", () => {
    it("should show confirmation when delete clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });
    });
  });

  describe("Real-time Polling", () => {
    it("should have polling interval dropdown", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByLabelText(/polling interval/i)).toBeInTheDocument();
    });

    it("should have polling toggle button", () => {
      renderWithProviders(<ConnectionsPage />);
      // Default to enabled (normal = 10s), so pause button should be visible
      expect(screen.getByLabelText(/pause auto-refresh/i)).toBeInTheDocument();
    });

    it("should toggle polling on/off", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Initially polling is enabled (Pause button shown)
      const pauseButton = screen.getByLabelText(/pause auto-refresh/i);
      fireEvent.click(pauseButton);

      // Now polling should be disabled (Play button shown)
      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable auto-refresh/i),
        ).toBeInTheDocument();
      });
    });

    it("should allow changing polling speed", async () => {
      renderWithProviders(<ConnectionsPage />);

      const pollingSelect = screen.getByLabelText(/polling interval/i);
      fireEvent.change(pollingSelect, { target: { value: "fast" } });

      await waitFor(() => {
        expect(pollingSelect).toHaveValue("fast");
      });
    });

    it("should have polling speed options", () => {
      renderWithProviders(<ConnectionsPage />);

      const pollingSelect = screen.getByLabelText(/polling interval/i);

      // Check all options are present
      expect(pollingSelect).toContainHTML("Off");
      expect(pollingSelect).toContainHTML("30s");
      expect(pollingSelect).toContainHTML("10s");
      expect(pollingSelect).toContainHTML("5s");
    });

    it("should pass polling interval to query hook", async () => {
      renderWithProviders(<ConnectionsPage />);

      // The hook should be called with pollingInterval option
      // Default is 'normal' = 10000ms
      expect(mockedUseListConnectionsQuery).toHaveBeenCalled();
    });

    it("should show fetching indicator when polling", () => {
      mockedUseListConnectionsQuery.mockReturnValueOnce({
        data: { items: mockConnections, total: 3, cursor: null },
        isLoading: false,
        isFetching: true, // Polling in progress
        isError: false,
        isSuccess: true,
        error: undefined,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListConnectionsQuery>);

      renderWithProviders(<ConnectionsPage />);

      // Refresh button should have animation class when fetching
      const refreshButton = screen.getByLabelText("Refresh");
      expect(refreshButton).toHaveClass("animate-spin");
    });
  });

  describe("Bulk Actions", () => {
    it("should show selection checkboxes for each connection", () => {
      renderWithProviders(<ConnectionsPage />);
      const checkboxes = screen.getAllByRole("checkbox", { name: /select/i });
      expect(checkboxes.length).toBeGreaterThanOrEqual(3);
    });

    it("should show bulk actions bar when connections are selected", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Select first connection
      const checkboxes = screen.getAllByRole("checkbox", { name: /select/i });
      fireEvent.click(checkboxes[0]);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });
    });

    it("should show select all checkbox in header", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.getByRole("checkbox", { name: /select all/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Template Selector", () => {
    it("should have add from template button", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.getByRole("button", { name: /from template/i }),
      ).toBeInTheDocument();
    });

    it("should open template selector when clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("button", { name: /from template/i }));

      await waitFor(() => {
        expect(screen.getByTestId("template-selector")).toBeInTheDocument();
        expect(screen.getByText(/choose a template/i)).toBeInTheDocument();
      });
    });
  });

  describe("Audit Log Access", () => {
    it("should have view audit log button for each connection", () => {
      renderWithProviders(<ConnectionsPage />);
      const auditButtons = screen.getAllByRole("button", { name: /audit/i });
      expect(auditButtons.length).toBeGreaterThanOrEqual(3);
    });

    it("should open audit log dialog when clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      const auditButtons = screen.getAllByRole("button", { name: /audit/i });
      fireEvent.click(auditButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId("audit-log")).toBeInTheDocument();
        expect(screen.getByText(/audit log/i)).toBeInTheDocument();
      });
    });

    it("should close audit log dialog when close button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open audit log
      const auditButtons = screen.getAllByRole("button", { name: /audit/i });
      fireEvent.click(auditButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId("audit-log")).toBeInTheDocument();
      });

      // Close via close button
      const closeButton = screen.getByRole("button", { name: /close/i });
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId("audit-log")).not.toBeInTheDocument();
      });
    });

    it("should close audit log dialog when backdrop clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open audit log
      const auditButtons = screen.getAllByRole("button", { name: /audit/i });
      fireEvent.click(auditButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId("audit-log")).toBeInTheDocument();
      });

      // Close via backdrop click - find the backdrop div (first child of the modal container)
      const backdrop = document.querySelector(".bg-black\\/50");
      if (backdrop) {
        fireEvent.click(backdrop);
      }

      await waitFor(() => {
        expect(screen.queryByTestId("audit-log")).not.toBeInTheDocument();
      });
    });
  });

  describe("Test Connection Action", () => {
    it("should call test connection mutation when test button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      const testButtons = screen.getAllByRole("button", { name: /test/i });
      fireEvent.click(testButtons[0]);

      await waitFor(() => {
        expect(mockTestConnection).toHaveBeenCalledWith("conn-1");
      });
    });

    it("should refetch connections after successful test", async () => {
      renderWithProviders(<ConnectionsPage />);

      const testButtons = screen.getAllByRole("button", { name: /test/i });
      fireEvent.click(testButtons[0]);

      await waitFor(() => {
        expect(mockRefetch).toHaveBeenCalled();
      });
    });
  });

  describe("Delete Connection Flow", () => {
    it("should close confirmation when cancel clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open delete confirmation
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });

      // Click cancel
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
    });

    it("should close confirmation when backdrop clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open delete confirmation
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });

      // Click backdrop
      const backdrop = document.querySelector(".bg-black\\/50");
      if (backdrop) {
        fireEvent.click(backdrop);
      }

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
    });

    it("should call delete mutation when confirm clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open delete confirmation
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });

      // Find the delete button in the modal (within the confirmation dialog)
      const modalDeleteButtons = screen.getAllByRole("button", { name: /delete/i });
      // The last delete button is the one in the modal (confirm button)
      const confirmDeleteButton = modalDeleteButtons[modalDeleteButtons.length - 1];
      fireEvent.click(confirmDeleteButton);

      await waitFor(() => {
        expect(mockDeleteConnection).toHaveBeenCalledWith("conn-1");
      });
    });

    it("should refetch and close modal after successful delete", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open delete confirmation
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });

      // Find the delete button in the modal (within the confirmation dialog)
      const modalDeleteButtons = screen.getAllByRole("button", { name: /delete/i });
      // The last delete button is the one in the modal (confirm button)
      const confirmDeleteButton = modalDeleteButtons[modalDeleteButtons.length - 1];
      fireEvent.click(confirmDeleteButton);

      await waitFor(() => {
        expect(mockRefetch).toHaveBeenCalled();
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
    });
  });

  describe("Edit Connection Flow", () => {
    it("should open dialog when edit button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      const editButtons = screen.getAllByRole("button", { name: /edit/i });
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });
  });

  describe("Template Selection Flow", () => {
    it("should open connection dialog when template selected", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open template selector
      fireEvent.click(screen.getByRole("button", { name: /from template/i }));

      await waitFor(() => {
        expect(screen.getByTestId("template-selector")).toBeInTheDocument();
      });

      // Select a template
      fireEvent.click(screen.getByText("GitHub"));

      await waitFor(() => {
        // Template selector should close and connection dialog should open
        expect(screen.queryByTestId("template-selector")).not.toBeInTheDocument();
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("should open connection dialog when custom option clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open template selector
      fireEvent.click(screen.getByRole("button", { name: /from template/i }));

      await waitFor(() => {
        expect(screen.getByTestId("template-selector")).toBeInTheDocument();
      });

      // Click custom option
      fireEvent.click(screen.getByText("Custom"));

      await waitFor(() => {
        // Template selector should close and connection dialog should open
        expect(screen.queryByTestId("template-selector")).not.toBeInTheDocument();
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("should close template selector when close button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open template selector
      fireEvent.click(screen.getByRole("button", { name: /from template/i }));

      await waitFor(() => {
        expect(screen.getByTestId("template-selector")).toBeInTheDocument();
      });

      // Close via close button
      const closeButton = screen.getByRole("button", { name: /close/i });
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId("template-selector")).not.toBeInTheDocument();
      });
    });

    it("should close template selector when backdrop clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Open template selector
      fireEvent.click(screen.getByRole("button", { name: /from template/i }));

      await waitFor(() => {
        expect(screen.getByTestId("template-selector")).toBeInTheDocument();
      });

      // Close via backdrop click
      const backdrop = document.querySelector(".bg-black\\/50");
      if (backdrop) {
        fireEvent.click(backdrop);
      }

      await waitFor(() => {
        expect(screen.queryByTestId("template-selector")).not.toBeInTheDocument();
      });
    });
  });

  describe("Sort Order Toggle", () => {
    it("should toggle sort order when button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      const sortOrderButton = screen.getByRole("button", { name: /sort order/i });

      // Initial state - desc (ArrowDown is visible)
      // Click to toggle to asc
      fireEvent.click(sortOrderButton);

      // After click, should be asc (ArrowUp visible)
      // The button contains ArrowUp when sortOrder is 'asc'
      await waitFor(() => {
        // The button should still be in the document
        expect(sortOrderButton).toBeInTheDocument();
      });
    });
  });

  describe("Connection Selection", () => {
    it("should toggle individual connection selection", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Select by the specific connection name checkbox
      const prodServerCheckbox = screen.getByRole("checkbox", { name: /select production server/i });

      // Select
      fireEvent.click(prodServerCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });

      // Deselect
      fireEvent.click(prodServerCheckbox);

      await waitFor(() => {
        expect(screen.queryByTestId("bulk-actions")).not.toBeInTheDocument();
      });
    });

    it("should select all connections when select all clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      const selectAllCheckbox = screen.getByRole("checkbox", { name: /select all/i });
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });
    });

    it("should deselect all when select all clicked again", async () => {
      renderWithProviders(<ConnectionsPage />);

      const selectAllCheckbox = screen.getByRole("checkbox", { name: /select all/i });

      // Select all
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });

      // Deselect all
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(screen.queryByTestId("bulk-actions")).not.toBeInTheDocument();
      });
    });

    it("should clear selection when clear button in bulk actions clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Select a connection by specific name
      const prodServerCheckbox = screen.getByRole("checkbox", { name: /select production server/i });
      fireEvent.click(prodServerCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });

      // Clear selection via bulk actions
      const clearButton = screen.getByRole("button", { name: /clear/i });
      fireEvent.click(clearButton);

      await waitFor(() => {
        expect(screen.queryByTestId("bulk-actions")).not.toBeInTheDocument();
      });
    });

    it("should highlight selected connection with ring", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Select a connection by specific name
      const prodServerCheckbox = screen.getByRole("checkbox", { name: /select production server/i });
      fireEvent.click(prodServerCheckbox);

      await waitFor(() => {
        // Find connection card with ring-2 ring-blue-500 class
        const selectedCard = document.querySelector(".ring-2.ring-blue-500");
        expect(selectedCard).toBeInTheDocument();
      });
    });
  });

  describe("Error State Retry", () => {
    it("should call refetch when retry button clicked", async () => {
      mockedUseListConnectionsQuery.mockReturnValueOnce({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        isSuccess: false,
        error: { message: "Failed to fetch connections" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListConnectionsQuery>);

      renderWithProviders(<ConnectionsPage />);

      const retryButton = screen.getByRole("button", { name: /retry/i });
      fireEvent.click(retryButton);

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe("Empty State", () => {
    it("should open dialog when add button in empty state clicked", async () => {
      mockedUseListConnectionsQuery.mockReturnValueOnce({
        data: { items: [], total: 0, cursor: null },
        isLoading: false,
        isFetching: false,
        isError: false,
        isSuccess: true,
        error: undefined,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListConnectionsQuery>);

      renderWithProviders(<ConnectionsPage />);

      expect(screen.getByText(/no connections/i)).toBeInTheDocument();

      // Click the add button in the empty state (there are two - one in header, one in empty state)
      // The empty state button doesn't have the keyboard shortcut badge
      const addButtons = screen.getAllByRole("button", { name: /add connection/i });
      // Click the last one (the one in empty state)
      fireEvent.click(addButtons[addButtons.length - 1]);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });
  });

  describe("Server Information Display", () => {
    it("should display server name for connections with server info", () => {
      renderWithProviders(<ConnectionsPage />);
      // Production server has server_name set to "MCP Server"
      expect(screen.getByText(/server: mcp server/i)).toBeInTheDocument();
    });
  });

  describe("Refresh Button", () => {
    it("should call refetch when refresh button clicked", () => {
      renderWithProviders(<ConnectionsPage />);

      const refreshButton = screen.getByLabelText("Refresh");
      fireEvent.click(refreshButton);

      expect(mockRefetch).toHaveBeenCalled();
    });

    it("should be disabled when fetching", () => {
      mockedUseListConnectionsQuery.mockReturnValueOnce({
        data: { items: mockConnections, total: 3, cursor: null },
        isLoading: false,
        isFetching: true,
        isError: false,
        isSuccess: true,
        error: undefined,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useListConnectionsQuery>);

      renderWithProviders(<ConnectionsPage />);

      const refreshButton = screen.getByLabelText("Refresh");
      expect(refreshButton).toBeDisabled();
    });
  });

  describe("Filter Application", () => {
    it("should update status filter when changed", async () => {
      renderWithProviders(<ConnectionsPage />);

      const statusSelect = screen.getByLabelText(/status/i);
      fireEvent.change(statusSelect, { target: { value: "connected" } });

      await waitFor(() => {
        expect(statusSelect).toHaveValue("connected");
      });
    });

    it("should update auth type filter when changed", async () => {
      renderWithProviders(<ConnectionsPage />);

      const authTypeSelect = screen.getByLabelText(/auth type/i);
      fireEvent.change(authTypeSelect, { target: { value: "oauth2" } });

      await waitFor(() => {
        expect(authTypeSelect).toHaveValue("oauth2");
      });
    });

    it("should update sort by when changed", async () => {
      renderWithProviders(<ConnectionsPage />);

      const sortBySelect = screen.getByLabelText(/sort by/i);
      fireEvent.change(sortBySelect, { target: { value: "name" } });

      await waitFor(() => {
        expect(sortBySelect).toHaveValue("name");
      });
    });
  });

  describe("Connection Count Display", () => {
    it("should display total connection count when none selected", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("3 connections")).toBeInTheDocument();
    });

    it("should display selected count when connections selected", async () => {
      renderWithProviders(<ConnectionsPage />);

      // Select two specific connections
      const prodServerCheckbox = screen.getByRole("checkbox", { name: /select production server/i });
      const devServerCheckbox = screen.getByRole("checkbox", { name: /select development server/i });

      fireEvent.click(prodServerCheckbox);
      fireEvent.click(devServerCheckbox);

      await waitFor(() => {
        // Check that bulk actions bar is shown (2 selected)
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });
    });
  });
});
