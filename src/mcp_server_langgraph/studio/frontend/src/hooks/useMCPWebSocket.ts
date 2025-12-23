/**
 * useMCPWebSocket Hook
 *
 * Custom hook for MCP 2025-11-25 protocol communication via WebSocket.
 * Features:
 * - JSON-RPC 2.0 message handling
 * - MCP protocol methods (initialize, tools/*, resources/*, prompts/*)
 * - Request/response tracking via message IDs
 * - Streaming notification handling
 * - Connection status and reconnection
 * - TypeScript type safety
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { useRealtimeSync, type ConnectionStatus } from "./useRealtimeSync";
import { useAppSelector } from "../store/hooks";
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";

// ============================================================================
// MCP Protocol Types
// ============================================================================

/**
 * JSON-RPC 2.0 Request
 */
export interface MCPRequest {
  jsonrpc: "2.0";
  id: number;
  method: string;
  params?: Record<string, unknown>;
}

/**
 * JSON-RPC 2.0 Response
 */
export interface MCPResponse {
  jsonrpc: "2.0";
  id: number | null;
  result?: unknown;
  error?: MCPError;
}

/**
 * JSON-RPC 2.0 Notification (no id)
 */
export interface MCPNotification {
  jsonrpc: "2.0";
  method: string;
  params?: Record<string, unknown>;
}

/**
 * MCP Error
 */
export interface MCPError {
  code: number;
  message: string;
  data?: unknown;
}

/**
 * Server info from initialize response
 */
export interface MCPServerInfo {
  name: string;
  version: string;
  description?: string;
}

/**
 * Server capabilities from initialize response
 */
export interface MCPCapabilities {
  tools?: { listChanged?: boolean };
  resources?: { listChanged?: boolean; subscribe?: boolean };
  prompts?: { listChanged?: boolean };
  elicitation?: Record<string, unknown>;
  sampling?: Record<string, unknown>;
  logging?: Record<string, unknown>;
}

/**
 * Tool definition
 */
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

/**
 * Resource definition
 */
export interface MCPResource {
  uri: string;
  name: string;
  mimeType?: string;
  description?: string;
}

/**
 * Prompt definition
 */
export interface MCPPrompt {
  name: string;
  description: string;
  arguments?: Array<{
    name: string;
    required?: boolean;
    description?: string;
  }>;
}

/**
 * Tool execution result content
 */
export interface MCPToolContent {
  type: "text" | "image" | "resource";
  text?: string;
  data?: string;
  mimeType?: string;
}

/**
 * Streaming chunk notification
 */
export interface MCPStreamingChunk {
  streamId: string;
  content: MCPToolContent;
}

// ============================================================================
// Hook Types
// ============================================================================

/**
 * Options for useMCPWebSocket hook
 */
export interface UseMCPWebSocketOptions {
  /** Custom WebSocket URL (default: constructs from window.location) */
  url?: string;
  /** Whether to use authenticated endpoint (default: true) */
  authenticated?: boolean;
  /** Whether to enable the connection (default: true) */
  enabled?: boolean;
  /** Client info for initialize handshake */
  clientInfo?: {
    name: string;
    version: string;
  };
  /** Callback when streaming chunk is received */
  onStreamingChunk?: (chunk: MCPStreamingChunk) => void;
  /** Callback when streaming starts */
  onStreamingStart?: (streamId: string, toolCallId: number) => void;
  /** Callback when streaming ends */
  onStreamingEnd?: (streamId: string) => void;
}

/**
 * Return type for useMCPWebSocket hook
 */
export interface UseMCPWebSocketReturn {
  /** Current connection status */
  status: ConnectionStatus;
  /** Whether MCP initialize handshake is complete */
  isInitialized: boolean;
  /** Server info from initialize response */
  serverInfo: MCPServerInfo | null;
  /** Server capabilities from initialize response */
  capabilities: MCPCapabilities | null;
  /** Available tools */
  tools: MCPTool[];
  /** Available resources */
  resources: MCPResource[];
  /** Available prompts */
  prompts: MCPPrompt[];
  /** Error message if any */
  error: string | null;
  /** Initialize the MCP connection */
  initialize: () => Promise<void>;
  /** List available tools */
  listTools: () => Promise<MCPTool[]>;
  /** List available resources */
  listResources: () => Promise<MCPResource[]>;
  /** List available prompts */
  listPrompts: () => Promise<MCPPrompt[]>;
  /** Call a tool */
  callTool: (
    name: string,
    args: Record<string, unknown>,
  ) => Promise<MCPToolContent[]>;
  /** Read a resource */
  readResource: (
    uri: string,
  ) => Promise<Array<{ uri: string; mimeType?: string; text?: string }>>;
  /** Get a prompt */
  getPrompt: (
    name: string,
    args?: Record<string, unknown>,
  ) => Promise<Array<{ role: string; content: unknown }>>;
  /** Disconnect */
  disconnect: () => void;
  /** Reconnect */
  reconnect: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get default MCP WebSocket URL
 */
function getDefaultMCPWebSocketUrl(
  authenticated: boolean,
  token?: string,
): string {
  if (typeof window === "undefined") {
    return authenticated
      ? "ws://localhost:8000/api/v1/ws/mcp/auth"
      : "ws://localhost:8000/api/v1/ws/mcp";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;

  // Build URL with endpoint and optional token
  const endpoint = authenticated ? "/api/v1/ws/mcp/auth" : "/api/v1/ws/mcp";
  const tokenParam =
    authenticated && token ? `?token=${encodeURIComponent(token)}` : "";

  return `${protocol}//${host}${endpoint}${tokenParam}`;
}

/**
 * Check if a message is an MCP response
 */
function isMCPResponse(data: unknown): data is MCPResponse {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  return msg.jsonrpc === "2.0" && ("result" in msg || "error" in msg);
}

/**
 * Check if a message is an MCP notification
 */
function isMCPNotification(data: unknown): data is MCPNotification {
  if (typeof data !== "object" || data === null) return false;
  const msg = data as Record<string, unknown>;
  return (
    msg.jsonrpc === "2.0" && "method" in msg && !("id" in msg && msg.id != null)
  );
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for MCP 2025-11-25 protocol communication
 *
 * @example
 * ```tsx
 * function MCPClient() {
 *   const {
 *     status,
 *     isInitialized,
 *     tools,
 *     callTool,
 *   } = useMCPWebSocket();
 *
 *   const handleQuery = async (query: string) => {
 *     const result = await callTool('langgraph-run', { query });
 *     console.log('Result:', result);
 *   };
 *
 *   return (
 *     <div>
 *       <span>MCP: {status} {isInitialized ? '(ready)' : '(initializing)'}</span>
 *       <div>Available tools: {tools.map(t => t.name).join(', ')}</div>
 *     </div>
 *   );
 * }
 * ```
 */
export function useMCPWebSocket(
  options: UseMCPWebSocketOptions = {},
): UseMCPWebSocketReturn {
  const {
    url,
    authenticated = true,
    enabled = true,
    clientInfo = { name: "studio-frontend", version: "1.0.0" },
    onStreamingChunk,
    onStreamingStart,
    onStreamingEnd,
  } = options;

  const isAuthenticated = useAppSelector(selectIsAuthenticated);

  // State
  const [isInitialized, setIsInitialized] = useState(false);
  const [serverInfo, setServerInfo] = useState<MCPServerInfo | null>(null);
  const [capabilities, setCapabilities] = useState<MCPCapabilities | null>(
    null,
  );
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [resources, setResources] = useState<MCPResource[]>([]);
  const [prompts, setPrompts] = useState<MCPPrompt[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const messageIdRef = useRef(0);
  const pendingRequestsRef = useRef<
    Map<
      number,
      {
        resolve: (value: unknown) => void;
        reject: (error: Error) => void;
      }
    >
  >(new Map());
  const callbacksRef = useRef({
    onStreamingChunk,
    onStreamingStart,
    onStreamingEnd,
  });

  // Keep callbacks ref updated
  useEffect(() => {
    callbacksRef.current = {
      onStreamingChunk,
      onStreamingStart,
      onStreamingEnd,
    };
  }, [onStreamingChunk, onStreamingStart, onStreamingEnd]);

  // Get auth token when authenticated - makes dependency explicit for React
  // Convert null to undefined for type compatibility
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL - recalculates when auth state changes via authToken
  const wsUrl = useMemo(
    () => url ?? getDefaultMCPWebSocketUrl(authenticated, authToken),
    [url, authenticated, authToken],
  );

  // Track effective enabled state - only connect when authenticated (for authenticated endpoints)
  // WebSocket requires valid auth token, so we only connect when authenticated
  const effectiveEnabled = authenticated ? enabled && isAuthenticated : enabled;

  // Track previous effective enabled state to detect changes
  const prevEnabledRef = useRef(effectiveEnabled);

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    if (isMCPResponse(data)) {
      // Handle response to a request
      const id = data.id;
      if (id !== null && pendingRequestsRef.current.has(id)) {
        const { resolve, reject } = pendingRequestsRef.current.get(id)!;
        pendingRequestsRef.current.delete(id);

        if (data.error) {
          reject(new Error(`${data.error.code}: ${data.error.message}`));
        } else {
          resolve(data.result);
        }
      }
    } else if (isMCPNotification(data)) {
      // Handle notifications (streaming, etc.)
      const method = data.method;
      const params = data.params ?? {};

      if (method === "$/streaming/start") {
        callbacksRef.current.onStreamingStart?.(
          params.streamId as string,
          params.toolCallId as number,
        );
      } else if (method === "$/streaming/chunk") {
        callbacksRef.current.onStreamingChunk?.({
          streamId: params.streamId as string,
          content: params.content as MCPToolContent,
        });
      } else if (method === "$/streaming/end") {
        callbacksRef.current.onStreamingEnd?.(params.streamId as string);
      }
    }
  }, []);

  // Use the underlying realtimeSync hook
  // Enable exponential backoff for better reconnection behavior
  const {
    status: realtimeStatus,
    send,
    disconnect,
    reconnect,
  } = useRealtimeSync({
    url: wsUrl,
    exponentialBackoff: true,
    reconnectInterval: 1000, // Start with 1 second
    maxDelayMs: 30000, // Max 30 seconds between attempts
    maxReconnectAttempts: 10, // Try up to 10 times
    onMessage: handleMessage,
    onError: (err) => setError(err.message),
    onConnect: () => setError(null),
    onDisconnect: () => {
      setIsInitialized(false);
      // Reject all pending requests
      pendingRequestsRef.current.forEach(({ reject }) => {
        reject(new Error("WebSocket disconnected"));
      });
      pendingRequestsRef.current.clear();
    },
  });

  // Track if enabled - if not authenticated or explicitly disabled, override status
  // WebSocket requires valid auth token, so we only connect when authenticated
  const status: ConnectionStatus = effectiveEnabled
    ? realtimeStatus
    : "disconnected";

  // Disconnect when disabled or unauthenticated, reconnect when transitioning to enabled+authenticated
  useEffect(() => {
    const wasDisabled = !prevEnabledRef.current;
    const isNowEnabled = effectiveEnabled;

    if (!effectiveEnabled) {
      disconnect();
    } else if (wasDisabled && isNowEnabled) {
      // Only reconnect when transitioning from disabled to enabled+authenticated
      // This handles both explicit enable changes and authentication state changes
      reconnect();
    }

    prevEnabledRef.current = effectiveEnabled;
  }, [effectiveEnabled, disconnect, reconnect]);

  // Send an MCP request and wait for response
  const sendRequest = useCallback(
    async (
      method: string,
      params?: Record<string, unknown>,
    ): Promise<unknown> => {
      if (status !== "connected") {
        throw new Error("Not connected to MCP server");
      }

      const id = ++messageIdRef.current;
      const request: MCPRequest = {
        jsonrpc: "2.0",
        id,
        method,
        params,
      };

      return new Promise((resolve, reject) => {
        pendingRequestsRef.current.set(id, { resolve, reject });

        // Set timeout for request
        setTimeout(() => {
          if (pendingRequestsRef.current.has(id)) {
            pendingRequestsRef.current.delete(id);
            reject(new Error(`Request timeout for ${method}`));
          }
        }, 30000);

        send(request);
      });
    },
    [status, send],
  );

  // Initialize MCP connection
  const initialize = useCallback(async () => {
    try {
      const result = (await sendRequest("initialize", {
        protocolVersion: "2025-11-25",
        capabilities: {},
        clientInfo,
      })) as {
        protocolVersion: string;
        serverInfo: MCPServerInfo;
        capabilities: MCPCapabilities;
      };

      setServerInfo(result.serverInfo);
      setCapabilities(result.capabilities);
      setIsInitialized(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Initialize failed");
      throw err;
    }
  }, [sendRequest, clientInfo]);

  // List tools
  const listTools = useCallback(async (): Promise<MCPTool[]> => {
    const result = (await sendRequest("tools/list", {})) as {
      tools: MCPTool[];
    };
    setTools(result.tools);
    return result.tools;
  }, [sendRequest]);

  // List resources
  const listResources = useCallback(async (): Promise<MCPResource[]> => {
    const result = (await sendRequest("resources/list", {})) as {
      resources: MCPResource[];
    };
    setResources(result.resources);
    return result.resources;
  }, [sendRequest]);

  // List prompts
  const listPrompts = useCallback(async (): Promise<MCPPrompt[]> => {
    const result = (await sendRequest("prompts/list", {})) as {
      prompts: MCPPrompt[];
    };
    setPrompts(result.prompts);
    return result.prompts;
  }, [sendRequest]);

  // Call a tool
  const callTool = useCallback(
    async (
      name: string,
      args: Record<string, unknown>,
    ): Promise<MCPToolContent[]> => {
      const result = (await sendRequest("tools/call", {
        name,
        arguments: args,
      })) as { content: MCPToolContent[]; isError?: boolean };

      if (result.isError) {
        throw new Error(result.content[0]?.text ?? "Tool execution failed");
      }

      return result.content;
    },
    [sendRequest],
  );

  // Read a resource
  const readResource = useCallback(
    async (
      uri: string,
    ): Promise<Array<{ uri: string; mimeType?: string; text?: string }>> => {
      const result = (await sendRequest("resources/read", { uri })) as {
        contents: Array<{ uri: string; mimeType?: string; text?: string }>;
      };
      return result.contents;
    },
    [sendRequest],
  );

  // Get a prompt
  const getPrompt = useCallback(
    async (
      name: string,
      args?: Record<string, unknown>,
    ): Promise<Array<{ role: string; content: unknown }>> => {
      const result = (await sendRequest("prompts/get", {
        name,
        arguments: args ?? {},
      })) as { messages: Array<{ role: string; content: unknown }> };
      return result.messages;
    },
    [sendRequest],
  );

  // Auto-initialize when connected
  useEffect(() => {
    if (status === "connected" && !isInitialized && effectiveEnabled) {
      initialize()
        .then(() => {
          // Also fetch tools, resources, prompts
          listTools().catch(() => {});
          listResources().catch(() => {});
          listPrompts().catch(() => {});
        })
        .catch(() => {});
    }
  }, [
    status,
    isInitialized,
    effectiveEnabled,
    initialize,
    listTools,
    listResources,
    listPrompts,
  ]);

  return {
    status,
    isInitialized,
    serverInfo,
    capabilities,
    tools,
    resources,
    prompts,
    error,
    initialize,
    listTools,
    listResources,
    listPrompts,
    callTool,
    readResource,
    getPrompt,
    disconnect,
    reconnect,
  };
}

export default useMCPWebSocket;
