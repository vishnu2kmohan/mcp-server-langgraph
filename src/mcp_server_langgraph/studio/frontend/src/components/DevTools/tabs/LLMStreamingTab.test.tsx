/**
 * LLMStreamingTab Component Tests
 *
 * TDD tests for real-time LLM streaming observability panel.
 * Displays TTFC, inter-chunk latency, and active stream status.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { LLMStreamingTab } from "./LLMStreamingTab";
import authReducer from "../../../store/slices/authSlice";
import notificationReducer from "../../../store/slices/notificationSlice";

// =============================================================================
// Mocks
// =============================================================================

// Mock the useLLMStreamingWebSocket hook
const mockUseLLMStreamingWebSocket = vi.fn();

vi.mock("../../../hooks/useLLMStreamingWebSocket", () => ({
  useLLMStreamingWebSocket: () => mockUseLLMStreamingWebSocket(),
}));

// Mock useParams for session ID
vi.mock("react-router", () => ({
  useParams: () => ({ sessionId: "test-session-123" }),
}));

// =============================================================================
// Test Helpers
// =============================================================================

function createTestStore() {
  return configureStore({
    reducer: {
      auth: authReducer,
      notifications: notificationReducer,
    },
    preloadedState: {
      auth: {
        isAuthenticated: true,
        accessToken: "test-token",
        refreshToken: null,
        user: null,
        isLoading: false,
        error: null,
        tokenExpiry: null,
        dpopNonce: null,
      },
    },
  });
}

function renderWithProvider(ui: React.ReactElement) {
  const store = createTestStore();
  return render(<Provider store={store}>{ui}</Provider>);
}

// =============================================================================
// Test Data
// =============================================================================

const mockActiveStream = {
  streamId: "stream-abc-123",
  sessionId: "test-session-123",
  model: "gpt-4",
  provider: "openai",
  startedAt: new Date().toISOString(),
  ttfcMs: 150.5,
  chunksReceived: 10,
  totalChunkSize: 256,
  lastChunkAt: new Date().toISOString(),
  status: "active" as const,
};

const mockCompletedStream = {
  ...mockActiveStream,
  streamId: "stream-def-456",
  status: "success" as const,
  ttfcMs: 200.0,
  chunksReceived: 25,
};

// =============================================================================
// Tests
// =============================================================================

describe("LLMStreamingTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock state
    mockUseLLMStreamingWebSocket.mockReturnValue({
      status: "connected",
      activeStreams: new Map(),
      sessionId: "test-session-123",
      error: null,
      setSessionId: vi.fn(),
      getStream: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe("rendering", () => {
    it("should render without crashing", () => {
      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByTestId("llm-streaming-tab")).toBeInTheDocument();
    });

    it("should display connection status", () => {
      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByText(/connected/i)).toBeInTheDocument();
    });

    it("should display empty state when no active streams", () => {
      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByText(/no active streams/i)).toBeInTheDocument();
    });

    it("should display session filter indicator", () => {
      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
    });
  });

  describe("active streams", () => {
    it("should display active stream cards", () => {
      const activeStreams = new Map([
        [mockActiveStream.streamId, mockActiveStream],
      ]);

      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "connected",
        activeStreams,
        sessionId: "test-session-123",
        error: null,
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByText(/gpt-4/i)).toBeInTheDocument();
      expect(screen.getByText(/openai/i)).toBeInTheDocument();
    });

    it("should display TTFC metric", () => {
      const activeStreams = new Map([
        [mockActiveStream.streamId, mockActiveStream],
      ]);

      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "connected",
        activeStreams,
        sessionId: "test-session-123",
        error: null,
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProvider(<LLMStreamingTab />);
      // TTFC should be displayed in ms
      expect(screen.getByText(/150\.5/)).toBeInTheDocument();
      expect(screen.getByText(/ttfc/i)).toBeInTheDocument();
    });

    it("should display chunk count", () => {
      const activeStreams = new Map([
        [mockActiveStream.streamId, mockActiveStream],
      ]);

      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "connected",
        activeStreams,
        sessionId: "test-session-123",
        error: null,
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByText(/10/)).toBeInTheDocument();
      expect(screen.getByText(/chunks/i)).toBeInTheDocument();
    });

    it("should show active status indicator for streaming", () => {
      const activeStreams = new Map([
        [mockActiveStream.streamId, mockActiveStream],
      ]);

      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "connected",
        activeStreams,
        sessionId: "test-session-123",
        error: null,
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByTestId("stream-status-active")).toBeInTheDocument();
    });
  });

  describe("connection states", () => {
    it("should show connecting indicator", () => {
      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "connecting",
        activeStreams: new Map(),
        sessionId: null,
        error: null,
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByText(/connecting/i)).toBeInTheDocument();
    });

    it("should show error state with message", () => {
      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "error",
        activeStreams: new Map(),
        sessionId: null,
        error: "WebSocket connection failed",
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProvider(<LLMStreamingTab />);
      expect(screen.getByText(/error/i)).toBeInTheDocument();
      expect(
        screen.getByText(/websocket connection failed/i),
      ).toBeInTheDocument();
    });

    it("should show reconnect button when disconnected", () => {
      const mockReconnect = vi.fn();
      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "disconnected",
        activeStreams: new Map(),
        sessionId: null,
        error: null,
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: mockReconnect,
      });

      renderWithProvider(<LLMStreamingTab />);
      const reconnectButton = screen.getByRole("button", {
        name: /reconnect/i,
      });
      expect(reconnectButton).toBeInTheDocument();
    });
  });

  describe("multiple streams", () => {
    it("should display multiple active streams", () => {
      const activeStreams = new Map([
        [mockActiveStream.streamId, mockActiveStream],
        [mockCompletedStream.streamId, mockCompletedStream],
      ]);

      mockUseLLMStreamingWebSocket.mockReturnValue({
        status: "connected",
        activeStreams,
        sessionId: "test-session-123",
        error: null,
        setSessionId: vi.fn(),
        getStream: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
      });

      renderWithProvider(<LLMStreamingTab />);
      // Should show both streams
      expect(screen.getAllByTestId(/stream-card/)).toHaveLength(2);
    });
  });
});
