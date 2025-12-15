/**
 * ConnectionHealthDashboard Tests
 *
 * TDD tests for the real-time connection health monitoring dashboard.
 * Uses WebSocket for live updates.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConnectionHealthDashboard } from "./ConnectionHealthDashboard";

// Mock the useConnectionHealth hook
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
const mockRefresh = vi.fn();
const mockCheckHealth = vi.fn();

vi.mock("../../hooks/useConnectionHealth", () => ({
  useConnectionHealth: vi.fn(() => ({
    isConnected: true,
    connections: [
      {
        id: "1",
        name: "GitHub MCP",
        status: "connected",
        url: "https://github.example.com",
        auth_type: "oauth2",
        tool_count: 5,
        resource_count: 3,
        prompt_count: 2,
      },
      {
        id: "2",
        name: "Slack MCP",
        status: "disconnected",
        url: "https://slack.example.com",
        auth_type: "api_key",
        tool_count: 0,
        resource_count: 0,
        prompt_count: 0,
      },
      {
        id: "3",
        name: "Local MCP",
        status: "error",
        url: "http://localhost:3000",
        auth_type: "none",
        tool_count: 0,
        resource_count: 0,
        prompt_count: 0,
        last_error: "Connection refused",
      },
    ],
    error: null,
    lastPong: new Date(),
    summary: {
      total: 3,
      connected: 1,
      disconnected: 1,
      connecting: 0,
      error: 1,
      auth_required: 0,
    },
    connect: mockConnect,
    disconnect: mockDisconnect,
    refresh: mockRefresh,
    checkHealth: mockCheckHealth,
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
  })),
}));

import { useConnectionHealth } from "../../hooks/useConnectionHealth";
const mockedUseConnectionHealth = vi.mocked(useConnectionHealth);

describe("ConnectionHealthDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Component Structure", () => {
    it("should render dashboard title", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByText(/connection health/i)).toBeInTheDocument();
    });

    it("should show WebSocket connection status", () => {
      render(<ConnectionHealthDashboard />);
      // WebSocket status uses data-testid
      const wsStatus = screen.getByTestId("ws-status");
      expect(wsStatus).toHaveTextContent("Connected");
    });

    it("should show refresh button", () => {
      render(<ConnectionHealthDashboard />);
      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Health Summary", () => {
    it("should display total connections count", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("should display connected count with indicator", () => {
      render(<ConnectionHealthDashboard />);
      // Should have a connected indicator
      expect(screen.getByTestId("summary-connected")).toHaveTextContent("1");
    });

    it("should display disconnected count", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByTestId("summary-disconnected")).toHaveTextContent("1");
    });

    it("should display error count", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByTestId("summary-error")).toHaveTextContent("1");
    });
  });

  describe("Connection List", () => {
    it("should display all connections", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByText("GitHub MCP")).toBeInTheDocument();
      expect(screen.getByText("Slack MCP")).toBeInTheDocument();
      expect(screen.getByText("Local MCP")).toBeInTheDocument();
    });

    it("should show status indicators for each connection", () => {
      render(<ConnectionHealthDashboard />);
      // Each connection should have a status indicator
      const statusIndicators = screen.getAllByTestId(/status-indicator/);
      expect(statusIndicators.length).toBe(3);
    });

    it("should show tool counts for connected servers", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByText(/5 tools/i)).toBeInTheDocument();
    });

    it("should show error message for errored connections", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByText(/connection refused/i)).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should call refresh when button clicked", () => {
      render(<ConnectionHealthDashboard />);

      fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

      expect(mockRefresh).toHaveBeenCalled();
    });

    it("should have check health button for each connection", () => {
      render(<ConnectionHealthDashboard />);

      const checkButtons = screen.getAllByRole("button", { name: /check/i });
      expect(checkButtons.length).toBe(3);
    });

    it("should call checkHealth with connection id", () => {
      render(<ConnectionHealthDashboard />);

      const checkButtons = screen.getAllByRole("button", { name: /check/i });
      fireEvent.click(checkButtons[0]);

      expect(mockCheckHealth).toHaveBeenCalledWith("1");
    });
  });

  describe("Disconnected State", () => {
    it("should show disconnected status when WebSocket not connected", () => {
      mockedUseConnectionHealth.mockReturnValueOnce({
        isConnected: false,
        connections: [],
        error: null,
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          auth_required: 0,
        },
        connect: mockConnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
      });

      render(<ConnectionHealthDashboard />);
      // WebSocket status uses data-testid
      const wsStatus = screen.getByTestId("ws-status");
      expect(wsStatus).toHaveTextContent("Disconnected");
    });

    it("should show reconnect button when disconnected", () => {
      mockedUseConnectionHealth.mockReturnValueOnce({
        isConnected: false,
        connections: [],
        error: null,
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          auth_required: 0,
        },
        connect: mockConnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
      });

      render(<ConnectionHealthDashboard />);
      expect(
        screen.getByRole("button", { name: /reconnect/i }),
      ).toBeInTheDocument();
    });

    it("should call connect when reconnect clicked", () => {
      mockedUseConnectionHealth.mockReturnValueOnce({
        isConnected: false,
        connections: [],
        error: null,
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          auth_required: 0,
        },
        connect: mockConnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
      });

      render(<ConnectionHealthDashboard />);
      fireEvent.click(screen.getByRole("button", { name: /reconnect/i }));

      expect(mockConnect).toHaveBeenCalled();
    });
  });

  describe("Error State", () => {
    it("should show error message when hook has error", () => {
      mockedUseConnectionHealth.mockReturnValueOnce({
        isConnected: false,
        connections: [],
        error: "WebSocket connection failed",
        lastPong: null,
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          auth_required: 0,
        },
        connect: mockConnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
      });

      render(<ConnectionHealthDashboard />);
      expect(
        screen.getByText(/websocket connection failed/i),
      ).toBeInTheDocument();
    });
  });

  describe("Auto-connect", () => {
    it("should auto-connect on mount by default", () => {
      render(<ConnectionHealthDashboard />);
      // The hook should be called with autoConnect: true
      expect(mockedUseConnectionHealth).toHaveBeenCalledWith({
        autoConnect: true,
      });
    });
  });

  describe("Empty State", () => {
    it("should show empty message when no connections", () => {
      mockedUseConnectionHealth.mockReturnValueOnce({
        isConnected: true,
        connections: [],
        error: null,
        lastPong: new Date(),
        summary: {
          total: 0,
          connected: 0,
          disconnected: 0,
          connecting: 0,
          error: 0,
          auth_required: 0,
        },
        connect: mockConnect,
        disconnect: mockDisconnect,
        refresh: mockRefresh,
        checkHealth: mockCheckHealth,
        subscribe: vi.fn(),
        unsubscribe: vi.fn(),
      });

      render(<ConnectionHealthDashboard />);
      expect(screen.getByText(/no connections/i)).toBeInTheDocument();
    });
  });

  describe("Last Pong Indicator", () => {
    it("should show last heartbeat time", () => {
      render(<ConnectionHealthDashboard />);
      expect(screen.getByText(/last heartbeat/i)).toBeInTheDocument();
    });
  });
});
