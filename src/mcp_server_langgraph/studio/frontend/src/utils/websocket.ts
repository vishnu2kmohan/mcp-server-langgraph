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
 * @param endpoint - The API endpoint path (e.g., "/api/v1/ws/notifications")
 * @param params - Optional query parameters to append
 * @param includeAuthToken - Whether to include auth token in params (default: false)
 * @returns Full WebSocket URL
 *
 * @example
 * ```ts
 * // Basic usage
 * buildWebSocketUrl("/api/v1/ws/notifications")
 * // => "ws://localhost:5175/api/v1/ws/notifications" (dev)
 * // => "wss://app.example.com/api/v1/ws/notifications" (prod)
 *
 * // With parameters
 * buildWebSocketUrl("/api/v1/ws/agents", { session_id: "123" })
 * // => "ws://localhost:5175/api/v1/ws/agents?session_id=123"
 *
 * // With auth token
 * buildWebSocketUrl("/api/v1/ws/mcp/auth", {}, true)
 * // => "wss://app.example.com/api/v1/ws/mcp/auth?token=eyJ..."
 * ```
 */
export function buildWebSocketUrl(
  endpoint: string,
  params?: Record<string, string>,
  includeAuthToken = false,
): string {
  const protocol = getWsProtocol();
  const host = getApiHost();

  // Build query parameters
  const urlParams = new URLSearchParams();

  // Add auth token if requested
  if (includeAuthToken) {
    const token = getAuthToken();
    if (token) {
      urlParams.set("token", token);
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
 */
export const WS_ENDPOINTS = {
  NOTIFICATIONS: "/api/v1/ws/notifications",
  AGENTS_REQUESTS: "/api/v1/ws/agents/requests",
  ALERTS: "/api/v1/ws/alerts",
  MCP: "/api/v1/ws/mcp",
  MCP_AUTH: "/api/v1/ws/mcp/auth",
  MCP_AGGREGATED: "/api/v1/ws/mcp/aggregated",
  METRICS_HEART: "/api/v1/ws/metrics/heart",
  AI_SUGGESTIONS: "/api/v1/ws/ai/suggestions",
  WORKFLOWS: "/api/v1/ws/workflows",
  CONNECTIONS: "/api/v1/ws/connections",
  AUDIT: "/api/v1/ws/audit",
  COST: "/api/v1/ws/usage/cost",
} as const;

export type WsEndpoint = (typeof WS_ENDPOINTS)[keyof typeof WS_ENDPOINTS];
