/**
 * Session Hooks Integration Tests
 *
 * Integration tests for the session-related hooks working together:
 * - useSessionSync: Syncs loader data to Redux
 * - useNewChat: Creates new sessions
 * - useMessageRevalidation: Revalidates after mutations
 *
 * These tests verify the full flow of:
 * 1. Creating a session
 * 2. Sending messages (optimistic updates)
 * 3. Revalidation
 * 4. Race condition protection
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore, type Middleware } from "@reduxjs/toolkit";
import React from "react";
import { http, HttpResponse } from "msw";
import { UNSAFE_DataRouterContext, createBrowserRouter } from "react-router";
import { useSessionSync } from "./useSessionSync";
import { useNewChat } from "./useNewChat";
import { useMessageRevalidation } from "./useMessageRevalidation";
import sessionReducer from "../store/slices/sessionSlice";
import type { ChatLoaderData } from "../router/loaders";
import type { Session } from "../types";
import { server } from "../mocks/server";
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

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockRevalidate = vi.fn();
const createMockRouter = () => ({
  revalidate: mockRevalidate,
  state: {
    revalidation: "idle" as const,
  },
});

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
      return React.createElement(
        UNSAFE_DataRouterContext.Provider,
        {
          value: {
            router: createMockRouter() as unknown as ReturnType<
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

const createMockSession = (overrides: Partial<Session> = {}): Session => ({
  id: "session-123",
  name: "Test Session",
  status: "active",
  created_at: "2025-01-15T10:00:00Z",
  updated_at: "2025-01-15T10:00:00Z",
  ...overrides,
});

const createMockLoaderData = (
  overrides: Partial<ChatLoaderData> = {},
): ChatLoaderData => ({
  sessionId: "session-123",
  session: createMockSession(),
  messages: [],
  artifacts: [],
  ...overrides,
});

// =============================================================================
// Integration Tests
// =============================================================================

describe("Session Hooks Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe("Full Message Flow", () => {
    it("should handle send message → revalidate → sync flow", async () => {
      const store = createTestStore();

      // Step 1: Initial sync with loader data
      const initialLoaderData = createMockLoaderData({
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
        ],
      });

      const { rerender: rerenderSync } = renderHook(
        ({ data }) => useSessionSync(data),
        {
          wrapper: createWrapper(store),
          initialProps: { data: initialLoaderData },
        },
      );

      // Verify initial sync worked
      expect(store.getState().session.currentSession?.messages).toHaveLength(1);

      // Step 2: Use revalidation hook
      const { result: revalidationResult } = renderHook(
        () => useMessageRevalidation({ debounceMs: 10 }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Step 3: Simulate sending a message (optimistic update)
      act(() => {
        store.dispatch({
          type: "session/addMessage",
          payload: {
            id: "msg-2",
            role: "user",
            content: "New message",
            timestamp: Date.now(),
          },
        });
      });

      // Verify optimistic update
      expect(store.getState().session.currentSession?.messages).toHaveLength(2);

      // Step 4: Trigger revalidation
      await act(async () => {
        revalidationResult.current.revalidateMessages();
        await new Promise((resolve) => setTimeout(resolve, 20));
      });

      // Verify revalidate was called
      expect(mockRevalidate).toHaveBeenCalledTimes(1);

      // Step 5: Simulate loader data coming back with new message
      const updatedLoaderData = createMockLoaderData({
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
          {
            id: "msg-2",
            role: "user",
            content: "New message",
            timestamp: Date.now(),
          },
          {
            id: "msg-3",
            role: "assistant",
            content: "Hi there!",
            timestamp: Date.now(),
          },
        ],
      });

      rerenderSync({ data: updatedLoaderData });

      // Verify sync updated Redux with new data
      expect(store.getState().session.currentSession?.messages).toHaveLength(3);
    });

    it("should protect optimistic updates from stale loader data", async () => {
      const store = createTestStore();

      // Initial sync
      const initialLoaderData = createMockLoaderData({
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
        ],
      });

      const { rerender: rerenderSync } = renderHook(
        ({ data }) => useSessionSync(data),
        {
          wrapper: createWrapper(store),
          initialProps: { data: initialLoaderData },
        },
      );

      expect(store.getState().session.currentSession?.messages).toHaveLength(1);

      // Set pending mutation (simulating message send in progress)
      act(() => {
        store.dispatch({ type: "session/setPendingMutation", payload: true });
      });

      // Add optimistic message
      act(() => {
        store.dispatch({
          type: "session/addMessage",
          payload: {
            id: "msg-2",
            role: "user",
            content: "Optimistic message",
            timestamp: Date.now(),
          },
        });
      });

      expect(store.getState().session.currentSession?.messages).toHaveLength(2);

      // Stale loader data arrives (doesn't include the new message yet)
      const staleLoaderData = createMockLoaderData({
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
        ],
      });

      rerenderSync({ data: staleLoaderData });

      // Optimistic update should be preserved
      expect(store.getState().session.currentSession?.messages).toHaveLength(2);
      expect(store.getState().session.currentSession?.messages[1].content).toBe(
        "Optimistic message",
      );

      // Clear pending mutation
      act(() => {
        store.dispatch({ type: "session/setPendingMutation", payload: false });
      });

      // Fresh loader data arrives
      const freshLoaderData = createMockLoaderData({
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
          {
            id: "msg-2",
            role: "user",
            content: "Optimistic message",
            timestamp: Date.now(),
          },
        ],
      });

      rerenderSync({ data: freshLoaderData });

      // Now sync should update
      expect(store.getState().session.currentSession?.messages).toHaveLength(2);
    });
  });

  describe("Session Creation Flow", () => {
    it("should create session and trigger navigation", async () => {
      const store = createTestStore();

      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat({ name: "My New Chat" });
      });

      // Verify navigation happened
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringMatching(/^\/studio\/v2\/chat\/session-/),
      );
    });

    it("should handle session creation errors", async () => {
      // Override handler to return error
      server.use(
        http.post("/api/v1/sessions", () => {
          return HttpResponse.json({ detail: "Server error" }, { status: 500 });
        }),
      );

      const store = createTestStore();

      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      // Verify error state
      expect(result.current.error).toBe("Server error");
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe("Revalidation with Debounce", () => {
    it("should debounce rapid message sends", async () => {
      const store = createTestStore();

      const { result } = renderHook(
        () => useMessageRevalidation({ debounceMs: 50 }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Rapid fire revalidation calls (simulating quick message sends)
      act(() => {
        result.current.revalidateMessages();
        result.current.revalidateMessages();
        result.current.revalidateMessages();
      });

      // Wait for debounce
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      // Should only call once
      expect(mockRevalidate).toHaveBeenCalledTimes(1);
    });

    it("should cleanup on unmount without calling revalidate", async () => {
      const store = createTestStore();

      const { result, unmount } = renderHook(
        () => useMessageRevalidation({ debounceMs: 100 }),
        {
          wrapper: createWrapper(store, { withRouter: true }),
        },
      );

      // Trigger revalidation
      act(() => {
        result.current.revalidateMessages();
      });

      // Unmount before debounce completes
      unmount();

      // Wait for what would have been the debounce
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 150));
      });

      // Should NOT have called revalidate
      expect(mockRevalidate).not.toHaveBeenCalled();
    });
  });

  describe("Auto-Revalidation", () => {
    it("should auto-revalidate when messages are added with autoRevalidate enabled", async () => {
      const store = createTestStore();

      // Set up initial session
      act(() => {
        store.dispatch({
          type: "session/setCurrentSession",
          payload: {
            id: "test-session",
            name: "Test",
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
      });

      renderHook(
        () => useMessageRevalidation({ debounceMs: 10, autoRevalidate: true }),
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
            content: "Test message",
            timestamp: Date.now(),
          },
        });
        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      // Should have auto-revalidated
      expect(mockRevalidate).toHaveBeenCalled();
    });
  });
});
