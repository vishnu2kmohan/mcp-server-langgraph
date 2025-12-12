/**
 * useMCPCompletion Hook
 *
 * Provides MCP completion/autocomplete functionality for prompts and resources.
 */

import { useState, useCallback } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';

// =============================================================================
// Types
// =============================================================================

export interface CompletionRef {
  type: 'ref/prompt' | 'ref/resource';
  name?: string;  // For prompts
  uri?: string;   // For resources
}

export interface CompletionArgument {
  name: string;
  value: string;
}

export interface CompletionResult {
  values: string[];
  total?: number;
  hasMore?: boolean;
}

export interface UseMCPCompletionResult {
  // State
  completions: string[];
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;

  // Operations
  complete: (ref: CompletionRef, argument: CompletionArgument) => Promise<CompletionResult>;
  clearCompletions: () => void;
}

// =============================================================================
// Hook
// =============================================================================

export function useMCPCompletion(): UseMCPCompletionResult {
  const { getClient, primaryServerId } = useMCPHost();

  const [completions, setCompletions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const complete = useCallback(
    async (ref: CompletionRef, argument: CompletionArgument): Promise<CompletionResult> => {
      if (!primaryServerId) {
        throw new Error('No primary server connected');
      }

      const client = getClient(primaryServerId);
      if (!client) {
        throw new Error('Primary server client not available');
      }

      setIsLoading(true);
      setError(null);

      try {
        const result = await client.complete(ref, argument);
        setCompletions(result.completion.values);
        setHasMore(result.completion.hasMore ?? false);
        return result.completion;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Completion failed';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [getClient, primaryServerId]
  );

  const clearCompletions = useCallback(() => {
    setCompletions([]);
    setError(null);
    setHasMore(false);
  }, []);

  return {
    completions,
    isLoading,
    error,
    hasMore,
    complete,
    clearCompletions,
  };
}
