/**
 * useNativeCapabilities Hook
 *
 * Hook for fetching native LLM provider tool capabilities for a specific model.
 * Returns which native tools are supported by the model and whether feature flags
 * are enabled for each tool.
 *
 * @example
 * ```tsx
 * const { capabilities, isLoading, supportsWebSearch, supportsCodeExecution } =
 *   useNativeCapabilities({ modelId: "claude-sonnet-4-20250514" });
 *
 * // Check if model supports native web search
 * if (supportsWebSearch) {
 *   // Show native tool preference option
 * }
 * ```
 *
 * @see GET /api/v1/tools/native-capabilities/{model_id}
 */

import { useMemo } from "react";
import { useGetNativeCapabilitiesQuery } from "../api";
import type { NativeToolCapabilityCamelCase } from "../types/tools";

// =============================================================================
// Types
// =============================================================================

/** Options for the useNativeCapabilities hook */
export interface UseNativeCapabilitiesOptions {
  /** Model ID to check capabilities for */
  modelId: string;
  /** Skip fetching capabilities (useful for conditional rendering) */
  skip?: boolean;
}

/** Return type for the useNativeCapabilities hook */
export interface UseNativeCapabilitiesResult {
  /** All native tool capabilities for the model */
  capabilities: NativeToolCapabilityCamelCase[];
  /** The native provider for this model (anthropic, google, openai, or null) */
  nativeProvider: string | null;
  /** Whether native tools are enabled globally (master switch) */
  masterEnabled: boolean;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  isError: boolean;
  /** Error details */
  error: unknown;
  /** Refetch function */
  refetch: () => void;

  // Convenience booleans for common checks
  /** Whether the model supports native web search (and it's enabled) */
  supportsWebSearch: boolean;
  /** Whether the model supports native code execution (and it's enabled) */
  supportsCodeExecution: boolean;
  /** Whether any native tools are available for this model */
  hasNativeTools: boolean;

  /** Check if a specific tool is supported and enabled */
  isToolAvailable: (toolName: string) => boolean;
  /** Get capability for a specific tool */
  getCapability: (
    toolName: string,
  ) => NativeToolCapabilityCamelCase | undefined;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for fetching native tool capabilities for a model.
 *
 * @param options - Configuration options including modelId
 * @returns Capability data, loading state, and utilities
 */
export function useNativeCapabilities(
  options: UseNativeCapabilitiesOptions,
): UseNativeCapabilitiesResult {
  const { modelId, skip = false } = options;

  // Fetch capabilities from API
  const { data, isLoading, isFetching, isError, error, refetch } =
    useGetNativeCapabilitiesQuery({ modelId }, { skip: skip || !modelId });

  // Extract capabilities from response
  const capabilities = useMemo(
    () => data?.capabilities ?? [],
    [data?.capabilities],
  );

  // Check if web search is supported and enabled
  const supportsWebSearch = useMemo(() => {
    const webSearch = capabilities.find((c) => c.toolName === "web_search");
    return webSearch?.supported === true && webSearch?.enabled === true;
  }, [capabilities]);

  // Check if code execution is supported and enabled
  const supportsCodeExecution = useMemo(() => {
    const codeExec = capabilities.find((c) => c.toolName === "code_execution");
    return codeExec?.supported === true && codeExec?.enabled === true;
  }, [capabilities]);

  // Check if any native tools are available
  const hasNativeTools = useMemo(() => {
    return (
      (data?.masterEnabled ?? false) &&
      capabilities.some((c) => c.supported && c.enabled)
    );
  }, [data?.masterEnabled, capabilities]);

  // Check if a specific tool is available (supported + enabled)
  const isToolAvailable = useMemo(() => {
    return (toolName: string): boolean => {
      if (!data?.masterEnabled) return false;
      const cap = capabilities.find((c) => c.toolName === toolName);
      return cap?.supported === true && cap?.enabled === true;
    };
  }, [capabilities, data?.masterEnabled]);

  // Get capability for a specific tool
  const getCapability = useMemo(() => {
    return (toolName: string): NativeToolCapabilityCamelCase | undefined => {
      return capabilities.find((c) => c.toolName === toolName);
    };
  }, [capabilities]);

  return {
    capabilities,
    nativeProvider: data?.nativeProvider ?? null,
    masterEnabled: data?.masterEnabled ?? false,
    isLoading: isLoading || isFetching,
    isError,
    error,
    refetch,
    supportsWebSearch,
    supportsCodeExecution,
    hasNativeTools,
    isToolAvailable,
    getCapability,
  };
}
