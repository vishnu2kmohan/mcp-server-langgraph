/**
 * Chat Message Type Definitions
 *
 * Consolidated types for chat messages, LangGraph visualization, and agent execution.
 * Extracted from ChatMessages.tsx for reusability across:
 * - ChatMessages component
 * - ChatPage
 * - Message-related hooks
 * - LangGraph visualization components
 *
 * Type naming convention follows types/hitl.ts pattern.
 */

// =============================================================================
// Source Citations
// =============================================================================

/**
 * Source citation for AI-generated responses
 */
export interface Source {
  title: string;
  url: string;
}

// =============================================================================
// Message Types
// =============================================================================

/**
 * Chat message with role-based content and optional AI metadata
 */
export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  sources?: Source[];
  /** AI confidence score (0-1) for assistant messages */
  confidence?: number;
  /** Whether this message has been flagged for hallucination */
  isReported?: boolean;
  /** LLM thinking/reasoning content (from Claude extended thinking, Gemini thinking_content, etc.) */
  thinkingContent?: string;
  /** Number of tokens used for thinking/reasoning */
  thinkingTokens?: number;
  /** Model name that generated this message */
  modelName?: string;
}

// =============================================================================
// LangGraph Visualization Types
// =============================================================================

/**
 * LangGraph node types for visualization
 */
export type LangGraphNodeType =
  | "start"
  | "end"
  | "tool"
  | "conditional"
  | "agent"
  | "default";

/**
 * LangGraph node status
 */
export type LangGraphNodeStatus =
  | "pending"
  | "running"
  | "completed"
  | "error"
  | "skipped";

/**
 * LangGraph node for execution visualization
 */
export interface LangGraphNode {
  id: string;
  name: string;
  type: LangGraphNodeType;
  status: LangGraphNodeStatus;
  /** Duration in milliseconds */
  duration?: number;
  /** Tool/function output if applicable */
  output?: string;
  /** Start timestamp in milliseconds (for time-travel debugging) */
  startTime?: number;
  /** End timestamp in milliseconds (for time-travel debugging) */
  endTime?: number;
}

/**
 * LangGraph edge connecting nodes
 */
export interface LangGraphEdge {
  from: string;
  to: string;
  /** Condition label for conditional edges */
  condition?: string;
}

// =============================================================================
// Agent Execution Trace
// =============================================================================

/**
 * Agent execution trace (distinct from LLM thinking content)
 * Tracks agent steps, token usage, and raw output for observability.
 * Supports LangGraph node/edge visualization.
 */
export interface AgentExecutionTrace {
  rawOutput?: string;
  steps?: Array<{ name: string; status: string; duration?: number }>;
  tokens?: { input: number; output: number };
  /** LangGraph nodes for graph visualization */
  nodes?: LangGraphNode[];
  /** LangGraph edges connecting nodes */
  edges?: LangGraphEdge[];
  /** Currently active node ID */
  currentNode?: string;
  /** Trace start timestamp in milliseconds (for time-travel debugging) */
  startTime?: number;
  /** Trace end timestamp in milliseconds (for time-travel debugging) */
  endTime?: number;
}

/**
 * @deprecated Use AgentExecutionTrace instead. Renamed for clarity.
 */
export type AgentTrace = AgentExecutionTrace;

/**
 * @deprecated Use AgentExecutionTrace instead. Renamed to clarify distinction from LLM thinking.
 */
export type ThinkingTrace = AgentExecutionTrace;
