/**
 * WebSocket URL Utilities
 *
 * Centralized WebSocket URL construction following 12-Factor App principles.
 * Configuration comes from environment variables, not hardcoded values.
 *
 * Environment Variables:
 * - VITE_API_HOST: Backend API host (default: derived from window.location)
 * - VITE_API_PORT: Backend API port (default: derived from window.location)
 */

import { getAuthToken } from "./storage";
import { PROTOCOL_VERSION } from "../types/websocket-protocols";

/**
 * Get API host from environment or window.location
 *
 * Priority:
 * 1. VITE_API_HOST environment variable (for production/staging config)
 * 2. window.location.host (for same-origin deployments)
 * 3. Fallback for SSR (never used in browser)
 */
export function getApiHost(): string {
  // Check for Vite environment variable first (12-Factor: config from env)
  const envHost = import.meta.env?.VITE_API_HOST;
  if (envHost) {
    const envPort = import.meta.env?.VITE_API_PORT;
    return envPort ? `${envHost}:${envPort}` : envHost;
  }

  // Use window.location for browser context (same-origin or proxy)
  if (typeof window !== "undefined" && window.location?.host) {
    return window.location.host;
  }

  // SSR fallback - this is only used during server-side rendering
  // and will be replaced by actual host when hydrated in browser
  return "localhost:8000";
}

/**
 * Get WebSocket protocol based on current page protocol
 */
export function getWsProtocol(): "ws:" | "wss:" {
  if (typeof window !== "undefined" && window.location?.protocol === "https:") {
    return "wss:";
  }
  return "ws:";
}

/**
 * Build a WebSocket URL for an API endpoint
 *
 * IMPORTANT: The includeAuthToken parameter is REQUIRED to prevent authentication bugs.
 * Most WebSocket endpoints require authentication (require_auth=True in backend).
 * See: ws_router.py for backend auth requirements.
 *
 * @param endpoint - The API endpoint path (e.g., "/api/v1/ws/notifications")
 * @param params - Query parameters to append (use {} for no params)
 * @param includeAuthToken - Whether to include auth token in params (REQUIRED - no default)
 * @returns Full WebSocket URL
 *
 * @example
 * ```ts
 * // Authenticated endpoint (most endpoints)
 * buildWebSocketUrl("/api/v1/ws/notifications", {}, true)
 * // => "wss://app.example.com/api/v1/ws/notifications?token=eyJ..."
 *
 * // Unauthenticated endpoint (rare - e.g., /ws/mcp for anonymous connections)
 * buildWebSocketUrl("/api/v1/ws/mcp", {}, false)
 * // => "wss://app.example.com/api/v1/ws/mcp"
 *
 * // With parameters
 * buildWebSocketUrl("/api/v1/ws/agents", { session_id: "123" }, true)
 * // => "wss://app.example.com/api/v1/ws/agents?session_id=123&token=eyJ..."
 * ```
 */
export function buildWebSocketUrl(
  endpoint: string,
  params: Record<string, string>,
  includeAuthToken: boolean,
): string {
  const protocol = getWsProtocol();
  const host = getApiHost();

  // Build query parameters
  const urlParams = new URLSearchParams();

  // Always include protocol version for compatibility checking
  urlParams.set("v", PROTOCOL_VERSION);

  // Add auth token if requested
  if (includeAuthToken) {
    const token = getAuthToken();
    if (token) {
      urlParams.set("token", token);
    } else if (
      typeof process !== "undefined" &&
      process.env?.NODE_ENV === "development"
    ) {
      // Development warning: auth token was requested but none available
      // This often causes "user=None" errors in backend WebSocket handlers
      console.warn(
        `[WebSocket Auth Warning] buildWebSocketUrl called with includeAuthToken=true for ${endpoint}, ` +
          `but no auth token is available. This will likely cause authentication failures. ` +
          `Check if the user is logged in or if getAuthToken() is returning the expected value.`,
      );
    }
  }

  // Add additional params
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      urlParams.set(key, value);
    });
  }

  const queryString = urlParams.toString();
  return `${protocol}//${host}${endpoint}${queryString ? `?${queryString}` : ""}`;
}

/**
 * WebSocket endpoint paths (centralized for consistency)
 *
 * Use these constants with buildWebSocketUrl() to ensure consistent URL construction.
 * For dynamic endpoints (with path parameters), use buildWebSocketUrlWithPath().
 *
 * @example
 * ```ts
 * // Static endpoint (authenticated - most endpoints)
 * buildWebSocketUrl(WS_ENDPOINTS.NOTIFICATIONS, {}, true)
 *
 * // Static endpoint (anonymous - only /ws/mcp)
 * buildWebSocketUrl(WS_ENDPOINTS.MCP, {}, false)
 *
 * // Dynamic endpoint with path parameter
 * buildWebSocketUrlWithPath(WS_ENDPOINTS.WORKFLOW_EXECUTION, { workflowId: "123" }, {}, true)
 * ```
 */
export const WS_ENDPOINTS = {
  // Core WebSocket endpoints
  NOTIFICATIONS: "/api/v1/ws/notifications",
  AGENTS_REQUESTS: "/api/v1/ws/agents/requests",
  ALERTS: "/api/v1/ws/alerts",

  // MCP WebSocket endpoints
  MCP: "/api/v1/ws/mcp",
  MCP_AUTH: "/api/v1/ws/mcp/auth",
  MCP_AGGREGATED: "/api/v1/ws/mcp/aggregated",
  MCP_TASKS: "/api/v1/ws/mcp/tasks",
  MCP_SESSION: "/api/v1/ws/mcp/:sessionId",

  // AI/UX WebSocket endpoints
  AI_SUGGESTIONS: "/api/v1/ws/ai/suggestions",
  ORCHESTRATOR_STATUS: "/api/v1/ws/orchestrator/status",

  // Workflow WebSocket endpoints
  WORKFLOW_EXECUTION: "/api/v1/ws/workflows/:workflowId",

  // Monitoring WebSocket endpoints
  METRICS_HEART: "/api/v1/ws/metrics/heart",
  // METRICS_SESSION: "/api/v1/ws/metrics/session", // TODO: Add backend handler
  COST: "/api/v1/ws/usage/cost",
  BUDGET_ALERTS: "/api/v1/ws/budget/alerts",

  // LLM Streaming WebSocket endpoints
  // LLM_STREAMING: "/api/v1/ws/llm/streaming", // TODO: Add backend handler

  // Connections WebSocket endpoints
  CONNECTIONS_REALTIME: "/api/v1/ws/connections/realtime",
  CONNECTIONS_HEALTH: "/api/v1/ws/connections/health",

  // DevTools WebSocket endpoints
  DEVTOOLS: "/api/v1/ws/devtools",

  // Audit WebSocket endpoints
  AUDIT: "/api/v1/ws/audit",

  // Trace WebSocket endpoints (for debugging)
  TRACES: "/api/v1/ws/traces",
} as const;

export type WsEndpoint = (typeof WS_ENDPOINTS)[keyof typeof WS_ENDPOINTS];

/**
 * Build a WebSocket URL with path parameters replaced.
 *
 * Use this for endpoints with dynamic path segments (e.g., `:workflowId`).
 *
 * IMPORTANT: The includeAuthToken parameter is REQUIRED. See buildWebSocketUrl docs.
 *
 * @param endpoint - The endpoint template with :param placeholders
 * @param pathParams - Object mapping param names to values
 * @param queryParams - Query parameters (use {} for no params)
 * @param includeAuthToken - Whether to include auth token (REQUIRED)
 * @returns Full WebSocket URL with substituted path parameters
 *
 * @example
 * ```ts
 * buildWebSocketUrlWithPath(
 *   WS_ENDPOINTS.WORKFLOW_EXECUTION,
 *   { workflowId: "abc-123" },
 *   { debug: "true" },
 *   true
 * )
 * // => "wss://app.example.com/api/v1/ws/workflows/abc-123?debug=true&token=eyJ..."
 * ```
 */
export function buildWebSocketUrlWithPath(
  endpoint: string,
  pathParams: Record<string, string>,
  queryParams: Record<string, string>,
  includeAuthToken: boolean,
): string {
  // Replace path parameters (e.g., :workflowId -> actual value)
  let resolvedEndpoint = endpoint;
  for (const [key, value] of Object.entries(pathParams)) {
    resolvedEndpoint = resolvedEndpoint.replace(`:${key}`, value);
  }

  return buildWebSocketUrl(resolvedEndpoint, queryParams, includeAuthToken);
}
