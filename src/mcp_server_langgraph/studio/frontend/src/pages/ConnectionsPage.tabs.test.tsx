/**
 * ConnectionsPage Tab Layout Tests
 *
 * Tests for the Three-Tab layout (Discover / My Connectors / Capabilities)
 * as specified in ADR-0102.
 *
 * @see ADR-0102 - Connections Page Redesign
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import personaReducer from "../store/slices/personaSlice";

// Mock the hooks and API
const mockListConnections = vi.fn();
const mockListTemplates = vi.fn();
const mockTestConnection = vi.fn();
const mockDeleteConnection = vi.fn();
const mockCreateConnection = vi.fn();
const mockUpdateConnection = vi.fn();

vi.mock("../api", () => ({
  useListConnectionsQuery: () => mockListConnections(),
  useListConnectionTemplatesQuery: () => mockListTemplates(),
  useTestConnectionMutation: () => [mockTestConnection, { isLoading: false }],
  useDeleteConnectionMutation: () => [mockDeleteConnection, { isLoading: false }],
  useCreateConnectionMutation: () => [mockCreateConnection, { isLoading: false }],
  useUpdateConnectionMutation: () => [mockUpdateConnection, { isLoading: false }],
  // Export transformSnakeToCamel as identity function since mock data is already camelCase
  transformSnakeToCamel: <T,>(obj: T): T => obj,
}));

// Mock the WebSocket hooks
vi.mock("../hooks/useConnectionsRealtimeWebSocket", () => ({
  useConnectionsRealtimeWebSocket: () => ({
    status: "connected",
    connections: [],
    subscribeAll: vi.fn(),
    requestHealthCheck: vi.fn(),
    error: null,
  }),
}));

vi.mock("../hooks/useMCPWebSocket", () => ({
  useMCPWebSocket: () => ({
    status: "connected",
    isInitialized: true,
    serverInfo: null,
    error: null,
  }),
}));

// Mock lazy components
vi.mock("../components/MCP", () => ({
  LazyAggregatedCapabilitiesPanel: () => <div data-testid="aggregated-capabilities-panel" />,
  LazyToolInvocationDialog: () => null,
  LazyResourceViewer: () => null,
  LazyPromptTester: () => null,
}));

// Import after mocks
import { ConnectionsPage } from "./ConnectionsPage";

const createTestStore = () =>
  configureStore({
    reducer: {
      persona: personaReducer,
    },
  });

const renderWithProviders = (ui: React.ReactNode) => {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <MemoryRouter>{ui}</MemoryRouter>
    </Provider>
  );
};

const mockConnectionsData = {
  items: [
    {
      id: "conn-1",
      name: "GitHub Connection",
      url: "https://api.github.com/mcp",
      status: "connected",
      authType: "oauth2",
      toolCount: 5,
      resourceCount: 3,
      promptCount: 2,
      serverName: "GitHub MCP",
    },
  ],
  total: 1,
};

const mockTemplatesData = {
  templates: [
    {
      id: "github",
      name: "GitHub",
      description: "Access GitHub repositories",
      icon: "github",
      authType: "oauth2",
      defaultUrl: "https://api.github.com/mcp",
      category: "development",
      oauth2Scopes: [],
      configFields: [],
      keywords: ["github", "repo"],
      popularity: 95,
      documentationUrl: "https://docs.github.com/",
    },
    {
      id: "slack",
      name: "Slack",
      description: "Access Slack channels",
      icon: "slack",
      authType: "oauth2",
      defaultUrl: "https://slack.com/api/mcp",
      category: "communication",
      oauth2Scopes: [],
      configFields: [],
      keywords: ["slack", "channel"],
      popularity: 90,
      documentationUrl: null,
    },
  ],
};

describe("ConnectionsPage Tab Layout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListConnections.mockReturnValue({
      data: mockConnectionsData,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: vi.fn(),
    });
    mockListTemplates.mockReturnValue({
      data: mockTemplatesData,
      isLoading: false,
      error: null,
    });
  });

  describe("Tab Rendering", () => {
    it("should render three tabs: Discover, My Connectors, Capabilities", () => {
      renderWithProviders(<ConnectionsPage />);

      expect(screen.getByRole("tab", { name: /discover/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /my connectors/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /capabilities/i })).toBeInTheDocument();
    });

    it("should default to My Connectors tab", () => {
      renderWithProviders(<ConnectionsPage />);

      const myConnectorsTab = screen.getByRole("tab", { name: /my connectors/i });
      expect(myConnectorsTab).toHaveAttribute("aria-selected", "true");
    });

    it("should show connection count badge on My Connectors tab", () => {
      renderWithProviders(<ConnectionsPage />);

      // The tab should show the count of connections
      expect(screen.getByText("1")).toBeInTheDocument();
    });
  });

  describe("Tab Navigation", () => {
    it("should switch to Discover tab when clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("tab", { name: /discover/i }));

      await waitFor(() => {
        expect(screen.getByRole("tab", { name: /discover/i })).toHaveAttribute(
          "aria-selected",
          "true"
        );
      });
    });

    it("should show ConnectorDirectory in Discover tab", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("tab", { name: /discover/i }));

      await waitFor(() => {
        // Should show connector templates in grid layout
        expect(screen.getByRole("list", { name: /connector templates/i })).toBeInTheDocument();
      });
    });

    it("should switch to Capabilities tab when clicked", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("tab", { name: /capabilities/i }));

      await waitFor(() => {
        expect(screen.getByRole("tab", { name: /capabilities/i })).toHaveAttribute(
          "aria-selected",
          "true"
        );
      });
    });

    it("should show CapabilitiesTab content in Capabilities tab", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("tab", { name: /capabilities/i }));

      await waitFor(() => {
        expect(screen.getByTestId("aggregated-capabilities-panel")).toBeInTheDocument();
      });
    });
  });

  describe("Discover Tab Content", () => {
    it("should show connector templates sorted by popularity", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("tab", { name: /discover/i }));

      await waitFor(() => {
        const cards = screen.getAllByRole("article");
        // GitHub (95) should be before Slack (90)
        expect(cards[0]).toHaveTextContent("GitHub");
      });
    });

    it("should show category filter chips", async () => {
      renderWithProviders(<ConnectionsPage />);

      fireEvent.click(screen.getByRole("tab", { name: /discover/i }));

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /all/i })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /development/i })).toBeInTheDocument();
      });
    });
  });

  describe("My Connectors Tab Content", () => {
    it("should show existing connections list", () => {
      renderWithProviders(<ConnectionsPage />);

      // Default tab should show connections
      expect(screen.getByText("GitHub Connection")).toBeInTheDocument();
    });

    it("should show connection status badges", () => {
      renderWithProviders(<ConnectionsPage />);

      expect(screen.getByText("connected")).toBeInTheDocument();
    });

    it("should show Add Connection button", () => {
      renderWithProviders(<ConnectionsPage />);

      expect(screen.getByRole("button", { name: /add connection/i })).toBeInTheDocument();
    });
  });

  describe("Tab Accessibility", () => {
    it("should have proper tablist role", () => {
      renderWithProviders(<ConnectionsPage />);

      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });

    it("should have proper tab roles", () => {
      renderWithProviders(<ConnectionsPage />);

      const tabs = screen.getAllByRole("tab");
      expect(tabs).toHaveLength(3);
    });

    it("should have proper tabpanel role for content", () => {
      renderWithProviders(<ConnectionsPage />);

      expect(screen.getByRole("tabpanel")).toBeInTheDocument();
    });
  });
});
