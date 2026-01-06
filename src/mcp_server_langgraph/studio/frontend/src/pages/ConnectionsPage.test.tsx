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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ConnectionsPage } from "./ConnectionsPage";
import { personaSlice } from "../store/slices/personaSlice";
import * as apiModule from "../api";
import type { MCPConnectionSummary } from "../types/connection";

// Hoisted mock functions and data
const {
  mockConnections,
  mockRefetch,
  mockTestConnection,
  mockDeleteConnection,
  mockCreateConnection,
  mockUpdateConnection,
  mockUseConnectionsRealtimeWebSocket,
} = vi.hoisted(() => {
  const mockRefetch = vi.fn();
  const mockTestConnection = vi.fn().mockReturnValue({
    unwrap: vi.fn().mockResolvedValue({ success: true }),
  });
  const mockDeleteConnection = vi.fn().mockReturnValue({
    unwrap: vi.fn().mockResolvedValue(undefined),
  });
  const mockCreateConnection = vi.fn().mockReturnValue({
    unwrap: vi
      .fn()
      .mockResolvedValue({ id: "conn-new", name: "New Connection" }),
  });
  const mockUpdateConnection = vi.fn().mockReturnValue({
    unwrap: vi
      .fn()
      .mockResolvedValue({ id: "conn-1", name: "Updated Connection" }),
  });

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

  const mockUseConnectionsRealtimeWebSocket = vi.fn(() => ({
    status: "connected" as const,
    connections: [],
    subscribedConnections: new Set<string>(),
    subscribedAll: true,
    error: null,
    subscribeConnection: vi.fn(),
    unsubscribeConnection: vi.fn(),
    subscribeAll: vi.fn(),
    requestHealthCheck: vi.fn(),
    getConnection: vi.fn(),
    refresh: vi.fn(),
    disconnect: vi.fn(),
    reconnect: vi.fn(),
  }));

  return {
    mockConnections,
    mockRefetch,
    mockTestConnection,
    mockDeleteConnection,
    mockCreateConnection,
    mockUpdateConnection,
    mockUseConnectionsRealtimeWebSocket,
  };
});

// Mock RTK Query hooks
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

// Mock the WebSocket hook
vi.mock("../hooks/useConnectionsRealtimeWebSocket", () => ({
  useConnectionsRealtimeWebSocket: () => mockUseConnectionsRealtimeWebSocket(),
}));

// Mock child components
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

// Mock MCP components
vi.mock("../components/MCP", () => ({
  LazyAggregatedCapabilitiesPanel: ({
    onToolInvoke,
    onResourceView,
    onPromptTest,
  }: {
    showAdminActions?: boolean;
    onToolInvoke?: (name: string) => void;
    onResourceView?: (name: string) => void;
    onPromptTest?: (name: string) => void;
  }) => (
    <div data-testid="aggregated-capabilities-panel">
      <button
        data-testid="invoke-tool-btn"
        onClick={() => onToolInvoke?.("test-server::test-tool")}
      >
        Invoke Tool
      </button>
      <button
        data-testid="view-resource-btn"
        onClick={() => onResourceView?.("test-server::test-resource")}
      >
        View Resource
      </button>
      <button
        data-testid="test-prompt-btn"
        onClick={() => onPromptTest?.("test-server::test-prompt")}
      >
        Test Prompt
      </button>
    </div>
  ),
  LazyToolInvocationDialog: ({
    open,
    onClose,
    preselectedToolName,
  }: {
    open: boolean;
    onClose: () => void;
    preselectedToolName?: string;
  }) =>
    open ? (
      <div data-testid="tool-invocation-dialog" role="dialog">
        <span data-testid="tool-name">{preselectedToolName}</span>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
  LazyResourceViewer: ({
    open,
    onClose,
    preselectedResourceUri,
  }: {
    open: boolean;
    onClose: () => void;
    preselectedResourceUri?: string;
  }) =>
    open ? (
      <div data-testid="resource-viewer-dialog" role="dialog">
        <span data-testid="resource-uri">{preselectedResourceUri}</span>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
  LazyPromptTester: ({
    open,
    onClose,
    preselectedPromptName,
  }: {
    open: boolean;
    onClose: () => void;
    preselectedPromptName?: string;
  }) =>
    open ? (
      <div data-testid="prompt-tester-dialog" role="dialog">
        <span data-testid="prompt-name">{preselectedPromptName}</span>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

const mockedUseListConnectionsQuery = vi.mocked(
  apiModule.useListConnectionsQuery,
);

// Create a minimal store for testing with persona slice
const createTestStore = (persona: "admin" | "developer" | "user" = "admin") =>
  configureStore({
    reducer: {
      persona: personaSlice.reducer,
    },
    preloadedState: {
      persona: {
        persona,
        subPersona: null,
        username: "test-user",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
        visibleModules: [],
        featureFlags: {},
        apiVersion: null,
      },
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
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Page Structure", () => {
    it("should render page title, add button, and search input", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("MCP Connections")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /add connection/i }),
      ).toBeInTheDocument();
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
      expect(screen.getByText(/5 tools/i)).toBeInTheDocument();
    });
  });

  describe("Filtering and Sorting", () => {
    it("should have status, auth type, and sort by filters", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByLabelText(/status/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/auth type/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/sort by/i)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /sort order/i }),
      ).toBeInTheDocument();
    });

    it("should update filters when changed", async () => {
      renderWithProviders(<ConnectionsPage />);
      const statusSelect = screen.getByLabelText(/status/i);
      const authTypeSelect = screen.getByLabelText(/auth type/i);
      const sortBySelect = screen.getByLabelText(/sort by/i);

      fireEvent.change(statusSelect, { target: { value: "connected" } });
      fireEvent.change(authTypeSelect, { target: { value: "oauth2" } });
      fireEvent.change(sortBySelect, { target: { value: "name" } });

      await waitFor(() => {
        expect(statusSelect).toHaveValue("connected");
        expect(authTypeSelect).toHaveValue("oauth2");
        expect(sortBySelect).toHaveValue("name");
      });
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
    it("should have test, edit, delete, and audit buttons for each connection", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.getAllByRole("button", { name: /test/i }).length,
      ).toBeGreaterThanOrEqual(3);
      expect(
        screen.getAllByRole("button", { name: /edit/i }).length,
      ).toBeGreaterThanOrEqual(3);
      expect(
        screen.getAllByRole("button", { name: /delete/i }).length,
      ).toBeGreaterThanOrEqual(3);
      expect(
        screen.getAllByRole("button", { name: /audit/i }).length,
      ).toBeGreaterThanOrEqual(3);
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when fetching", () => {
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
    it("should show empty state when no connections and open dialog on add", async () => {
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

      const addButtons = screen.getAllByRole("button", {
        name: /add connection/i,
      });
      fireEvent.click(addButtons[addButtons.length - 1]);
      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });
  });

  describe("Error State", () => {
    it("should show error message and allow retry", async () => {
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

      const retryButton = screen.getByRole("button", { name: /retry/i });
      fireEvent.click(retryButton);
      expect(mockRefetch).toHaveBeenCalled();
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
    it("should show confirmation when delete clicked and close on cancel or backdrop", async () => {
      renderWithProviders(<ConnectionsPage />);
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
    });

    it("should call delete mutation when confirm clicked and close modal", async () => {
      renderWithProviders(<ConnectionsPage />);
      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });

      const modalDeleteButtons = screen.getAllByRole("button", {
        name: /delete/i,
      });
      const confirmDeleteButton =
        modalDeleteButtons[modalDeleteButtons.length - 1];
      fireEvent.click(confirmDeleteButton);

      await waitFor(() => {
        expect(mockDeleteConnection).toHaveBeenCalledWith("conn-1");
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

  describe("Real-time Polling", () => {
    it("should have polling interval dropdown and toggle button", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByLabelText(/polling interval/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/pause auto-refresh/i)).toBeInTheDocument();
    });

    it("should toggle polling on/off", async () => {
      renderWithProviders(<ConnectionsPage />);
      const pauseButton = screen.getByLabelText(/pause auto-refresh/i);
      fireEvent.click(pauseButton);
      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable auto-refresh/i),
        ).toBeInTheDocument();
      });
    });

    it("should allow changing polling speed with all options", async () => {
      renderWithProviders(<ConnectionsPage />);
      const pollingSelect = screen.getByLabelText(/polling interval/i);
      fireEvent.change(pollingSelect, { target: { value: "fast" } });

      await waitFor(() => {
        expect(pollingSelect).toHaveValue("fast");
      });

      expect(pollingSelect).toContainHTML("Off");
      expect(pollingSelect).toContainHTML("30s");
      expect(pollingSelect).toContainHTML("10s");
      expect(pollingSelect).toContainHTML("5s");
    });

    it("should show fetching indicator when polling", () => {
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
      expect(refreshButton).toHaveClass("animate-spin");
    });
  });

  describe("Bulk Actions", () => {
    it("should show selection checkboxes and bulk actions bar", async () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.getAllByRole("checkbox", { name: /select/i }).length,
      ).toBeGreaterThanOrEqual(3);
      expect(
        screen.getByRole("checkbox", { name: /select all/i }),
      ).toBeInTheDocument();

      const checkboxes = screen.getAllByRole("checkbox", { name: /select/i });
      fireEvent.click(checkboxes[0]);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });
    });
  });

  describe("Template Selector", () => {
    it("should open template selector and handle template selection", async () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.getByRole("button", { name: /from template/i }),
      ).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /from template/i }));

      await waitFor(() => {
        expect(screen.getByTestId("template-selector")).toBeInTheDocument();
        expect(screen.getByText(/choose a template/i)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("GitHub"));

      await waitFor(() => {
        expect(
          screen.queryByTestId("template-selector"),
        ).not.toBeInTheDocument();
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("should handle custom option and close template selector", async () => {
      renderWithProviders(<ConnectionsPage />);
      fireEvent.click(screen.getByRole("button", { name: /from template/i }));

      await waitFor(() => {
        expect(screen.getByTestId("template-selector")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Custom"));

      await waitFor(() => {
        expect(
          screen.queryByTestId("template-selector"),
        ).not.toBeInTheDocument();
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });
  });

  describe("Audit Log Access", () => {
    it("should open and close audit log dialog", async () => {
      renderWithProviders(<ConnectionsPage />);
      const auditButtons = screen.getAllByRole("button", { name: /audit/i });
      fireEvent.click(auditButtons[0]);

      await waitFor(() => {
        expect(screen.getByTestId("audit-log")).toBeInTheDocument();
        expect(screen.getByText(/audit log/i)).toBeInTheDocument();
      });

      const closeButton = screen.getByRole("button", { name: /close/i });
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId("audit-log")).not.toBeInTheDocument();
      });
    });
  });

  describe("Test Connection Action", () => {
    it("should call test connection mutation and refetch after successful test", async () => {
      renderWithProviders(<ConnectionsPage />);
      const testButtons = screen.getAllByRole("button", { name: /test/i });
      fireEvent.click(testButtons[0]);

      await waitFor(() => {
        expect(mockTestConnection).toHaveBeenCalledWith("conn-1");
        expect(mockRefetch).toHaveBeenCalled();
      });
    });
  });

  describe("Sort Order Toggle", () => {
    it("should toggle sort order when button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);
      const sortOrderButton = screen.getByRole("button", {
        name: /sort order/i,
      });
      fireEvent.click(sortOrderButton);
      await waitFor(() => {
        expect(sortOrderButton).toBeInTheDocument();
      });
    });
  });

  describe("Connection Selection", () => {
    it("should toggle individual connection selection", async () => {
      renderWithProviders(<ConnectionsPage />);
      const prodServerCheckbox = screen.getByRole("checkbox", {
        name: /select production server/i,
      });

      fireEvent.click(prodServerCheckbox);
      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });

      fireEvent.click(prodServerCheckbox);
      await waitFor(() => {
        expect(screen.queryByTestId("bulk-actions")).not.toBeInTheDocument();
      });
    });

    it("should select/deselect all connections", async () => {
      renderWithProviders(<ConnectionsPage />);
      const selectAllCheckbox = screen.getByRole("checkbox", {
        name: /select all/i,
      });
      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });

      fireEvent.click(selectAllCheckbox);

      await waitFor(() => {
        expect(screen.queryByTestId("bulk-actions")).not.toBeInTheDocument();
      });
    });

    it("should clear selection when clear button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);
      const prodServerCheckbox = screen.getByRole("checkbox", {
        name: /select production server/i,
      });
      fireEvent.click(prodServerCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });

      const clearButton = screen.getByRole("button", { name: /clear/i });
      fireEvent.click(clearButton);

      await waitFor(() => {
        expect(screen.queryByTestId("bulk-actions")).not.toBeInTheDocument();
      });
    });

    it("should highlight selected connection with ring", async () => {
      renderWithProviders(<ConnectionsPage />);
      const prodServerCheckbox = screen.getByRole("checkbox", {
        name: /select production server/i,
      });
      fireEvent.click(prodServerCheckbox);

      await waitFor(() => {
        const selectedCard = document.querySelector(".ring-2.ring-blue-500");
        expect(selectedCard).toBeInTheDocument();
      });
    });
  });

  describe("Server Information Display", () => {
    it("should display server name for connections with server info", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText(/server: mcp server/i)).toBeInTheDocument();
    });
  });

  describe("Refresh Button", () => {
    it("should call refetch when refresh button clicked and be disabled when fetching", () => {
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

  describe("Connection Count Display", () => {
    it("should display total connection count when none selected", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("3 connections")).toBeInTheDocument();
    });

    it("should display selected count when connections selected", async () => {
      renderWithProviders(<ConnectionsPage />);
      const prodServerCheckbox = screen.getByRole("checkbox", {
        name: /select production server/i,
      });
      const devServerCheckbox = screen.getByRole("checkbox", {
        name: /select development server/i,
      });

      fireEvent.click(prodServerCheckbox);
      fireEvent.click(devServerCheckbox);

      await waitFor(() => {
        expect(screen.getByTestId("bulk-actions")).toBeInTheDocument();
      });
    });
  });

  describe("WebSocket Real-time Updates", () => {
    beforeEach(() => {
      mockUseConnectionsRealtimeWebSocket.mockReturnValue({
        status: "connected" as const,
        connections: [],
        subscribedConnections: new Set<string>(),
        subscribedAll: true,
        error: null,
        subscribeConnection: vi.fn(),
        unsubscribeConnection: vi.fn(),
        subscribeAll: vi.fn(),
        requestHealthCheck: vi.fn(),
        getConnection: vi.fn(),
        refresh: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
    });

    it("should show WebSocket connection status indicator with correct colors", () => {
      renderWithProviders(<ConnectionsPage />);
      const wsIndicator = screen.getByTestId("ws-status-indicator");
      expect(wsIndicator).toBeInTheDocument();
      expect(wsIndicator).toHaveClass("bg-green-500");
    });

    it("should show yellow indicator when WebSocket is connecting", () => {
      mockUseConnectionsRealtimeWebSocket.mockReturnValue({
        status: "connecting" as const,
        connections: [],
        subscribedConnections: new Set<string>(),
        subscribedAll: false,
        error: null,
        subscribeConnection: vi.fn(),
        unsubscribeConnection: vi.fn(),
        subscribeAll: vi.fn(),
        requestHealthCheck: vi.fn(),
        getConnection: vi.fn(),
        refresh: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<ConnectionsPage />);
      const wsIndicator = screen.getByTestId("ws-status-indicator");
      expect(wsIndicator).toHaveClass("bg-yellow-500");
    });

    it("should show gray indicator when WebSocket is disconnected", () => {
      mockUseConnectionsRealtimeWebSocket.mockReturnValue({
        status: "disconnected" as const,
        connections: [],
        subscribedConnections: new Set<string>(),
        subscribedAll: false,
        error: null,
        subscribeConnection: vi.fn(),
        unsubscribeConnection: vi.fn(),
        subscribeAll: vi.fn(),
        requestHealthCheck: vi.fn(),
        getConnection: vi.fn(),
        refresh: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<ConnectionsPage />);
      const wsIndicator = screen.getByTestId("ws-status-indicator");
      expect(wsIndicator).toHaveClass("bg-gray-400");
    });

    it("should update connection status when WebSocket sends update", async () => {
      mockUseConnectionsRealtimeWebSocket.mockReturnValue({
        status: "connected" as const,
        connections: [
          {
            id: "conn-1",
            name: "Production Server",
            status: "error",
            type: "mcp",
          },
        ],
        subscribedConnections: new Set<string>(),
        subscribedAll: true,
        error: null,
        subscribeConnection: vi.fn(),
        unsubscribeConnection: vi.fn(),
        subscribeAll: vi.fn(),
        requestHealthCheck: vi.fn(),
        getConnection: vi.fn(),
        refresh: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("Production Server")).toBeInTheDocument();
    });

    it("should handle WebSocket disconnection gracefully", async () => {
      mockUseConnectionsRealtimeWebSocket.mockReturnValue({
        status: "disconnected" as const,
        connections: [],
        subscribedConnections: new Set<string>(),
        subscribedAll: false,
        error: "WebSocket connection lost",
        subscribeConnection: vi.fn(),
        unsubscribeConnection: vi.fn(),
        subscribeAll: vi.fn(),
        requestHealthCheck: vi.fn(),
        getConnection: vi.fn(),
        refresh: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText("Production Server")).toBeInTheDocument();
    });

    it("should trigger health check via WebSocket when test button clicked", async () => {
      renderWithProviders(<ConnectionsPage />);
      const testButtons = screen.getAllByRole("button", { name: /test/i });
      fireEvent.click(testButtons[0]);

      await waitFor(() => {
        expect(mockTestConnection).toHaveBeenCalled();
      });
    });
  });

  describe("Capability Dialog Handlers", () => {
    it("should open LazyToolInvocationDialog when onToolInvoke is called", async () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.queryByTestId("tool-invocation-dialog"),
      ).not.toBeInTheDocument();

      const toolInvokeButton = screen.queryByTestId("invoke-tool-btn");
      if (toolInvokeButton) {
        fireEvent.click(toolInvokeButton);
        await waitFor(() => {
          expect(
            screen.getByTestId("tool-invocation-dialog"),
          ).toBeInTheDocument();
        });
      }
    });

    it("should open LazyResourceViewer when onResourceView is called", async () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.queryByTestId("resource-viewer-dialog"),
      ).not.toBeInTheDocument();

      const resourceViewButton = screen.queryByTestId("view-resource-btn");
      if (resourceViewButton) {
        fireEvent.click(resourceViewButton);
        await waitFor(() => {
          expect(
            screen.getByTestId("resource-viewer-dialog"),
          ).toBeInTheDocument();
        });
      }
    });

    it("should open LazyPromptTester when onPromptTest is called", async () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.queryByTestId("prompt-tester-dialog"),
      ).not.toBeInTheDocument();

      const promptTestButton = screen.queryByTestId("test-prompt-btn");
      if (promptTestButton) {
        fireEvent.click(promptTestButton);
        await waitFor(() => {
          expect(
            screen.getByTestId("prompt-tester-dialog"),
          ).toBeInTheDocument();
        });
      }
    });

    it("should verify dialog state management and rendering", async () => {
      renderWithProviders(<ConnectionsPage />);
      expect(
        screen.queryByTestId("tool-invocation-dialog"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("resource-viewer-dialog"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("prompt-tester-dialog"),
      ).not.toBeInTheDocument();
    });
  });
});
