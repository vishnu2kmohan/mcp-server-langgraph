/**
 * useAvailableTools Hook
 *
 * Hook for fetching and managing available tools (built-in + MCP) for manual selection.
 * Provides filtering, grouping, and lookup utilities.
 *
 * @example
 * ```tsx
 * const { tools, isLoading, groupedTools, filteredTools } = useAvailableTools({
 *   searchTerm: "calc",
 *   source: "builtin",
 * });
 * ```
 */

import { useMemo, useCallback } from "react";
import { useListUnifiedToolsQuery } from "../api";
import type {
  UnifiedToolCamelCase,
  ToolSource,
  GroupedTools,
} from "../types/tools";

// =============================================================================
// Types
// =============================================================================

/** Options for the useAvailableTools hook */
export interface UseAvailableToolsOptions {
  /** Skip fetching tools (useful for conditional rendering) */
  skip?: boolean;
  /** Search term for filtering tools (matches name, displayName, description) */
  searchTerm?: string;
  /** Filter by tool source (builtin or mcp) */
  source?: ToolSource;
  /** Filter by category */
  category?: string;
}

/** Return type for the useAvailableTools hook */
export interface UseAvailableToolsResult {
  /** All tools from API */
  tools: UnifiedToolCamelCase[];
  /** Filtered tools based on options */
  filteredTools: UnifiedToolCamelCase[];
  /** Tools grouped by source (builtin) and server (mcp) */
  groupedTools: GroupedTools;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  isError: boolean;
  /** Error details */
  error: unknown;
  /** Refetch function */
  refetch: () => void;
  /** Count of built-in tools */
  builtinCount: number;
  /** Count of MCP tools */
  mcpCount: number;
  /** Count of native LLM provider tools (v7) */
  nativeCount: number;
  /** Total count of tools */
  totalCount: number;
  /** Get a tool by its name */
  getToolByName: (name: string) => UnifiedToolCamelCase | undefined;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for fetching and managing available tools.
 *
 * @param options - Configuration options
 * @returns Tool data, loading state, and utilities
 */
export function useAvailableTools(
  options: UseAvailableToolsOptions = {},
): UseAvailableToolsResult {
  const { skip = false, searchTerm, source, category } = options;

  // Fetch tools from API
  const { data, isLoading, isFetching, isError, error, refetch } =
    useListUnifiedToolsQuery(undefined, { skip });

  // Extract tools from response
  const tools = useMemo(() => data?.tools ?? [], [data?.tools]);

  // Group tools by source and server
  const groupedTools = useMemo<GroupedTools>(() => {
    const builtin: UnifiedToolCamelCase[] = [];
    const mcp: Record<string, UnifiedToolCamelCase[]> = {};
    const native: Record<string, UnifiedToolCamelCase[]> = {}; // v7

    for (const tool of tools) {
      if (tool.source === "builtin") {
        builtin.push(tool);
      } else if (tool.source === "mcp" && tool.serverName) {
        if (!mcp[tool.serverName]) {
          mcp[tool.serverName] = [];
        }
        mcp[tool.serverName].push(tool);
      } else if (tool.source === "native" && tool.provider) {
        // v7: Group native tools by provider
        if (!native[tool.provider]) {
          native[tool.provider] = [];
        }
        native[tool.provider].push(tool);
      }
    }

    return { builtin, mcp, native };
  }, [tools]);

  // Filter tools based on options
  const filteredTools = useMemo(() => {
    let filtered = [...tools];

    // Filter by source
    if (source) {
      filtered = filtered.filter((tool) => tool.source === source);
    }

    // Filter by category
    if (category) {
      filtered = filtered.filter((tool) => tool.category === category);
    }

    // Filter by search term
    if (searchTerm && searchTerm.trim()) {
      const term = searchTerm.toLowerCase().trim();
      filtered = filtered.filter(
        (tool) =>
          tool.name.toLowerCase().includes(term) ||
          tool.displayName.toLowerCase().includes(term) ||
          tool.description.toLowerCase().includes(term) ||
          (tool.serverName && tool.serverName.toLowerCase().includes(term)),
      );
    }

    return filtered;
  }, [tools, source, category, searchTerm]);

  // Get tool by name helper
  const getToolByName = useCallback(
    (name: string): UnifiedToolCamelCase | undefined => {
      return tools.find((tool) => tool.name === name);
    },
    [tools],
  );

  return {
    tools,
    filteredTools,
    groupedTools,
    isLoading: isLoading || isFetching,
    isError,
    error,
    refetch,
    builtinCount: data?.builtinCount ?? 0,
    mcpCount: data?.mcpCount ?? 0,
    nativeCount: data?.nativeCount ?? 0, // v7
    totalCount: data?.totalCount ?? 0,
    getToolByName,
  };
}
