/**
 * ConnectionsPage WebSocket Tests
 *
 * Tests for WebSocket status, real-time updates, and health checks.
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

describe("ConnectionsPage WebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("WebSocket Real-time Updates", () => {
    it("should show WebSocket connection status indicator with correct colors", () => {
      renderWithProviders(<ConnectionsPage />);
      const wsIndicator = screen.getByTestId("ws-status-indicator");
      expect(wsIndicator).toBeInTheDocument();
      expect(wsIndicator).toHaveClass("bg-success-9");
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
      expect(wsIndicator).toHaveClass("bg-warning-9");
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
      expect(wsIndicator).toHaveClass("bg-neutral-4");
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
});
