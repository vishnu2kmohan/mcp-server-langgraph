/**
 * useMCPConnection Hook
 *
 * Manages a single MCP server connection using StreamableHTTP transport.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { createMCPClient, MCPClient } from '../api/mcp-client';
import type {
  MCPConnectionStatus,
  MCPServerCapabilities,
  MCPServerInfo,
} from '../api/mcp-types';

// =============================================================================
// Types
// =============================================================================

export interface UseMCPConnectionOptions {
  url: string;
  authToken?: string;
  autoConnect?: boolean;
  timeout?: number;
}

export interface UseMCPConnectionResult {
  // Connection state
  status: MCPConnectionStatus;
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  serverInfo: MCPServerInfo | null;
  serverCapabilities: MCPServerCapabilities | null;

  // Actions
  connect: () => Promise<void>;
  disconnect: () => void;
  setAuthToken: (token: string | null) => void;

  // Client access
  client: MCPClient;
}

// =============================================================================
// Hook
// =============================================================================

export function useMCPConnection(
  options: UseMCPConnectionOptions
): UseMCPConnectionResult {
  const { url, authToken, autoConnect = false, timeout } = options;

  const clientRef = useRef<MCPClient>(
    createMCPClient({ baseUrl: url, authToken, timeout })
  );

  const [status, setStatus] = useState<MCPConnectionStatus>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const [serverInfo, setServerInfo] = useState<MCPServerInfo | null>(null);
  const [serverCapabilities, setServerCapabilities] =
    useState<MCPServerCapabilities | null>(null);

  const connect = useCallback(async () => {
    setStatus('connecting');
    setError(null);

    try {
      const result = await clientRef.current.initialize();
      setServerInfo(result.serverInfo);
      setServerCapabilities(result.capabilities);
      setStatus('connected');
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err : new Error('Connection failed'));
      throw err;
    }
  }, []);

  const disconnect = useCallback(() => {
    clientRef.current.disconnect();
    setStatus('disconnected');
    setServerInfo(null);
    setServerCapabilities(null);
  }, []);

  const setAuthToken = useCallback((token: string | null) => {
    clientRef.current.setAuthToken(token);
  }, []);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect().catch(() => {
        // Error is already captured in state
      });
    }

    return () => {
      clientRef.current.disconnect();
    };
  }, [autoConnect, connect]);

  return {
    status,
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    error,
    serverInfo,
    serverCapabilities,
    connect,
    disconnect,
    setAuthToken,
    client: clientRef.current,
  };
}
