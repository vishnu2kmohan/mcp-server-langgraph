/**
 * useConnectorSuggestions Hook
 *
 * Fetches connector template suggestions based on user input keywords.
 * Uses debouncing to avoid excessive API calls and filters out
 * already-configured connections.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import {
  useGetTemplateSuggestionsQuery,
  useListConnectionsQuery,
} from "../api";
import type { ConnectionTemplate } from "../types/connectionTemplate";

export interface UseConnectorSuggestionsOptions {
  /** Whether suggestions are enabled */
  enabled?: boolean;
  /** Minimum input length before fetching suggestions */
  minInputLength?: number;
  /** Debounce delay in milliseconds */
  debounceMs?: number;
}

export interface UseConnectorSuggestionsResult {
  /** Suggested templates that user hasn't configured yet */
  suggestions: ConnectionTemplate[];
  /** Whether suggestions are being fetched */
  isLoading: boolean;
  /** Whether suggestions are currently visible */
  isVisible: boolean;
  /** Update the input to trigger suggestion fetch */
  updateInput: (input: string) => void;
  /** Dismiss (hide) the suggestions */
  dismiss: () => void;
  /** Reset the dismissed state (show suggestions again on next match) */
  reset: () => void;
}

/**
 * Hook for fetching connector suggestions based on user input keywords.
 *
 * @example
 * ```tsx
 * const { suggestions, isLoading, isVisible, updateInput, dismiss } = useConnectorSuggestions({
 *   enabled: true,
 *   minInputLength: 5,
 *   debounceMs: 300,
 * });
 *
 * // Update on input change
 * useEffect(() => {
 *   updateInput(chatInput);
 * }, [chatInput, updateInput]);
 *
 * // Show suggestion bar when visible and has suggestions
 * if (isVisible && suggestions.length > 0) {
 *   return <ConnectorSuggestionBar suggestions={suggestions} onDismiss={dismiss} />;
 * }
 * ```
 */
export function useConnectorSuggestions({
  enabled = true,
  minInputLength = 5,
  debounceMs = 300,
}: UseConnectorSuggestionsOptions = {}): UseConnectorSuggestionsResult {
  const [debouncedQuery, setDebouncedQuery] = useState<string | undefined>(
    undefined,
  );
  const [isDismissed, setIsDismissed] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastInputRef = useRef<string | undefined>(undefined);

  // Fetch configured connections to filter out already-connected templates
  const { data: connectionsData } = useListConnectionsQuery(
    { limit: 100 },
    { skip: !enabled },
  );

  // Fetch template suggestions based on debounced query
  const {
    data: suggestionsData,
    isLoading,
    isFetching,
  } = useGetTemplateSuggestionsQuery(
    { query: debouncedQuery ?? "" },
    {
      skip:
        !enabled || !debouncedQuery || debouncedQuery.length < minInputLength,
    },
  );

  // Extract template IDs that are already configured
  const configuredTemplateIds = new Set(
    (connectionsData?.items || [])
      .filter((c) => c.status === "connected")
      // Try to match connection name/url to template id (heuristic)
      .map((c) => c.name?.toLowerCase().replace(/\s+/g, "-")),
  );

  // Filter and transform suggestions to exclude already-configured connections
  // Transform API response to match ConnectionTemplate type (undefined -> null)
  const filteredSuggestions: ConnectionTemplate[] = (
    suggestionsData?.templates || []
  )
    .filter((template) => !configuredTemplateIds.has(template.id))
    .map((t) => ({
      ...t,
      config_fields: t.config_fields.map((f) => ({
        ...f,
        placeholder: f.placeholder ?? null,
        description: f.description ?? null,
        default: f.default ?? null,
      })),
    }));

  // Update input with debouncing
  const updateInput = useCallback(
    (input: string) => {
      lastInputRef.current = input;

      // Clear existing timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Reset dismissed state when input changes significantly
      if (Math.abs(input.length - (debouncedQuery?.length || 0)) > 5) {
        setIsDismissed(false);
      }

      // Skip if input is too short
      if (input.length < minInputLength) {
        setDebouncedQuery(undefined);
        return;
      }

      // Debounce the query update
      debounceTimerRef.current = setTimeout(() => {
        setDebouncedQuery(input);
      }, debounceMs);
    },
    [debounceMs, minInputLength, debouncedQuery],
  );

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Dismiss handler
  const dismiss = useCallback(() => {
    setIsDismissed(true);
  }, []);

  // Reset dismissed state
  const reset = useCallback(() => {
    setIsDismissed(false);
  }, []);

  // Determine visibility
  const isVisible =
    enabled &&
    !isDismissed &&
    (debouncedQuery?.length ?? 0) >= minInputLength &&
    (isLoading || isFetching || filteredSuggestions.length > 0);

  return {
    suggestions: filteredSuggestions,
    isLoading: isLoading || isFetching,
    isVisible,
    updateInput,
    dismiss,
    reset,
  };
}
