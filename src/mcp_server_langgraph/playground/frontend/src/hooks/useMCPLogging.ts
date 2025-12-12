/**
 * useMCPLogging Hook
 *
 * Provides MCP logging level management.
 */

import { useState, useCallback } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { MCPLogLevel } from '../api/mcp-types';

// =============================================================================
// Types
// =============================================================================

export interface UseMCPLoggingResult {
  // Current log level
  currentLevel: MCPLogLevel;
  isLoading: boolean;
  error: string | null;

  // Operations
  setLogLevel: (level: MCPLogLevel) => Promise<void>;
}

// =============================================================================
// Log Levels (ordered by severity)
// =============================================================================

export const LOG_LEVELS: MCPLogLevel[] = [
  'debug',
  'info',
  'notice',
  'warning',
  'error',
  'critical',
  'alert',
  'emergency',
];

// =============================================================================
// Hook
// =============================================================================

export function useMCPLogging(): UseMCPLoggingResult {
  const { getClient, primaryServerId } = useMCPHost();

  const [currentLevel, setCurrentLevel] = useState<MCPLogLevel>('info');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setLogLevel = useCallback(
    async (level: MCPLogLevel): Promise<void> => {
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
        await client.setLogLevel(level);
        setCurrentLevel(level);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to set log level');
      } finally {
        setIsLoading(false);
      }
    },
    [getClient, primaryServerId]
  );

  return {
    currentLevel,
    isLoading,
    error,
    setLogLevel,
  };
}
