/**
 * useMCPTools Hook
 *
 * Provides access to MCP tools from all connected servers.
 * Includes helpers for common tool operations.
 */

import { useCallback, useMemo } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { MCPTool, MCPToolResult, MCPStreamChunk, MCPRequestOptions } from '../api/mcp-types';

// =============================================================================
// Types
// =============================================================================

export interface UseMCPToolsResult {
  // Available tools
  tools: MCPTool[];
  isLoading: boolean;

  // Tool operations
  callTool: (name: string, args?: Record<string, unknown>) => Promise<MCPToolResult>;
  streamToolCall: (
    name: string,
    args: Record<string, unknown>,
    onChunk: (chunk: MCPStreamChunk) => void,
    options?: MCPRequestOptions
  ) => Promise<void>;

  // Tool lookup
  findTool: (name: string) => MCPTool | undefined;

  // Convenience helpers for common tools
  agentChat: (
    message: string,
    onChunk: (content: string) => void,
    conversationId?: string
  ) => Promise<void>;
  executePython: (code: string) => Promise<MCPToolResult>;
  conversationSearch: (query: string) => Promise<MCPToolResult>;
  conversationGet: (id: string) => Promise<MCPToolResult>;
  searchTools: (query: string) => Promise<MCPToolResult>;
}

// =============================================================================
// Hook
// =============================================================================

export function useMCPTools(): UseMCPToolsResult {
  const { allTools, getClient, primaryServerId } = useMCPHost();

  const findTool = useCallback(
    (name: string): MCPTool | undefined => {
      return allTools.find((t) => t.name === name);
    },
    [allTools]
  );

  const callTool = useCallback(
    async (name: string, args?: Record<string, unknown>): Promise<MCPToolResult> => {
      if (!primaryServerId) {
        throw new Error('No primary server connected');
      }

      const client = getClient(primaryServerId);
      if (!client) {
        throw new Error('Primary server client not available');
      }

      return client.callTool(name, args);
    },
    [getClient, primaryServerId]
  );

  const streamToolCall = useCallback(
    async (
      name: string,
      args: Record<string, unknown>,
      onChunk: (chunk: MCPStreamChunk) => void,
      options?: MCPRequestOptions
    ): Promise<void> => {
      if (!primaryServerId) {
        throw new Error('No primary server connected');
      }

      const client = getClient(primaryServerId);
      if (!client) {
        throw new Error('Primary server client not available');
      }

      return client.streamToolCall(name, args, onChunk, options);
    },
    [getClient, primaryServerId]
  );

  // Helper: Chat with agent
  const agentChat = useCallback(
    async (
      message: string,
      onChunk: (content: string) => void,
      conversationId?: string
    ): Promise<void> => {
      await streamToolCall(
        'agent_chat',
        { message, conversation_id: conversationId },
        (chunk) => {
          if (chunk.type === 'chunk' && chunk.content) {
            onChunk(chunk.content);
          }
        }
      );
    },
    [streamToolCall]
  );

  // Helper: Execute Python code
  const executePython = useCallback(
    async (code: string): Promise<MCPToolResult> => {
      return callTool('execute_python', { code });
    },
    [callTool]
  );

  // Helper: Search conversations
  const conversationSearch = useCallback(
    async (query: string): Promise<MCPToolResult> => {
      return callTool('conversation_search', { query });
    },
    [callTool]
  );

  // Helper: Get conversation
  const conversationGet = useCallback(
    async (id: string): Promise<MCPToolResult> => {
      return callTool('conversation_get', { id });
    },
    [callTool]
  );

  // Helper: Search tools
  const searchTools = useCallback(
    async (query: string): Promise<MCPToolResult> => {
      return callTool('search_tools', { query });
    },
    [callTool]
  );

  return {
    tools: allTools,
    isLoading: false,
    callTool,
    streamToolCall,
    findTool,
    agentChat,
    executePython,
    conversationSearch,
    conversationGet,
    searchTools,
  };
}
