/**
 * useMCPCompletion Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMCPCompletion } from './useMCPCompletion';

// Mock completion result
const mockCompletionResult = {
  completion: {
    values: ['option1', 'option2', 'option3'],
    total: 10,
    hasMore: true,
  },
};

// Mock MCPHost context
const mockClient = {
  complete: vi.fn().mockResolvedValue(mockCompletionResult),
};

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: () => ({
    getClient: () => mockClient,
    primaryServerId: 'test-server',
  }),
}));

describe('useMCPCompletion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_initialize_with_empty_completions', () => {
    const { result } = renderHook(() => useMCPCompletion());

    expect(result.current.completions).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.hasMore).toBe(false);
  });

  it('should_complete_prompt_argument', async () => {
    const { result } = renderHook(() => useMCPCompletion());

    const ref = { type: 'ref/prompt' as const, name: 'test-prompt' };
    const argument = { name: 'arg1', value: 'val' };

    await act(async () => {
      await result.current.complete(ref, argument);
    });

    expect(mockClient.complete).toHaveBeenCalledWith(ref, argument);
    expect(result.current.completions).toEqual(['option1', 'option2', 'option3']);
    expect(result.current.hasMore).toBe(true);
  });

  it('should_complete_resource_argument', async () => {
    const { result } = renderHook(() => useMCPCompletion());

    const ref = { type: 'ref/resource' as const, uri: 'file:///test' };
    const argument = { name: 'path', value: '/home' };

    await act(async () => {
      await result.current.complete(ref, argument);
    });

    expect(mockClient.complete).toHaveBeenCalledWith(ref, argument);
    expect(result.current.completions).toEqual(['option1', 'option2', 'option3']);
  });

  it('should_clear_completions', async () => {
    const { result } = renderHook(() => useMCPCompletion());

    // First, complete to get some results
    const ref = { type: 'ref/prompt' as const, name: 'test' };
    await act(async () => {
      await result.current.complete(ref, { name: 'arg', value: 'val' });
    });

    expect(result.current.completions).toHaveLength(3);

    // Then clear
    act(() => {
      result.current.clearCompletions();
    });

    expect(result.current.completions).toEqual([]);
    expect(result.current.hasMore).toBe(false);
  });

  it('should_handle_errors', async () => {
    mockClient.complete.mockRejectedValueOnce(new Error('Completion failed'));

    const { result } = renderHook(() => useMCPCompletion());

    const ref = { type: 'ref/prompt' as const, name: 'test' };
    let error: Error | undefined;

    await act(async () => {
      try {
        await result.current.complete(ref, { name: 'arg', value: 'val' });
      } catch (e) {
        error = e as Error;
      }
    });

    expect(error?.message).toBe('Completion failed');
    expect(result.current.error).toBe('Completion failed');
  });
});
