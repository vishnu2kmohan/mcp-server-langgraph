/**
 * mcpStore Tests
 *
 * TDD tests for MCP state management.
 * Tests cover:
 * - Initial state
 * - Server lifecycle (add, remove, connect)
 * - Tool/resource/prompt aggregation
 * - Elicitation handling
 * - Sampling handling
 */

import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { createTestMCPStore } from './mcpStore';
import type {
  MCPTool,
  PendingElicitation,
  PendingSamplingRequest,
} from '../types/mcp';

// Mock fetch
const mockFetch = vi.fn() as Mock;

describe('mcpStore', () => {
  let store: ReturnType<typeof createTestMCPStore>;

  beforeEach(() => {
    store = createTestMCPStore();
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('initial state', () => {
    it('should have empty servers map', () => {
      expect(store.getState().servers.size).toBe(0);
    });

    it('should have null primary server', () => {
      expect(store.getState().primaryServerId).toBeNull();
    });

    it('should have default capabilities', () => {
      const caps = store.getState().capabilities;
      expect(caps.elicitation).toBe(true);
      expect(caps.sampling).toBe(true);
      expect(caps.roots.listChanged).toBe(true);
    });

    it('should have empty elicitations', () => {
      expect(store.getState().pendingElicitations).toEqual([]);
    });

    it('should have empty sampling requests', () => {
      expect(store.getState().pendingSamplingRequests).toEqual([]);
    });

    it('should have no error', () => {
      expect(store.getState().error).toBeNull();
    });
  });

  describe('addServer', () => {
    it('should add a server with connecting status', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'test-server', version: '1.0.0' },
            capabilities: { tools: { listChanged: true } },
          }),
      });

      // Act
      await store.getState().addServer('server1', 'http://localhost:8080');

      // Assert
      expect(store.getState().servers.has('server1')).toBe(true);
      const server = store.getState().servers.get('server1');
      expect(server?.status).toBe('connected');
    });

    it('should set server as primary if specified', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'primary-server', version: '1.0.0' },
            capabilities: {},
          }),
      });

      // Act
      await store.getState().addServer('primary', 'http://localhost:8080', { primary: true });

      // Assert
      expect(store.getState().primaryServerId).toBe('primary');
    });

    it('should set first server as primary by default', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'first-server', version: '1.0.0' },
            capabilities: {},
          }),
      });

      // Act
      await store.getState().addServer('first', 'http://localhost:8080');

      // Assert
      expect(store.getState().primaryServerId).toBe('first');
    });

    it('should handle connection error', async () => {
      // Arrange
      mockFetch.mockRejectedValueOnce(new Error('Connection refused'));

      // Act
      await store.getState().addServer('failing', 'http://localhost:9999');

      // Assert
      const server = store.getState().servers.get('failing');
      expect(server?.status).toBe('error');
      expect(server?.error).toBe('Connection refused');
    });
  });

  describe('removeServer', () => {
    it('should remove server from map', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'test', version: '1.0.0' },
            capabilities: {},
          }),
      });
      await store.getState().addServer('to-remove', 'http://localhost:8080');

      // Act
      store.getState().removeServer('to-remove');

      // Assert
      expect(store.getState().servers.has('to-remove')).toBe(false);
    });

    it('should clear primary if removed server was primary', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'primary', version: '1.0.0' },
            capabilities: {},
          }),
      });
      await store.getState().addServer('primary-server', 'http://localhost:8080', { primary: true });

      // Act
      store.getState().removeServer('primary-server');

      // Assert
      expect(store.getState().primaryServerId).toBeNull();
    });
  });

  describe('setPrimaryServer', () => {
    it('should set primary server', async () => {
      // Arrange
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              serverInfo: { name: 's1', version: '1.0.0' },
              capabilities: {},
            }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              serverInfo: { name: 's2', version: '1.0.0' },
              capabilities: {},
            }),
        });

      await store.getState().addServer('s1', 'http://localhost:8080');
      await store.getState().addServer('s2', 'http://localhost:8081');

      // Act
      store.getState().setPrimaryServer('s2');

      // Assert
      expect(store.getState().primaryServerId).toBe('s2');
    });
  });

  describe('updateServerStatus', () => {
    it('should update server status', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'test', version: '1.0.0' },
            capabilities: {},
          }),
      });
      await store.getState().addServer('test', 'http://localhost:8080');

      // Act
      store.getState().updateServerStatus('test', 'disconnected');

      // Assert
      expect(store.getState().servers.get('test')?.status).toBe('disconnected');
    });

    it('should set error when status is error', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'test', version: '1.0.0' },
            capabilities: {},
          }),
      });
      await store.getState().addServer('test', 'http://localhost:8080');

      // Act
      store.getState().updateServerStatus('test', 'error', 'Server timeout');

      // Assert
      const server = store.getState().servers.get('test');
      expect(server?.status).toBe('error');
      expect(server?.error).toBe('Server timeout');
    });
  });

  describe('setServerTools', () => {
    it('should set tools for server', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'test', version: '1.0.0' },
            capabilities: { tools: { listChanged: true } },
          }),
      });
      await store.getState().addServer('test', 'http://localhost:8080');

      const tools: MCPTool[] = [
        { name: 'tool1', description: 'First tool', inputSchema: {}, serverId: 'test' },
        { name: 'tool2', description: 'Second tool', inputSchema: {}, serverId: 'test' },
      ];

      // Act
      store.getState().setServerTools('test', tools);

      // Assert
      expect(store.getState().servers.get('test')?.tools).toHaveLength(2);
    });
  });

  describe('getAllTools', () => {
    it('should aggregate tools from all servers', async () => {
      // Arrange
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              serverInfo: { name: 's1', version: '1.0.0' },
              capabilities: { tools: { listChanged: true } },
            }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              serverInfo: { name: 's2', version: '1.0.0' },
              capabilities: { tools: { listChanged: true } },
            }),
        });

      await store.getState().addServer('s1', 'http://localhost:8080');
      await store.getState().addServer('s2', 'http://localhost:8081');

      store.getState().setServerTools('s1', [
        { name: 'tool1', description: 'T1', inputSchema: {}, serverId: 's1' },
      ]);
      store.getState().setServerTools('s2', [
        { name: 'tool2', description: 'T2', inputSchema: {}, serverId: 's2' },
        { name: 'tool3', description: 'T3', inputSchema: {}, serverId: 's2' },
      ]);

      // Act
      const allTools = store.getState().getAllTools();

      // Assert
      expect(allTools).toHaveLength(3);
    });
  });

  describe('getAllResources', () => {
    it('should aggregate resources from all servers', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 's1', version: '1.0.0' },
            capabilities: { resources: { listChanged: true } },
          }),
      });

      await store.getState().addServer('s1', 'http://localhost:8080');

      store.getState().setServerResources('s1', [
        { uri: 'file://test.txt', name: 'Test File', serverId: 's1' },
      ]);

      // Act
      const allResources = store.getState().getAllResources();

      // Assert
      expect(allResources).toHaveLength(1);
      expect(allResources[0].name).toBe('Test File');
    });
  });

  describe('getAllPrompts', () => {
    it('should aggregate prompts from all servers', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 's1', version: '1.0.0' },
            capabilities: { prompts: { listChanged: true } },
          }),
      });

      await store.getState().addServer('s1', 'http://localhost:8080');

      store.getState().setServerPrompts('s1', [
        { name: 'prompt1', description: 'First prompt', serverId: 's1' },
      ]);

      // Act
      const allPrompts = store.getState().getAllPrompts();

      // Assert
      expect(allPrompts).toHaveLength(1);
    });
  });

  describe('elicitation', () => {
    it('should add elicitation request', () => {
      // Arrange
      const elicitation: PendingElicitation = {
        id: 'elic-1',
        serverId: 's1',
        message: 'Please provide credentials',
        requestedSchema: { type: 'object' },
        createdAt: Date.now(),
      };

      // Act
      store.getState().addElicitation(elicitation);

      // Assert
      expect(store.getState().pendingElicitations).toHaveLength(1);
      expect(store.getState().pendingElicitations[0].id).toBe('elic-1');
    });

    it('should remove elicitation on respond', () => {
      // Arrange
      const elicitation: PendingElicitation = {
        id: 'elic-1',
        serverId: 's1',
        message: 'Please provide credentials',
        requestedSchema: { type: 'object' },
        createdAt: Date.now(),
      };
      store.getState().addElicitation(elicitation);

      // Act
      store.getState().respondToElicitation('elic-1', 'accept', { username: 'test' });

      // Assert
      expect(store.getState().pendingElicitations).toHaveLength(0);
    });
  });

  describe('sampling', () => {
    it('should add sampling request', () => {
      // Arrange
      const sampling: PendingSamplingRequest = {
        id: 'sample-1',
        serverId: 's1',
        messages: [{ role: 'user', content: 'Hello' }],
        maxTokens: 1024,
        createdAt: Date.now(),
      };

      // Act
      store.getState().addSamplingRequest(sampling);

      // Assert
      expect(store.getState().pendingSamplingRequests).toHaveLength(1);
    });

    it('should remove sampling request on respond', () => {
      // Arrange
      const sampling: PendingSamplingRequest = {
        id: 'sample-1',
        serverId: 's1',
        messages: [{ role: 'user', content: 'Hello' }],
        maxTokens: 1024,
        createdAt: Date.now(),
      };
      store.getState().addSamplingRequest(sampling);

      // Act
      store.getState().respondToSampling('sample-1', true, { content: 'Response' });

      // Assert
      expect(store.getState().pendingSamplingRequests).toHaveLength(0);
    });
  });

  describe('reset', () => {
    it('should reset to initial state', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            serverInfo: { name: 'test', version: '1.0.0' },
            capabilities: {},
          }),
      });
      await store.getState().addServer('test', 'http://localhost:8080');
      store.getState().addElicitation({
        id: 'e1',
        serverId: 'test',
        message: 'test',
        requestedSchema: {},
        createdAt: Date.now(),
      });

      // Act
      store.getState().reset();

      // Assert
      expect(store.getState().servers.size).toBe(0);
      expect(store.getState().primaryServerId).toBeNull();
      expect(store.getState().pendingElicitations).toEqual([]);
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      // Arrange
      store.setState({ error: 'Some error' });

      // Act
      store.getState().clearError();

      // Assert
      expect(store.getState().error).toBeNull();
    });
  });
});
