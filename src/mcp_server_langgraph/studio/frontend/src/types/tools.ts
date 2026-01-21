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

/**
 * Tool source - built-in (Python), MCP server, or native LLM provider
 * v7: Added "native" for native LLM provider tools (Anthropic web_search, etc.)
 */
export type ToolSource = "builtin" | "mcp" | "native";

/** Tool selection mode for chat requests */
export type ToolSelectionMode = "auto" | "manual" | "none";

/**
 * Tool preference for native vs builtin execution
 * v7: Controls whether to use native LLM provider tools when available
 */
export type ToolPreference = "auto" | "native" | "builtin" | "mcp";

// =============================================================================
// Unified Tool Types (Snake Case - Backend Response)
// =============================================================================

/** Unified tool representation from backend (snake_case) */
export interface UnifiedTool {
  /**
   * Unique tool identifier for selection (v7)
   * Format: "source:name" (e.g., "builtin:web_search", "mcp:github:create_issue", "native:web_search")
   */
  tool_id: string;
  /** Tool name (qualified name for MCP tools, e.g., "github:create_issue") */
  name: string;
  /** Human-readable display name */
  display_name: string;
  /** Tool description */
  description: string;
  /** Tool source: "builtin", "mcp", or "native" */
  source: ToolSource;
  /** MCP server name (MCP tools only, null for built-in/native) */
  server_name: string | null;
  /** Native tool provider (v7: "anthropic", "google", null for non-native) */
  provider: string | null;
  /** Tool category (calculator, search, filesystem, native, etc.) */
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
  /** Number of native LLM provider tools (v7) */
  native_count: number;
  /** Total number of tools */
  total_count: number;
}

// =============================================================================
// Unified Tool Types (Camel Case - Frontend Use)
// =============================================================================

/** Unified tool representation for frontend use (camelCase) */
export interface UnifiedToolCamelCase {
  /**
   * Unique tool identifier for selection (v7)
   * Format: "source:name" (e.g., "builtin:web_search", "mcp:github:create_issue", "native:web_search")
   */
  toolId: string;
  /** Tool name (qualified name for MCP tools, e.g., "github:create_issue") */
  name: string;
  /** Human-readable display name */
  displayName: string;
  /** Tool description */
  description: string;
  /** Tool source: "builtin", "mcp", or "native" */
  source: ToolSource;
  /** MCP server name (MCP tools only, null for built-in/native) */
  serverName: string | null;
  /** Native tool provider (v7: "anthropic", "google", null for non-native) */
  provider: string | null;
  /** Tool category (calculator, search, filesystem, native, etc.) */
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
  /** Number of native LLM provider tools (v7) */
  nativeCount: number;
  /** Total number of tools */
  totalCount: number;
}

// =============================================================================
// Query Parameters
// =============================================================================

/** Query parameters for listing tools */
export interface ListToolsParams {
  /** Filter by source (all, builtin, mcp, native) - v7: added native */
  source?: "all" | "builtin" | "mcp" | "native";
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
  | "computer_use"
  | "native"; // v7: Native LLM provider tools category

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
  // v7: Native LLM provider tools category
  native: {
    id: "native",
    displayName: "Native",
    description: "Native LLM provider tools (Anthropic, Google)",
    icon: "Zap",
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
  /** Native LLM provider tools grouped by provider (v7) */
  native: Record<string, UnifiedToolCamelCase[]>;
}

// =============================================================================
// Tool Selection State
// =============================================================================

/** State for tool selection in chat input */
export interface ToolSelectionState {
  /** Currently selected tool IDs (v7: using tool_id for selection) */
  selectedTools: string[];
  /** Tool selection mode */
  mode: ToolSelectionMode;
  /** Tool preference for native vs builtin execution (v7) */
  preference: ToolPreference;
  /** Whether the selector dropdown is open */
  isOpen: boolean;
  /** Search term for filtering tools */
  searchTerm: string;
}
