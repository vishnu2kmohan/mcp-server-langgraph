/**
 * useMCPElicitation Hook
 *
 * Handles MCP elicitation requests from servers (2025-11-25 spec).
 * Provides UI controls for accept/decline/cancel actions.
 */

import { useCallback, useMemo } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { PendingElicitation } from '../api/mcp-types';

export interface UseMCPElicitationResult {
  // Current elicitation (first in queue)
  currentElicitation: PendingElicitation | null;
  pendingCount: number;
  hasPending: boolean;

  // Actions per 2025-11-25 spec
  accept: (content: Record<string, unknown>) => Promise<void>;
  decline: () => Promise<void>;
  cancel: () => Promise<void>;
}

export function useMCPElicitation(): UseMCPElicitationResult {
  const { pendingElicitations, respondToElicitation } = useMCPHost();

  const currentElicitation = useMemo(() => {
    return pendingElicitations.length > 0 ? pendingElicitations[0] : null;
  }, [pendingElicitations]);

  const accept = useCallback(
    async (content: Record<string, unknown>): Promise<void> => {
      if (!currentElicitation) return;
      respondToElicitation(currentElicitation.id, 'accept', content);
    },
    [currentElicitation, respondToElicitation]
  );

  const decline = useCallback(async (): Promise<void> => {
    if (!currentElicitation) return;
    respondToElicitation(currentElicitation.id, 'decline', undefined);
  }, [currentElicitation, respondToElicitation]);

  const cancel = useCallback(async (): Promise<void> => {
    if (!currentElicitation) return;
    respondToElicitation(currentElicitation.id, 'cancel', undefined);
  }, [currentElicitation, respondToElicitation]);

  return {
    currentElicitation,
    pendingCount: pendingElicitations.length,
    hasPending: pendingElicitations.length > 0,
    accept,
    decline,
    cancel,
  };
}
