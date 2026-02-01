/**
 * useAvailableTools Hook Tests
 *
 * TDD: These tests are written FIRST to define the expected behavior
 * of the useAvailableTools hook for manual tool selection.
 *
 * Tests verify:
 * 1. Hook fetches unified tools from API
 * 2. Returns loading state
 * 3. Returns tools data (built-in + MCP)
 * 4. Groups tools by source and server
 * 5. Provides search filtering
 * 6. Returns error state on failure
 * 7. Provides refetch function
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { useAvailableTools } from "./useAvailableTools";
import type { UnifiedToolCamelCase } from "../types/tools";

// Mock the RTK Query endpoint
vi.mock("../api", () => ({
  useListUnifiedToolsQuery: vi.fn(),
}));

import { useListUnifiedToolsQuery } from "../api";

const mockUseListUnifiedToolsQuery = useListUnifiedToolsQuery as ReturnType<
  typeof vi.fn
>;

// Sample tool data for tests
const mockBuiltinTools: UnifiedToolCamelCase[] = [
  {
    name: "calculator",
    displayName: "Calculator",
    description: "Perform mathematical calculations",
    source: "builtin",
    serverName: null,
    category: "calculator",
    inputSchema: {},
    requiresSandbox: false,
  },
  {
    name: "web_search",
    displayName: "Web Search",
    description: "Search the web",
    source: "builtin",
    serverName: null,
    category: "search",
    inputSchema: {},
    requiresSandbox: false,
  },
];

const mockMCPTools: UnifiedToolCamelCase[] = [
  {
    name: "github:create_issue",
    displayName: "Create Issue",
    description: "Create a GitHub issue",
    source: "mcp",
    serverName: "github",
    category: null,
    inputSchema: {},
    requiresSandbox: false,
  },
  {
    name: "github:list_repos",
    displayName: "List Repos",
    description: "List GitHub repositories",
    source: "mcp",
    serverName: "github",
    category: null,
    inputSchema: {},
    requiresSandbox: false,
  },
  {
    name: "slack:send_message",
    displayName: "Send Message",
    description: "Send a Slack message",
    source: "mcp",
    serverName: "slack",
    category: null,
    inputSchema: {},
    requiresSandbox: false,
  },
];

describe("useAvailableTools", () => {
  // Create a minimal Redux store wrapper
  const createWrapper = () => {
    const store = configureStore({
      reducer: {
        test: (state = {}) => state,
      },
    });

    return ({ children }: { children: ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should return isLoading true when fetching", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isFetching: true,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.tools).toEqual([]);
    });

    it("should return isLoading false after data loads", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: mockBuiltinTools,
          builtinCount: 2,
          mcpCount: 0,
          totalCount: 2,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.tools).toHaveLength(2);
    });
  });

  // ===========================================================================
  // Data Fetching Tests
  // ===========================================================================

  describe("data fetching", () => {
    it("should return all tools from the API", () => {
      const allTools = [...mockBuiltinTools, ...mockMCPTools];
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: allTools,
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.tools).toHaveLength(5);
      expect(result.current.builtinCount).toBe(2);
      expect(result.current.mcpCount).toBe(3);
      expect(result.current.totalCount).toBe(5);
    });

    it("should skip fetching when skip option is true", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      renderHook(() => useAvailableTools({ skip: true }), {
        wrapper: createWrapper(),
      });

      expect(mockUseListUnifiedToolsQuery).toHaveBeenCalledWith(undefined, {
        skip: true,
      });
    });
  });

  // ===========================================================================
  // Grouped Tools Tests
  // ===========================================================================

  describe("grouped tools", () => {
    it("should group built-in tools separately", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.groupedTools.builtin).toHaveLength(2);
      expect(result.current.groupedTools.builtin[0].name).toBe("calculator");
      expect(result.current.groupedTools.builtin[1].name).toBe("web_search");
    });

    it("should group MCP tools by server name", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(Object.keys(result.current.groupedTools.mcp)).toContain("github");
      expect(Object.keys(result.current.groupedTools.mcp)).toContain("slack");
      expect(result.current.groupedTools.mcp["github"]).toHaveLength(2);
      expect(result.current.groupedTools.mcp["slack"]).toHaveLength(1);
    });

    it("should return empty groups when no tools available", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [],
          builtinCount: 0,
          mcpCount: 0,
          totalCount: 0,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.groupedTools.builtin).toEqual([]);
      expect(result.current.groupedTools.mcp).toEqual({});
    });
  });

  // ===========================================================================
  // Search/Filter Tests
  // ===========================================================================

  describe("search filtering", () => {
    it("should filter tools by search term (case insensitive)", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useAvailableTools({ searchTerm: "calc" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.filteredTools).toHaveLength(1);
      expect(result.current.filteredTools[0].name).toBe("calculator");
    });

    it("should filter by tool description", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useAvailableTools({ searchTerm: "GitHub" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.filteredTools).toHaveLength(2);
      expect(
        result.current.filteredTools.every((t) => t.serverName === "github"),
      ).toBe(true);
    });

    it("should return all tools when search term is empty", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useAvailableTools({ searchTerm: "" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.filteredTools).toHaveLength(5);
    });

    it("should return empty array when no tools match search", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: mockBuiltinTools,
          builtinCount: 2,
          mcpCount: 0,
          totalCount: 2,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useAvailableTools({ searchTerm: "nonexistent" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.filteredTools).toHaveLength(0);
    });
  });

  // ===========================================================================
  // Error State Tests
  // ===========================================================================

  describe("error state", () => {
    it("should return isError true on failure", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        error: { status: 500, data: "Internal Server Error" },
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBeDefined();
    });

    it("should return empty tools array on error", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        error: { status: 500, data: "Internal Server Error" },
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.tools).toEqual([]);
    });
  });

  // ===========================================================================
  // Refetch Tests
  // ===========================================================================

  describe("refetch", () => {
    it("should provide refetch function", () => {
      const mockRefetch = vi.fn();
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: mockBuiltinTools,
          builtinCount: 2,
          mcpCount: 0,
          totalCount: 2,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: mockRefetch,
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.refetch).toBe(mockRefetch);
    });
  });

  // ===========================================================================
  // Tool Lookup Tests
  // ===========================================================================

  describe("tool lookup", () => {
    it("should provide getToolByName helper", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      const tool = result.current.getToolByName("calculator");
      expect(tool).toBeDefined();
      expect(tool?.displayName).toBe("Calculator");
    });

    it("should return undefined for unknown tool name", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: mockBuiltinTools,
          builtinCount: 2,
          mcpCount: 0,
          totalCount: 2,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      const tool = result.current.getToolByName("unknown_tool");
      expect(tool).toBeUndefined();
    });
  });

  // ===========================================================================
  // Category Filtering Tests
  // ===========================================================================

  describe("category filtering", () => {
    it("should filter tools by category", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: mockBuiltinTools,
          builtinCount: 2,
          mcpCount: 0,
          totalCount: 2,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useAvailableTools({ category: "calculator" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.filteredTools).toHaveLength(1);
      expect(result.current.filteredTools[0].category).toBe("calculator");
    });

    it("should return all tools when category is undefined", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: mockBuiltinTools,
          builtinCount: 2,
          mcpCount: 0,
          totalCount: 2,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useAvailableTools(), {
        wrapper: createWrapper(),
      });

      expect(result.current.filteredTools).toHaveLength(2);
    });
  });

  // ===========================================================================
  // Source Filtering Tests
  // ===========================================================================

  describe("source filtering", () => {
    it("should filter by builtin source", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useAvailableTools({ source: "builtin" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.filteredTools).toHaveLength(2);
      expect(
        result.current.filteredTools.every((t) => t.source === "builtin"),
      ).toBe(true);
    });

    it("should filter by mcp source", () => {
      mockUseListUnifiedToolsQuery.mockReturnValue({
        data: {
          tools: [...mockBuiltinTools, ...mockMCPTools],
          builtinCount: 2,
          mcpCount: 3,
          totalCount: 5,
        },
        isLoading: false,
        isFetching: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      const { result } = renderHook(
        () => useAvailableTools({ source: "mcp" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.filteredTools).toHaveLength(3);
      expect(
        result.current.filteredTools.every((t) => t.source === "mcp"),
      ).toBe(true);
    });
  });
});
