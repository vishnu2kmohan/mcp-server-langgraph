/**
 * useMCPSampling Tests
 *
 * Tests for handling MCP sampling requests from servers.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMCPSampling } from './useMCPSampling';

const mockPendingSamplingRequests = [
  {
    id: 'sample-1',
    serverId: 'server1',
    messages: [{ role: 'user', content: { type: 'text', text: 'Summarize this' } }],
    maxTokens: 100,
    systemPrompt: 'You are a helpful assistant',
    createdAt: '2025-01-01T00:00:00Z',
  },
];

const mockRespondToSampling = vi.fn();

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(() => ({
    pendingSamplingRequests: mockPendingSamplingRequests,
    respondToSampling: mockRespondToSampling,
  })),
}));

describe('useMCPSampling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_return_current_sampling_request', () => {
    const { result } = renderHook(() => useMCPSampling());
    expect(result.current.currentRequest).toEqual(mockPendingSamplingRequests[0]);
  });

  it('should_return_pending_count', () => {
    const { result } = renderHook(() => useMCPSampling());
    expect(result.current.pendingCount).toBe(1);
  });

  it('should_approve_sampling_request', async () => {
    const { result } = renderHook(() => useMCPSampling());

    const llmResult = { role: 'assistant', content: 'Summary here' };
    await act(async () => {
      await result.current.approve(llmResult);
    });

    expect(mockRespondToSampling).toHaveBeenCalledWith('sample-1', true, llmResult);
  });

  it('should_reject_sampling_request', async () => {
    const { result } = renderHook(() => useMCPSampling());

    await act(async () => {
      await result.current.reject('Not authorized');
    });

    expect(mockRespondToSampling).toHaveBeenCalledWith('sample-1', false, 'Not authorized');
  });

  it('should_indicate_when_sampling_is_pending', () => {
    const { result } = renderHook(() => useMCPSampling());
    expect(result.current.hasPending).toBe(true);
  });
});
