/**
 * useMCPPrompts Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMCPPrompts } from './useMCPPrompts';

const mockGetClient = vi.fn();
const mockAllPrompts = [
  { name: 'code_review', description: 'Review code', arguments: [{ name: 'code', required: true }] },
  { name: 'summarize', description: 'Summarize text', arguments: [] },
];

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(() => ({
    allPrompts: mockAllPrompts,
    getClient: mockGetClient,
    primaryServerId: 'primary',
  })),
}));

describe('useMCPPrompts', () => {
  const mockClient = {
    getPrompt: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetClient.mockReturnValue(mockClient);
  });

  it('should_return_all_available_prompts', () => {
    const { result } = renderHook(() => useMCPPrompts());
    expect(result.current.prompts).toEqual(mockAllPrompts);
  });

  it('should_get_prompt_messages', async () => {
    mockClient.getPrompt.mockResolvedValue({
      messages: [{ role: 'user', content: { type: 'text', text: 'Review: code' } }],
    });

    const { result } = renderHook(() => useMCPPrompts());

    let promptResult;
    await act(async () => {
      promptResult = await result.current.getPrompt('code_review', { code: 'function test(){}' });
    });

    expect(promptResult?.messages).toHaveLength(1);
  });

  it('should_find_prompt_by_name', () => {
    const { result } = renderHook(() => useMCPPrompts());
    const prompt = result.current.findPrompt('code_review');
    expect(prompt?.description).toBe('Review code');
  });
});
