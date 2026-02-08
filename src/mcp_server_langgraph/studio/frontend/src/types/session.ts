/**
 * Session Types
 *
 * Type definitions for chat session state including:
 * - Session metadata
 * - Messages
 * - Streaming state
 * - Store state and actions
 */

import type { SnakeToCamelCaseDeep } from "../api/transforms";

// ==============================================================================
// Model Configuration
// ==============================================================================

/** Supported LLM providers */
export type ModelProvider =
  | "openai"
  | "anthropic"
  | "google"
  | "azure"
  | "unknown";

/** Session configuration */
export interface SessionConfig {
  modelProvider: ModelProvider;
  modelName: string;
  temperature: number;
  maxTokens: number;
  systemPrompt?: string;
}

/**
 * Reasoning effort levels for extended thinking models.
 *
 * Maps to FF_MAX_THINKING_BUDGET on the backend:
 * - none: No extended thinking, standard response mode
 * - low: Quick responses, minimal reasoning (~1K thinking tokens)
 * - medium: Balanced reasoning (default, ~10K thinking tokens)
 * - high: Deep reasoning, comprehensive analysis (~100K thinking tokens)
 * - ultra: Maximum reasoning depth, exhaustive analysis (model-dependent max)
 *
 * Support varies by vendor:
 * - OpenAI o1/o3: low, medium, high (native reasoning_effort)
 * - Anthropic Claude: all levels (extended_thinking budget)
 * - Google Gemini: all levels (thinking_budget)
 */
export type ReasoningEffortLevel = "none" | "low" | "medium" | "high" | "ultra";

/**
 * Server configuration response from /api/v1/config/defaults
 * Used for frontend hydration of backend-configured defaults.
 *
 * 12-Factor App Pattern: Configuration is read from environment variables
 * by the backend and exposed via this endpoint. The frontend uses these
 * values to initialize UI state, ensuring consistency across deployments
 * (AWS/EKS, GCP/GKE, Azure/AKS, OpenShift, Rancher, etc.).
 */
export interface ServerConfig {
  model_name: string;
  model_provider: ModelProvider | "unknown";
  max_tokens: number;
  temperature: number;
  /**
   * Default reasoning effort level for extended thinking models.
   * Corresponds to FF_MAX_THINKING_BUDGET environment variable.
   * Optional for backward compatibility with older backend versions.
   */
  default_reasoning_effort?: ReasoningEffortLevel;
  /**
   * Override for executor model in critique loop.
   * When null, auto-selected based on task complexity.
   * Only relevant when critique_loop_enabled is true.
   */
  executor_model_name?: string | null;
  /**
   * Override for critic model in critique loop.
   * When null, auto-selected based on task complexity/risk.
   * Only relevant when critique_loop_enabled is true.
   */
  critic_model_name?: string | null;
  /**
   * Whether the critique loop feature is enabled (FF_ENABLE_CRITIQUE_LOOP).
   * When true, responses are refined through executor+critic iterations.
   */
  critique_loop_enabled?: boolean;
}

/**
 * ServerConfig with camelCase keys for frontend use.
 * Used after transformSnakeToCamel transformation.
 */
export type ServerConfigCamelCase = SnakeToCamelCaseDeep<ServerConfig>;

/**
 * Default session configuration - FALLBACK ONLY
 *
 * NOTE: This is a fallback for when the server config endpoint is unavailable.
 * The frontend should prefer using the ServerConfig from /api/v1/config/defaults
 * to ensure the UI reflects the backend-configured model.
 *
 * Matches backend settings.model_name default (gemini-2.5-flash).
 * In test/CI environment: MODEL_NAME=vertex_ai/gemini-3-flash-preview
 *
 * @deprecated Prefer using useGetServerConfigQuery() and apply server defaults
 */
export const DEFAULT_SESSION_CONFIG: SessionConfig = {
  modelProvider: "google",
  modelName: "gemini-2.5-flash", // Matches backend settings.model_name default
  temperature: 0.7,
  maxTokens: 8192,
};

// ==============================================================================
// Message Types
// ==============================================================================

/** Message role */
export type MessageRole = "user" | "assistant" | "system";

/** Tool call within a message */
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  duration?: number;
}

/** Token usage stats (client-side camelCase format) */
export interface ClientTokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

/**
 * Token breakdown for StatusBar display.
 * Alias for ClientTokenUsage - same structure, different semantic context.
 */
export type TokenBreakdown = ClientTokenUsage;

/**
 * Cost breakdown information for StatusBar display.
 * Shows estimated cost and optional per-model breakdown.
 */
export interface CostBreakdown {
  /** Estimated cost in USD */
  estimatedCostUsd: number;
  /** Cost by model (for multi-model sessions) */
  byModel?: Record<string, { tokens: number; cost: number }>;
}

/** Agent transparency metadata */
/** Agent execution step metadata */
export interface AgentStep {
  name: string;
  status: string;
  duration?: number;
}

// Re-export AgentExecutionTrace from types/chat for backwards compatibility
export type { AgentExecutionTrace } from "./chat";

export interface AgentMetadata {
  confidence?: number;
  reasoning?: string;
  responseFormat?: "concise" | "detailed";
  verificationScore?: number;
  refinementAttempts?: number;
  /** Agent execution steps for trace display */
  steps?: AgentStep[];
  /** Full execution trace with OTEL correlation (per-message traces) */
  executionTrace?: import("./chat").AgentExecutionTrace;
}

/** Source citation from web search results */
export interface SourceCitation {
  title: string;
  url: string;
  snippet?: string | null;
  /** Relevance score for ranking (0.0 to 1.0) */
  relevance_score?: number | null;
}

/** Message delivery status for optimistic updates */
export type MessageStatus = "pending" | "sent" | "failed";

/** Chat message */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  usage?: ClientTokenUsage;
  agentMetadata?: AgentMetadata;
  /** LLM thinking/reasoning content (from Claude extended thinking, Gemini thinking_content, etc.) */
  thinkingContent?: string;
  /** Number of tokens used for thinking/reasoning */
  thinkingTokens?: number;
  /** Model name that generated this message */
  modelName?: string;
  /** Source citations from web search results */
  sources?: SourceCitation[];
  /** Whether this message has been reported as hallucination */
  isReported?: boolean;
  /** Delivery status for optimistic updates (Finding 3: stream failure fallback) */
  status?: MessageStatus;
}

// ==============================================================================
// Session Types
// ==============================================================================

/** Session summary for list views */
export interface SessionSummary {
  id: string;
  name: string;
  /** Longer context or notes for the session */
  description?: string;
  createdAt: number;
  updatedAt: number;
  messageCount: number;
  organizationId?: string;
}

/** Full session details (client-side format) */
export interface ClientSession {
  id: string;
  name: string;
  /** Longer context or notes for the session */
  description?: string;
  config: SessionConfig;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
  organizationId?: string;
}

// ==============================================================================
// Streaming
// ==============================================================================

/** Stream chunk type */
export type StreamChunkType =
  | "chunk"
  | "complete"
  | "error"
  | "tool_call"
  | "tool_result";

/** Stream chunk from API */
export interface StreamChunk {
  type: StreamChunkType;
  content?: string;
  messageId?: string;
  usage?: ClientTokenUsage;
  toolCall?: ToolCall;
  error?: string;
}

// ==============================================================================
// Store State
// ==============================================================================

/** Session store state */
export interface SessionState {
  /** List of session summaries */
  sessions: SessionSummary[];

  /** Currently active session */
  currentSession: ClientSession | null;

  /** Whether session list is loading */
  isLoadingSessions: boolean;

  /** Whether current session is loading */
  isLoadingSession: boolean;

  /** Whether a message is being sent/streamed */
  isSending: boolean;

  /** Error message if any */
  error: string | null;

  /** Whether more sessions are available for pagination */
  hasMore?: boolean;

  /** Total count of sessions (for pagination display) */
  totalCount?: number;

  /** Whether loading more sessions */
  isLoadingMore?: boolean;

  /** Current pagination cursor */
  cursor?: string | null;

  /** Whether there are pending mutations (prevents stale loader data from overwriting optimistic updates) */
  hasPendingMutation?: boolean;

  // ==========================================================================
  // Navigation Tracking (Phase 4.2: AI Predictions Support)
  // ==========================================================================

  /** Recent pages visited (last 5, most recent first) */
  recentPages: string[];

  /** Current page path */
  currentPage: string;

  /** Current navigation context for AI predictions */
  navigationContext: NavigationContext;
}

/** Navigation context for AI predictions */
export interface NavigationContext {
  /** Current page path */
  page: string;
  /** Active feature on the page */
  feature?: string;
  /** Current action being performed */
  action?: string;
}

/** Session store actions */
export interface SessionActions {
  /** Fetch list of sessions */
  fetchSessions: () => Promise<void>;

  /** Create a new session */
  createSession: (
    name: string,
    config?: Partial<SessionConfig>,
  ) => Promise<string | null>;

  /** Load a session by ID */
  loadSession: (sessionId: string) => Promise<void>;

  /** Delete a session */
  deleteSession: (sessionId: string) => Promise<void>;

  /** Rename a session */
  renameSession: (sessionId: string, name: string) => Promise<void>;

  /** Send a message in the current session */
  sendMessage: (content: string) => Promise<void>;

  /** Add a message to the current session (for streaming) */
  addMessage: (message: ChatMessage) => void;

  /** Update a message in the current session */
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;

  /** Clear messages in the current session */
  clearMessages: () => Promise<void>;

  /** Close current session */
  closeSession: () => void;

  /** Clear error */
  clearError: () => void;
}

/** Combined session store type */
export type SessionStore = SessionState & SessionActions;
