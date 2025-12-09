/**
 * MCPHostContext Tests
 *
 * Tests for the MCP Host context that manages multiple server connections
 * and provides aggregated capabilities to child components.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import {
  MCPHostProvider,
  useMCPHost,
  MCPHostContextValue,
} from './MCPHostContext';

// =============================================================================
// Test Setup
// =============================================================================

// Mock MCP Client
const mockClient = {
  initialize: vi.fn(),
  disconnect: vi.fn(),
  getStatus: vi.fn().mockReturnValue('disconnected'),
  getServerCapabilities: vi.fn().mockReturnValue(null),
  getServerInfo: vi.fn().mockReturnValue(null),
  ping: vi.fn(),
  setAuthToken: vi.fn(),
  listTools: vi.fn(),
  callTool: vi.fn(),
  streamToolCall: vi.fn(),
  listResources: vi.fn(),
  readResource: vi.fn(),
  listPrompts: vi.fn(),
  getPrompt: vi.fn(),
};

vi.mock('../api/mcp-client', () => ({
  createMCPClient: vi.fn(() => mockClient),
  MCPClientError: class MCPClientError extends Error {
    code?: number;
    data?: unknown;
    constructor(message: string, code?: number, data?: unknown) {
      super(message);
      this.code = code;
      this.data = data;
    }
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  return <MCPHostProvider>{children}</MCPHostProvider>;
}

describe('MCPHostContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClient.getStatus.mockReturnValue('disconnected');
    mockClient.getServerCapabilities.mockReturnValue(null);
    mockClient.getServerInfo.mockReturnValue(null);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Provider Tests
  // ===========================================================================

  describe('MCPHostProvider', () => {
    it('should_provide_context_to_children', () => {
      // WHEN: Rendering hook with provider
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // THEN: Context should be available
      expect(result.current).toBeDefined();
      expect(result.current.servers).toBeDefined();
    });

    it('should_throw_when_used_outside_provider', () => {
      // GIVEN: No provider wrapper
      // WHEN/THEN: Using hook should throw
      expect(() => {
        renderHook(() => useMCPHost());
      }).toThrow('useMCPHost must be used within MCPHostProvider');
    });

    it('should_start_with_empty_servers_map', () => {
      // WHEN: Rendering hook
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // THEN: Should have no servers
      expect(result.current.servers.size).toBe(0);
    });
  });

  // ===========================================================================
  // Server Management Tests
  // ===========================================================================

  describe('server management', () => {
    it('should_add_server_and_connect', async () => {
      // GIVEN: Mock successful connection
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: { tools: { listChanged: true } },
        serverInfo: { name: 'test-server', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.getServerCapabilities.mockReturnValue({ tools: { listChanged: true } });
      mockClient.getServerInfo.mockReturnValue({ name: 'test-server', version: '1.0.0' });
      mockClient.listTools.mockResolvedValue([]);
      mockClient.listResources.mockResolvedValue({ resources: [] });
      mockClient.listPrompts.mockResolvedValue([]);

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding a server
      await act(async () => {
        await result.current.addServer('primary', 'http://localhost:8001');
      });

      // THEN: Server should be added and connected
      expect(result.current.servers.size).toBe(1);
      expect(result.current.servers.get('primary')?.status).toBe('connected');
    });

    it('should_remove_server_and_disconnect', async () => {
      // GIVEN: A connected server
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: {},
        serverInfo: { name: 'test', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.listTools.mockResolvedValue([]);
      mockClient.listResources.mockResolvedValue({ resources: [] });
      mockClient.listPrompts.mockResolvedValue([]);

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      await act(async () => {
        await result.current.addServer('primary', 'http://localhost:8001');
      });

      expect(result.current.servers.size).toBe(1);

      // WHEN: Removing the server
      act(() => {
        result.current.removeServer('primary');
      });

      // THEN: Server should be removed
      expect(result.current.servers.size).toBe(0);
      expect(mockClient.disconnect).toHaveBeenCalled();
    });

    it('should_handle_connection_failure', async () => {
      // GIVEN: Connection fails
      mockClient.initialize.mockRejectedValue(new Error('Connection refused'));
      mockClient.getStatus.mockReturnValue('error');

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding a server that fails to connect
      await act(async () => {
        try {
          await result.current.addServer('primary', 'http://localhost:8001');
        } catch {
          // Expected to fail
        }
      });

      // THEN: Server should show error status
      const server = result.current.servers.get('primary');
      expect(server?.status).toBe('error');
      expect(server?.error).toBeDefined();
    });

    it('should_manage_multiple_servers', async () => {
      // GIVEN: Mock successful connections
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: {},
        serverInfo: { name: 'test', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.listTools.mockResolvedValue([]);
      mockClient.listResources.mockResolvedValue({ resources: [] });
      mockClient.listPrompts.mockResolvedValue([]);

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding multiple servers
      await act(async () => {
        await result.current.addServer('server1', 'http://localhost:8001');
        await result.current.addServer('server2', 'http://localhost:8002');
      });

      // THEN: Both servers should be tracked
      expect(result.current.servers.size).toBe(2);
      expect(result.current.servers.has('server1')).toBe(true);
      expect(result.current.servers.has('server2')).toBe(true);
    });
  });

  // ===========================================================================
  // Aggregated Capabilities Tests
  // ===========================================================================

  describe('aggregated capabilities', () => {
    it('should_aggregate_tools_from_all_servers', async () => {
      // GIVEN: Two servers with different tools
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: { tools: { listChanged: true } },
        serverInfo: { name: 'test', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.listResources.mockResolvedValue({ resources: [] });
      mockClient.listPrompts.mockResolvedValue([]);

      let callCount = 0;
      mockClient.listTools.mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve([
            { name: 'tool1', description: 'Tool 1', inputSchema: {} },
          ]);
        }
        return Promise.resolve([
          { name: 'tool2', description: 'Tool 2', inputSchema: {} },
        ]);
      });

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding multiple servers
      await act(async () => {
        await result.current.addServer('server1', 'http://localhost:8001');
        await result.current.addServer('server2', 'http://localhost:8002');
      });

      // THEN: All tools should be aggregated
      expect(result.current.allTools.length).toBe(2);
      expect(result.current.allTools.map(t => t.name)).toContain('tool1');
      expect(result.current.allTools.map(t => t.name)).toContain('tool2');
    });

    it('should_aggregate_resources_from_all_servers', async () => {
      // GIVEN: Servers with resources
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: { resources: { subscribe: true } },
        serverInfo: { name: 'test', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.listTools.mockResolvedValue([]);
      mockClient.listPrompts.mockResolvedValue([]);

      let callCount = 0;
      mockClient.listResources.mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({
            resources: [{ uri: 'res://1', name: 'Resource 1' }],
          });
        }
        return Promise.resolve({
          resources: [{ uri: 'res://2', name: 'Resource 2' }],
        });
      });

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding multiple servers
      await act(async () => {
        await result.current.addServer('server1', 'http://localhost:8001');
        await result.current.addServer('server2', 'http://localhost:8002');
      });

      // THEN: All resources should be aggregated
      expect(result.current.allResources.length).toBe(2);
    });

    it('should_aggregate_prompts_from_all_servers', async () => {
      // GIVEN: Servers with prompts
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: { prompts: { listChanged: true } },
        serverInfo: { name: 'test', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.listTools.mockResolvedValue([]);
      mockClient.listResources.mockResolvedValue({ resources: [] });

      let callCount = 0;
      mockClient.listPrompts.mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve([{ name: 'prompt1', description: 'Prompt 1' }]);
        }
        return Promise.resolve([{ name: 'prompt2', description: 'Prompt 2' }]);
      });

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding multiple servers
      await act(async () => {
        await result.current.addServer('server1', 'http://localhost:8001');
        await result.current.addServer('server2', 'http://localhost:8002');
      });

      // THEN: All prompts should be aggregated
      expect(result.current.allPrompts.length).toBe(2);
    });
  });

  // ===========================================================================
  // Client Capabilities Tests
  // ===========================================================================

  describe('client capabilities', () => {
    it('should_declare_elicitation_capability', () => {
      // WHEN: Rendering hook
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // THEN: Elicitation should be enabled
      expect(result.current.capabilities.elicitation).toBe(true);
    });

    it('should_declare_sampling_capability', () => {
      // WHEN: Rendering hook
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // THEN: Sampling should be enabled
      expect(result.current.capabilities.sampling).toBe(true);
    });

    it('should_declare_roots_capability', () => {
      // WHEN: Rendering hook
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // THEN: Roots should be declared
      expect(result.current.capabilities.roots).toEqual({ listChanged: true });
    });
  });

  // ===========================================================================
  // Elicitation Queue Tests
  // ===========================================================================

  describe('elicitation queue', () => {
    it('should_track_pending_elicitations', () => {
      // WHEN: Rendering hook
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // THEN: Should have empty pending elicitations
      expect(result.current.pendingElicitations).toEqual([]);
    });

    it('should_add_elicitation_to_queue', async () => {
      // GIVEN: Provider with elicitation handler
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding an elicitation
      act(() => {
        result.current.addElicitation({
          id: 'elicit-1',
          serverId: 'server1',
          message: 'Approve this action?',
          requestedSchema: { type: 'object', properties: { approved: { type: 'boolean' } } },
          createdAt: new Date().toISOString(),
        });
      });

      // THEN: Elicitation should be in queue
      expect(result.current.pendingElicitations.length).toBe(1);
      expect(result.current.pendingElicitations[0].id).toBe('elicit-1');
    });

    it('should_remove_elicitation_after_response', async () => {
      // GIVEN: An elicitation in the queue
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      act(() => {
        result.current.addElicitation({
          id: 'elicit-1',
          serverId: 'server1',
          message: 'Approve?',
          requestedSchema: { type: 'object' },
          createdAt: new Date().toISOString(),
        });
      });

      expect(result.current.pendingElicitations.length).toBe(1);

      // WHEN: Responding to elicitation
      act(() => {
        result.current.respondToElicitation('elicit-1', 'accept', { approved: true });
      });

      // THEN: Elicitation should be removed
      expect(result.current.pendingElicitations.length).toBe(0);
    });
  });

  // ===========================================================================
  // Sampling Queue Tests
  // ===========================================================================

  describe('sampling queue', () => {
    it('should_track_pending_sampling_requests', () => {
      // WHEN: Rendering hook
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // THEN: Should have empty pending sampling requests
      expect(result.current.pendingSamplingRequests).toEqual([]);
    });

    it('should_add_sampling_request_to_queue', async () => {
      // GIVEN: Provider
      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding a sampling request
      act(() => {
        result.current.addSamplingRequest({
          id: 'sample-1',
          serverId: 'server1',
          messages: [{ role: 'user', content: { type: 'text', text: 'Hello' } }],
          maxTokens: 100,
          createdAt: new Date().toISOString(),
        });
      });

      // THEN: Request should be in queue
      expect(result.current.pendingSamplingRequests.length).toBe(1);
      expect(result.current.pendingSamplingRequests[0].id).toBe('sample-1');
    });
  });

  // ===========================================================================
  // Primary Server Tests
  // ===========================================================================

  describe('primary server', () => {
    it('should_track_primary_server', async () => {
      // GIVEN: A connected server
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: {},
        serverInfo: { name: 'primary-server', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.listTools.mockResolvedValue([]);
      mockClient.listResources.mockResolvedValue({ resources: [] });
      mockClient.listPrompts.mockResolvedValue([]);

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      // WHEN: Adding a server as primary
      await act(async () => {
        await result.current.addServer('primary', 'http://localhost:8001', { primary: true });
      });

      // THEN: Should be the primary server
      expect(result.current.primaryServerId).toBe('primary');
    });

    it('should_allow_changing_primary_server', async () => {
      // GIVEN: Two connected servers
      mockClient.initialize.mockResolvedValue({
        protocolVersion: '2025-06-18',
        capabilities: {},
        serverInfo: { name: 'test', version: '1.0.0' },
      });
      mockClient.getStatus.mockReturnValue('connected');
      mockClient.listTools.mockResolvedValue([]);
      mockClient.listResources.mockResolvedValue({ resources: [] });
      mockClient.listPrompts.mockResolvedValue([]);

      const { result } = renderHook(() => useMCPHost(), { wrapper });

      await act(async () => {
        await result.current.addServer('server1', 'http://localhost:8001', { primary: true });
        await result.current.addServer('server2', 'http://localhost:8002');
      });

      expect(result.current.primaryServerId).toBe('server1');

      // WHEN: Changing primary server
      act(() => {
        result.current.setPrimaryServer('server2');
      });

      // THEN: Primary should change
      expect(result.current.primaryServerId).toBe('server2');
    });
  });
});
