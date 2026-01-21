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
import { setPlan, type ExecutionPlan } from "../store/slices/executionModeSlice";

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
 *
 * Maps to FF_MAX_THINKING_BUDGET on the backend:
 * - none: No extended thinking, standard response mode
 * - low: Quick responses, minimal reasoning (~1K thinking tokens)
 * - medium: Balanced reasoning (default, ~10K thinking tokens)
 * - high: Deep reasoning, comprehensive analysis (~100K thinking tokens)
 * - ultra: Maximum reasoning depth, exhaustive analysis (model-dependent max)
 */
export type ReasoningEffortLevel = "none" | "low" | "medium" | "high" | "ultra";

/**
 * Auth required event from SSE stream (ADR-0102)
 * Emitted when a tool call requires authentication
 */
export interface AuthRequiredEvent {
  connectionId: string | null;
  templateId: string | null;
  toolName: string;
  message: string;
  retryMessageId: string | null;
}

/**
 * Plan generated event from SSE stream
 * Emitted when an execution plan is generated and requires approval
 */
export interface PlanGeneratedEvent {
  planId: string;
  status: "awaiting_approval" | "approved" | "rejected";
  complexity: "simple" | "complicated" | "complex";
  riskLevel: "low" | "medium" | "high";
  taskType: string;
  executorModel: string;
  estimatedCost: string;
  toolsNeeded: string[];
  thinkingBudget: string;
  critiqueRounds: number;
  requiresApproval: boolean;
}

/**
 * Source citation from web search results
 * Displayed in chat UI as clickable source links
 */
export interface SourceCitation {
  title: string;
  url: string;
  snippet?: string | null;
}

/**
 * Knowledge Base focus mode for context retrieval
 */
export type KBFocusMode = "all" | "kb_only" | "web_only" | "none";

/**
 * Tool selection mode for chat requests
 */
export type ToolSelectionMode = "auto" | "manual" | "none";

/**
 * Tool preference for native vs builtin execution (v7)
 */
export type ToolPreference = "auto" | "native" | "builtin" | "mcp";

/**
 * Options for starting a stream
 */
/**
 * Execution mode for plan-and-execute workflow
 */
export type ExecutionModeType = "default" | "plan" | "auto_accept" | "bypass";

export interface StartStreamOptions {
  /** Model ID to use for this request (overrides server default) */
  model?: string;
  /** Reasoning effort level for thinking models (low/medium/high) */
  reasoningEffort?: ReasoningEffortLevel;
  /** Whether to enable extended thinking for supported models */
  enableThinking?: boolean;
  /** Knowledge Base focus mode for context retrieval */
  kbFocus?: KBFocusMode;
  /** Tool selection mode: auto (semantic), manual (explicit), none (disabled) */
  toolSelectionMode?: ToolSelectionMode;
  /** Explicitly selected tool names (used when toolSelectionMode is "manual") */
  selectedTools?: string[];
  /** Execution mode for plan approval workflow (Ctrl/Cmd+Shift+M toggle) */
  executionMode?: ExecutionModeType;
  /** Tool preference for native vs builtin execution (v7) */
  toolPreference?: ToolPreference;
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
  /** Semantically selected tools for this request (ADR-0099) */
  selectedTools: string[];
  /** Semantic similarity scores for each selected tool */
  selectionScores: Record<string, number>;
  /** Total number of tools available for selection */
  totalAvailableTools: number | null;
  /** Auth required event from stream (ADR-0102) */
  authRequired: AuthRequiredEvent | null;
  /** Source citations from web search results */
  sources: SourceCitation[];
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
    selectedTools: [],
    selectionScores: {},
    totalAvailableTools: null,
    authRequired: null,
    sources: [],
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
      selectedTools?: string[];
      selectionScores?: Record<string, number>;
      totalAvailableTools?: number;
      authRequired?: AuthRequiredEvent;
      planGenerated?: PlanGeneratedEvent;
      sources?: SourceCitation[];
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
            selectedTools?: string[];
            selectionScores?: Record<string, number>;
            totalAvailableTools?: number;
            authRequired?: AuthRequiredEvent;
            planGenerated?: PlanGeneratedEvent;
            sources?: SourceCitation[];
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

          // Handle semantic tool selection events (ADR-0099)
          if (data.selected_tools !== undefined) {
            result.selectedTools = data.selected_tools;
          }
          if (data.selection_scores !== undefined) {
            result.selectionScores = data.selection_scores;
          }
          if (data.total_available !== undefined) {
            result.totalAvailableTools = data.total_available;
          }

          // Handle auth_required events (ADR-0102)
          if (data.type === "auth_required") {
            result.authRequired = {
              connectionId: data.connection_id ?? null,
              templateId: data.template_id ?? null,
              toolName: data.tool_name,
              message: data.message,
              retryMessageId: data.retry_message_id ?? null,
            };
          }

          // Handle plan_generated events (Execution Mode feature)
          if (data.plan_generated) {
            result.planGenerated = {
              planId: data.plan_generated.plan_id,
              status: data.plan_generated.status,
              complexity: data.plan_generated.complexity,
              riskLevel: data.plan_generated.risk_level,
              taskType: data.plan_generated.task_type,
              executorModel: data.plan_generated.executor_model,
              estimatedCost: data.plan_generated.estimated_cost,
              toolsNeeded: data.plan_generated.tools_needed ?? [],
              thinkingBudget: data.plan_generated.thinking_budget,
              critiqueRounds: data.plan_generated.critique_rounds,
              requiresApproval: data.plan_generated.requires_approval,
            };
          }

          // Handle source citations from web search results
          if (data.sources && Array.isArray(data.sources)) {
            result.sources = data.sources.map(
              (s: { title: string; url: string; snippet?: string | null }) => ({
                title: s.title,
                url: s.url,
                snippet: s.snippet ?? null,
              }),
            );
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
        selectedTools: [],
        selectionScores: {},
        totalAvailableTools: null,
        authRequired: null,
        sources: [],
      });

      // Build request body matching ChatCompletionRequest
      const requestBody: Record<string, unknown> = {
        session_id: sessionId,
        messages: [{ role: "user", content: message }],
      };

      // Add model if provided (overrides server default)
      if (options?.model) {
        requestBody.model = options.model;
      }

      // Add reasoning effort if provided
      if (options?.reasoningEffort) {
        requestBody.reasoning_effort = options.reasoningEffort;
      }

      // Add enable_thinking if explicitly set (default is true on server)
      if (options?.enableThinking !== undefined) {
        requestBody.enable_thinking = options.enableThinking;
      }

      // Add KB focus mode if provided
      if (options?.kbFocus) {
        requestBody.kb_focus = options.kbFocus;
      }

      // Add tool selection mode if provided (defaults to "auto" on server)
      if (options?.toolSelectionMode) {
        requestBody.tool_selection_mode = options.toolSelectionMode;
      }

      // Add selected tools for manual mode
      if (
        options?.toolSelectionMode === "manual" &&
        options?.selectedTools &&
        options.selectedTools.length > 0
      ) {
        requestBody.selected_tools = options.selectedTools;
      }

      // Add execution mode for plan approval workflow (Ctrl/Cmd+Shift+M toggle)
      if (options?.executionMode) {
        requestBody.execution_mode = options.executionMode;
      }

      // v7: Add tool preference for native vs builtin execution
      if (options?.toolPreference) {
        requestBody.tool_preference = options.toolPreference;
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

              // Dispatch plan_generated to Redux (Issue 7: Wire up plan rendering)
              if (parsed.planGenerated && sessionIdRef.current) {
                const plan: ExecutionPlan = {
                  planId: parsed.planGenerated.planId,
                  sessionId: sessionIdRef.current,
                  status: parsed.planGenerated.status,
                  complexity: parsed.planGenerated.complexity,
                  riskLevel: parsed.planGenerated.riskLevel,
                  taskType: parsed.planGenerated.taskType,
                  executorModel: parsed.planGenerated.executorModel,
                  criticModel: "", // Optional field, not always in SSE
                  estimatedCost: parsed.planGenerated.estimatedCost,
                  message: "", // Optional field, not always in SSE
                  toolsNeeded: parsed.planGenerated.toolsNeeded,
                  thinkingBudget: parsed.planGenerated.thinkingBudget,
                  critiqueRounds: parsed.planGenerated.critiqueRounds,
                  orchestrator: "", // Optional field, not always in SSE
                  requiresApproval: parsed.planGenerated.requiresApproval,
                };
                dispatch(setPlan(plan));
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

                // Handle semantic tool selection updates (ADR-0099)
                if (parsed.selectedTools !== undefined) {
                  updates.selectedTools = parsed.selectedTools;
                }
                if (parsed.selectionScores !== undefined) {
                  updates.selectionScores = parsed.selectionScores;
                }
                if (parsed.totalAvailableTools !== undefined) {
                  updates.totalAvailableTools = parsed.totalAvailableTools;
                }

                // Handle auth_required events (ADR-0102)
                if (parsed.authRequired !== undefined) {
                  updates.authRequired = parsed.authRequired;
                }

                // Handle source citations from web search results
                if (parsed.sources !== undefined && parsed.sources.length > 0) {
                  // Append new sources (deduplicate by URL)
                  const existingUrls = new Set(prev.sources.map((s) => s.url));
                  const newSources = parsed.sources.filter(
                    (s) => !existingUrls.has(s.url),
                  );
                  if (newSources.length > 0) {
                    updates.sources = [...prev.sources, ...newSources];
                  }
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
      selectedTools: [],
      selectionScores: {},
      totalAvailableTools: null,
      authRequired: null,
      sources: [],
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
