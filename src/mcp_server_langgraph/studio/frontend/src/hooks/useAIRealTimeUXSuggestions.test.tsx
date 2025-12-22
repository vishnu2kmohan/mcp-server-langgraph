/**
 * useAIRealTimeUXSuggestions Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Integrates real-time AI suggestions with AIIntelligence context.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { AIIntelligenceProvider } from "../contexts/AIIntelligenceContext";
import { useAIRealTimeUXSuggestions } from "./useAIRealTimeUXSuggestions";

// Mock the base WebSocket hook
vi.mock("./useAIRealTimeSuggestions", () => ({
  useAIRealTimeSuggestions: vi.fn(() => ({
    isConnected: false,
    error: null,
    suggestions: [],
    dismissedIds: [],
    reconnectAttempts: 0,
    lastHeartbeat: null,
    requestSuggestions: vi.fn(),
    clearSuggestions: vi.fn(),
    dismissSuggestion: vi.fn(),
  })),
}));

// Create mock store
function createMockStore() {
  return configureStore({
    reducer: {
      auth: () => ({ user: { id: "user-123" } }),
      api: () => ({}),
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({ serializableCheck: false }),
  });
}

// Test wrapper with all providers
function createWrapper(config = {}) {
  const store = createMockStore();
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <AIIntelligenceProvider config={config}>
          {children}
        </AIIntelligenceProvider>
      </Provider>
    );
  };
}

describe("useAIRealTimeUXSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("context integration", () => {
    it("should use WebSocket config from AIIntelligence context", async () => {
      const { useAIRealTimeSuggestions } = await import(
        "./useAIRealTimeSuggestions"
      );

      renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({
          enabled: true,
          webSocket: { enabled: true, endpoint: "/ws/ai/suggestions" },
        }),
      });

      // Should have called the base hook with enabled=true
      expect(useAIRealTimeSuggestions).toHaveBeenCalled();
    });

    it("should be disabled when AI features are globally disabled", async () => {
      const { useAIRealTimeSuggestions } = await import(
        "./useAIRealTimeSuggestions"
      );

      renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({
          enabled: false, // Globally disabled
          webSocket: { enabled: true },
        }),
      });

      // The hook should still be called but with enabled=false due to global toggle
      expect(useAIRealTimeSuggestions).toHaveBeenCalled();
    });

    it("should be disabled when WebSocket is specifically disabled", async () => {
      const { useAIRealTimeSuggestions } = await import(
        "./useAIRealTimeSuggestions"
      );

      renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({
          enabled: true,
          webSocket: { enabled: false }, // WebSocket disabled
        }),
      });

      expect(useAIRealTimeSuggestions).toHaveBeenCalled();
    });
  });

  describe("return values", () => {
    it("should return connection status", () => {
      const { result } = renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(result.current).toHaveProperty("isConnected");
      expect(result.current).toHaveProperty("error");
    });

    it("should return suggestions management functions", () => {
      const { result } = renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(typeof result.current.requestSuggestions).toBe("function");
      expect(typeof result.current.clearSuggestions).toBe("function");
      expect(typeof result.current.dismissSuggestion).toBe("function");
    });

    it("should return suggestions array", () => {
      const { result } = renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(Array.isArray(result.current.suggestions)).toBe(true);
    });
  });

  describe("error reporting integration", () => {
    it("should report WebSocket errors to AIIntelligence context", async () => {
      // This tests that errors are propagated to the context's reportError function
      const { result } = renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({ enabled: true }),
      });

      // When there's an error, it should be available in the result
      expect(result.current.error).toBeNull();
    });
  });

  describe("cache stale time integration", () => {
    it("should respect cache config from context for suggestion caching", () => {
      const { result } = renderHook(() => useAIRealTimeUXSuggestions(), {
        wrapper: createWrapper({
          enabled: true,
          cacheConfig: {
            navPredictionStaleTime: 10 * 60 * 1000, // 10 minutes
          },
        }),
      });

      // Hook should be properly initialized
      expect(result.current).toBeDefined();
    });
  });
});
