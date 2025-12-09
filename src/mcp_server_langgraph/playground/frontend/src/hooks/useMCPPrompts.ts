/**
 * useMCPPrompts Hook
 *
 * Provides access to MCP prompts from all connected servers.
 */

import { useCallback } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { MCPPrompt, PromptGetResult } from '../api/mcp-types';

export interface UseMCPPromptsResult {
  prompts: MCPPrompt[];
  isLoading: boolean;
  getPrompt: (name: string, args?: Record<string, string>) => Promise<PromptGetResult>;
  findPrompt: (name: string) => MCPPrompt | undefined;
}

export function useMCPPrompts(): UseMCPPromptsResult {
  const { allPrompts, getClient, primaryServerId } = useMCPHost();

  const findPrompt = useCallback(
    (name: string): MCPPrompt | undefined => {
      return allPrompts.find((p) => p.name === name);
    },
    [allPrompts]
  );

  const getPrompt = useCallback(
    async (name: string, args?: Record<string, string>): Promise<PromptGetResult> => {
      if (!primaryServerId) {
        throw new Error('No primary server connected');
      }
      const client = getClient(primaryServerId);
      if (!client) {
        throw new Error('Primary server client not available');
      }
      return client.getPrompt(name, args);
    },
    [getClient, primaryServerId]
  );

  return {
    prompts: allPrompts,
    isLoading: false,
    getPrompt,
    findPrompt,
  };
}
