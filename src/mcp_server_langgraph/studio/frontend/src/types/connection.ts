/**
 * MCP Connection Types
 *
 * Type definitions for MCP server connection management.
 * Supports OAuth2 and API Key authentication per MCP 2025-03-26 spec.
 *
 * ADR-0091 Phase 6: Types use snake_case to match backend API responses.
 * RTK Query transforms responses to camelCase at runtime.
 * Use `*CamelCase` type aliases for frontend components.
 */

import type { SnakeToCamelCaseDeep } from "../api/transforms";

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

/**
 * Connection scope - determines access control (ADR-0102 Phase 6)
 *
 * - user: Personal connection, only accessible by owner
 * - project: Shared connection, accessible by all project members
 * - session: Ephemeral connection, only valid for current session
 */
export type ConnectionScope = "user" | "project" | "session";

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
  /** Connection scope - determines access control (ADR-0102 Phase 6) */
  scope: ConnectionScope;
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
  /** Connection scope - determines access control (ADR-0102 Phase 6) */
  scope: ConnectionScope;
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

/**
 * Request model for creating an MCP connection
 *
 * ADR-0091 Phase 6: Uses camelCase - transformed to snake_case at API boundary
 */
export interface MCPConnectionCreate {
  name: string;
  description?: string | null;
  url: string;
  transport?: TransportProtocol;
  authType?: AuthType;
  apiKey?: string | null;
  oauth2ClientId?: string | null;
  oauth2ClientSecret?: string | null;
  oauth2Scopes?: string[] | null;
  projectId?: string | null;
  /** Connection scope - defaults to "user" (ADR-0102 Phase 6) */
  scope?: ConnectionScope;
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
  /** Filter by connection scope (ADR-0102 Phase 6) */
  scope?: ConnectionScope;
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
// Database Connection Types (SQLGlot Phase 6)
// ==============================================================================

/** Database dialect identifier */
export type DatabaseDialect =
  | "postgres"
  | "mysql"
  | "sqlite"
  | "bigquery"
  | "snowflake"
  | "duckdb"
  | "redshift"
  | "clickhouse"
  | "trino";

/** SSL/TLS mode for database connections */
export type SSLMode = "disable" | "require" | "verify-ca" | "verify-full";

/** Connection method for credential source */
export type ConnectionMethod =
  | "credentials"
  | "secret_ref"
  | "connection_string";

/** Full database connection entity (snake_case - matches API) */
export interface DatabaseConnection {
  id: string;
  name: string;
  description: string | null;
  dialect: DatabaseDialect;
  host: string | null;
  port: number | null;
  database: string | null;
  project_id: string | null;
  account_id: string | null;
  warehouse_id: string | null;
  ssl_mode: SSLMode;
  status: ConnectionStatus;
  last_tested_at: string | null;
  dialect_version: string | null;
  owner_id: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

/**
 * Request model for creating a database connection (camelCase)
 *
 * ADR-0091 Phase 6: Uses camelCase - transformed to snake_case at API boundary
 */
export interface DatabaseConnectionCreate {
  name: string;
  description?: string | null;
  dialect: DatabaseDialect;
  host?: string | null;
  port?: number | null;
  database?: string | null;
  projectId?: string | null;
  accountId?: string | null;
  warehouseId?: string | null;
  connectionMethod?: ConnectionMethod;
  username?: string | null;
  password?: string | null;
  secretPath?: string | null;
  secretKey?: string | null;
  sslMode?: SSLMode;
  scope?: ConnectionScope;
}

/** Request model for updating a database connection (camelCase) */
export interface DatabaseConnectionUpdate {
  name?: string | null;
  description?: string | null;
  host?: string | null;
  port?: number | null;
  database?: string | null;
  sslMode?: SSLMode | null;
}

/** Result of testing a database connection */
export interface DatabaseConnectionTestResult {
  success: boolean;
  error: string | null;
  dialect_version: string | null;
}

/** Response for listing database connections */
export interface DatabaseConnectionListResponse {
  items: DatabaseConnection[];
  total: number;
}

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

// ==============================================================================
// ADR-0091 Phase 6: CamelCase Type Aliases (for transformed responses)
// ==============================================================================

/**
 * OAuth2Config type with camelCase keys (after RTK Query transformation).
 */
export type OAuth2ConfigCamelCase = SnakeToCamelCaseDeep<OAuth2Config>;

/**
 * AggregatedTool type with camelCase keys (after RTK Query transformation).
 */
export type AggregatedToolCamelCase = SnakeToCamelCaseDeep<AggregatedTool>;

/**
 * AggregatedResource type with camelCase keys (after RTK Query transformation).
 */
export type AggregatedResourceCamelCase =
  SnakeToCamelCaseDeep<AggregatedResource>;

/**
 * AggregatedPrompt type with camelCase keys (after RTK Query transformation).
 */
export type AggregatedPromptCamelCase = SnakeToCamelCaseDeep<AggregatedPrompt>;

/**
 * ServerCapabilitySummary type with camelCase keys (after RTK Query transformation).
 */
export type ServerCapabilitySummaryCamelCase =
  SnakeToCamelCaseDeep<ServerCapabilitySummary>;

/**
 * AggregatedServersResponse type with camelCase keys (after RTK Query transformation).
 */
export type AggregatedServersResponseCamelCase =
  SnakeToCamelCaseDeep<AggregatedServersResponse>;

/**
 * MCPConnection type with camelCase keys (after RTK Query transformation).
 */
export type MCPConnectionCamelCase = SnakeToCamelCaseDeep<MCPConnection>;

/**
 * MCPConnectionSummary type with camelCase keys (after RTK Query transformation).
 */
export type MCPConnectionSummaryCamelCase =
  SnakeToCamelCaseDeep<MCPConnectionSummary>;

/**
 * ConnectionListResponse type with camelCase keys (after RTK Query transformation).
 */
export interface ConnectionListResponseCamelCase {
  items: MCPConnectionSummaryCamelCase[];
  total: number;
  cursor: string | null;
}

/**
 * DatabaseConnection type with camelCase keys (after RTK Query transformation).
 */
export type DatabaseConnectionCamelCase =
  SnakeToCamelCaseDeep<DatabaseConnection>;

/**
 * DatabaseConnectionTestResult type with camelCase keys (after RTK Query transformation).
 */
export type DatabaseConnectionTestResultCamelCase =
  SnakeToCamelCaseDeep<DatabaseConnectionTestResult>;
