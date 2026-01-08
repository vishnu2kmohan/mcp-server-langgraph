/**
 * WebSocket Protocol Types
 *
 * Type-safe protocol definitions for all WebSocket endpoints.
 * Based on the protocol contracts defined in docs-internal/websocket-protocol-contracts.md
 *
 * Features:
 * - Discriminated unions for type-safe message handling
 * - Type guards for runtime validation
 * - Full TypeScript type inference
 *
 * @see docs-internal/websocket-protocol-contracts.md
 */

// =============================================================================
// Protocol Version
// =============================================================================

/**
 * WebSocket protocol version.
 * Used for client-server compatibility checking.
 * Must match the version in Python: mcp_server_langgraph.websocket.protocols.PROTOCOL_VERSION
 */
export const PROTOCOL_VERSION = "1.0.0";

// =============================================================================
// Message Envelope (Base Type)
// =============================================================================

/**
 * Generic message envelope for all WebSocket messages.
 * All WebSocket messages follow this structure.
 *
 * @template T - The message type string literal
 * @template P - The payload type
 */
export interface MessageEnvelope<T extends string, P = unknown> {
  /** Message type identifier */
  type: T;
  /** Optional message ID for correlation */
  id?: string;
  /** Message-specific data */
  payload?: P;
}

// =============================================================================
// DevTools Protocol (/api/v1/ws/devtools)
// =============================================================================

/** Console log levels */
export type ConsoleLogLevel = "info" | "warning" | "error" | "debug";

/** Console log sources */
export type ConsoleLogSource =
  | "system"
  | "api"
  | "mcp"
  | "notification"
  | "execution"
  | "websocket";

/** Console log entry payload */
export interface ConsoleLogPayload {
  id?: string;
  level: ConsoleLogLevel;
  source: ConsoleLogSource;
  message: string;
  timestamp: number;
  data?: Record<string, unknown>;
  stackTrace?: string;
}

/** Console log entry message (Server → Client) */
export interface ConsoleLogEntry {
  type: "console";
  payload: ConsoleLogPayload;
}

/** HTTP methods */
export type HttpMethod =
  | "GET"
  | "POST"
  | "PUT"
  | "DELETE"
  | "PATCH"
  | "OPTIONS";

/** Network request statuses */
export type NetworkRequestStatus =
  | "pending"
  | "completed"
  | "error"
  | "cancelled";

/** Network request entry payload */
export interface NetworkRequestPayload {
  id?: string;
  method: HttpMethod;
  url: string;
  status: NetworkRequestStatus;
  statusCode?: number;
  startTime: number;
  endTime?: number;
  duration?: number;
  requestSize?: number;
  responseSize?: number;
  source?: string;
}

/** Network request entry message (Server → Client) */
export interface NetworkRequestEntry {
  type: "network";
  payload: NetworkRequestPayload;
}

/** Network update entry payload (for updating existing entries) */
export interface NetworkUpdatePayload {
  id: string;
  status: "completed" | "error";
  statusCode?: number;
  duration?: number;
  responseSize?: number;
  endTime?: number;
}

/** Network update entry message (Server → Client) */
export interface NetworkUpdateEntry {
  type: "network_update";
  payload: NetworkUpdatePayload;
}

/** Agent trace step payload (DevTools-specific) */
export interface TraceStepPayload {
  id?: string;
  session_id: string;
  node_id?: string;
  name: string;
  status: string;
  start_time: number;
  end_time?: number;
  duration_ms?: number;
  attributes?: Record<string, unknown>;
}

/** Agent trace step message (Server → Client, DevTools WebSocket) */
export interface TraceStepEntry {
  type: "trace_step";
  payload: TraceStepPayload;
}

/** Union of all DevTools messages */
export type DevToolsMessage =
  | ConsoleLogEntry
  | NetworkRequestEntry
  | NetworkUpdateEntry
  | TraceStepEntry;

// =============================================================================
// Traces Protocol (/api/v1/ws/traces)
// =============================================================================

/** Trace span status */
export type TraceSpanStatus = "ok" | "error" | "unset";

/** Trace span entry payload */
export interface TraceSpanPayload {
  span_id: string;
  trace_id: string;
  parent_span_id: string | null;
  name: string;
  start_time: number;
  end_time: number;
  duration_ms: number;
  status: TraceSpanStatus;
  service_name: string;
  attributes: Record<string, unknown>;
}

/** Trace span entry message (Server → Client) */
export interface TraceSpanEntry {
  type: "trace_span";
  payload: TraceSpanPayload;
}

/** Trace event entry payload */
export interface TraceEventPayload {
  span_id: string;
  name: string;
  timestamp: string;
  attributes: Record<string, unknown>;
}

/** Trace event entry message (Server → Client) */
export interface TraceEventEntry {
  type: "trace_event";
  payload: TraceEventPayload;
}

/** Trace subscribe payload (Client → Server) */
export interface TraceSubscribePayload {
  service_filter?: string;
  trace_id?: string;
}

/** Trace subscribe message (Client → Server) */
export interface TraceSubscribeMessage {
  type: "subscribe";
  id?: string;
  payload?: TraceSubscribePayload;
}

/** Union of all Traces messages */
export type TracesMessage =
  | TraceSpanEntry
  | TraceEventEntry
  | TraceSubscribeMessage;

// =============================================================================
// Budget Alerts Protocol (/api/v1/ws/budget/alerts)
// =============================================================================

/** Budget entity types */
export type BudgetEntityType = "organization" | "project" | "team" | "user";

/** Budget alert status */
export type BudgetAlertStatus = "ok" | "warning" | "critical" | "exceeded";

/** Budget alert entry payload */
export interface BudgetAlertPayload {
  entity_type: BudgetEntityType;
  entity_id: string;
  status: BudgetAlertStatus;
  percent_used: number;
  current_spend: string;
  remaining: string;
  monthly_limit_usd: string;
  message: string;
}

/** Budget alert entry message (Server → Client) */
export interface BudgetAlertEntry {
  type: "budget_alert";
  payload: BudgetAlertPayload;
}

/** Budget subscribed confirmation payload */
export interface BudgetSubscribedPayload {
  entity_ids: string[];
  subscribe_all: boolean;
}

/** Budget subscribed response (Server → Client) */
export interface BudgetSubscribedResponse {
  type: "subscribed";
  payload: BudgetSubscribedPayload;
}

/** Budget unsubscribed response (Server → Client) */
export interface BudgetUnsubscribedResponse {
  type: "unsubscribed";
  payload: Record<string, never>;
}

/** Subscribe to entities payload (Client → Server) */
export interface BudgetSubscribeEntitiesPayload {
  entity_ids: string[];
}

/** Subscribe to entities message (Client → Server) */
export interface BudgetSubscribeEntitiesMessage {
  type: "subscribe_entities";
  id?: string;
  payload: BudgetSubscribeEntitiesPayload;
}

/** Subscribe to all alerts message (Client → Server) */
export interface BudgetSubscribeAllMessage {
  type: "subscribe_all";
  id?: string;
  payload: Record<string, never>;
}

/** Unsubscribe message (Client → Server) */
export interface BudgetUnsubscribeMessage {
  type: "unsubscribe";
  id?: string;
  payload: Record<string, never>;
}

/** Union of all Budget Alerts messages */
export type BudgetAlertsMessage =
  | BudgetAlertEntry
  | BudgetSubscribedResponse
  | BudgetUnsubscribedResponse
  | WebSocketError;

// =============================================================================
// AI Suggestions Protocol (/api/v1/ws/ai/suggestions)
// =============================================================================

/** Suggestion response payload */
export interface SuggestionResponsePayload {
  suggestion_id: string;
  text: string;
  confidence: number;
  reasoning?: string;
}

/** Suggestion response message (Server → Client) */
export interface SuggestionResponseEntry {
  type: "suggestion_response";
  payload: SuggestionResponsePayload;
}

/** Suggestion request payload (Client → Server) */
export interface SuggestionRequestPayload {
  session_id: string;
  input_text: string;
  cursor_position: number;
  context_window: number;
}

/** Suggestion request message (Client → Server) */
export interface SuggestionRequestMessage {
  type: "suggestion_request";
  id?: string;
  payload: SuggestionRequestPayload;
}

/** Suggestion accept payload (Client → Server) */
export interface SuggestionAcceptPayload {
  suggestion_id: string;
}

/** Suggestion accept message (Client → Server) */
export interface SuggestionAcceptMessage {
  type: "suggestion_accept";
  id?: string;
  payload: SuggestionAcceptPayload;
}

/** Suggestion reject payload (Client → Server) */
export interface SuggestionRejectPayload {
  suggestion_id: string;
  reason?: string;
}

/** Suggestion reject message (Client → Server) */
export interface SuggestionRejectMessage {
  type: "suggestion_reject";
  id?: string;
  payload: SuggestionRejectPayload;
}

/** Context update payload (Client → Server) */
export interface ContextUpdatePayload {
  session_id: string;
  context: string;
}

/** Context update message (Client → Server) */
export interface ContextUpdateMessage {
  type: "context_update";
  id?: string;
  payload: ContextUpdatePayload;
}

/** Union of all AI Suggestions messages */
export type AISuggestionsMessage =
  | SuggestionResponseEntry
  | SuggestionRequestMessage
  | SuggestionAcceptMessage
  | SuggestionRejectMessage
  | ContextUpdateMessage
  | WebSocketError;

// =============================================================================
// MCP Aggregated Protocol (/api/v1/ws/mcp/aggregated)
// =============================================================================

/** MCP server connection status */
export type MCPServerConnectionStatus = "connected" | "disconnected" | "error";

/** MCP server status payload */
export interface MCPServerStatusPayload {
  server_id: string;
  status: MCPServerConnectionStatus;
  name: string;
  timestamp: number;
}

/** MCP server status message (Server → Client) */
export interface MCPServerStatusEntry {
  type: "server_status";
  payload: MCPServerStatusPayload;
}

/** MCP tool call status */
export type MCPToolCallStatus = "started" | "completed" | "error";

/** MCP tool call payload */
export interface MCPToolCallPayload {
  server_id: string;
  tool_name: string;
  call_id: string;
  status: MCPToolCallStatus;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  duration_ms: number;
  timestamp: number;
}

/** MCP tool call message (Server → Client) */
export interface MCPToolCallEntry {
  type: "tool_call";
  payload: MCPToolCallPayload;
}

/** Union of all MCP Aggregated messages */
export type MCPAggregatedMessage = MCPServerStatusEntry | MCPToolCallEntry;

// =============================================================================
// Error Protocol (Common to all endpoints)
// =============================================================================

/** WebSocket error codes */
export type WebSocketErrorCode =
  | "token_expired"
  | "unauthorized"
  | "rate_limited"
  | "internal_error"
  | "invalid_request"
  | "not_found";

/** WebSocket error payload */
export interface WebSocketErrorPayload {
  code: WebSocketErrorCode;
  message: string;
  retryable: boolean;
  details?: Record<string, unknown>;
}

/** WebSocket error message */
export interface WebSocketError {
  type: "error";
  payload: WebSocketErrorPayload;
}

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Check if a value is a valid object with a type field
 */
function isMessageEnvelope(
  value: unknown,
): value is { type: string; payload?: unknown } {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    typeof (value as { type: unknown }).type === "string"
  );
}

/**
 * Type guard for ConsoleLogEntry
 */
export function isConsoleLogEntry(value: unknown): value is ConsoleLogEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "console" && "payload" in value;
}

/**
 * Type guard for NetworkRequestEntry
 */
export function isNetworkRequestEntry(
  value: unknown,
): value is NetworkRequestEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "network" && "payload" in value;
}

/**
 * Type guard for NetworkUpdateEntry
 */
export function isNetworkUpdateEntry(
  value: unknown,
): value is NetworkUpdateEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "network_update" && "payload" in value;
}

/**
 * Type guard for TraceStepEntry
 */
export function isTraceStepEntry(value: unknown): value is TraceStepEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "trace_step" && "payload" in value;
}

/**
 * Type guard for TraceSpanEntry
 */
export function isTraceSpanEntry(value: unknown): value is TraceSpanEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "trace_span" && "payload" in value;
}

/**
 * Type guard for TraceEventEntry
 */
export function isTraceEventEntry(value: unknown): value is TraceEventEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "trace_event" && "payload" in value;
}

/**
 * Type guard for BudgetAlertEntry
 */
export function isBudgetAlertEntry(value: unknown): value is BudgetAlertEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "budget_alert" && "payload" in value;
}

/**
 * Type guard for SuggestionResponseEntry
 */
export function isSuggestionResponseEntry(
  value: unknown,
): value is SuggestionResponseEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "suggestion_response" && "payload" in value;
}

/**
 * Type guard for MCPServerStatusEntry
 */
export function isMCPServerStatusEntry(
  value: unknown,
): value is MCPServerStatusEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "server_status" && "payload" in value;
}

/**
 * Type guard for MCPToolCallEntry
 */
export function isMCPToolCallEntry(value: unknown): value is MCPToolCallEntry {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "tool_call" && "payload" in value;
}

/**
 * Type guard for WebSocketError
 */
export function isWebSocketError(value: unknown): value is WebSocketError {
  if (!isMessageEnvelope(value)) return false;
  return value.type === "error" && "payload" in value;
}

// All types are exported at their definition points above
