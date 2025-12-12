/**
 * useMCPElicitation Tests
 *
 * Tests for handling MCP elicitation requests from servers.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMCPElicitation } from './useMCPElicitation';

const mockPendingElicitations = [
  {
    id: 'elicit-1',
    serverId: 'server1',
    message: 'Approve this action?',
    requestedSchema: { type: 'object', properties: { approved: { type: 'boolean' } } },
    createdAt: '2025-01-01T00:00:00Z',
  },
];

const mockRespondToElicitation = vi.fn();

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(() => ({
    pendingElicitations: mockPendingElicitations,
    respondToElicitation: mockRespondToElicitation,
  })),
}));

describe('useMCPElicitation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_return_current_elicitation', () => {
    const { result } = renderHook(() => useMCPElicitation());
    expect(result.current.currentElicitation).toEqual(mockPendingElicitations[0]);
  });

  it('should_return_all_pending_elicitations', () => {
    const { result } = renderHook(() => useMCPElicitation());
    expect(result.current.pendingCount).toBe(1);
  });

  it('should_accept_elicitation_with_content', async () => {
    const { result } = renderHook(() => useMCPElicitation());

    await act(async () => {
      await result.current.accept({ approved: true });
    });

    expect(mockRespondToElicitation).toHaveBeenCalledWith('elicit-1', 'accept', { approved: true });
  });

  it('should_decline_elicitation', async () => {
    const { result } = renderHook(() => useMCPElicitation());

    await act(async () => {
      await result.current.decline();
    });

    expect(mockRespondToElicitation).toHaveBeenCalledWith('elicit-1', 'decline', undefined);
  });

  it('should_cancel_elicitation', async () => {
    const { result } = renderHook(() => useMCPElicitation());

    await act(async () => {
      await result.current.cancel();
    });

    expect(mockRespondToElicitation).toHaveBeenCalledWith('elicit-1', 'cancel', undefined);
  });

  it('should_indicate_when_elicitation_is_pending', () => {
    const { result } = renderHook(() => useMCPElicitation());
    expect(result.current.hasPending).toBe(true);
  });
});
