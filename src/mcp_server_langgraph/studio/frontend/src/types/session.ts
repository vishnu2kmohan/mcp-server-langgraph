/**
 * Session Types
 *
 * Type definitions for chat session state including:
 * - Session metadata
 * - Messages
 * - Streaming state
 * - Store state and actions
 */

// ==============================================================================
// Model Configuration
// ==============================================================================

/** Supported LLM providers */
export type ModelProvider = 'openai' | 'anthropic' | 'google' | 'azure';

/** Session configuration */
export interface SessionConfig {
  modelProvider: ModelProvider;
  modelName: string;
  temperature: number;
  maxTokens: number;
  systemPrompt?: string;
}

/** Default session configuration */
export const DEFAULT_SESSION_CONFIG: SessionConfig = {
  modelProvider: 'openai',
  modelName: 'gpt-4',
  temperature: 0.7,
  maxTokens: 4096,
};

// ==============================================================================
// Message Types
// ==============================================================================

/** Message role */
export type MessageRole = 'user' | 'assistant' | 'system';

/** Tool call within a message */
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  duration?: number;
}

/** Token usage stats */
export interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

/** Agent transparency metadata */
export interface AgentMetadata {
  confidence?: number;
  reasoning?: string;
  responseFormat?: 'concise' | 'detailed';
  verificationScore?: number;
  refinementAttempts?: number;
}

/** Chat message */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  usage?: TokenUsage;
  agentMetadata?: AgentMetadata;
}

// ==============================================================================
// Session Types
// ==============================================================================

/** Session summary for list views */
export interface SessionSummary {
  id: string;
  name: string;
  createdAt: number;
  updatedAt: number;
  messageCount: number;
  organizationId?: string;
}

/** Full session details */
export interface Session {
  id: string;
  name: string;
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
export type StreamChunkType = 'chunk' | 'complete' | 'error' | 'tool_call' | 'tool_result';

/** Stream chunk from API */
export interface StreamChunk {
  type: StreamChunkType;
  content?: string;
  messageId?: string;
  usage?: TokenUsage;
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
  currentSession: Session | null;

  /** Whether session list is loading */
  isLoadingSessions: boolean;

  /** Whether current session is loading */
  isLoadingSession: boolean;

  /** Whether a message is being sent/streamed */
  isSending: boolean;

  /** Error message if any */
  error: string | null;
}

/** Session store actions */
export interface SessionActions {
  /** Fetch list of sessions */
  fetchSessions: () => Promise<void>;

  /** Create a new session */
  createSession: (name: string, config?: Partial<SessionConfig>) => Promise<string | null>;

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
