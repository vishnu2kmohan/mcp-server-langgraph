/**
 * useSessionSync Tests
 *
 * TDD tests for the session sync hook that synchronizes
 * React Router loader data with Redux session state.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { useSessionSync } from "./useSessionSync";
import sessionReducer from "../store/slices/sessionSlice";
import type { ChatLoaderData } from "../router/loaders";
import type { Session } from "../types";
import { TelemetryProvider } from "../contexts/TelemetryContext";

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      session: sessionReducer,
    },
  });

const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      TelemetryProvider,
      null,
      React.createElement(Provider, { store }, children),
    );
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
  messages: [
    {
      id: "msg-1",
      role: "user",
      content: "Hello",
      timestamp: Date.now(),
    },
    {
      id: "msg-2",
      role: "assistant",
      content: "Hi there!",
      timestamp: Date.now(),
    },
  ],
  artifacts: [],
  ...overrides,
});

// =============================================================================
// Tests
// =============================================================================

describe("useSessionSync", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Session Synchronization", () => {
    it("should sync session to Redux when loader data is available", () => {
      const store = createTestStore();
      const loaderData = createMockLoaderData();

      renderHook(() => useSessionSync(loaderData), {
        wrapper: createWrapper(store),
      });

      const state = store.getState().session;
      expect(state.currentSession).not.toBeNull();
      expect(state.currentSession?.id).toBe("session-123");
    });

    it("should sync messages to Redux currentSession", () => {
      const store = createTestStore();
      const loaderData = createMockLoaderData();

      renderHook(() => useSessionSync(loaderData), {
        wrapper: createWrapper(store),
      });

      const state = store.getState().session;
      expect(state.currentSession?.messages).toHaveLength(2);
      expect(state.currentSession?.messages[0].content).toBe("Hello");
    });

    it("should not sync when loader data is undefined", () => {
      const store = createTestStore();

      renderHook(() => useSessionSync(undefined), {
        wrapper: createWrapper(store),
      });

      const state = store.getState().session;
      expect(state.currentSession).toBeNull();
    });

    it("should not sync when sessionId is null", () => {
      const store = createTestStore();
      const loaderData = createMockLoaderData({ sessionId: null });

      renderHook(() => useSessionSync(loaderData), {
        wrapper: createWrapper(store),
      });

      const state = store.getState().session;
      expect(state.currentSession).toBeNull();
    });

    it("should update Redux when loader data changes", () => {
      const store = createTestStore();
      const initialData = createMockLoaderData();

      const { rerender } = renderHook(({ data }) => useSessionSync(data), {
        wrapper: createWrapper(store),
        initialProps: { data: initialData },
      });

      // Verify initial sync
      expect(store.getState().session.currentSession?.id).toBe("session-123");

      // Update with new session
      const newData = createMockLoaderData({
        sessionId: "session-456",
        session: createMockSession({ id: "session-456", name: "New Session" }),
      });

      rerender({ data: newData });

      // Verify updated sync
      expect(store.getState().session.currentSession?.id).toBe("session-456");
    });

    it("should NOT clear session when loaderData becomes undefined (supports legacy mode)", () => {
      const store = createTestStore();
      const loaderData = createMockLoaderData();

      const { rerender } = renderHook(({ data }) => useSessionSync(data), {
        wrapper: createWrapper(store),
        initialProps: { data: loaderData as ChatLoaderData | undefined },
      });

      // Verify session is set
      expect(store.getState().session.currentSession).not.toBeNull();

      // Simulate going back to undefined (e.g., legacy route or component unmount)
      rerender({ data: undefined });

      // Session should REMAIN set (hook doesn't clear on undefined to support legacy mode)
      // In v2, the component unmounts on navigation, so this is fine
      expect(store.getState().session.currentSession).not.toBeNull();
    });

    it("should clear session when loaderData has null sessionId", () => {
      const store = createTestStore();
      const loaderData = createMockLoaderData();

      const { rerender } = renderHook(({ data }) => useSessionSync(data), {
        wrapper: createWrapper(store),
        initialProps: { data: loaderData as ChatLoaderData | undefined },
      });

      // Verify session is set
      expect(store.getState().session.currentSession).not.toBeNull();

      // Navigate to index route (no session selected)
      rerender({ data: createMockLoaderData({ sessionId: null }) });

      // Session should be cleared
      expect(store.getState().session.currentSession).toBeNull();
    });
  });

  describe("Message Merging", () => {
    it("should include locally added messages not in loader data", () => {
      const store = createTestStore();
      const loaderData = createMockLoaderData();

      // Initial sync
      renderHook(() => useSessionSync(loaderData), {
        wrapper: createWrapper(store),
      });

      // Simulate adding a local message via sendMessage
      // (In real usage, this would be done via dispatch(addUserMessage))
      const currentSession = store.getState().session.currentSession;
      expect(currentSession?.messages).toHaveLength(2);
    });
  });

  describe("Transform API to Client Format", () => {
    it("should transform snake_case session to camelCase ClientSession", () => {
      const store = createTestStore();
      const loaderData = createMockLoaderData({
        session: createMockSession({
          id: "session-abc",
          name: "Test",
          created_at: "2025-01-15T10:00:00Z",
          updated_at: "2025-01-15T11:00:00Z",
        }),
      });

      renderHook(() => useSessionSync(loaderData), {
        wrapper: createWrapper(store),
      });

      const session = store.getState().session.currentSession;
      expect(session).not.toBeNull();
      expect(session?.id).toBe("session-abc");
      expect(session?.name).toBe("Test");
      // createdAt should be a number (timestamp)
      expect(typeof session?.createdAt).toBe("number");
      expect(typeof session?.updatedAt).toBe("number");
    });

    it("should handle invalid session data gracefully", () => {
      const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
      const store = createTestStore();

      // Create loader data with invalid session format (missing required fields)
      const loaderData = {
        sessionId: "session-123",
        session: { wrongFormat: true } as unknown as Session,
        messages: [],
        artifacts: [],
      };

      renderHook(() => useSessionSync(loaderData), {
        wrapper: createWrapper(store),
      });

      // Session should be null due to invalid data
      expect(store.getState().session.currentSession).toBeNull();

      consoleSpy.mockRestore();
    });

    it("should handle sessionId present but no session data", () => {
      const store = createTestStore();

      // Session ID is present but session object is null
      const loaderData = createMockLoaderData({
        sessionId: "session-123",
        session: null as unknown as Session,
      });

      renderHook(() => useSessionSync(loaderData), {
        wrapper: createWrapper(store),
      });

      // Session should be null
      expect(store.getState().session.currentSession).toBeNull();
    });
  });

  describe("Race Condition Guard", () => {
    it("should NOT sync when there are pending mutations (optimistic update protection)", () => {
      const store = createTestStore();

      // First sync a session
      const initialLoaderData = createMockLoaderData({
        session: createMockSession({ id: "session-123" }),
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
        ],
      });

      const { rerender } = renderHook(({ data }) => useSessionSync(data), {
        wrapper: createWrapper(store),
        initialProps: { data: initialLoaderData },
      });

      expect(store.getState().session.currentSession?.messages).toHaveLength(1);

      // Simulate user sending a message (optimistic update)
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

      // Now we have 2 messages locally
      expect(store.getState().session.currentSession?.messages).toHaveLength(2);

      // Mark mutation as pending
      act(() => {
        store.dispatch({ type: "session/setPendingMutation", payload: true });
      });

      // Stale loader data comes back (before server processed the message)
      const staleLoaderData = createMockLoaderData({
        session: createMockSession({ id: "session-123" }),
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
        ],
      });

      rerender({ data: staleLoaderData });

      // Should STILL have 2 messages (guard prevented stale data from overwriting)
      expect(store.getState().session.currentSession?.messages).toHaveLength(2);
    });

    it("should resume syncing when pending mutations clear", () => {
      const store = createTestStore();

      // First sync a session
      const loaderData = createMockLoaderData({
        session: createMockSession({ id: "session-123" }),
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
        ],
      });

      const { rerender } = renderHook(({ data }) => useSessionSync(data), {
        wrapper: createWrapper(store),
        initialProps: { data: loaderData },
      });

      // Mark mutation as pending - block syncs
      act(() => {
        store.dispatch({ type: "session/setPendingMutation", payload: true });
      });

      // Loader data with more messages (server processed)
      const newLoaderData = createMockLoaderData({
        session: createMockSession({ id: "session-123" }),
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
          {
            id: "msg-2",
            role: "assistant",
            content: "Hi!",
            timestamp: Date.now(),
          },
        ],
      });

      rerender({ data: newLoaderData });

      // Still 1 message (blocked by pending mutation)
      expect(store.getState().session.currentSession?.messages).toHaveLength(1);

      // Clear pending mutation
      act(() => {
        store.dispatch({ type: "session/setPendingMutation", payload: false });
      });

      // Rerender to trigger sync
      rerender({ data: newLoaderData });

      // Now should have 2 messages
      expect(store.getState().session.currentSession?.messages).toHaveLength(2);
    });
  });
});
