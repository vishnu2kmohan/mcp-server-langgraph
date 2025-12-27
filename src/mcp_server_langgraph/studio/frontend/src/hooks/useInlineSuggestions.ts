/**
 * useInlineSuggestions Hook
 *
 * Manages AI inline suggestions for chat input.
 * Provides debounced suggestion fetching, acceptance/dismissal handling,
 * and integrates with the AI suggestions WebSocket when available.
 *
 * Usage:
 *   const {
 *     suggestion,
 *     isLoading,
 *     updateInput,
 *     acceptSuggestion,
 *     dismissSuggestion,
 *   } = useInlineSuggestions({
 *     enabled: featureEnabled,
 *     sessionId: currentSessionId,
 *     onAccept: (suggestion) => setInput(input + suggestion),
 *   });
 */

import { useState, useCallback, useRef, useEffect } from "react";
import debounce from "lodash/debounce";

/**
 * Suggestion response from fetch function.
 */
export interface SuggestionResponse {
  text: string;
  confidence?: number;
  reasoning?: string;
}

/**
 * Fetch context passed to the suggestion fetcher.
 */
export interface SuggestionFetchContext {
  sessionId?: string;
  signal?: AbortSignal;
}

/**
 * Options for useInlineSuggestions hook.
 */
export interface UseInlineSuggestionsOptions {
  /** Enable/disable suggestions. */
  enabled?: boolean;

  /** Minimum input length before fetching suggestions. */
  minLength?: number;

  /** Debounce delay in milliseconds. */
  debounceMs?: number;

  /** Minimum confidence threshold for showing suggestions. */
  minConfidence?: number;

  /** Session ID for context. */
  sessionId?: string;

  /** Custom fetch function for suggestions. */
  fetchSuggestion?: (
    input: string,
    context?: SuggestionFetchContext,
  ) => Promise<string | SuggestionResponse>;

  /** Callback when suggestion is accepted. */
  onAccept?: (suggestion: string) => void;

  /** Callback when suggestion is dismissed. */
  onDismiss?: () => void;

  /** Callback on error. */
  onError?: (error: Error) => void;
}

/**
 * Return type for useInlineSuggestions hook.
 */
export interface UseInlineSuggestionsResult {
  /** Current suggestion text. */
  suggestion: string;

  /** Whether a suggestion is being fetched. */
  isLoading: boolean;

  /** Error message if fetch failed. */
  error: string | null;

  /** Update the input text to trigger suggestion fetch. */
  updateInput: (input: string) => void;

  /** Accept the current suggestion. */
  acceptSuggestion: () => void;

  /** Dismiss the current suggestion. */
  dismissSuggestion: () => void;

  /** Manually set suggestion (for testing). */
  setSuggestion: (suggestion: string) => void;
}

/**
 * Default suggestion fetcher using the REST API.
 *
 * Fetches suggestions from /api/v1/ai/chat-suggestions endpoint.
 * Falls back to empty string if the API is unavailable or returns no results.
 *
 * For real-time suggestions, consumers should use the WebSocket-based
 * `useAIRealTimeSuggestions` hook instead.
 */
const defaultFetchSuggestion = async (
  input: string,
  context?: SuggestionFetchContext,
): Promise<SuggestionResponse | string> => {
  // If no session ID is provided, return empty (cannot get context-aware suggestions)
  if (!context?.sessionId) {
    return "";
  }

  try {
    const response = await fetch("/api/v1/ai/chat-suggestions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      signal: context.signal,
      body: JSON.stringify({
        input_text: input,
        session_id: context.sessionId,
        max_suggestions: 1,
      }),
    });

    if (!response.ok) {
      // API not available or error - return empty (graceful degradation)
      return "";
    }

    const data = await response.json();

    // Return the first suggestion if available
    if (data.suggestions && data.suggestions.length > 0) {
      const suggestion = data.suggestions[0];
      return {
        text: suggestion.text || suggestion.content || "",
        confidence: suggestion.confidence ?? 0.7,
        reasoning: suggestion.reasoning,
      };
    }

    return "";
  } catch {
    // Network error or API unavailable - return empty (graceful degradation)
    return "";
  }
};

/**
 * Hook for managing inline AI suggestions in chat input.
 */
export function useInlineSuggestions(
  options: UseInlineSuggestionsOptions = {},
): UseInlineSuggestionsResult {
  const {
    enabled = true,
    minLength = 3,
    debounceMs = 300,
    minConfidence = 0,
    sessionId,
    fetchSuggestion = defaultFetchSuggestion,
    onAccept,
    onDismiss,
    onError,
  } = options;

  // State
  const [suggestion, setSuggestion] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Refs for cleanup and cancellation
  const abortControllerRef = useRef<AbortController | null>(null);
  const inputRef = useRef<string>("");

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Fetch suggestion for input
  const fetchSuggestionInternal = useCallback(
    async (input: string) => {
      // Cancel previous request
      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      setIsLoading(true);

      try {
        const context: SuggestionFetchContext = {
          sessionId,
          signal: abortControllerRef.current.signal,
        };

        const result = await fetchSuggestion(input, context);

        // Handle both string and object responses
        if (typeof result === "string") {
          setSuggestion(result);
        } else {
          // Check confidence threshold
          const confidence = result.confidence ?? 1;
          if (confidence >= minConfidence) {
            setSuggestion(result.text);
          } else {
            setSuggestion("");
          }
        }

        setError(null);
      } catch (err) {
        // Ignore abort errors
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch suggestion";
        setError(errorMessage);
        setSuggestion("");
        onError?.(err instanceof Error ? err : new Error(errorMessage));
      } finally {
        setIsLoading(false);
      }
    },
    [fetchSuggestion, minConfidence, onError, sessionId],
  );

  // Create debounced fetch function
  // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce returns a function with unknown deps
  const debouncedFetch = useCallback(
    debounce((input: string) => {
      fetchSuggestionInternal(input);
    }, debounceMs),
    [fetchSuggestionInternal, debounceMs],
  );

  // Cancel debounced fetch on cleanup
  useEffect(() => {
    return () => {
      debouncedFetch.cancel();
    };
  }, [debouncedFetch]);

  // Update input and trigger suggestion fetch
  const updateInput = useCallback(
    (input: string) => {
      inputRef.current = input;

      // Clear error on new input
      setError(null);

      // If disabled or input too short, clear suggestion
      if (!enabled || input.trim().length < minLength) {
        setSuggestion("");
        setIsLoading(false);
        return;
      }

      // Fetch suggestion (debounced)
      debouncedFetch(input);
    },
    [enabled, minLength, debouncedFetch],
  );

  // Accept the current suggestion
  const acceptSuggestion = useCallback(() => {
    if (suggestion) {
      onAccept?.(suggestion);
      setSuggestion("");
    }
  }, [suggestion, onAccept]);

  // Dismiss the current suggestion
  const dismissSuggestion = useCallback(() => {
    setSuggestion("");
    onDismiss?.();
  }, [onDismiss]);

  return {
    suggestion,
    isLoading,
    error,
    updateInput,
    acceptSuggestion,
    dismissSuggestion,
    setSuggestion,
  };
}

export default useInlineSuggestions;
