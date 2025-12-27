/**
 * MCP Connection Types
 *
 * Type definitions for MCP server connection management.
 * Supports OAuth2 and API Key authentication per MCP 2025-03-26 spec.
 */

// ==============================================================================
// Auth Types
// ==============================================================================

/** Authentication type for MCP connections */
export type AuthType = "none" | "api_key" | "oauth2";

/**
 * Transport protocol for MCP connections (per MCP 2025-11-25 spec)
 *
 * - streamable_http: HTTP endpoint with SSE streaming (recommended for remote servers)
 * - stdio: Standard I/O for local subprocess-based servers
 */
export type TransportProtocol = "streamable_http" | "stdio";

/** Connection status */
export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error"
  | "auth_required";

// ==============================================================================
// OAuth2 Configuration
// ==============================================================================

/** OAuth2 configuration (client credentials only, not tokens) */
export interface OAuth2Config {
  client_id: string | null;
  authorization_url: string | null;
  token_url: string | null;
  scopes: string[];
}

// ==============================================================================
// Connection Models
// ==============================================================================

/** Full MCP connection entity */
export interface MCPConnection {
  id: string;
  name: string;
  description: string | null;
  url: string;
  transport: TransportProtocol;
  auth_type: AuthType;
  oauth2_config: OAuth2Config | null;
  /** For stdio transport: command to execute */
  command: string | null;
  /** For stdio transport: command arguments */
  args: string[] | null;
  /** For stdio transport: environment variables */
  env: Record<string, string> | null;
  status: ConnectionStatus;
  last_error: string | null;
  last_connected_at: string | null;
  server_name: string | null;
  server_version: string | null;
  server_capabilities: Record<string, unknown> | null;
  tool_count: number;
  resource_count: number;
  prompt_count: number;
  owner_id: string;
  organization_id: string | null;
  project_id: string | null;
  created_at: string;
  updated_at: string;
}

/** Summary of an MCP connection for list responses */
export interface MCPConnectionSummary {
  id: string;
  name: string;
  url: string;
  transport: TransportProtocol;
  auth_type: AuthType;
  status: ConnectionStatus;
  server_name: string | null;
  tool_count: number;
  resource_count: number;
  prompt_count: number;
  last_connected_at: string | null;
  created_at: string;
}

// ==============================================================================
// Request Models
// ==============================================================================

/** Request model for creating an MCP connection */
export interface MCPConnectionCreate {
  name: string;
  description?: string | null;
  url: string;
  transport?: TransportProtocol;
  auth_type?: AuthType;
  api_key?: string | null;
  oauth2_client_id?: string | null;
  oauth2_client_secret?: string | null;
  oauth2_scopes?: string[] | null;
  project_id?: string | null;
  /** For stdio transport: command to execute */
  command?: string | null;
  /** For stdio transport: command arguments */
  args?: string[] | null;
  /** For stdio transport: environment variables */
  env?: Record<string, string> | null;
}

/** Request model for updating an MCP connection */
export interface MCPConnectionUpdate {
  name?: string | null;
  description?: string | null;
  url?: string | null;
}

// ==============================================================================
// Response Models
// ==============================================================================

/** Response from listing connections */
export interface ConnectionListResponse {
  items: MCPConnectionSummary[];
  total: number;
  cursor: string | null;
}

/** Result of testing an MCP connection */
export interface MCPConnectionTestResult {
  success: boolean;
  server_name: string | null;
  server_version: string | null;
  tool_count: number;
  resource_count: number;
  prompt_count: number;
  error: string | null;
}

/** Response from starting OAuth2 flow */
export interface OAuth2StartResponse {
  authorization_url: string;
  state: string;
}

// ==============================================================================
// Filter Options
// ==============================================================================

/** Sort field options for connections */
export type ConnectionSortField =
  | "name"
  | "created_at"
  | "updated_at"
  | "status";

/** Options for filtering connections */
export interface ConnectionFilterOptions {
  status?: ConnectionStatus;
  auth_type?: AuthType;
  project_id?: string;
  search?: string;
  cursor?: string;
  limit?: number;
  sort_by?: ConnectionSortField;
  sort_order?: "asc" | "desc";
}

// ==============================================================================
// Store Types
// ==============================================================================

/** Connection store state */
export interface ConnectionState {
  /** Loaded connections */
  connections: MCPConnectionSummary[];

  /** Selected connection detail */
  selectedConnection: MCPConnection | null;

  /** Loading states */
  isLoading: boolean;
  isCreating: boolean;
  isTesting: boolean;

  /** Error state */
  error: string | null;

  /** Pagination cursor */
  nextCursor: string | null;
}

/** Connection store actions */
export interface ConnectionActions {
  /** List connections with optional filters */
  listConnections: (options?: ConnectionFilterOptions) => Promise<void>;

  /** Get connection by ID */
  getConnection: (id: string) => Promise<MCPConnection | null>;

  /** Create a new connection */
  createConnection: (data: MCPConnectionCreate) => Promise<MCPConnection>;

  /** Update a connection */
  updateConnection: (
    id: string,
    data: MCPConnectionUpdate,
  ) => Promise<MCPConnection>;

  /** Delete a connection */
  deleteConnection: (id: string) => Promise<void>;

  /** Test a connection */
  testConnection: (id: string) => Promise<MCPConnectionTestResult>;

  /** Start OAuth2 flow */
  startOAuth2Flow: (id: string) => Promise<OAuth2StartResponse>;

  /** Clear selected connection */
  clearSelection: () => void;

  /** Clear error */
  clearError: () => void;

  /** Reset state */
  reset: () => void;
}

/** Combined connection store type */
export type ConnectionStore = ConnectionState & ConnectionActions;

// ==============================================================================
// Aggregated Capabilities Types (MCP 2025-11-25)
// ==============================================================================

/** Tool from an external MCP server (with qualified naming) */
export interface AggregatedTool {
  qualified_name: string;
  server_name: string;
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

/** Resource from an external MCP server (with qualified naming) */
export interface AggregatedResource {
  qualified_name: string;
  server_name: string;
  uri: string;
  name: string;
  description: string | null;
  mime_type: string | null;
}

/** Prompt from an external MCP server (with qualified naming) */
export interface AggregatedPrompt {
  qualified_name: string;
  server_name: string;
  name: string;
  description: string | null;
  arguments: Array<{
    name: string;
    required?: boolean;
    description?: string;
  }>;
}

/** Response for listing aggregated tools */
export interface AggregatedToolsResponse {
  tools: AggregatedTool[];
  total_count: number;
}

/** Response for listing aggregated resources */
export interface AggregatedResourcesResponse {
  resources: AggregatedResource[];
  total_count: number;
}

/** Response for listing aggregated prompts */
export interface AggregatedPromptsResponse {
  prompts: AggregatedPrompt[];
  total_count: number;
}

/** Server capability summary */
export interface ServerCapabilitySummary {
  server_name: string;
  tool_count: number;
  resource_count: number;
  prompt_count: number;
}

/** Response for all servers summary */
export interface AggregatedServersResponse {
  servers: ServerCapabilitySummary[];
  total_servers: number;
  total_tools: number;
  total_resources: number;
  total_prompts: number;
}
