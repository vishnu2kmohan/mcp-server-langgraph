/**
 * Centralized API Configuration
 *
 * Single source of truth for all API endpoints and URL construction.
 * Supports environment variable configuration following 12-Factor App principles.
 *
 * Environment Variables:
 * - VITE_API_BASE_URL: API base URL (e.g., https://api.example.com/v1)
 * - VITE_WS_BASE_URL: WebSocket base URL (e.g., wss://ws.example.com/v1)
 *
 * Usage:
 * ```typescript
 * import { API_ENDPOINTS, getApiBaseUrl, buildApiUrl } from '../config/api';
 * import { buildWebSocketUrl, WS_ENDPOINTS } from '../utils/websocket';
 *
 * // Get API base URL
 * const apiUrl = getApiBaseUrl();
 *
 * // Build API URL for an endpoint
 * const url = buildApiUrl(API_ENDPOINTS.SESSIONS);
 *
 * // Build WebSocket URL (use utils/websocket.ts)
 * const wsUrl = buildWebSocketUrl(WS_ENDPOINTS.NOTIFICATIONS, {}, true);
 * ```
 */

// =============================================================================
// SSR-Safe Defaults
// =============================================================================

/**
 * Default URLs for SSR (Node.js) environment where window is undefined.
 * These match the backend default port (8000).
 */
export const SSR_DEFAULTS = {
  API_BASE_URL: "http://localhost:8000/api/v1",
  WS_BASE_URL: "ws://localhost:8000/api/v1", // nosemgrep: detect-insecure-websocket
} as const;

// =============================================================================
// API Endpoints (Single Source of Truth)
// =============================================================================

/**
 * All API endpoint paths (relative to base URL).
 * This centralizes endpoint definitions to prevent duplication across hooks.
 */
export const API_ENDPOINTS = {
  // Auth endpoints
  AUTH_LOGIN: "/auth/login",
  AUTH_LOGOUT: "/auth/logout",
  AUTH_REFRESH: "/auth/refresh",
  AUTH_PKCE_CALLBACK: "/auth/pkce/callback",

  // Session endpoints
  SESSIONS: "/sessions",

  // Config endpoints
  CONFIG_DEFAULTS: "/config/defaults",
  FEATURE_FLAGS: "/feature-flags",

  // Cost tracking endpoints
  COST_SUMMARY: "/cost/summary",
  COST_BY_SESSION: "/cost/by-session",

  // Observability endpoints
  OBSERVABILITY_HEALTH: "/observability/health",
  OBSERVABILITY_METRICS: "/observability/metrics",

  // MCP endpoints
  MCP_TOOLS: "/mcp/tools",
  MCP_RESOURCES: "/mcp/resources",
  MCP_PROMPTS: "/mcp/prompts",

  // WebSocket endpoints (relative paths)
  WS_NOTIFICATIONS: "/ws/notifications",
  WS_ALERTS: "/ws/alerts",
  WS_MCP: "/ws/mcp",
  WS_MCP_AUTH: "/ws/mcp/auth",
  WS_TRACES: "/ws/traces",
  WS_AUDIT: "/ws/audit",
  WS_COST: "/ws/cost",
  WS_HEART: "/ws/heart",
  WS_AI_SUGGESTIONS: "/ws/ai/suggestions",
  WS_CONNECTIONS: "/ws/connections",
  WS_CONNECTIONS_HEALTH: "/ws/connections/health",
  WS_MCP_TASKS: "/ws/mcp/tasks",
  WS_AGENT_REQUESTS: "/ws/agent-requests",
  WS_DEVTOOLS: "/ws/devtools",
  WS_MCP_AGGREGATED: "/ws/mcp/aggregated",
} as const;

// =============================================================================
// URL Construction Functions
// =============================================================================

/**
 * Window-like interface for testing and SSR
 */
interface WindowLike {
  location: {
    protocol: string;
    host: string;
  };
}

/**
 * Get the API base URL.
 *
 * Priority:
 * 1. VITE_API_BASE_URL environment variable (if set)
 * 2. Relative URL "/api/v1" (browser, same-origin deployments)
 * 3. SSR default (Node.js environment)
 *
 * @returns API base URL
 */
export function getApiBaseUrl(): string {
  // Check for Vite env var first
  if (
    typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_API_BASE_URL
  ) {
    return import.meta.env.VITE_API_BASE_URL;
  }

  // In browser, use relative URL (works for same-origin deployments)
  if (typeof window !== "undefined") {
    return "/api/v1";
  }

  // SSR fallback
  return SSR_DEFAULTS.API_BASE_URL;
}

/**
 * Get the WebSocket base URL.
 *
 * Priority:
 * 1. VITE_WS_BASE_URL environment variable (if set)
 * 2. Derived from window.location (wss:// for https://, ws:// for http://)
 * 3. SSR default (Node.js environment)
 *
 * @param windowRef - Optional window reference (for testing/SSR)
 * @returns WebSocket base URL
 */
export function getWebSocketBaseUrl(windowRef?: WindowLike): string {
  // Check for Vite env var first
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_WS_BASE_URL) {
    return import.meta.env.VITE_WS_BASE_URL;
  }

  // Use provided window reference or global window
  const win = windowRef ?? (typeof window !== "undefined" ? window : undefined);

  if (!win) {
    // SSR fallback
    return SSR_DEFAULTS.WS_BASE_URL;
  }

  // Derive from window.location
  const protocol = win.location.protocol === "https:" ? "wss:" : "ws:";
  const host = win.location.host;

  return `${protocol}//${host}/api/v1`;
}

/**
 * Build a complete API URL for a given endpoint.
 *
 * @param endpoint - API endpoint path (e.g., API_ENDPOINTS.SESSIONS)
 * @returns Complete API URL
 *
 * @example
 * ```typescript
 * const url = buildApiUrl(API_ENDPOINTS.SESSIONS);
 * // Returns: "/api/v1/sessions" or "https://api.example.com/v1/sessions"
 * ```
 */
export function buildApiUrl(endpoint: string): string {
  const baseUrl = getApiBaseUrl();
  return `${baseUrl}${endpoint}`;
}

// =============================================================================
// Re-exports for Migration Convenience
// =============================================================================

/**
 * Re-export WS_ENDPOINTS from websocket.ts for migration convenience.
 *
 * New code should import directly from '../utils/websocket':
 * ```typescript
 * import { buildWebSocketUrl, WS_ENDPOINTS } from '../utils/websocket';
 * ```
 */
export { WS_ENDPOINTS } from "../utils/websocket";
