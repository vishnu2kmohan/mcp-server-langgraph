/**
 * MCP Types
 *
 * Type definitions for Model Context Protocol state management.
 * Based on MCP 2025-11-25 specification.
 */

// ==============================================================================
// Server Connection
// ==============================================================================

/** MCP connection status */
export type MCPConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

/** MCP server info from initialization */
export interface MCPServerInfo {
  name: string;
  version: string;
}

/** MCP server capabilities */
export interface MCPServerCapabilities {
  tools?: { listChanged?: boolean };
  resources?: { subscribe?: boolean; listChanged?: boolean };
  prompts?: { listChanged?: boolean };
  logging?: Record<string, never>;
}

/** MCP server connection */
export interface MCPServerConnection {
  id: string;
  url: string;
  status: MCPConnectionStatus;
  serverInfo?: MCPServerInfo;
  capabilities?: MCPServerCapabilities;
  error?: string;
  lastConnected?: number;
}

// ==============================================================================
// Tools
// ==============================================================================

/** JSON Schema type */
export interface JSONSchema {
  type?: 'object' | 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'null';
  properties?: Record<string, JSONSchema>;
  required?: string[];
  description?: string;
  default?: unknown;
}

/** MCP Tool */
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: JSONSchema;
  serverId: string;
}

// ==============================================================================
// Resources
// ==============================================================================

/** MCP Resource */
export interface MCPResource {
  uri: string;
  name: string;
  description?: string;
  mimeType?: string;
  serverId: string;
}

// ==============================================================================
// Prompts
// ==============================================================================

/** MCP Prompt argument */
export interface MCPPromptArgument {
  name: string;
  description?: string;
  required?: boolean;
}

/** MCP Prompt */
export interface MCPPrompt {
  name: string;
  description?: string;
  arguments?: MCPPromptArgument[];
  serverId: string;
}

// ==============================================================================
// Elicitation
// ==============================================================================

/** Elicitation action */
export type ElicitationAction = 'accept' | 'decline' | 'cancel';

/** Pending elicitation request */
export interface PendingElicitation {
  id: string;
  serverId: string;
  message: string;
  requestedSchema: JSONSchema;
  createdAt: number;
  mode?: 'inline' | 'url';
  url?: string;
}

// ==============================================================================
// Sampling
// ==============================================================================

/** Sampling message */
export interface SamplingMessage {
  role: 'user' | 'assistant';
  content: string;
}

/** Model preferences for sampling */
export interface ModelPreferences {
  hints?: Array<{ name?: string }>;
  costPriority?: number;
  speedPriority?: number;
  intelligencePriority?: number;
}

/** Pending sampling request */
export interface PendingSamplingRequest {
  id: string;
  serverId: string;
  messages: SamplingMessage[];
  modelPreferences?: ModelPreferences;
  systemPrompt?: string;
  maxTokens: number;
  createdAt: number;
}

// ==============================================================================
// Server Entry (Internal)
// ==============================================================================

/** Server entry with full data */
export interface ServerEntry extends MCPServerConnection {
  tools: MCPTool[];
  resources: MCPResource[];
  prompts: MCPPrompt[];
}

// ==============================================================================
// Store State
// ==============================================================================

/** Client capabilities configuration */
export interface MCPClientCapabilities {
  elicitation: boolean;
  sampling: boolean;
  roots: { listChanged: boolean };
}

/** MCP store state */
export interface MCPState {
  /** Connected servers */
  servers: Map<string, ServerEntry>;

  /** Primary server ID */
  primaryServerId: string | null;

  /** Client capabilities */
  capabilities: MCPClientCapabilities;

  /** Pending elicitation requests */
  pendingElicitations: PendingElicitation[];

  /** Pending sampling requests */
  pendingSamplingRequests: PendingSamplingRequest[];

  /** Whether initial connection is in progress */
  isConnecting: boolean;

  /** Global error */
  error: string | null;
}

/** Add server options */
export interface AddServerOptions {
  primary?: boolean;
  authToken?: string;
}

/** MCP store actions */
export interface MCPActions {
  /** Add a server connection */
  addServer: (id: string, url: string, options?: AddServerOptions) => Promise<void>;

  /** Remove a server connection */
  removeServer: (id: string) => void;

  /** Set primary server */
  setPrimaryServer: (id: string) => void;

  /** Update server status */
  updateServerStatus: (id: string, status: MCPConnectionStatus, error?: string) => void;

  /** Set server tools */
  setServerTools: (id: string, tools: MCPTool[]) => void;

  /** Set server resources */
  setServerResources: (id: string, resources: MCPResource[]) => void;

  /** Set server prompts */
  setServerPrompts: (id: string, prompts: MCPPrompt[]) => void;

  /** Add elicitation request */
  addElicitation: (elicitation: PendingElicitation) => void;

  /** Respond to elicitation */
  respondToElicitation: (id: string, action: ElicitationAction, content?: Record<string, unknown>) => void;

  /** Add sampling request */
  addSamplingRequest: (request: PendingSamplingRequest) => void;

  /** Respond to sampling */
  respondToSampling: (id: string, approved: boolean, result?: unknown) => void;

  /** Get all tools from all servers */
  getAllTools: () => MCPTool[];

  /** Get all resources from all servers */
  getAllResources: () => MCPResource[];

  /** Get all prompts from all servers */
  getAllPrompts: () => MCPPrompt[];

  /** Clear error */
  clearError: () => void;

  /** Reset state */
  reset: () => void;
}

/** Combined MCP store type */
export type MCPStore = MCPState & MCPActions;
