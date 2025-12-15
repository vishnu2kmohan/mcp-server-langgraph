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
  auth_type: AuthType;
  oauth2_config: OAuth2Config | null;
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
  auth_type?: AuthType;
  api_key?: string | null;
  oauth2_client_id?: string | null;
  oauth2_client_secret?: string | null;
  oauth2_scopes?: string[] | null;
  project_id?: string | null;
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
