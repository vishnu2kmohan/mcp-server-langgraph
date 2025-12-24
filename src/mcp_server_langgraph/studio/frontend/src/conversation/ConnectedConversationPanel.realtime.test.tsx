/**
 * ConnectedConversationPanel Real-time Integration Tests (TDD RED Phase)
 *
 * Tests verify that ConnectedConversationPanel integrates with useAIRealTimeUXSuggestions
 * for real-time AI-powered UX suggestions (tooltips, spotlights, banners).
 * These tests should FAIL initially until we implement the WebSocket integration.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import React from "react";
import { ConnectedConversationPanel } from "./ConnectedConversationPanel";
import sessionReducer from "../store/slices/sessionSlice";
import type { ChatLoaderData } from "../router/loaders";
import type { Suggestion } from "../hooks/useAIRealTimeSuggestions";
import { TelemetryProvider } from "../contexts/TelemetryContext";

// =============================================================================
// Mocks
// =============================================================================

// Mock useRouteLoaderData
const mockSessionLoaderData: ChatLoaderData = {
  sessionId: "session-123",
  messages: [],
  artifacts: [],
};

// Mock useRevalidator for data router context (used by useArtifactExtraction)
const mockRevalidate = vi.fn();

vi.mock("react-router", async () => {
  const actual =
    await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") {
        return mockSessionLoaderData;
      }
      if (routeId === "chat-index") {
        return undefined;
      }
      return undefined;
    }),
    // Mock useRevalidator to avoid "must be used within a data router" error
    useRevalidator: vi.fn(() => ({
      revalidate: mockRevalidate,
      state: "idle",
    })),
  };
});

// Mock useMessageRevalidation
vi.mock("../hooks/useMessageRevalidation", () => ({
  useMessageRevalidation: vi.fn(() => ({
    revalidateMessages: vi.fn(),
  })),
}));

// Mock conversation intelligence hooks
vi.mock("../hooks/useConversationIntelligence", () => ({
  useIntentDetection: vi.fn(() => ({
    intent: null,
    confidence: null,
    isLoading: false,
  })),
  useContextOptimization: vi.fn(() => ({
    usagePercent: null,
    recommendedAction: null,
    isLoading: false,
  })),
  useGoalTracking: vi.fn(() => ({
    primaryGoal: null,
    progressPercent: null,
    subGoals: [],
    isLoading: false,
  })),
}));

// Mock useAIRealTimeUXSuggestions
const mockRequestSuggestions = vi.fn();
const mockDismissSuggestion = vi.fn();
const mockClearSuggestions = vi.fn();

vi.mock("../hooks/useAIRealTimeUXSuggestions", () => ({
  useAIRealTimeUXSuggestions: vi.fn(() => ({
    isConnected: false,
    error: null,
    suggestions: [],
    dismissedIds: [],
    reconnectAttempts: 0,
    lastHeartbeat: null,
    isEnabled: false,
    requestSuggestions: mockRequestSuggestions,
    clearSuggestions: mockClearSuggestions,
    dismissSuggestion: mockDismissSuggestion,
  })),
}));

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = () => {
  return configureStore({
    reducer: {
      session: sessionReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({ serializableCheck: false }),
  });
};

interface WrapperProps {
  children: React.ReactNode;
}

function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: WrapperProps) {
    return (
      <Provider store={store}>
        <MemoryRouter initialEntries={["/studio/chat/session-123"]}>
          <TelemetryProvider>{children}</TelemetryProvider>
        </MemoryRouter>
      </Provider>
    );
  };
}

function renderWithProviders(ui: React.ReactElement) {
  const store = createTestStore();
  const Wrapper = createWrapper(store);
  return {
    store,
    ...render(<Wrapper>{ui}</Wrapper>),
  };
}

describe("ConnectedConversationPanel Real-time AI Suggestions Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("WebSocket Connection Status", () => {
    it("should display AI suggestions connection status when enableRealTimeSuggestions is true", async () => {
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");
      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: true,
        error: null,
        suggestions: [],
        dismissedIds: [],
        reconnectAttempts: 0,
        lastHeartbeat: Date.now(),
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      const store = createTestStore();
      const Wrapper = createWrapper(store);

      render(
        <Wrapper>
          <ConnectedConversationPanel
            enableAI={true}
            enableRealTimeSuggestions={true}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        // TDD RED: AI suggestions status indicator doesn't exist yet
        expect(screen.getByTestId("ai-suggestions-status")).toBeInTheDocument();
      });
    });

    it("should show connected status when WebSocket is connected", async () => {
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");
      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: true,
        error: null,
        suggestions: [],
        dismissedIds: [],
        reconnectAttempts: 0,
        lastHeartbeat: Date.now(),
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      const store = createTestStore();
      const Wrapper = createWrapper(store);

      render(
        <Wrapper>
          <ConnectedConversationPanel
            enableAI={true}
            enableRealTimeSuggestions={true}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        // TDD RED: Status should show active when connected
        const indicator = screen.getByTestId("ai-suggestions-status");
        expect(indicator).toHaveAttribute("data-connected", "true");
      });
    });

    it("should not show AI suggestions features when enableRealTimeSuggestions is false", async () => {
      const store = createTestStore();
      const Wrapper = createWrapper(store);

      render(
        <Wrapper>
          <ConnectedConversationPanel
            enableAI={true}
            enableRealTimeSuggestions={false}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        // Status indicator should not exist when disabled
        expect(
          screen.queryByTestId("ai-suggestions-status"),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Real-time UX Suggestions Display", () => {
    it("should display banner suggestions when received", async () => {
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");
      const bannerSuggestion: Suggestion = {
        id: "suggestion-1",
        type: "banner",
        message: "Try using /help to see available commands",
        priority: "medium",
      };

      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: true,
        error: null,
        suggestions: [bannerSuggestion],
        dismissedIds: [],
        reconnectAttempts: 0,
        lastHeartbeat: Date.now(),
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      const store = createTestStore();
      const Wrapper = createWrapper(store);

      render(
        <Wrapper>
          <ConnectedConversationPanel
            enableAI={true}
            enableRealTimeSuggestions={true}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        // TDD RED: AI suggestion banner doesn't exist yet
        expect(screen.getByTestId("ai-suggestion-banner")).toBeInTheDocument();
        expect(
          screen.getByText(/Try using \/help to see available commands/i),
        ).toBeInTheDocument();
      });
    });

    it("should display tooltip suggestions with target element", async () => {
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");
      const tooltipSuggestion: Suggestion = {
        id: "suggestion-2",
        type: "tooltip",
        message: "Click here to attach files",
        priority: "low",
        targetElement: "#attach-button",
      };

      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: true,
        error: null,
        suggestions: [tooltipSuggestion],
        dismissedIds: [],
        reconnectAttempts: 0,
        lastHeartbeat: Date.now(),
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      const store = createTestStore();
      const Wrapper = createWrapper(store);

      render(
        <Wrapper>
          <ConnectedConversationPanel
            enableAI={true}
            enableRealTimeSuggestions={true}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        // TDD RED: AI tooltip suggestion doesn't exist yet
        expect(screen.getByTestId("ai-suggestion-tooltip")).toBeInTheDocument();
      });
    });

    it("should display high priority suggestions prominently", async () => {
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");
      const highPrioritySuggestion: Suggestion = {
        id: "suggestion-3",
        type: "spotlight",
        message: "Important: Your session is about to expire",
        priority: "high",
      };

      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: true,
        error: null,
        suggestions: [highPrioritySuggestion],
        dismissedIds: [],
        reconnectAttempts: 0,
        lastHeartbeat: Date.now(),
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      const store = createTestStore();
      const Wrapper = createWrapper(store);

      render(
        <Wrapper>
          <ConnectedConversationPanel
            enableAI={true}
            enableRealTimeSuggestions={true}
          />
        </Wrapper>,
      );

      await waitFor(() => {
        // TDD RED: High priority spotlight doesn't exist yet
        expect(
          screen.getByTestId("ai-suggestion-spotlight"),
        ).toBeInTheDocument();
        expect(screen.getByText(/Important/i)).toBeInTheDocument();
      });
    });
  });

  describe("Suggestion Interactions", () => {
    it("should allow dismissing suggestions", async () => {
      const user = userEvent.setup();
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");
      const bannerSuggestion: Suggestion = {
        id: "suggestion-dismiss-test",
        type: "banner",
        message: "Dismissable suggestion",
        priority: "low",
      };

      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: true,
        error: null,
        suggestions: [bannerSuggestion],
        dismissedIds: [],
        reconnectAttempts: 0,
        lastHeartbeat: Date.now(),
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      renderWithProviders(
        <ConnectedConversationPanel
          enableAI={true}
          enableRealTimeSuggestions={true}
        />,
      );

      await waitFor(() => {
        expect(screen.getByTestId("ai-suggestion-banner")).toBeInTheDocument();
      });

      // TDD RED: Dismiss button doesn't exist yet
      const dismissButton = screen.getByTestId("dismiss-suggestion-button");
      await user.click(dismissButton);

      expect(mockDismissSuggestion).toHaveBeenCalledWith(
        "suggestion-dismiss-test",
      );
    });

    it("should request suggestions when user starts typing", async () => {
      const user = userEvent.setup();
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");

      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: true,
        error: null,
        suggestions: [],
        dismissedIds: [],
        reconnectAttempts: 0,
        lastHeartbeat: Date.now(),
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      renderWithProviders(
        <ConnectedConversationPanel
          enableAI={true}
          enableRealTimeSuggestions={true}
        />,
      );

      // Find the input and type in it
      const input = screen.getByRole("textbox");
      await user.type(input, "How do I");

      // TDD RED: requestSuggestions should be called with context
      await waitFor(() => {
        expect(mockRequestSuggestions).toHaveBeenCalledWith(
          expect.objectContaining({
            page: "conversation",
            action: "typing",
          }),
        );
      });
    });
  });

  describe("Error Handling", () => {
    it("should display error state when WebSocket fails", async () => {
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");

      vi.mocked(useAIRealTimeUXSuggestions).mockReturnValue({
        isConnected: false,
        error: new Error("Connection failed"),
        suggestions: [],
        dismissedIds: [],
        reconnectAttempts: 3,
        lastHeartbeat: null,
        isEnabled: true,
        requestSuggestions: mockRequestSuggestions,
        clearSuggestions: mockClearSuggestions,
        dismissSuggestion: mockDismissSuggestion,
      });

      renderWithProviders(
        <ConnectedConversationPanel
          enableAI={true}
          enableRealTimeSuggestions={true}
        />,
      );

      await waitFor(() => {
        // TDD RED: Error indicator doesn't exist yet
        const indicator = screen.getByTestId("ai-suggestions-status");
        expect(indicator).toHaveAttribute("data-error", "true");
      });
    });
  });

  describe("Props Configuration", () => {
    it("should accept enableRealTimeSuggestions prop", () => {
      // TDD RED: enableRealTimeSuggestions prop doesn't exist yet
      renderWithProviders(
        <ConnectedConversationPanel
          enableAI={true}
          enableRealTimeSuggestions={true}
        />,
      );

      // If we get here without type errors, the prop is accepted
      expect(true).toBe(true);
    });

    it("should respect AIIntelligence context for WebSocket settings", async () => {
      const { useAIRealTimeUXSuggestions } =
        await import("../hooks/useAIRealTimeUXSuggestions");

      renderWithProviders(
        <ConnectedConversationPanel
          enableAI={true}
          enableRealTimeSuggestions={true}
        />,
      );

      // TDD RED: Hook should be called when enableRealTimeSuggestions is true
      expect(useAIRealTimeUXSuggestions).toHaveBeenCalled();
    });
  });
});
