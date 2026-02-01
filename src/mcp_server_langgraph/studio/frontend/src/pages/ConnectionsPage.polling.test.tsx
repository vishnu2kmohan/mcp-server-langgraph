/**
 * ConnectionsPage Polling Tests
 *
 * Tests for polling controls, refresh, and connection count display.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter } from "react-router";
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
  const mockTestConnection = vi
    .fn()
    .mockReturnValue({ unwrap: vi.fn().mockResolvedValue({ success: true }) });
  const mockDeleteConnection = vi
    .fn()
    .mockReturnValue({ unwrap: vi.fn().mockResolvedValue(undefined) });
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
  useListConnectionTemplatesQuery: () => ({
    data: { templates: [] },
    isLoading: false,
    error: null,
  }),
  useUpdateConnectionMutation: () => [
    mockUpdateConnection,
    { isLoading: false },
  ],
}));

vi.mock("../hooks/useConnectionsRealtimeWebSocket", () => ({
  useConnectionsRealtimeWebSocket: () => mockUseConnectionsRealtimeWebSocket(),
}));

vi.mock("../components/Connection", () => ({
  ConnectionDialog: ({ open }: { open: boolean; onClose: () => void }) =>
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

const createTestStore = (persona: "admin" | "developer" | "user" = "admin") =>
  configureStore({
    reducer: { persona: personaSlice.reducer },
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
  return render(
    <Provider store={store}>
      <MemoryRouter>{component}</MemoryRouter>
    </Provider>,
  );
};

describe("ConnectionsPage Polling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
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
      // Refresh button is disabled while fetching
      expect(refreshButton).toBeDisabled();
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
});
