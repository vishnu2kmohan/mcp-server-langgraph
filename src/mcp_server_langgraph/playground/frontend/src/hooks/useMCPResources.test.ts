/**
 * useMCPResources Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMCPResources } from './useMCPResources';

const mockGetClient = vi.fn();
const mockAllResources = [
  { uri: 'playground://traces', name: 'Traces', mimeType: 'application/json' },
  { uri: 'playground://logs', name: 'Logs', mimeType: 'application/json' },
];

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(() => ({
    allResources: mockAllResources,
    getClient: mockGetClient,
    primaryServerId: 'primary',
  })),
}));

describe('useMCPResources', () => {
  const mockClient = {
    readResource: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetClient.mockReturnValue(mockClient);
  });

  it('should_return_all_available_resources', () => {
    const { result } = renderHook(() => useMCPResources());
    expect(result.current.resources).toEqual(mockAllResources);
  });

  it('should_read_resource_content', async () => {
    mockClient.readResource.mockResolvedValue({
      contents: [{ uri: 'playground://traces', text: '{"traces":[]}' }],
    });

    const { result } = renderHook(() => useMCPResources());

    let content;
    await act(async () => {
      content = await result.current.readResource('playground://traces');
    });

    expect(content).toEqual({
      contents: [{ uri: 'playground://traces', text: '{"traces":[]}' }],
    });
  });

  it('should_find_resource_by_uri', () => {
    const { result } = renderHook(() => useMCPResources());
    const resource = result.current.findResource('playground://traces');
    expect(resource?.name).toBe('Traces');
  });
});
