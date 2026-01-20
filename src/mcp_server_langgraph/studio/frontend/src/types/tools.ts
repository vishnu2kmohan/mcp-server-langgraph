/**
 * Unified Tool Types
 *
 * Types for the unified tools API combining built-in and MCP tools.
 * Used for manual tool selection in the chat input.
 *
 * @see GET /api/v1/tools
 */

// =============================================================================
// Tool Source
// =============================================================================

/** Tool source - built-in (Python) or MCP server */
export type ToolSource = "builtin" | "mcp";

/** Tool selection mode for chat requests */
export type ToolSelectionMode = "auto" | "manual" | "none";

// =============================================================================
// Unified Tool Types (Snake Case - Backend Response)
// =============================================================================

/** Unified tool representation from backend (snake_case) */
export interface UnifiedTool {
  /** Tool name (qualified name for MCP tools, e.g., "github:create_issue") */
  name: string;
  /** Human-readable display name */
  display_name: string;
  /** Tool description */
  description: string;
  /** Tool source: "builtin" or "mcp" */
  source: ToolSource;
  /** MCP server name (MCP tools only, null for built-in) */
  server_name: string | null;
  /** Tool category (calculator, search, filesystem, etc.) */
  category: string | null;
  /** JSON Schema for tool parameters */
  input_schema: Record<string, unknown>;
  /** Whether tool requires sandbox environment */
  requires_sandbox: boolean;
}

/** Response from GET /api/v1/tools (snake_case) */
export interface UnifiedToolsListResponse {
  /** List of unified tools */
  tools: UnifiedTool[];
  /** Number of built-in tools */
  builtin_count: number;
  /** Number of MCP tools */
  mcp_count: number;
  /** Total number of tools */
  total_count: number;
}

// =============================================================================
// Unified Tool Types (Camel Case - Frontend Use)
// =============================================================================

/** Unified tool representation for frontend use (camelCase) */
export interface UnifiedToolCamelCase {
  /** Tool name (qualified name for MCP tools, e.g., "github:create_issue") */
  name: string;
  /** Human-readable display name */
  displayName: string;
  /** Tool description */
  description: string;
  /** Tool source: "builtin" or "mcp" */
  source: ToolSource;
  /** MCP server name (MCP tools only, null for built-in) */
  serverName: string | null;
  /** Tool category (calculator, search, filesystem, etc.) */
  category: string | null;
  /** JSON Schema for tool parameters */
  inputSchema: Record<string, unknown>;
  /** Whether tool requires sandbox environment */
  requiresSandbox: boolean;
}

/** Response from GET /api/v1/tools (camelCase for frontend) */
export interface UnifiedToolsListResponseCamelCase {
  /** List of unified tools */
  tools: UnifiedToolCamelCase[];
  /** Number of built-in tools */
  builtinCount: number;
  /** Number of MCP tools */
  mcpCount: number;
  /** Total number of tools */
  totalCount: number;
}

// =============================================================================
// Query Parameters
// =============================================================================

/** Query parameters for listing tools */
export interface ListToolsParams {
  /** Filter by source (all, builtin, mcp) */
  source?: "all" | "builtin" | "mcp";
  /** Filter by category */
  category?: string;
  /** Search term for filtering */
  search?: string;
}

// =============================================================================
// Tool Categories
// =============================================================================

/** Known tool categories for built-in tools */
export type ToolCategory =
  | "calculator"
  | "search"
  | "filesystem"
  | "code_execution"
  | "web"
  | "visual"
  | "computer_use";

/** Category display information */
export interface ToolCategoryInfo {
  /** Category ID */
  id: ToolCategory;
  /** Display name */
  displayName: string;
  /** Description */
  description: string;
  /** Lucide icon name */
  icon: string;
}

/** Tool categories metadata */
export const TOOL_CATEGORIES: Record<ToolCategory, ToolCategoryInfo> = {
  calculator: {
    id: "calculator",
    displayName: "Calculator",
    description: "Mathematical operations",
    icon: "Calculator",
  },
  search: {
    id: "search",
    displayName: "Search",
    description: "Knowledge base and web search",
    icon: "Search",
  },
  filesystem: {
    id: "filesystem",
    displayName: "Filesystem",
    description: "File reading and directory operations",
    icon: "FolderOpen",
  },
  code_execution: {
    id: "code_execution",
    displayName: "Code Execution",
    description: "Execute code in sandboxed environment",
    icon: "Code",
  },
  web: {
    id: "web",
    displayName: "Web",
    description: "Web fetching and HTTP operations",
    icon: "Globe",
  },
  visual: {
    id: "visual",
    displayName: "Visual",
    description: "Screenshots and visual verification",
    icon: "Eye",
  },
  computer_use: {
    id: "computer_use",
    displayName: "Computer Use",
    description: "Browser and desktop automation",
    icon: "Monitor",
  },
};

// =============================================================================
// Grouped Tools
// =============================================================================

/** Tools grouped by source and server */
export interface GroupedTools {
  /** Built-in tools */
  builtin: UnifiedToolCamelCase[];
  /** MCP tools grouped by server name */
  mcp: Record<string, UnifiedToolCamelCase[]>;
}

// =============================================================================
// Tool Selection State
// =============================================================================

/** State for tool selection in chat input */
export interface ToolSelectionState {
  /** Currently selected tool names */
  selectedTools: string[];
  /** Tool selection mode */
  mode: ToolSelectionMode;
  /** Whether the selector dropdown is open */
  isOpen: boolean;
  /** Search term for filtering tools */
  searchTerm: string;
}
