/**
 * ConnectionsPage Structure Tests
 *
 * Tests for page layout, connection list, filters, and actions.
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

  // Use camelCase properties to match what component expects after RTK Query transformation
  const mockConnections: MCPConnectionSummary[] = [
    {
      id: "conn-1",
      name: "Production Server",
      url: "https://prod.example.com",
      authType: "oauth2",
      status: "connected",
      serverName: "MCP Server",
      toolCount: 5,
      resourceCount: 3,
      promptCount: 2,
      lastConnectedAt: "2024-01-01T00:00:00Z",
      createdAt: "2024-01-01T00:00:00Z",
    } as unknown as MCPConnectionSummary,
    {
      id: "conn-2",
      name: "Development Server",
      url: "https://dev.example.com",
      authType: "api_key",
      status: "disconnected",
      serverName: null,
      toolCount: 0,
      resourceCount: 0,
      promptCount: 0,
      lastConnectedAt: null,
      createdAt: "2024-01-02T00:00:00Z",
    } as unknown as MCPConnectionSummary,
    {
      id: "conn-3",
      name: "Staging Server",
      url: "https://staging.example.com",
      authType: "none",
      status: "error",
      serverName: null,
      toolCount: 0,
      resourceCount: 0,
      promptCount: 0,
      lastConnectedAt: null,
      createdAt: "2024-01-03T00:00:00Z",
    } as unknown as MCPConnectionSummary,
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

describe("ConnectionsPage Structure", () => {
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

  describe("Server Information Display", () => {
    it("should display server name for connections with server info", () => {
      renderWithProviders(<ConnectionsPage />);
      expect(screen.getByText(/server: mcp server/i)).toBeInTheDocument();
    });
  });
});
