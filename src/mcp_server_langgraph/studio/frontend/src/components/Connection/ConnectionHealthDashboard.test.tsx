/**
 * ConnectionHealthDashboard Tests
 *
 * TDD tests for the real-time connection health monitoring dashboard.
 * Uses WebSocket for live updates.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ConnectionHealthDashboard } from "./ConnectionHealthDashboard";

// Mock the useConnectionHealthWebSocket hook
const mockReconnect = vi.fn();
const mockDisconnect = vi.fn();
const mockRefresh = vi.fn();
const mockCheckHealth = vi.fn();

// Mock data uses camelCase per ADR-0091 (transforms applied at API boundary)
vi.mock("../../hooks/useConnectionHealthWebSocket", () => ({
  useConnectionHealthWebSocket: vi.fn(() => ({
    status: "connected",
    connections: [
      {
        id: "1",
        name: "GitHub MCP",
        status: "connected",
        url: "https://github.example.com",
        authType: "oauth2",
        toolCount: 5,
        resourceCount: 3,
        promptCount: 2,
      },
      {
        id: "2",
        name: "Slack MCP",
        status: "disconnected",
        url: "https://slack.example.com",
        authType: "api_key",
        toolCount: 0,
        resourceCount: 0,
        promptCount: 0,
      },
      {
        id: "3",
        name: "Local MCP",
        status: "error",
        url: "http://localhost:3000",
        authType: "none",
        toolCount: 0,
        resourceCount: 0,
        promptCount: 0,
        lastError: "Connection refused",
      },
    ],
    error: null,
    lastPong: new Date().toISOString(),
    summary: {
      total: 3,
      connected: 1,
      disconnected: 1,
      connecting: 0,
      error: 1,
      authRequired: 0,
    },
    reconnect: mockReconnect,
    disconnect: mockDisconnect,
    refresh: mockRefresh,
    checkHealth: mockCheckHealth,
  })),
}));

import { useConnectionHealthWebSocket } from "../../hooks/useConnectionHealthWebSocket";
import { TestProvider } from "@/test-utils";
const mockedUseConnectionHealthWebSocket = vi.mocked(
  useConnectionHealthWebSocket,
);

describe("ConnectionHealthDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Component Structure", () => {
    it("should render dashboard title", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByText(/connection health/i)).toBeInTheDocument();
    });

    it("should show WebSocket connection status", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      // WebSocket status uses data-testid
      const wsStatus = screen.getByTestId("ws-status");
      expect(wsStatus).toHaveTextContent("Connected");
    });

    it("should show refresh button", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Health Summary", () => {
    it("should display total connections count", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("should display connected count with indicator", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      // Should have a connected indicator
      expect(screen.getByTestId("summary-connected")).toHaveTextContent("1");
    });

    it("should display disconnected count", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByTestId("summary-disconnected")).toHaveTextContent("1");
    });

    it("should display error count", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByTestId("summary-error")).toHaveTextContent("1");
    });
  });

  describe("Connection List", () => {
    it("should display all connections", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByText("GitHub MCP")).toBeInTheDocument();
      expect(screen.getByText("Slack MCP")).toBeInTheDocument();
      expect(screen.getByText("Local MCP")).toBeInTheDocument();
    });

    it("should show status indicators for each connection", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      // Each connection should have a status indicator
      const statusIndicators = screen.getAllByTestId(/status-indicator/);
      expect(statusIndicators.length).toBe(3);
    });

    it("should show tool counts for connected servers", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByText(/5 tools/i)).toBeInTheDocument();
    });

    it("should show error message for errored connections", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByText(/connection refused/i)).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should call refresh when button clicked", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

      expect(mockRefresh).toHaveBeenCalled();
    });

    it("should have check health button for each connection", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );

      const checkButtons = screen.getAllByRole("button", { name: /check/i });
      expect(checkButtons.length).toBe(3);
    });

    it("should call checkHealth with connection id", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );

      const checkButtons = screen.getAllByRole("button", { name: /check/i });
      fireEvent.click(checkButtons[0]);

      expect(mockCheckHealth).toHaveBeenCalledWith("1");
    });
  });

  describe("Disconnected State", () => {
    it("should show disconnected status when WebSocket not connected", () => {
      mockedUseConnectionHealthWebSocket.mockReturnValueOnce({
        status: "disconnected",
        connections: [],
        error: null,
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          authRequired: 0,
        },
        reconnect: mockReconnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
      });

      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      // WebSocket status uses data-testid
      const wsStatus = screen.getByTestId("ws-status");
      expect(wsStatus).toHaveTextContent("Disconnected");
    });

    it("should show reconnect button when disconnected", () => {
      mockedUseConnectionHealthWebSocket.mockReturnValueOnce({
        status: "disconnected",
        connections: [],
        error: null,
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          authRequired: 0,
        },
        reconnect: mockReconnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
      });

      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /reconnect/i }),
      ).toBeInTheDocument();
    });

    it("should call reconnect when reconnect clicked", () => {
      mockedUseConnectionHealthWebSocket.mockReturnValueOnce({
        status: "disconnected",
        connections: [],
        error: null,
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          authRequired: 0,
        },
        reconnect: mockReconnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
      });

      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /reconnect/i }));

      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("Error State", () => {
    it("should show error message when hook has error", () => {
      mockedUseConnectionHealthWebSocket.mockReturnValueOnce({
        status: "error",
        connections: [],
        error: "WebSocket connection failed",
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          authRequired: 0,
        },
        reconnect: mockReconnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
      });

      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(
        screen.getByText(/websocket connection failed/i),
      ).toBeInTheDocument();
    });
  });

  describe("Auto-connect", () => {
    it("should auto-connect on mount by default", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      // useConnectionHealthWebSocket auto-connects by default (no options needed)
      expect(mockedUseConnectionHealthWebSocket).toHaveBeenCalled();
    });
  });

  describe("Empty State", () => {
    it("should show empty message when no connections", () => {
      mockedUseConnectionHealthWebSocket.mockReturnValueOnce({
        status: "connected",
        connections: [],
        error: null,
        lastPong: new Date().toISOString(),
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          authRequired: 0,
        },
        reconnect: mockReconnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
      });

      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByText(/no connections/i)).toBeInTheDocument();
    });
  });

  describe("Last Pong Indicator", () => {
    it("should show last heartbeat time", () => {
      render(
        <TestProvider>
          <ConnectionHealthDashboard />
        </TestProvider>,
      );
      expect(screen.getByText(/last heartbeat/i)).toBeInTheDocument();
    });
  });
});
