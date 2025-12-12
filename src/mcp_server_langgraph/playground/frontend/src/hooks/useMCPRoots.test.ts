/**
 * useMCPRoots Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMCPRoots } from './useMCPRoots';
import type { MCPRoot } from '../api/mcp-types';

// Mock roots
const mockRoots: MCPRoot[] = [
  { uri: 'file:///home/user', name: 'Home' },
  { uri: 'file:///project', name: 'Project' },
];

// Mock MCPHost context
const mockClient = {
  listRoots: vi.fn().mockResolvedValue(mockRoots),
};

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: () => ({
    getClient: () => mockClient,
    primaryServerId: 'test-server',
  }),
}));

describe('useMCPRoots', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_initialize_with_empty_roots', () => {
    const { result } = renderHook(() => useMCPRoots({ autoLoad: false }));

    expect(result.current.roots).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should_refresh_roots', async () => {
    const { result } = renderHook(() => useMCPRoots({ autoLoad: false }));

    await act(async () => {
      await result.current.refreshRoots();
    });

    expect(mockClient.listRoots).toHaveBeenCalled();
    expect(result.current.roots).toEqual(mockRoots);
  });

  it('should_handle_errors', async () => {
    mockClient.listRoots.mockRejectedValueOnce(new Error('Failed to fetch roots'));

    const { result } = renderHook(() => useMCPRoots({ autoLoad: false }));

    await act(async () => {
      await result.current.refreshRoots();
    });

    expect(result.current.error).toBe('Failed to fetch roots');
    expect(result.current.roots).toEqual([]);
  });
});
