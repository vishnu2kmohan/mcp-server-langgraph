/**
 * ConnectionsPage Test Utilities
 *
 * Shared mock data, mock functions, store factory, and render helpers
 * for ConnectionsPage tests.
 */

import { vi } from "vitest";
import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { personaSlice } from "../store/slices/personaSlice";
import type { MCPConnectionSummary } from "../types/connection";
import type React from "react";

// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Button } from "@/components/UI/Button";

// =============================================================================
// Hoisted Mock Functions and Data
// =============================================================================

export const {
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

// =============================================================================
// Store Factory
// =============================================================================

export const createTestStore = (
  persona: "admin" | "developer" | "user" = "admin",
) =>
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

// =============================================================================
// Render Helper
// =============================================================================

export const renderWithProviders = (component: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

// =============================================================================
// Mock Setup Functions
// =============================================================================

/**
 * Setup API module mocks - call this in test files that need to mock RTK Query hooks
 */
export const setupApiMocks = () => {
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
};

/**
 * Setup WebSocket hook mock
 */
export const setupWebSocketMock = () => {
  vi.mock("../hooks/useConnectionsRealtimeWebSocket", () => ({
    useConnectionsRealtimeWebSocket: () =>
      mockUseConnectionsRealtimeWebSocket(),
  }));
};

/**
 * Setup child component mocks
 */
export const setupComponentMocks = () => {
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
          <Button variant="danger" onClick={onClearSelection}>Clear</Button>
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
        <Button
          variant="primary"
          onClick={() => onSelect({ id: "github", name: "GitHub" })}>
          GitHub
        </Button>
        {showCustomOption && onCustom && (
          <Button variant="primary" onClick={onCustom}>Custom</Button>
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
};

/**
 * Setup MCP component mocks
 */
export const setupMCPMocks = () => {
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
        <Button
          variant="primary"
          data-testid="invoke-tool-btn"
          onClick={() => onToolInvoke?.("test-server::test-tool")}>
          Invoke Tool
        </Button>
        <Button
          variant="primary"
          data-testid="view-resource-btn"
          onClick={() => onResourceView?.("test-server::test-resource")}>
          View Resource
        </Button>
        <Button
          variant="primary"
          data-testid="test-prompt-btn"
          onClick={() => onPromptTest?.("test-server::test-prompt")}>
          Test Prompt
        </Button>
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
          <Button variant="secondary" onClick={onClose}>Close</Button>
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
          <Button variant="secondary" onClick={onClose}>Close</Button>
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
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>
      ) : null,
  }));
};
