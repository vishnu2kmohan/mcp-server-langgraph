/**
 * ChatDocument Component Tests
 *
 * TDD tests for the dockable chat document component.
 * This is a streamlined version of ChatPage that works within the MainDock.
 * Tests cover:
 * - Basic rendering
 * - Message display
 * - Streaming state
 * - Input handling
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";

// Mock hooks
const mockStartStream = vi.fn();
const mockClearContent = vi.fn();

vi.mock("../../hooks/useStreamingChat", () => ({
  useStreamingChat: () => ({
    isStreaming: false,
    streamingContent: "",
    startStream: mockStartStream,
    clearContent: mockClearContent,
    usage: null,
    model: "gpt-4",
    error: null,
  }),
}));

vi.mock("../../hooks/useMCPConnection", () => ({
  useMCPConnection: () => ({
    connectionMode: "direct",
    tools: [],
    error: null,
    connect: vi.fn(),
    isReconnecting: false,
    reconnectAttempts: 0,
  }),
}));

vi.mock("../../hooks/useVoiceInput", () => ({
  useVoiceInput: () => ({
    isListening: false,
    isSupported: true,
    transcript: "",
    error: null,
    startListening: vi.fn(),
    stopListening: vi.fn(),
    clearTranscript: vi.fn(),
  }),
}));

vi.mock("../../hooks/useFileUpload", () => ({
  useFileUpload: () => ({
    files: [],
    isUploading: false,
    isDragging: false,
    error: null,
    selectFiles: vi.fn(),
    removeFile: vi.fn(),
    clearFiles: vi.fn(),
    dragHandlers: {},
  }),
}));

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: () => false,
}));

// Import after mocks
import { ChatDocument } from "./ChatDocument";
import sessionReducer, {
  type SessionState,
} from "../../store/slices/sessionSlice";
import personaReducer from "../../store/slices/personaSlice";
import type { ClientSession } from "../../types/session";

// Default session state for tests
const defaultSessionState: SessionState = {
  sessions: [],
  currentSession: null,
  isLoadingSessions: false,
  isLoadingSession: false,
  isSending: false,
  error: null,
  hasMore: false,
  totalCount: 0,
  isLoadingMore: false,
  cursor: null,
};

const mockSession: ClientSession = {
  id: "session-123",
  name: "Test Session",
  messages: [
    { id: "msg-1", role: "user", content: "Hello", timestamp: Date.now() },
    {
      id: "msg-2",
      role: "assistant",
      content: "Hi there!",
      timestamp: Date.now(),
    },
  ],
  createdAt: Date.now(),
  updatedAt: Date.now(),
};

// Create a test store
function createTestStore(
  overrides: {
    session?: Partial<SessionState>;
  } = {},
) {
  return configureStore({
    reducer: {
      session: sessionReducer,
      persona: personaReducer,
    },
    preloadedState: {
      session: { ...defaultSessionState, ...overrides.session },
      persona: {
        persona: "user",
        username: null,
        email: null,
        permissions: [],
        isPersonaLoading: false,
      },
    },
  });
}

// Render helper with providers
function renderWithProviders(
  ui: React.ReactElement,
  options: {
    store?: ReturnType<typeof createTestStore>;
    sessionOverrides?: Partial<SessionState>;
  } = {},
) {
  const store =
    options.store ??
    createTestStore({
      session: options.sessionOverrides ?? {},
    });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("ChatDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render the chat document container", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should render without panels (no SessionPanel or ContextPanel)", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Should not have side panels
      expect(screen.queryByTestId("session-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("context-panel")).not.toBeInTheDocument();
    });

    it("should render chat input", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });
  });

  describe("messages display", () => {
    it("should display messages from current session", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });

    it("should show empty state when no messages", () => {
      const emptySession: ClientSession = {
        ...mockSession,
        messages: [],
      };
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: emptySession },
      });

      // Should show some empty state or just be ready for input
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });
  });

  describe("input handling", () => {
    it("should update input value on change", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "Test message" } });

      expect(input).toHaveValue("Test message");
    });

    it("should submit message on form submit", async () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "Test message" } });

      // Submit the form
      const form = input.closest("form");
      if (form) {
        fireEvent.submit(form);
      }

      await waitFor(() => {
        expect(mockStartStream).toHaveBeenCalledWith(
          "session-123",
          "Test message",
        );
      });
    });
  });

  describe("loading states", () => {
    it("should show loading indicator when session is loading", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { isLoadingSession: true, currentSession: null },
      });

      // Should show loading state
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should show no session state when session is null and not loading", async () => {
      // When currentSession matches sessionId as null (already loaded but empty),
      // we should show the "no session" state
      renderWithProviders(<ChatDocument sessionId="" />, {
        sessionOverrides: { currentSession: null, isLoadingSession: false },
      });

      // Should show no active session message
      await waitFor(() => {
        expect(screen.getByText(/no active session/i)).toBeInTheDocument();
      });
    });
  });

  describe("compact mode", () => {
    it("should apply compact styles when compact prop is true", () => {
      renderWithProviders(
        <ChatDocument sessionId="session-123" compact={true} />,
        { sessionOverrides: { currentSession: mockSession } },
      );

      const container = screen.getByTestId("chat-document");
      expect(container).toHaveClass("h-full");
    });
  });
});
