/**
 * useMCPConnection Tests
 *
 * Tests for the hook that manages a single MCP server connection.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useMCPConnection } from './useMCPConnection';

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
  MCPClientError: class MCPClientError extends Error {},
}));

describe('useMCPConnection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockClient.getStatus.mockReturnValue('disconnected');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should_start_disconnected', () => {
    // WHEN: Hook is rendered
    const { result } = renderHook(() =>
      useMCPConnection({ url: 'http://localhost:8001' })
    );

    // THEN: Should be disconnected
    expect(result.current.isConnected).toBe(false);
    expect(result.current.status).toBe('disconnected');
  });

  it('should_connect_when_connect_is_called', async () => {
    // GIVEN: Mock successful connection
    mockClient.initialize.mockResolvedValue({
      protocolVersion: '2025-06-18',
      capabilities: { tools: {} },
      serverInfo: { name: 'test', version: '1.0.0' },
    });
    mockClient.getStatus.mockReturnValue('connected');
    mockClient.getServerCapabilities.mockReturnValue({ tools: {} });
    mockClient.getServerInfo.mockReturnValue({ name: 'test', version: '1.0.0' });

    const { result } = renderHook(() =>
      useMCPConnection({ url: 'http://localhost:8001' })
    );

    // WHEN: Connect is called
    await act(async () => {
      await result.current.connect();
    });

    // THEN: Should be connected
    expect(result.current.isConnected).toBe(true);
    expect(result.current.serverInfo).toEqual({ name: 'test', version: '1.0.0' });
  });

  it('should_handle_connection_error', async () => {
    // GIVEN: Connection fails
    mockClient.initialize.mockRejectedValue(new Error('Connection refused'));
    mockClient.getStatus.mockReturnValue('error');

    const { result } = renderHook(() =>
      useMCPConnection({ url: 'http://localhost:8001' })
    );

    // WHEN: Connect is called and fails
    await act(async () => {
      try {
        await result.current.connect();
      } catch {
        // Expected to fail
      }
    });

    // THEN: Should show error
    expect(result.current.error).toBeDefined();
    expect(result.current.status).toBe('error');
  });

  it('should_disconnect_when_disconnect_is_called', async () => {
    // GIVEN: Connected client
    mockClient.initialize.mockResolvedValue({
      protocolVersion: '2025-06-18',
      capabilities: {},
      serverInfo: { name: 'test', version: '1.0.0' },
    });
    mockClient.getStatus.mockReturnValue('connected');

    const { result } = renderHook(() =>
      useMCPConnection({ url: 'http://localhost:8001' })
    );

    await act(async () => {
      await result.current.connect();
    });

    // WHEN: Disconnect is called
    mockClient.getStatus.mockReturnValue('disconnected');
    act(() => {
      result.current.disconnect();
    });

    // THEN: Should be disconnected
    expect(result.current.isConnected).toBe(false);
    expect(mockClient.disconnect).toHaveBeenCalled();
  });

  it('should_auto_connect_when_autoConnect_is_true', async () => {
    // GIVEN: Mock successful connection
    mockClient.initialize.mockResolvedValue({
      protocolVersion: '2025-06-18',
      capabilities: {},
      serverInfo: { name: 'test', version: '1.0.0' },
    });
    mockClient.getStatus.mockReturnValue('connected');

    // WHEN: Hook is rendered with autoConnect
    const { result } = renderHook(() =>
      useMCPConnection({ url: 'http://localhost:8001', autoConnect: true })
    );

    // THEN: Should auto-connect
    await waitFor(() => {
      expect(mockClient.initialize).toHaveBeenCalled();
    });
  });

  it('should_expose_client_for_direct_access', () => {
    // WHEN: Hook is rendered
    const { result } = renderHook(() =>
      useMCPConnection({ url: 'http://localhost:8001' })
    );

    // THEN: Client should be accessible
    expect(result.current.client).toBeDefined();
  });

  it('should_update_auth_token', () => {
    // GIVEN: Hook is rendered
    const { result } = renderHook(() =>
      useMCPConnection({ url: 'http://localhost:8001' })
    );

    // WHEN: Auth token is set
    act(() => {
      result.current.setAuthToken('new-token');
    });

    // THEN: Client should receive token
    expect(mockClient.setAuthToken).toHaveBeenCalledWith('new-token');
  });
});
