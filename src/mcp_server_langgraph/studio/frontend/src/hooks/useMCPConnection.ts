/**
 * useMCPConnection Hook
 *
 * MCP connection hook with WebSocket and REST fallback.
 * Strategy:
 * 1. Attempt WebSocket connection to /api/v1/mcp/ws
 * 2. If WebSocket fails or disconnects, fall back to REST
 * 3. REST uses /api/v1/mcp/tools for tools list
 * 4. Periodically attempt WebSocket reconnection
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { useAppDispatch } from "../store/hooks";
import { logout } from "../store/slices/authSlice";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";
import {
  WS_CLOSE_TOKEN_EXPIRED,
  ensureValidTokenForWebSocket,
} from "../utils/websocketAuth";

export interface Tool {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
}

export type ConnectionMode = "websocket" | "rest" | "disconnected";

export interface MCPConnectionOptions {
  autoConnect?: boolean;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  sessionId?: string;
}

export interface MCPConnectionState {
  isConnected: boolean;
  connectionMode: ConnectionMode;
  tools: Tool[];
  error: string | null;
  isReconnecting: boolean;
  reconnectAttempts: number;
  connect: () => void;
  disconnect: () => void;
  callTool: (name: string, args: Record<string, unknown>) => Promise<unknown>;
}

export function useMCPConnection(
  options: MCPConnectionOptions = {},
): MCPConnectionState {
  const navigate = useNavigate();
  // Redux dispatch for token expiration handling
  const dispatch = useAppDispatch();
  const {
    autoConnect = false,
    autoReconnect = false,
    maxReconnectAttempts = 5,
    sessionId,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionMode, setConnectionMode] =
    useState<ConnectionMode>("disconnected");
  const [tools, setTools] = useState<Tool[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const messageIdRef = useRef(0);
  const pendingRequestsRef = useRef<
    Map<
      number,
      { resolve: (value: unknown) => void; reject: (error: Error) => void }
    >
  >(new Map());
  const wasConnectedRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const manualDisconnectRef = useRef(false);
  const inReconnectSequenceRef = useRef(false);
  const isMountedRef = useRef(true);

  const getNextMessageId = useCallback(() => {
    messageIdRef.current += 1;
    return messageIdRef.current;
  }, []);

  // Handle auth failure - redirect to login
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  const sendRequest = useCallback(
    (method: string, params?: Record<string, unknown>): Promise<unknown> => {
      return new Promise((resolve, reject) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          reject(new Error("WebSocket not connected"));
          return;
        }

        const id = getNextMessageId();
        const message = {
          jsonrpc: "2.0",
          id,
          method,
          params,
        };

        pendingRequestsRef.current.set(id, { resolve, reject });
        wsRef.current.send(JSON.stringify(message));
      });
    },
    [getNextMessageId],
  );

  const fetchToolsViaRest = useCallback(async () => {
    try {
      const response = await authenticatedFetch("/api/v1/mcp/tools", {
        method: "GET",
        onAuthFailure: handleAuthFailure,
      });
      if (response.ok) {
        const data = await response.json();
        setTools(data.tools || []);
      }
    } catch {
      throw new Error("Failed to fetch tools via REST");
    }
  }, [handleAuthFailure]);

  const fallbackToRest = useCallback(async () => {
    try {
      await fetchToolsViaRest();
      // Only update state if still mounted
      if (!isMountedRef.current) return;
      setConnectionMode("rest");
      setIsConnected(true);
      setError(null);
    } catch (err) {
      // Only update state if still mounted
      if (!isMountedRef.current) return;
      setConnectionMode("disconnected");
      setIsConnected(false);
      setError(err instanceof Error ? err.message : "Connection failed");
    }
  }, [fetchToolsViaRest]);

  // Cancel any pending reconnection
  const cancelReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    inReconnectSequenceRef.current = false;
    setIsReconnecting(false);
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    setError(null);
    manualDisconnectRef.current = false;

    // Build WebSocket URL
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    let wsUrl = `${protocol}//${window.location.host}/api/v1/ws/mcp`;
    if (sessionId) {
      wsUrl += `?session=${sessionId}`;
    }

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        wasConnectedRef.current = true;
        // Only update state if still mounted
        if (!isMountedRef.current) return;
        setIsConnected(true);
        setConnectionMode("websocket");
        setError(null);
        // Reset reconnection state on successful connection
        inReconnectSequenceRef.current = false;
        setIsReconnecting(false);
        setReconnectAttempts(0);

        // Request tools list
        sendRequest("tools/list")
          .then((result) => {
            if (!isMountedRef.current) return;
            const toolsResult = result as { tools: Tool[] };
            setTools(toolsResult.tools || []);
          })
          .catch(() => {
            // Ignore errors for now
          });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle response to our request
          if (data.id && pendingRequestsRef.current.has(data.id)) {
            const { resolve, reject } = pendingRequestsRef.current.get(
              data.id,
            )!;
            pendingRequestsRef.current.delete(data.id);

            if (data.error) {
              reject(new Error(data.error.message || "Unknown error"));
            } else {
              resolve(data.result);
            }
          }
        } catch {
          // Ignore parse errors
        }
      };

      ws.onerror = () => {
        // WebSocket error - will trigger onclose
      };

      ws.onclose = async (event) => {
        wsRef.current = null;
        const wasConnected = wasConnectedRef.current;
        wasConnectedRef.current = false;

        // Only update state if still mounted
        if (!isMountedRef.current) return;

        // Handle token expiration close code (4010)
        if (event.code === WS_CLOSE_TOKEN_EXPIRED) {
          const refreshed = await ensureValidTokenForWebSocket();
          if (refreshed) {
            // Token refreshed successfully - reconnect
            inReconnectSequenceRef.current = true;
            setIsReconnecting(true);
            reconnectTimerRef.current = setTimeout(() => {
              if (isMountedRef.current) connect();
            }, 100);
          } else {
            // Refresh failed - logout
            dispatch(logout());
          }
          return;
        }

        // If we were never properly connected (error during handshake)
        if (!wasConnected) {
          // If we're in a reconnection sequence, continue trying
          // Otherwise, fall back to REST
          if (
            autoReconnect &&
            !manualDisconnectRef.current &&
            inReconnectSequenceRef.current
          ) {
            // This is a failed reconnection attempt - increment counter
            setReconnectAttempts((prev) => {
              const newAttempts = prev + 1;
              if (newAttempts < maxReconnectAttempts) {
                // Schedule next attempt with exponential backoff
                if (isMountedRef.current) setIsReconnecting(true);
                const delay = newAttempts * 1000;
                reconnectTimerRef.current = setTimeout(() => {
                  if (isMountedRef.current) connect();
                }, delay);
              } else {
                // Max attempts reached
                inReconnectSequenceRef.current = false;
                if (isMountedRef.current) setIsReconnecting(false);
              }
              return newAttempts;
            });
          } else {
            // Not in reconnection sequence, fall back to REST
            fallbackToRest();
          }
        } else {
          // Connection was established but then lost
          setIsConnected(false);
          setConnectionMode("disconnected");

          // Schedule reconnection if enabled and not manually disconnected
          if (autoReconnect && !manualDisconnectRef.current) {
            // Start reconnection sequence
            inReconnectSequenceRef.current = true;
            setIsReconnecting(true);
            setReconnectAttempts(0);
            // First attempt after 1 second
            reconnectTimerRef.current = setTimeout(() => {
              if (isMountedRef.current) connect();
            }, 1000);
          }
        }
      };
    } catch {
      fallbackToRest();
    }
  }, [
    sessionId,
    sendRequest,
    fallbackToRest,
    autoReconnect,
    maxReconnectAttempts,
    dispatch,
  ]);

  const disconnect = useCallback(() => {
    manualDisconnectRef.current = true;
    cancelReconnect();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionMode("disconnected");
    setTools([]);
    setReconnectAttempts(0);
    pendingRequestsRef.current.clear();
  }, [cancelReconnect]);

  const callTool = useCallback(
    async (name: string, args: Record<string, unknown>): Promise<unknown> => {
      if (
        connectionMode === "websocket" &&
        wsRef.current?.readyState === WebSocket.OPEN
      ) {
        return sendRequest("tools/call", { name, arguments: args });
      }

      // REST fallback
      const response = await authenticatedFetch("/api/v1/mcp/tools/call", {
        method: "POST",
        body: JSON.stringify({ name, arguments: args }),
        onAuthFailure: handleAuthFailure,
      });

      if (!response.ok) {
        throw new Error("Tool call failed");
      }

      return response.json();
    },
    [connectionMode, sendRequest, handleAuthFailure],
  );

  // Track mounted state for async callback safety
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      cancelReconnect();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [autoConnect]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isConnected,
    connectionMode,
    tools,
    error,
    isReconnecting,
    reconnectAttempts,
    connect,
    disconnect,
    callTool,
  };
}
