/**
 * useMCPRoots Hook
 *
 * Provides access to MCP roots (filesystem roots the server has access to).
 */

import { useState, useCallback, useEffect } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { MCPRoot } from '../api/mcp-types';

// =============================================================================
// Types
// =============================================================================

export interface UseMCPRootsOptions {
  /** Automatically load roots on mount */
  autoLoad?: boolean;
}

export interface UseMCPRootsResult {
  // Root list
  roots: MCPRoot[];
  isLoading: boolean;
  error: string | null;

  // Operations
  refreshRoots: () => Promise<void>;
}

// =============================================================================
// Hook
// =============================================================================

export function useMCPRoots(options: UseMCPRootsOptions = {}): UseMCPRootsResult {
  const { autoLoad = true } = options;
  const { getClient, primaryServerId } = useMCPHost();

  const [roots, setRoots] = useState<MCPRoot[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshRoots = useCallback(async () => {
    if (!primaryServerId) {
      setError('No primary server connected');
      return;
    }

    const client = getClient(primaryServerId);
    if (!client) {
      setError('Primary server client not available');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const rootList = await client.listRoots();
      setRoots(rootList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to list roots');
    } finally {
      setIsLoading(false);
    }
  }, [getClient, primaryServerId]);

  // Auto-load on mount if enabled
  useEffect(() => {
    if (autoLoad && primaryServerId) {
      refreshRoots();
    }
  }, [autoLoad, primaryServerId, refreshRoots]);

  return {
    roots,
    isLoading,
    error,
    refreshRoots,
  };
}
