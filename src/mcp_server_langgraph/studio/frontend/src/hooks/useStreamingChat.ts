/**
 * useStreamingChat Hook
 *
 * React hook for handling streaming chat responses using fetch + ReadableStream.
 * Uses POST requests with JSON body to support the backend's streaming endpoint.
 *
 * Note: We use fetch with ReadableStream instead of EventSource because:
 * - EventSource only supports GET requests
 * - Our backend expects POST /api/v1/chat/completions/stream with a JSON body
 */

import { useState, useCallback, useRef, useEffect } from "react";

/**
 * Token usage information from streaming response
 */
export interface StreamingUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

/**
 * State for streaming chat
 */
interface StreamingChatState {
  isStreaming: boolean;
  streamingContent: string;
  error: string | null;
  usage: StreamingUsage | null;
  model: string | null;
  traceId: string | null;
}

/**
 * Return type for useStreamingChat hook
 */
export interface UseStreamingChatReturn extends StreamingChatState {
  startStream: (sessionId: string, message: string) => void;
  stopStream: () => void;
  clearContent: () => void;
}

/**
 * Hook for managing streaming chat with fetch + ReadableStream
 *
 * @returns Streaming chat state and control functions
 *
 * @example
 * ```tsx
 * const { isStreaming, streamingContent, startStream, stopStream } = useStreamingChat();
 *
 * const handleSend = (message: string) => {
 *   startStream('session-123', message);
 * };
 *
 * return (
 *   <div>
 *     {isStreaming && <p>Loading...</p>}
 *     <p>{streamingContent}</p>
 *   </div>
 * );
 * ```
 */
export function useStreamingChat(): UseStreamingChatReturn {
  const [state, setState] = useState<StreamingChatState>({
    isStreaming: false,
    streamingContent: "",
    error: null,
    usage: null,
    model: null,
    traceId: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Parse SSE data line and extract content
   */
  const parseSSELine = useCallback(
    (
      line: string,
    ): {
      content?: string;
      usage?: StreamingUsage;
      model?: string;
      traceId?: string;
      done?: boolean;
    } | null => {
      // Check for done signal
      if (line === "data: [DONE]") {
        return { done: true };
      }

      // Parse data lines
      if (line.startsWith("data: ")) {
        const jsonStr = line.slice(6); // Remove "data: " prefix
        try {
          const data = JSON.parse(jsonStr);

          const result: {
            content?: string;
            usage?: StreamingUsage;
            model?: string;
            traceId?: string;
          } = {};

          // Handle content - support both direct content and delta.content formats
          if (data.content) {
            result.content = data.content;
          } else if (data.delta?.content) {
            result.content = data.delta.content;
          }

          // Handle usage
          if (data.usage) {
            result.usage = {
              promptTokens: data.usage.prompt_tokens,
              completionTokens: data.usage.completion_tokens,
              totalTokens: data.usage.total_tokens,
            };
          }

          // Handle model
          if (data.model) {
            result.model = data.model;
          }

          // Handle trace_id for observability correlation
          if (data.trace_id) {
            result.traceId = data.trace_id;
          }

          return result;
        } catch {
          // Ignore non-JSON data lines
          return null;
        }
      }

      return null;
    },
    [],
  );

  /**
   * Start streaming chat response
   */
  const startStream = useCallback(
    (sessionId: string, message: string) => {
      // Abort any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Reset state
      setState({
        isStreaming: true,
        streamingContent: "",
        error: null,
        usage: null,
        model: null,
        traceId: null,
      });

      // Build request body matching ChatCompletionRequest
      const requestBody = {
        session_id: sessionId,
        messages: [{ role: "user", content: message }],
      };

      // Start the fetch + stream processing
      const processStream = async () => {
        try {
          // Get JWT token from localStorage (hybrid auth: JWT primary, cookies fallback)
          const token = localStorage.getItem("auth_token");

          const response = await fetch("/api/v1/chat/completions/stream", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify(requestBody),
            signal: abortController.signal,
            // Include credentials (cookies) for forward-auth (Keycloak SSO)
            credentials: "include",
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error("No response body");
          }

          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();

            if (done) {
              setState((prev) => ({ ...prev, isStreaming: false }));
              break;
            }

            // Decode chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });

            // Process complete lines
            const lines = buffer.split("\n");
            buffer = lines.pop() || ""; // Keep incomplete line in buffer

            for (const line of lines) {
              const trimmedLine = line.trim();
              if (!trimmedLine) continue;

              const parsed = parseSSELine(trimmedLine);
              if (!parsed) continue;

              if (parsed.done) {
                setState((prev) => ({ ...prev, isStreaming: false }));
                return;
              }

              setState((prev) => {
                const updates: Partial<StreamingChatState> = {};

                if (parsed.content) {
                  updates.streamingContent =
                    prev.streamingContent + parsed.content;
                }

                if (parsed.usage) {
                  updates.usage = parsed.usage;
                }

                if (parsed.model) {
                  updates.model = parsed.model;
                }

                if (parsed.traceId) {
                  updates.traceId = parsed.traceId;
                }

                return { ...prev, ...updates };
              });
            }
          }
        } catch (error) {
          // Ignore abort errors
          if (error instanceof Error && error.name === "AbortError") {
            return;
          }

          setState((prev) => ({
            ...prev,
            isStreaming: false,
            error: `Stream connection failed: ${error instanceof Error ? error.message : String(error)}`,
          }));
        }
      };

      // Start processing (don't await - let it run async)
      processStream();
    },
    [parseSSELine],
  );

  /**
   * Stop streaming
   */
  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setState((prev) => ({ ...prev, isStreaming: false }));
  }, []);

  /**
   * Clear accumulated content
   */
  const clearContent = useCallback(() => {
    setState((prev) => ({
      ...prev,
      streamingContent: "",
      error: null,
      usage: null,
      model: null,
      traceId: null,
    }));
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    ...state,
    startStream,
    stopStream,
    clearContent,
  };
}
