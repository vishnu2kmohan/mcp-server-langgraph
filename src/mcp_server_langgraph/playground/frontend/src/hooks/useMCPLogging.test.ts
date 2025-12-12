/**
 * useMCPLogging Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMCPLogging, LOG_LEVELS } from './useMCPLogging';

// Mock MCPHost context
const mockClient = {
  setLogLevel: vi.fn().mockResolvedValue(undefined),
};

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: () => ({
    getClient: () => mockClient,
    primaryServerId: 'test-server',
  }),
}));

describe('useMCPLogging', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_initialize_with_default_level', () => {
    const { result } = renderHook(() => useMCPLogging());

    expect(result.current.currentLevel).toBe('info');
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should_set_log_level', async () => {
    const { result } = renderHook(() => useMCPLogging());

    await act(async () => {
      await result.current.setLogLevel('debug');
    });

    expect(mockClient.setLogLevel).toHaveBeenCalledWith('debug');
    expect(result.current.currentLevel).toBe('debug');
  });

  it('should_handle_errors', async () => {
    mockClient.setLogLevel.mockRejectedValueOnce(new Error('Failed to set level'));

    const { result } = renderHook(() => useMCPLogging());

    await act(async () => {
      await result.current.setLogLevel('error');
    });

    expect(result.current.error).toBe('Failed to set level');
    // Level should not change on error
    expect(result.current.currentLevel).toBe('info');
  });

  it('should_export_log_levels', () => {
    expect(LOG_LEVELS).toEqual([
      'debug',
      'info',
      'notice',
      'warning',
      'error',
      'critical',
      'alert',
      'emergency',
    ]);
  });
});
