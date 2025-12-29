/**
 * useMCPResources Hook
 *
 * Provides access to MCP resources from all connected servers.
 */

import { useCallback } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { MCPResource, ResourceReadResult } from '../api/mcp-types';

export interface UseMCPResourcesResult {
  resources: MCPResource[];
  isLoading: boolean;
  readResource: (uri: string) => Promise<ResourceReadResult>;
  findResource: (uri: string) => MCPResource | undefined;
}

export function useMCPResources(): UseMCPResourcesResult {
  const { allResources, getClient, primaryServerId } = useMCPHost();

  const findResource = useCallback(
    (uri: string): MCPResource | undefined => {
      return allResources.find((r) => r.uri === uri);
    },
    [allResources]
  );

  const readResource = useCallback(
    async (uri: string): Promise<ResourceReadResult> => {
      if (!primaryServerId) {
        throw new Error('No primary server connected');
      }
      const client = getClient(primaryServerId);
      if (!client) {
        throw new Error('Primary server client not available');
      }
      return client.readResource(uri);
    },
    [getClient, primaryServerId]
  );

  return {
    resources: allResources,
    isLoading: false,
    readResource,
    findResource,
  };
}
