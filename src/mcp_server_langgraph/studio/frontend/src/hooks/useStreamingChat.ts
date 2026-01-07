/**
 * useStreamingChat Hook
 *
 * React hook for handling streaming chat responses using fetch + ReadableStream.
 * Uses POST requests with JSON body to support the backend's streaming endpoint.
 *
 * Features:
 * - Streaming content accumulation
 * - Thinking/reasoning content parsing (Claude, Gemini, OpenAI)
 * - Reasoning effort control (low/medium/high)
 * - Token usage tracking
 * - Model and trace ID tracking
 *
 * Note: We use fetch with ReadableStream instead of EventSource because:
 * - EventSource only supports GET requests
 * - Our backend expects POST /api/v1/chat/completions/stream with a JSON body
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";
import { useAppDispatch } from "../store/hooks";
import {
  addNode,
  clearNodes,
  setCurrentSessionId,
  type LangGraphNode as ReduxLangGraphNode,
} from "../store/slices/langGraphSlice";

/**
 * Token usage information from streaming response
 */
export interface StreamingUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

/**
 * Reasoning effort level for thinking models
 */
export type ReasoningEffortLevel = "low" | "medium" | "high";

/**
 * Knowledge Base focus mode for context retrieval
 */
export type KBFocusMode = "all" | "kb_only" | "web_only" | "none";

/**
 * Options for starting a stream
 */
export interface StartStreamOptions {
  /** Reasoning effort level for thinking models (low/medium/high) */
  reasoningEffort?: ReasoningEffortLevel;
  /** Knowledge Base focus mode for context retrieval */
  kbFocus?: KBFocusMode;
}

/**
 * LangGraph node for execution visualization
 */
export interface LangGraphNode {
  id: string;
  name: string;
  type: "start" | "end" | "tool" | "conditional" | "agent" | "default";
  status: "pending" | "running" | "completed" | "error" | "skipped";
  duration?: number;
  output?: string;
}

/**
 * LangGraph edge connecting nodes
 */
export interface LangGraphEdge {
  from: string;
  to: string;
  condition?: string;
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
  /** LLM thinking/reasoning content (from Claude thinking blocks, Gemini thinking_content, etc.) */
  thinkingContent: string;
  /** Number of tokens used for thinking/reasoning */
  thinkingTokens: number | null;
  /** LangGraph nodes for graph visualization */
  langgraphNodes: LangGraphNode[];
  /** LangGraph edges connecting nodes */
  langgraphEdges: LangGraphEdge[];
  /** Currently active node ID */
  currentNode: string | null;
}

/**
 * Return type for useStreamingChat hook
 */
export interface UseStreamingChatReturn extends StreamingChatState {
  startStream: (
    sessionId: string,
    message: string,
    options?: StartStreamOptions,
  ) => void;
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
 * const { isStreaming, streamingContent, thinkingContent, startStream, stopStream } = useStreamingChat();
 *
 * const handleSend = (message: string) => {
 *   startStream('session-123', message, { reasoningEffort: 'high' });
 * };
 *
 * return (
 *   <div>
 *     {thinkingContent && <ThinkingTrace content={thinkingContent} />}
 *     <p>{streamingContent}</p>
 *   </div>
 * );
 * ```
 */
export function useStreamingChat(): UseStreamingChatReturn {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [state, setState] = useState<StreamingChatState>({
    isStreaming: false,
    streamingContent: "",
    error: null,
    usage: null,
    model: null,
    traceId: null,
    thinkingContent: "",
    thinkingTokens: null,
    langgraphNodes: [],
    langgraphEdges: [],
    currentNode: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  // Store sessionId in ref so it's accessible inside processStream
  const sessionIdRef = useRef<string | null>(null);

  /**
   * Parse SSE data line and extract content
   */
  const parseSSELine = useCallback(
    (
      line: string,
    ): {
      content?: string;
      thinking?: string;
      thinkingTokens?: number;
      usage?: StreamingUsage;
      model?: string;
      traceId?: string;
      done?: boolean;
      langgraphNode?: LangGraphNode;
      langgraphEdge?: LangGraphEdge;
      currentNode?: string;
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
            thinking?: string;
            thinkingTokens?: number;
            usage?: StreamingUsage;
            model?: string;
            traceId?: string;
            langgraphNode?: LangGraphNode;
            langgraphEdge?: LangGraphEdge;
            currentNode?: string;
          } = {};

          // Handle content - support both direct content and delta.content formats
          if (data.content) {
            result.content = data.content;
          } else if (data.delta?.content) {
            result.content = data.delta.content;
          }

          // Handle thinking content - Claude style (thinking field)
          if (data.thinking) {
            result.thinking = data.thinking;
          }
          // Handle thinking content - Gemini style (thinking_content field)
          else if (data.thinking_content) {
            result.thinking = data.thinking_content;
          }
          // Handle thinking content - delta format
          else if (data.delta?.thinking) {
            result.thinking = data.delta.thinking;
          }

          // Handle thinking tokens
          if (data.thinking_tokens !== undefined) {
            result.thinkingTokens = data.thinking_tokens;
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

          // Handle LangGraph node updates
          if (data.langgraph_node) {
            result.langgraphNode = data.langgraph_node as LangGraphNode;
          }

          // Handle LangGraph edge updates
          if (data.langgraph_edge) {
            result.langgraphEdge = data.langgraph_edge as LangGraphEdge;
          }

          // Handle current node updates
          if (data.current_node) {
            result.currentNode = data.current_node;
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
    (sessionId: string, message: string, options?: StartStreamOptions) => {
      // Abort any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Store sessionId for use in processStream
      sessionIdRef.current = sessionId;

      // Dispatch Redux actions for LangGraph tracking
      dispatch(setCurrentSessionId(sessionId));
      dispatch(clearNodes(sessionId));

      // Reset state
      setState({
        isStreaming: true,
        streamingContent: "",
        error: null,
        usage: null,
        model: null,
        traceId: null,
        thinkingContent: "",
        thinkingTokens: null,
        langgraphNodes: [],
        langgraphEdges: [],
        currentNode: null,
      });

      // Build request body matching ChatCompletionRequest
      const requestBody: Record<string, unknown> = {
        session_id: sessionId,
        messages: [{ role: "user", content: message }],
      };

      // Add reasoning effort if provided
      if (options?.reasoningEffort) {
        requestBody.reasoning_effort = options.reasoningEffort;
      }

      // Add KB focus mode if provided
      if (options?.kbFocus) {
        requestBody.kb_focus = options.kbFocus;
      }

      // Start the fetch + stream processing
      const processStream = async () => {
        try {
          // Handle authentication failure by saving current route and redirecting to login
          const handleAuthFailure = () => {
            saveCurrentRouteAsIntended();
            navigate("/login", { replace: true });
          };

          // Use authenticatedFetch for automatic 401 handling with token refresh
          const response = await authenticatedFetch(
            "/api/v1/chat/completions/stream",
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(requestBody),
              signal: abortController.signal,
              onAuthFailure: handleAuthFailure,
            },
          );

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

              // Dispatch LangGraph node to Redux (outside setState)
              if (parsed.langgraphNode && sessionIdRef.current) {
                const reduxNode: ReduxLangGraphNode = {
                  ...parsed.langgraphNode,
                  sessionId: sessionIdRef.current,
                  startTime: Date.now(),
                };
                dispatch(addNode(reduxNode));
              }

              setState((prev) => {
                const updates: Partial<StreamingChatState> = {};

                if (parsed.content) {
                  updates.streamingContent =
                    prev.streamingContent + parsed.content;
                }

                if (parsed.thinking) {
                  updates.thinkingContent =
                    prev.thinkingContent + parsed.thinking;
                }

                if (parsed.thinkingTokens !== undefined) {
                  updates.thinkingTokens = parsed.thinkingTokens;
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

                // Handle LangGraph node updates
                if (parsed.langgraphNode) {
                  const existingNodeIndex = prev.langgraphNodes.findIndex(
                    (n) => n.id === parsed.langgraphNode!.id,
                  );
                  if (existingNodeIndex >= 0) {
                    // Update existing node
                    const updatedNodes = [...prev.langgraphNodes];
                    updatedNodes[existingNodeIndex] = parsed.langgraphNode;
                    updates.langgraphNodes = updatedNodes;
                  } else {
                    // Add new node
                    updates.langgraphNodes = [
                      ...prev.langgraphNodes,
                      parsed.langgraphNode,
                    ];
                  }
                }

                // Handle LangGraph edge updates
                if (parsed.langgraphEdge) {
                  const edgeExists = prev.langgraphEdges.some(
                    (e) =>
                      e.from === parsed.langgraphEdge!.from &&
                      e.to === parsed.langgraphEdge!.to,
                  );
                  if (!edgeExists) {
                    updates.langgraphEdges = [
                      ...prev.langgraphEdges,
                      parsed.langgraphEdge,
                    ];
                  }
                }

                // Handle current node updates
                if (parsed.currentNode !== undefined) {
                  updates.currentNode = parsed.currentNode;
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
    [parseSSELine, dispatch, navigate],
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
      thinkingContent: "",
      thinkingTokens: null,
      langgraphNodes: [],
      langgraphEdges: [],
      currentNode: null,
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
