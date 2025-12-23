/**
 * useDevToolsContext Hook Tests
 *
 * TDD tests for context detection hook.
 * Tests cover:
 * - Detecting session context from chat routes
 * - Detecting workflow context from workflow routes
 * - Falling back to global context
 * - Extracting entity IDs from URL params
 * - Updating Redux state on context changes
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useLocation, useSearchParams } from "react-router";
import React from "react";
import { useDevToolsContext } from "./useDevToolsContext";
import devToolsReducer, {
  setDetectedContext,
  setContextEntityId,
} from "../../../store/slices/devToolsSlice";
import type { DevToolsContext } from "../../../store/slices/devToolsSlice";

// Mock react-router hooks
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useLocation: vi.fn(),
    useSearchParams: vi.fn(),
  };
});

describe("useDevToolsContext", () => {
  const mockUseLocation = vi.mocked(useLocation);
  const mockUseSearchParams = vi.mocked(useSearchParams);

  // Create a test store
  function createTestStore(initialContext: DevToolsContext = "global") {
    return configureStore({
      reducer: {
        devTools: devToolsReducer,
      },
      preloadedState: {
        devTools: {
          collapsed: true,
          height: 250,
          maximized: false,
          activeTab: "console" as const,
          detectedContext: initialContext,
          contextEntityId: null,
          consoleFilter: "all" as const,
          aiInsightsEnabled: false,
          aiSuggestedLayout: null,
        },
      },
    });
  }

  // Wrapper with Redux Provider
  function createWrapper(store: ReturnType<typeof createTestStore>) {
    return function Wrapper({ children }: { children: React.ReactNode }) {
      return React.createElement(Provider, { store }, children);
    };
  }

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock values
    mockUseLocation.mockReturnValue({
      pathname: "/studio",
      search: "",
      hash: "",
      state: null,
      key: "default",
    });
    mockUseSearchParams.mockReturnValue([new URLSearchParams(), vi.fn()]);
  });

  // ===========================================================================
  // Context Detection from Routes
  // ===========================================================================

  describe("context detection", () => {
    it("should detect session context from /studio/chat route", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "",
        hash: "",
        state: null,
        key: "chat",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.context).toBe("session");
    });

    it("should detect session context from /studio/chat route", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "",
        hash: "",
        state: null,
        key: "chat",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.context).toBe("session");
    });

    it("should detect workflow context from /studio/workflows route", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/workflows",
        search: "",
        hash: "",
        state: null,
        key: "workflows",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.context).toBe("workflow");
    });

    it("should detect workflow context from /studio/workflows route", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/workflows",
        search: "",
        hash: "",
        state: null,
        key: "workflows",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.context).toBe("workflow");
    });

    it("should detect global context for other routes", () => {
      const store = createTestStore("session"); // Start with session
      mockUseLocation.mockReturnValue({
        pathname: "/studio/settings",
        search: "",
        hash: "",
        state: null,
        key: "settings",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.context).toBe("global");
    });

    it("should detect global context for /studio/observability", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/observability",
        search: "",
        hash: "",
        state: null,
        key: "observability",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.context).toBe("global");
    });

    it("should detect global context for /studio/cost", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/cost",
        search: "",
        hash: "",
        state: null,
        key: "cost",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.context).toBe("global");
    });
  });

  // ===========================================================================
  // Entity ID Extraction
  // ===========================================================================

  describe("entity ID extraction", () => {
    it("should extract session ID from ?session= param", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "?session=session-123",
        hash: "",
        state: null,
        key: "chat",
      });
      mockUseSearchParams.mockReturnValue([
        new URLSearchParams("session=session-123"),
        vi.fn(),
      ]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.entityId).toBe("session-123");
    });

    it("should extract workflow ID from ?workflow= param", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/workflows",
        search: "?workflow=workflow-456",
        hash: "",
        state: null,
        key: "workflows",
      });
      mockUseSearchParams.mockReturnValue([
        new URLSearchParams("workflow=workflow-456"),
        vi.fn(),
      ]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.entityId).toBe("workflow-456");
    });

    it("should return null when no entity ID in params", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "",
        hash: "",
        state: null,
        key: "chat",
      });
      mockUseSearchParams.mockReturnValue([new URLSearchParams(), vi.fn()]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.entityId).toBeNull();
    });

    it("should extract ID from route path segment /chat/:id", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat/session-789",
        search: "",
        hash: "",
        state: null,
        key: "chat-id",
      });
      mockUseSearchParams.mockReturnValue([new URLSearchParams(), vi.fn()]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.entityId).toBe("session-789");
    });

    it("should extract ID from route path segment /workflows/:id", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/workflows/workflow-abc",
        search: "",
        hash: "",
        state: null,
        key: "workflow-id",
      });
      mockUseSearchParams.mockReturnValue([new URLSearchParams(), vi.fn()]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.entityId).toBe("workflow-abc");
    });
  });

  // ===========================================================================
  // Redux State Updates
  // ===========================================================================

  describe("Redux state updates", () => {
    it("should dispatch setDetectedContext when context changes", () => {
      const store = createTestStore("global");
      const dispatchSpy = vi.spyOn(store, "dispatch");

      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "",
        hash: "",
        state: null,
        key: "chat",
      });

      renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(dispatchSpy).toHaveBeenCalledWith(setDetectedContext("session"));
    });

    it("should dispatch setContextEntityId when entity ID changes", () => {
      const store = createTestStore();
      const dispatchSpy = vi.spyOn(store, "dispatch");

      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "?session=new-session",
        hash: "",
        state: null,
        key: "chat",
      });
      mockUseSearchParams.mockReturnValue([
        new URLSearchParams("session=new-session"),
        vi.fn(),
      ]);

      renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(dispatchSpy).toHaveBeenCalledWith(
        setContextEntityId("new-session"),
      );
    });

    it("should not dispatch if context is the same", () => {
      const store = createTestStore("session");
      const dispatchSpy = vi.spyOn(store, "dispatch");

      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "",
        hash: "",
        state: null,
        key: "chat",
      });

      renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      // Should not dispatch setDetectedContext since it's already "session"
      const contextDispatchCalls = dispatchSpy.mock.calls.filter(
        (call) => call[0]?.type === "devTools/setDetectedContext",
      );
      expect(contextDispatchCalls.length).toBe(0);
    });
  });

  // ===========================================================================
  // Return Value
  // ===========================================================================

  describe("return value", () => {
    it("should return context, entityId, and contextLabel", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "?session=my-session",
        hash: "",
        state: null,
        key: "chat",
      });
      mockUseSearchParams.mockReturnValue([
        new URLSearchParams("session=my-session"),
        vi.fn(),
      ]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toHaveProperty("context");
      expect(result.current).toHaveProperty("entityId");
      expect(result.current).toHaveProperty("contextLabel");
    });

    it("should return correct contextLabel for session", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "?session=my-session",
        hash: "",
        state: null,
        key: "chat",
      });
      mockUseSearchParams.mockReturnValue([
        new URLSearchParams("session=my-session"),
        vi.fn(),
      ]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.contextLabel).toBe("Session: my-session");
    });

    it("should return correct contextLabel for workflow", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/workflows",
        search: "?workflow=my-workflow",
        hash: "",
        state: null,
        key: "workflows",
      });
      mockUseSearchParams.mockReturnValue([
        new URLSearchParams("workflow=my-workflow"),
        vi.fn(),
      ]);

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.contextLabel).toBe("Workflow: my-workflow");
    });

    it("should return 'Global' contextLabel for global context", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/settings",
        search: "",
        hash: "",
        state: null,
        key: "settings",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.contextLabel).toBe("Global");
    });

    it("should return context type without ID if no entity ID", () => {
      const store = createTestStore();
      mockUseLocation.mockReturnValue({
        pathname: "/studio/chat",
        search: "",
        hash: "",
        state: null,
        key: "chat",
      });

      const { result } = renderHook(() => useDevToolsContext(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.contextLabel).toBe("Session");
    });
  });
});
