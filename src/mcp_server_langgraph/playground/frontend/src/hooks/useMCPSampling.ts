/**
 * useMCPSampling Hook
 *
 * Handles MCP sampling requests from servers (server→client LLM requests).
 */

import { useCallback, useMemo } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { PendingSamplingRequest } from '../api/mcp-types';

export interface UseMCPSamplingResult {
  // Current sampling request (first in queue)
  currentRequest: PendingSamplingRequest | null;
  pendingCount: number;
  hasPending: boolean;

  // Actions
  approve: (result: unknown) => Promise<void>;
  reject: (reason?: string) => Promise<void>;
}

export function useMCPSampling(): UseMCPSamplingResult {
  const { pendingSamplingRequests, respondToSampling } = useMCPHost();

  const currentRequest = useMemo(() => {
    return pendingSamplingRequests.length > 0 ? pendingSamplingRequests[0] : null;
  }, [pendingSamplingRequests]);

  const approve = useCallback(
    async (result: unknown): Promise<void> => {
      if (!currentRequest) return;
      respondToSampling(currentRequest.id, true, result);
    },
    [currentRequest, respondToSampling]
  );

  const reject = useCallback(
    async (reason?: string): Promise<void> => {
      if (!currentRequest) return;
      respondToSampling(currentRequest.id, false, reason);
    },
    [currentRequest, respondToSampling]
  );

  return {
    currentRequest,
    pendingCount: pendingSamplingRequests.length,
    hasPending: pendingSamplingRequests.length > 0,
    approve,
    reject,
  };
}
