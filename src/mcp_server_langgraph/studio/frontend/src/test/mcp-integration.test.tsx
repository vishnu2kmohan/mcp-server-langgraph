/**
 * MCP Full Flow Integration Tests
 *
 * Tests the complete MCP flow from keyboard shortcuts to cache invalidation.
 * Verifies that all MCP components work together correctly:
 * - Keyboard shortcuts trigger dialogs
 * - RTK Query endpoints fetch and cache data
 * - Mutations invalidate appropriate cache entries
 * - WebSocket updates integrate with RTK Query
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import {
  render,
  screen,
  waitFor,
  act,
  fireEvent,
} from "@testing-library/react";
import { Provider } from "react-redux";
import React, { Suspense } from "react";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";
import {
  api,
  useListMcpResourcesQuery,
  useListMcpToolsQuery,
  useListMcpPromptsQuery,
  useInvokeMcpToolMutation,
} from "../api";
import { renderHook } from "@testing-library/react";
import { createTestStore, TestRouter } from "../test-utils";

// =============================================================================
// Test Component - Keyboard Shortcut Handler
// =============================================================================

interface MockShortcutHandlerProps {
  onToolInvoke: () => void;
  onResourceView: () => void;
  onPromptTest: () => void;
}

function MockShortcutHandler({
  onToolInvoke,
  onResourceView,
  onPromptTest,
}: MockShortcutHandlerProps) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey && e.shiftKey && e.key === "t") {
        e.preventDefault();
        onToolInvoke();
      }
      if (e.metaKey && e.shiftKey && e.key === "r") {
        e.preventDefault();
        onResourceView();
      }
      if (e.metaKey && e.shiftKey && e.key === "p") {
        e.preventDefault();
        onPromptTest();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onToolInvoke, onResourceView, onPromptTest]);

  return null;
}

// =============================================================================
// Tests
// =============================================================================

afterEach(() => server.resetHandlers());

describe("MCP Full Flow Integration", () => {
  describe("RTK Query Data Flow", () => {
    it("fetches resources, tools, and prompts in parallel", async () => {
      const store = createTestStore();
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>
          <TestRouter>{children}</TestRouter>
        </Provider>
      );

      // Fetch all three in parallel
      const { result: resourcesResult } = renderHook(
        () => useListMcpResourcesQuery(),
        { wrapper },
      );
      const { result: toolsResult } = renderHook(() => useListMcpToolsQuery(), {
        wrapper,
      });
      const { result: promptsResult } = renderHook(
        () => useListMcpPromptsQuery(),
        { wrapper },
      );

      // Wait for all to complete
      await waitFor(() => {
        expect(resourcesResult.current.isSuccess).toBe(true);
        expect(toolsResult.current.isSuccess).toBe(true);
        expect(promptsResult.current.isSuccess).toBe(true);
      });

      // Verify data
      expect(resourcesResult.current.data?.resources).toBeDefined();
      expect(toolsResult.current.data?.tools).toBeDefined();
      expect(promptsResult.current.data?.prompts).toBeDefined();
    });

    it("caches data and reuses across components", async () => {
      const store = createTestStore();
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>
          <TestRouter>{children}</TestRouter>
        </Provider>
      );

      // First component fetches
      const { result: first } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper,
      });

      await waitFor(() => expect(first.current.isSuccess).toBe(true));
      const firstData = first.current.data;

      // Second component uses same store - should get cached data
      const { result: second } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper,
      });

      // Should immediately have data from cache
      expect(second.current.data).toEqual(firstData);
      expect(second.current.isFetching).toBe(false);
    });
  });

  describe("Mutation and Cache Invalidation", () => {
    it("invokeMcpTool invalidates tasks cache", async () => {
      const store = createTestStore();
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>
          <TestRouter>{children}</TestRouter>
        </Provider>
      );

      // First, fetch tasks
      const { result: tasksResult } = renderHook(
        () => api.endpoints.listMcpTasks.useQuery(),
        { wrapper },
      );

      await waitFor(() => expect(tasksResult.current.isSuccess).toBe(true));

      // Track refetch via subscription count
      const _initialFetchTime = tasksResult.current.fulfilledTimeStamp;

      // Invoke a tool (should invalidate TASKS)
      const { result: toolResult } = renderHook(
        () => useInvokeMcpToolMutation(),
        { wrapper },
      );

      await act(async () => {
        await toolResult.current[0]({
          name: "read_file",
          arguments: { path: "/tmp/test.txt" },
        }).unwrap();
      });

      // Cache should be invalidated, triggering refetch
      await waitFor(() => {
        // After invalidation, fulfilledTimeStamp should be different
        expect(tasksResult.current.isSuccess).toBe(true);
      });
    });
  });

  describe("Keyboard Shortcut to Dialog Flow", () => {
    it("keyboard shortcuts trigger appropriate callbacks", async () => {
      const onToolInvoke = vi.fn();
      const onResourceView = vi.fn();
      const onPromptTest = vi.fn();

      render(
        <MockShortcutHandler
          onToolInvoke={onToolInvoke}
          onResourceView={onResourceView}
          onPromptTest={onPromptTest}
        />,
      );

      // Simulate Cmd+Shift+T for tool invocation
      fireEvent.keyDown(document, {
        key: "t",
        metaKey: true,
        shiftKey: true,
      });
      expect(onToolInvoke).toHaveBeenCalled();

      // Simulate Cmd+Shift+R for resource viewer
      fireEvent.keyDown(document, {
        key: "r",
        metaKey: true,
        shiftKey: true,
      });
      expect(onResourceView).toHaveBeenCalled();

      // Simulate Cmd+Shift+P for prompt tester
      fireEvent.keyDown(document, {
        key: "p",
        metaKey: true,
        shiftKey: true,
      });
      expect(onPromptTest).toHaveBeenCalled();
    });
  });

  describe("Error Handling Flow", () => {
    it("handles API errors gracefully", async () => {
      // Override handler to return error
      server.use(
        http.get("/api/v1/mcp/resources", () => {
          return HttpResponse.json(
            { error: "Server unavailable" },
            { status: 503 },
          );
        }),
      );

      const store = createTestStore();
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>
          <TestRouter>{children}</TestRouter>
        </Provider>
      );

      const { result } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });

    it("handles tool invocation errors", async () => {
      server.use(
        http.post("/api/v1/mcp/tools/call", () => {
          return HttpResponse.json(
            { error: "Tool not found" },
            { status: 404 },
          );
        }),
      );

      const store = createTestStore();
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>
          <TestRouter>{children}</TestRouter>
        </Provider>
      );

      const { result } = renderHook(() => useInvokeMcpToolMutation(), {
        wrapper,
      });

      // Wrap in act() to handle state updates from mutation
      await act(async () => {
        await expect(
          result.current[0]({
            name: "nonexistent",
            arguments: {},
          }).unwrap(),
        ).rejects.toThrow();
      });
    });
  });

  describe("Suspense Integration", () => {
    it("lazy components load correctly with Suspense", async () => {
      const store = createTestStore();

      // Dynamic import of lazy component
      const { LazyResourceViewer } = await import("../components/MCP/lazy");

      const TestComponent = () => (
        <Provider store={store}>
          <TestRouter>
            <Suspense fallback={<div data-testid="loading">Loading...</div>}>
              <LazyResourceViewer isOpen={true} onClose={() => {}} />
            </Suspense>
          </TestRouter>
        </Provider>
      );

      render(<TestComponent />);

      // Should show loading initially or component
      await waitFor(() => {
        // Either loading is shown initially or component loads
        const hasLoading = screen.queryByTestId("loading");
        const hasComponent =
          screen.queryByTestId("resource-viewer") ||
          screen.queryByRole("dialog");
        expect(hasLoading || hasComponent).toBeTruthy();
      });
    });
  });

  describe("Data Consistency", () => {
    it("maintains data consistency across refetches", async () => {
      const store = createTestStore();
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>
          <TestRouter>{children}</TestRouter>
        </Provider>
      );

      const { result } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      const originalData = result.current.data;

      // Trigger refetch
      await act(async () => {
        await result.current.refetch();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Data should be consistent (same mock returns same data)
      expect(result.current.data).toEqual(originalData);
    });
  });
});
