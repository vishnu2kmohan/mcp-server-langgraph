/**
 * useMessageRevalidation Tests
 *
 * TDD tests for the hook that revalidates loader data after sending messages.
 *
 * In v2 routes with loaders, after a message is sent:
 * 1. The message is added to Redux (optimistic)
 * 2. The API is called
 * 3. Loader data needs revalidation to sync from server
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore, type Middleware } from "@reduxjs/toolkit";
import React from "react";
import { UNSAFE_DataRouterContext, createBrowserRouter } from "react-router";
import { useMessageRevalidation } from "./useMessageRevalidation";
import sessionReducer from "../store/slices/sessionSlice";
import { TelemetryProvider } from "../contexts/TelemetryContext";

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = () => {
  const silentMiddleware: Middleware = () => (next) => (action) => {
    return next(action);
  };

  return configureStore({
    reducer: {
      session: sessionReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
      }).concat(silentMiddleware),
  });
};

// Create a mock router for testing
const mockRevalidate = vi.fn();
const mockRouter = {
  revalidate: mockRevalidate,
  state: {
    revalidation: "idle" as const,
  },
};

const createWrapper = (
  store: ReturnType<typeof createTestStore>,
  options: { withRouter?: boolean } = {},
) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    const reduxProvider = React.createElement(Provider, { store }, children);
    const withTelemetry = React.createElement(
      TelemetryProvider,
      null,
      reduxProvider,
    );

    if (options.withRouter) {
      // Wrap with data router context
      return React.createElement(
        UNSAFE_DataRouterContext.Provider,
        {
          value: {
            router: mockRouter as unknown as ReturnType<
              typeof createBrowserRouter
            >,
            basename: "/",
          },
        },
        withTelemetry,
      );
    }

    return withTelemetry;
  };
};

// =============================================================================
// Tests
// =============================================================================

describe("useMessageRevalidation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Revalidation Triggering", () => {
    it("should provide a revalidate function", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useMessageRevalidation(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.revalidateMessages).toBeDefined();
      expect(typeof result.current.revalidateMessages).toBe("function");
    });

    it("should call router revalidate when revalidateMessages is called in data router context", async () => {
      const store = createTestStore();
      // Use short debounce for testing
      const { result } = renderHook(
        () => useMessageRevalidation({ debounceMs: 10 }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      await act(async () => {
        result.current.revalidateMessages();
        // Wait for debounce to complete
        await new Promise((resolve) => setTimeout(resolve, 20));
      });

      expect(mockRevalidate).toHaveBeenCalledTimes(1);
    });

    it("should be a no-op when not in data router context", async () => {
      const store = createTestStore();
      const { result } = renderHook(
        () => useMessageRevalidation({ debounceMs: 10 }),
        {
          wrapper: createWrapper(store, { withRouter: false }),
        },
      );

      await act(async () => {
        result.current.revalidateMessages();
        await new Promise((resolve) => setTimeout(resolve, 20));
      });

      // Should not throw and should not call revalidate
      expect(mockRevalidate).not.toHaveBeenCalled();
    });

    it("should debounce rapid revalidation calls", async () => {
      const store = createTestStore();
      const { result } = renderHook(
        () => useMessageRevalidation({ debounceMs: 100 }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Call revalidate multiple times rapidly
      await act(async () => {
        result.current.revalidateMessages();
        result.current.revalidateMessages();
        result.current.revalidateMessages();
      });

      // Wait for debounce to settle
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 150));
      });

      // Should only call revalidate once
      expect(mockRevalidate).toHaveBeenCalledTimes(1);
    });

    it("should expose revalidation state", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useMessageRevalidation(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isRevalidating).toBe(false);
    });
  });

  describe("Cleanup on Unmount", () => {
    it("should cancel pending revalidation on unmount", async () => {
      const store = createTestStore();
      const { result, unmount } = renderHook(
        () => useMessageRevalidation({ debounceMs: 100 }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Trigger revalidation but don't wait for debounce
      act(() => {
        result.current.revalidateMessages();
      });

      // Unmount before debounce completes
      unmount();

      // Wait for what would have been the debounce period
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 150));
      });

      // Should NOT have called revalidate since we unmounted
      expect(mockRevalidate).not.toHaveBeenCalled();
    });

    it("should not throw when unmounting after revalidation completes", async () => {
      const store = createTestStore();
      const { result, unmount } = renderHook(
        () => useMessageRevalidation({ debounceMs: 10 }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Trigger and wait for revalidation
      await act(async () => {
        result.current.revalidateMessages();
        await new Promise((resolve) => setTimeout(resolve, 20));
      });

      expect(mockRevalidate).toHaveBeenCalledTimes(1);

      // Unmount should not throw
      expect(() => unmount()).not.toThrow();
    });
  });

  describe("Auto Revalidation", () => {
    it("should auto-revalidate when autoRevalidate is true and message is added", async () => {
      const store = createTestStore();

      // First, set up a session with messages
      store.dispatch({
        type: "session/setCurrentSession",
        payload: {
          id: "test-session",
          name: "Test Session",
          messages: [],
          config: {
            modelName: "gpt-4",
            modelProvider: "openai",
            temperature: 0.7,
            maxTokens: 4096,
          },
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      renderHook(
        () => useMessageRevalidation({ debounceMs: 10, autoRevalidate: true }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Add a message to trigger auto-revalidation
      await act(async () => {
        store.dispatch({
          type: "session/addMessage",
          payload: {
            id: "msg-1",
            role: "user",
            content: "test message",
            timestamp: Date.now(),
          },
        });
        // Wait for debounce
        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      // Should have auto-revalidated
      expect(mockRevalidate).toHaveBeenCalled();
    });

    it("should NOT auto-revalidate when autoRevalidate is false", async () => {
      const store = createTestStore();

      // First, set up a session with messages
      store.dispatch({
        type: "session/setCurrentSession",
        payload: {
          id: "test-session",
          name: "Test Session",
          messages: [],
          config: {
            modelName: "gpt-4",
            modelProvider: "openai",
            temperature: 0.7,
            maxTokens: 4096,
          },
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      renderHook(
        () => useMessageRevalidation({ debounceMs: 10, autoRevalidate: false }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Add a message
      await act(async () => {
        store.dispatch({
          type: "session/addMessage",
          payload: {
            id: "msg-1",
            role: "user",
            content: "test message",
            timestamp: Date.now(),
          },
        });
        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      // Should NOT have auto-revalidated
      expect(mockRevalidate).not.toHaveBeenCalled();
    });
  });
});
