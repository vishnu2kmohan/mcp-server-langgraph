/**
 * TypeScript interfaces for Playground API
 *
 * These types mirror the backend API models and are used
 * throughout the frontend for type-safe data handling.
 */

// =============================================================================
// Session Types
// =============================================================================

export interface SessionConfig {
  modelProvider: 'openai' | 'anthropic' | 'google' | 'azure';
  modelName: string;
  temperature: number;
  maxTokens: number;
  systemPrompt?: string;
}

export interface CreateSessionRequest {
  name: string;
  config?: Partial<SessionConfig>;
}

export interface SessionSummary {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
}

export interface SessionMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface SessionDetails {
  id: string;
  name: string;
  config: SessionConfig;
  messages: SessionMessage[];
  createdAt: string;
  updatedAt: string;
}

// =============================================================================
// Chat Types
// =============================================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  usage?: TokenUsage;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
  duration?: number;
}

export interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

export interface StreamChunk {
  type: 'chunk' | 'complete' | 'error' | 'tool_call' | 'tool_result';
  content?: string;
  messageId?: string;
  usage?: TokenUsage;
  toolCall?: ToolCall;
  error?: string;
}

// =============================================================================
// Observability Types
// =============================================================================

export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  logger?: string;
  attributes?: Record<string, unknown>;
}

export interface SpanInfo {
  spanId: string;
  parentSpanId?: string;
  operationName: string;
  serviceName: string;
  startTime: string;
  endTime?: string;
  durationMs?: number;
  status: 'OK' | 'ERROR' | 'UNSET';
  attributes?: Record<string, unknown>;
  events?: SpanEvent[];
}

export interface SpanEvent {
  name: string;
  timestamp: string;
  attributes?: Record<string, unknown>;
}

export interface TraceInfo {
  traceId: string;
  spans: SpanInfo[];
  startTime: string;
  endTime?: string;
  totalDurationMs?: number;
}

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low';

export interface Alert {
  id: string;
  severity: AlertSeverity;
  title: string;
  description: string;
  source: string;
  timestamp: string;
  acknowledged: boolean;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// Metrics Types
// =============================================================================

export interface LLMMetrics {
  totalCalls: number;
  totalTokens: number;
  promptTokens: number;
  completionTokens: number;
  averageLatencyMs: number;
  p50LatencyMs: number;
  p99LatencyMs: number;
  errorRate: number;
}

export interface ToolMetrics {
  totalCalls: number;
  successRate: number;
  averageLatencyMs: number;
  errorCount: number;
  byTool: Record<
    string,
    {
      calls: number;
      successRate: number;
      averageLatencyMs: number;
    }
  >;
}

export interface MetricsSummary {
  llm: LLMMetrics;
  tools: ToolMetrics;
  sessionDurationMs: number;
  messageCount: number;
}

// =============================================================================
// Error Types
// =============================================================================

export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class PlaygroundAPIError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'PlaygroundAPIError';
  }
}

// =============================================================================
// Connection Types
// =============================================================================

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

export interface ConnectionState {
  status: ConnectionStatus;
  error?: string;
  lastConnected?: string;
  reconnectAttempts?: number;
}

// =============================================================================
// Authentication Types
// =============================================================================

export interface AuthUser {
  id: string;
  username: string;
  email?: string;
  roles: string[];
}

export interface AuthTokens {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  user: AuthUser;
  tokens: AuthTokens;
}

export interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
