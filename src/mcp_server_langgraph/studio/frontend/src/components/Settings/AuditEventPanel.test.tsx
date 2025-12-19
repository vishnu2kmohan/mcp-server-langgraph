/**
 * AuditEventPanel Tests
 *
 * TDD tests for the audit event streaming panel.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock the useAuditWebSocket hook
const mockUseAuditWebSocket = vi.fn();
vi.mock("../../hooks/useAuditWebSocket", () => ({
  useAuditWebSocket: (...args: unknown[]) => mockUseAuditWebSocket(...args),
}));

// Import after mocks
import { AuditEventPanel } from "./AuditEventPanel";

// =============================================================================
// Test Data
// =============================================================================

const mockEvents = [
  {
    event_id: "evt-1",
    timestamp: "2025-01-15T10:30:00Z",
    category: "authentication",
    event_type: "login",
    actor: "user@example.com",
    resource: "/api/v1/auth/login",
    regulation: "SOC2",
  },
  {
    event_id: "evt-2",
    timestamp: "2025-01-15T10:25:00Z",
    category: "data_access",
    event_type: "read",
    actor: "admin@example.com",
    resource: "/api/v1/sessions/123",
    details: { session_id: "123" },
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("AuditEventPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuditWebSocket.mockReturnValue({
      status: "connected",
      isConnected: true,
      events: [],
      currentFilter: null,
      isPaused: false,
      setFilter: vi.fn(),
      clearFilter: vi.fn(),
      clearEvents: vi.fn(),
      pause: vi.fn(),
      resume: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    });
  });

  describe("basic rendering", () => {
    it("should render the audit event panel", () => {
      render(<AuditEventPanel />);
      expect(screen.getByTestId("audit-event-panel")).toBeInTheDocument();
    });

    it("should show connection status", () => {
      render(<AuditEventPanel />);
      expect(screen.getByTestId("audit-status")).toBeInTheDocument();
      expect(screen.getByText(/connected/i)).toBeInTheDocument();
    });

    it("should show empty state when no events", () => {
      render(<AuditEventPanel />);
      expect(screen.getByText(/no audit events/i)).toBeInTheDocument();
    });
  });

  describe("event display", () => {
    it("should display events when available", () => {
      mockUseAuditWebSocket.mockReturnValue({
        status: "connected",
        isConnected: true,
        events: mockEvents,
        currentFilter: null,
        isPaused: false,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      expect(screen.getByText("user@example.com")).toBeInTheDocument();
      expect(screen.getByText("admin@example.com")).toBeInTheDocument();
    });

    it("should show event category badges", () => {
      mockUseAuditWebSocket.mockReturnValue({
        status: "connected",
        isConnected: true,
        events: mockEvents,
        currentFilter: null,
        isPaused: false,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      expect(screen.getByText(/authentication/i)).toBeInTheDocument();
      expect(screen.getByText(/data_access/i)).toBeInTheDocument();
    });
  });

  describe("controls", () => {
    it("should have pause/resume button", () => {
      render(<AuditEventPanel />);
      expect(screen.getByTestId("pause-button")).toBeInTheDocument();
    });

    it("should call pause when pause button clicked", async () => {
      const mockPause = vi.fn();
      mockUseAuditWebSocket.mockReturnValue({
        status: "connected",
        isConnected: true,
        events: [],
        currentFilter: null,
        isPaused: false,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: vi.fn(),
        pause: mockPause,
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      fireEvent.click(screen.getByTestId("pause-button"));
      await waitFor(() => {
        expect(mockPause).toHaveBeenCalled();
      });
    });

    it("should show resume button when paused", () => {
      mockUseAuditWebSocket.mockReturnValue({
        status: "connected",
        isConnected: true,
        events: [],
        currentFilter: null,
        isPaused: true,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      expect(screen.getByText(/resume/i)).toBeInTheDocument();
    });

    it("should have clear events button", () => {
      mockUseAuditWebSocket.mockReturnValue({
        status: "connected",
        isConnected: true,
        events: mockEvents,
        currentFilter: null,
        isPaused: false,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      expect(screen.getByTestId("clear-button")).toBeInTheDocument();
    });

    it("should call clearEvents when clear button clicked", async () => {
      const mockClearEvents = vi.fn();
      mockUseAuditWebSocket.mockReturnValue({
        status: "connected",
        isConnected: true,
        events: mockEvents,
        currentFilter: null,
        isPaused: false,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: mockClearEvents,
        pause: vi.fn(),
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      fireEvent.click(screen.getByTestId("clear-button"));
      await waitFor(() => {
        expect(mockClearEvents).toHaveBeenCalled();
      });
    });
  });

  describe("disconnected state", () => {
    it("should show disconnected status when not connected", () => {
      mockUseAuditWebSocket.mockReturnValue({
        status: "disconnected",
        isConnected: false,
        events: [],
        currentFilter: null,
        isPaused: false,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
    });

    it("should show reconnect button when disconnected", () => {
      mockUseAuditWebSocket.mockReturnValue({
        status: "disconnected",
        isConnected: false,
        events: [],
        currentFilter: null,
        isPaused: false,
        setFilter: vi.fn(),
        clearFilter: vi.fn(),
        clearEvents: vi.fn(),
        pause: vi.fn(),
        resume: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });
      render(<AuditEventPanel />);
      expect(screen.getByTestId("reconnect-button")).toBeInTheDocument();
    });
  });
});
