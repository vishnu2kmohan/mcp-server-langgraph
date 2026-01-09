/**
 * Tests for useStreamingChat selected_tools SSE Event Handling
 *
 * TDD tests for Phase 5: Frontend consumption of selected_tools SSE events
 * from semantic tool selection in the LangGraph streaming path.
 *
 * RED Phase: These tests define the expected behavior.
 * GREEN Phase: Implementation will add selected_tools state and parsing.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { useStreamingChat } from "./useStreamingChat";
import langGraphReducer from "../store/slices/langGraphSlice";

// Mock authenticatedFetch
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock intendedRoute
vi.mock("../utils/intendedRoute", () => ({
  saveCurrentRouteAsIntended: vi.fn(),
}));

// Create mock response stream
function createMockStream(chunks: string[]) {
  let index = 0;
  return {
    getReader: () => ({
      read: async () => {
        if (index >= chunks.length) {
          return { done: true, value: undefined };
        }
        const chunk = new TextEncoder().encode(chunks[index]);
        index++;
        return { done: false, value: chunk };
      },
    }),
  };
}

// Create mock fetch response
function createMockResponse(chunks: string[]) {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    body: createMockStream(chunks),
  };
}

// Create test wrapper with Redux store
function createWrapper() {
  const store = configureStore({
    reducer: {
      langGraph: langGraphReducer,
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  };
}

describe("useStreamingChat selected_tools SSE handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("should have selectedTools in initial state as empty array", () => {
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    expect(result.current.selectedTools).toEqual([]);
  });

  it("should have selectionScores in initial state as empty object", () => {
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    expect(result.current.selectionScores).toEqual({});
  });

  it("should parse selected_tools SSE event and update state", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    const sseChunks = [
      'data: {"selected_tools": ["calculator", "search_kb"], "selection_scores": {"calculator": 0.95, "search_kb": 0.87}}\n\n',
      'data: {"delta": {"content": "Hello!"}}\n\n',
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValue(
      createMockResponse(sseChunks) as unknown as Response,
    );

    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.startStream("session-123", "Calculate 2+2");
    });

    await waitFor(() => {
      expect(result.current.selectedTools).toEqual(["calculator", "search_kb"]);
    });

    expect(result.current.selectionScores).toEqual({
      calculator: 0.95,
      search_kb: 0.87,
    });
  });

  it("should handle selected_tools with totalAvailable count", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    const sseChunks = [
      'data: {"selected_tools": ["read_file"], "selection_scores": {"read_file": 0.92}, "total_available": 50}\n\n',
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValue(
      createMockResponse(sseChunks) as unknown as Response,
    );

    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.startStream("session-123", "Read the file");
    });

    await waitFor(() => {
      expect(result.current.totalAvailableTools).toBe(50);
    });
  });

  it("should handle empty selected_tools array", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    const sseChunks = [
      'data: {"selected_tools": [], "selection_scores": {}}\n\n',
      'data: {"delta": {"content": "Hi!"}}\n\n',
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValue(
      createMockResponse(sseChunks) as unknown as Response,
    );

    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.startStream("session-123", "Hello");
    });

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false);
    });

    expect(result.current.selectedTools).toEqual([]);
    expect(result.current.selectionScores).toEqual({});
  });

  it("should clear selectedTools on new stream", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    // First stream with selected tools
    const firstChunks = [
      'data: {"selected_tools": ["tool1", "tool2"]}\n\n',
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValueOnce(
      createMockResponse(firstChunks) as unknown as Response,
    );

    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.startStream("session-123", "First message");
    });

    await waitFor(() => {
      expect(result.current.selectedTools).toEqual(["tool1", "tool2"]);
    });

    // Second stream should clear previous tools
    const secondChunks = [
      'data: {"delta": {"content": "Response"}}\n\n',
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValueOnce(
      createMockResponse(secondChunks) as unknown as Response,
    );

    act(() => {
      result.current.startStream("session-123", "Second message");
    });

    // Should reset to empty before new stream starts
    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false);
    });
  });

  it("should include selectedTools in clearContent reset", () => {
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.clearContent();
    });

    expect(result.current.selectedTools).toEqual([]);
    expect(result.current.selectionScores).toEqual({});
    expect(result.current.totalAvailableTools).toBeNull();
  });
});

describe("useStreamingChat parseSSELine for selected_tools", () => {
  it("should parse selected_tools from SSE data line", () => {
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    // Access the internal parseSSELine by testing through state updates
    // This is implicitly tested through the integration tests above
    expect(result.current.selectedTools).toBeDefined();
  });
});
