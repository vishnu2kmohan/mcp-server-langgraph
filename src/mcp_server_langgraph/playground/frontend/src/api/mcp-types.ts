/**
 * MCP Protocol Types (2025-11-25 Specification)
 *
 * TypeScript interfaces for the Model Context Protocol,
 * including JSON-RPC 2.0, tools, resources, prompts,
 * elicitation, and sampling.
 */

// =============================================================================
// JSON-RPC 2.0 Types
// =============================================================================

export interface JSONRPCRequest<P = unknown> {
  jsonrpc: '2.0';
  id: string | number;
  method: string;
  params?: P;
}

export interface JSONRPCResponse<T = unknown> {
  jsonrpc: '2.0';
  id: string | number;
  result?: T;
  error?: JSONRPCError;
}

export interface JSONRPCError {
  code: number;
  message: string;
  data?: unknown;
}

export interface JSONRPCNotification<P = unknown> {
  jsonrpc: '2.0';
  method: string;
  params?: P;
}

// Standard JSON-RPC error codes
export const JSON_RPC_ERROR_CODES = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,
} as const;

// =============================================================================
// MCP Initialization Types
// =============================================================================

export interface MCPServerInfo {
  name: string;
  version: string;
}

export interface MCPClientInfo {
  name: string;
  version: string;
}

export interface MCPServerCapabilities {
  tools?: { listChanged?: boolean };
  resources?: { subscribe?: boolean; listChanged?: boolean };
  prompts?: { listChanged?: boolean };
  logging?: Record<string, never>;
  experimental?: Record<string, unknown>;
}

export interface MCPClientCapabilities {
  elicitation?: Record<string, never>;
  sampling?: Record<string, never>;
  roots?: { listChanged?: boolean };
  experimental?: Record<string, unknown>;
}

export interface InitializeParams {
  protocolVersion: string;
  capabilities: MCPClientCapabilities;
  clientInfo: MCPClientInfo;
}

export interface InitializeResult {
  protocolVersion: string;
  capabilities: MCPServerCapabilities;
  serverInfo: MCPServerInfo;
  instructions?: string;
}

// =============================================================================
// SEP-973: Icons Metadata (New in 2025-11-25)
// =============================================================================

export interface IconReference {
  uri: string;  // data: URI or https: URI
}

// =============================================================================
// MCP Tool Types
// =============================================================================

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: JSONSchema;
  icon?: IconReference;  // SEP-973
}

export interface MCPToolCallParams {
  name: string;
  arguments?: Record<string, unknown>;
}

export interface MCPToolResult {
  content: MCPContent[];
  isError?: boolean;
}

// =============================================================================
// MCP Resource Types
// =============================================================================

export interface MCPResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
  icon?: IconReference;  // SEP-973
}

export interface MCPResourceTemplate {
  uriTemplate: string;
  name: string;
  description?: string;
  mimeType?: string;
}

export interface MCPResourceContent {
  uri: string;
  mimeType?: string;
  text?: string;
  blob?: string;
}

export interface ResourceReadParams {
  uri: string;
}

export interface ResourceReadResult {
  contents: MCPResourceContent[];
}

export interface ResourceListResult {
  resources: MCPResource[];
  resourceTemplates?: MCPResourceTemplate[];
}

// =============================================================================
// MCP Prompt Types
// =============================================================================

export interface MCPPrompt {
  name: string;
  description?: string;
  arguments?: MCPPromptArgument[];
  icon?: IconReference;  // SEP-973
}

export interface MCPPromptArgument {
  name: string;
  description?: string;
  required?: boolean;
}

export interface MCPPromptMessage {
  role: 'user' | 'assistant';
  content: MCPContent;
}

export interface PromptGetParams {
  name: string;
  arguments?: Record<string, string>;
}

export interface PromptGetResult {
  description?: string;
  messages: MCPPromptMessage[];
}

export interface PromptListResult {
  prompts: MCPPrompt[];
}

// =============================================================================
// MCP Elicitation Types (2025-11-25 Spec)
// =============================================================================

export interface ElicitationCreateParams {
  message: string;
  requestedSchema: JSONSchema;
  // SEP-1036: URL mode for OAuth credential collection
  mode?: 'inline' | 'url';
  url?: string;  // Required when mode='url'
}

export type ElicitationAction = 'accept' | 'decline' | 'cancel';

export interface ElicitationResult {
  action: ElicitationAction;
  content?: Record<string, unknown>;
}

export interface PendingElicitation {
  id: string;
  serverId: string;
  message: string;
  requestedSchema: JSONSchema;
  createdAt: string;
  // SEP-1036: URL mode for OAuth credential collection
  mode?: 'inline' | 'url';
  url?: string;  // Required when mode='url'
}

// =============================================================================
// MCP Sampling Types (Server→Client LLM Requests)
// =============================================================================

export interface SamplingMessage {
  role: 'user' | 'assistant';
  content: MCPContent;
}

export interface ModelHint {
  name?: string;
}

export interface ModelPreferences {
  hints?: ModelHint[];
  costPriority?: number;
  speedPriority?: number;
  intelligencePriority?: number;
}

// SEP-1577: Sampling with Tools (New in 2025-11-25)
export interface SamplingTool {
  name: string;
  description?: string;
  inputSchema: JSONSchema;
}

// SEP-1577: Tool selection preference
export interface ToolChoice {
  type: 'auto' | 'none' | 'tool';
  name?: string;  // Required when type='tool'
}

export interface SamplingCreateParams {
  messages: SamplingMessage[];
  modelPreferences?: ModelPreferences;
  systemPrompt?: string;
  includeContext?: 'none' | 'thisServer' | 'allServers';
  temperature?: number;
  maxTokens: number;
  stopSequences?: string[];
  metadata?: Record<string, unknown>;
  // SEP-1577: Tool definitions for agentic loops
  tools?: SamplingTool[];
  toolChoice?: ToolChoice;
}

export type StopReason = 'endTurn' | 'stopSequence' | 'maxTokens';

export interface SamplingResult {
  role: 'assistant';
  content: MCPContent;
  model: string;
  stopReason?: StopReason;
}

export interface PendingSamplingRequest {
  id: string;
  serverId: string;
  messages: SamplingMessage[];
  modelPreferences?: ModelPreferences;
  systemPrompt?: string;
  maxTokens: number;
  createdAt: string;
  // SEP-1577: Tool definitions for agentic loops
  tools?: SamplingTool[];
  toolChoice?: ToolChoice;
}

// =============================================================================
// MCP Tasks Types (SEP-1686: Durable Request Tracking)
// =============================================================================

export type MCPTaskState = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface MCPTask {
  id: string;
  method: string;
  state: MCPTaskState;
  progress?: number;  // 0-100
  progressMessage?: string;
  result?: unknown;
  error?: JSONRPCError;
  createdAt: string;
  updatedAt: string;
}

export interface TaskCreateResult {
  taskId: string;
}

export interface TaskGetParams {
  taskId: string;
}

export interface TaskGetResult {
  task: MCPTask;
}

export interface TaskListResult {
  tasks: MCPTask[];
}

export interface TaskCancelParams {
  taskId: string;
}

// =============================================================================
// MCP Roots Types
// =============================================================================

export interface MCPRoot {
  uri: string;
  name?: string;
}

export interface RootsListResult {
  roots: MCPRoot[];
}

// =============================================================================
// MCP Logging Types
// =============================================================================

export type MCPLogLevel = 'debug' | 'info' | 'notice' | 'warning' | 'error' | 'critical' | 'alert' | 'emergency';

export interface LoggingMessageParams {
  level: MCPLogLevel;
  logger?: string;
  data?: unknown;
}

// =============================================================================
// MCP Content Types
// =============================================================================

export interface TextContent {
  type: 'text';
  text: string;
}

export interface ImageContent {
  type: 'image';
  data: string;
  mimeType: string;
}

export interface ResourceContent {
  type: 'resource';
  resource: MCPResourceContent;
}

export type MCPContent = TextContent | ImageContent | ResourceContent;

// =============================================================================
// JSON Schema Types (Subset for MCP)
// =============================================================================

export interface JSONSchema {
  type?: 'object' | 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'null';
  properties?: Record<string, JSONSchema>;
  required?: string[];
  items?: JSONSchema;
  enum?: (string | number | boolean | null)[];
  // SEP-1330: Human-readable labels for enum values (same order as enum array)
  enumNames?: string[];
  description?: string;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  format?: string;
  title?: string;
  additionalProperties?: boolean | JSONSchema;
}

// =============================================================================
// Streaming Types (NDJSON)
// =============================================================================

export type MCPStreamChunkType =
  | 'chunk'
  | 'complete'
  | 'error'
  | 'tool_call'
  | 'tool_result'
  | 'elicitation'
  | 'sampling';

export interface MCPStreamChunk {
  type: MCPStreamChunkType;
  content?: string;
  messageId?: string;
  usage?: MCPTokenUsage;
  toolCall?: MCPToolCallInfo;
  toolResult?: MCPToolResult;
  elicitation?: ElicitationCreateParams;
  sampling?: SamplingCreateParams;
  error?: string;
}

export interface MCPTokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

export interface MCPToolCallInfo {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

// =============================================================================
// MCP Server Connection Types
// =============================================================================

export type MCPConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface MCPServerConnection {
  id: string;
  url: string;
  status: MCPConnectionStatus;
  serverInfo?: MCPServerInfo;
  capabilities?: MCPServerCapabilities;
  error?: string;
  lastConnected?: string;
}

// =============================================================================
// MCP Method Names
// =============================================================================

export const MCP_METHODS = {
  // Lifecycle
  INITIALIZE: 'initialize',
  INITIALIZED: 'notifications/initialized',
  PING: 'ping',

  // Tools
  TOOLS_LIST: 'tools/list',
  TOOLS_CALL: 'tools/call',

  // Resources
  RESOURCES_LIST: 'resources/list',
  RESOURCES_READ: 'resources/read',
  RESOURCES_SUBSCRIBE: 'resources/subscribe',
  RESOURCES_UNSUBSCRIBE: 'resources/unsubscribe',

  // Prompts
  PROMPTS_LIST: 'prompts/list',
  PROMPTS_GET: 'prompts/get',

  // Elicitation (Server → Client)
  ELICITATION_CREATE: 'elicitation/create',

  // Sampling (Server → Client)
  SAMPLING_CREATE: 'sampling/createMessage',

  // Roots (Server → Client)
  ROOTS_LIST: 'roots/list',

  // Logging
  LOGGING_SET_LEVEL: 'logging/setLevel',

  // Completion
  COMPLETION_COMPLETE: 'completion/complete',

  // Tasks (SEP-1686)
  TASKS_LIST: 'tasks/list',
  TASKS_GET: 'tasks/get',
  TASKS_CANCEL: 'tasks/cancel',
} as const;

// =============================================================================
// Type Guards
// =============================================================================

export function isTextContent(content: MCPContent): content is TextContent {
  return content.type === 'text';
}

export function isImageContent(content: MCPContent): content is ImageContent {
  return content.type === 'image';
}

export function isResourceContent(content: MCPContent): content is ResourceContent {
  return content.type === 'resource';
}

export function isJSONRPCError(response: JSONRPCResponse): boolean {
  return response.error !== undefined;
}

// =============================================================================
// Helper Types
// =============================================================================

export type MCPMethod = typeof MCP_METHODS[keyof typeof MCP_METHODS];

export interface MCPRequestOptions {
  timeout?: number;
  signal?: AbortSignal;
}
