/**
 * useMCPTools Tests
 *
 * Tests for the hook that manages MCP tool discovery and execution.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { useMCPTools } from './useMCPTools';
import { MCPHostProvider } from '../contexts/MCPHostContext';

// Mock the context
const mockGetClient = vi.fn();
const mockAllTools = [
  { name: 'agent_chat', description: 'Chat with agent', inputSchema: {} },
  { name: 'execute_python', description: 'Run Python', inputSchema: {} },
];

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: vi.fn(() => ({
    allTools: mockAllTools,
    getClient: mockGetClient,
    primaryServerId: 'primary',
  })),
  MCPHostProvider: ({ children }: { children: ReactNode }) => children,
}));

describe('useMCPTools', () => {
  const mockClient = {
    callTool: vi.fn(),
    streamToolCall: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetClient.mockReturnValue(mockClient);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should_return_all_available_tools', () => {
    // WHEN: Hook is rendered
    const { result } = renderHook(() => useMCPTools());

    // THEN: Should have tools
    expect(result.current.tools).toEqual(mockAllTools);
  });

  it('should_call_tool_with_arguments', async () => {
    // GIVEN: Mock tool result
    mockClient.callTool.mockResolvedValue({
      content: [{ type: 'text', text: 'Hello!' }],
    });

    const { result } = renderHook(() => useMCPTools());

    // WHEN: Calling a tool
    let toolResult;
    await act(async () => {
      toolResult = await result.current.callTool('agent_chat', { message: 'Hi' });
    });

    // THEN: Should return result
    expect(mockClient.callTool).toHaveBeenCalledWith('agent_chat', { message: 'Hi' });
    expect(toolResult).toEqual({ content: [{ type: 'text', text: 'Hello!' }] });
  });

  it('should_stream_tool_call', async () => {
    // GIVEN: Mock streaming
    mockClient.streamToolCall.mockImplementation(
      async (_name: string, _args: unknown, onChunk: (chunk: unknown) => void) => {
        onChunk({ type: 'chunk', content: 'Hello' });
        onChunk({ type: 'chunk', content: ' World' });
        onChunk({ type: 'complete' });
      }
    );

    const { result } = renderHook(() => useMCPTools());
    const chunks: unknown[] = [];

    // WHEN: Streaming tool call
    await act(async () => {
      await result.current.streamToolCall(
        'agent_chat',
        { message: 'Hi' },
        (chunk) => chunks.push(chunk)
      );
    });

    // THEN: Should receive chunks
    expect(chunks).toHaveLength(3);
  });

  it('should_provide_agent_chat_helper', async () => {
    // GIVEN: Mock streaming
    mockClient.streamToolCall.mockImplementation(
      async (_name: string, _args: unknown, onChunk: (chunk: unknown) => void) => {
        onChunk({ type: 'chunk', content: 'Response' });
        onChunk({ type: 'complete' });
      }
    );

    const { result } = renderHook(() => useMCPTools());
    const chunks: string[] = [];

    // WHEN: Using agentChat helper
    await act(async () => {
      await result.current.agentChat('Hello', (content) => chunks.push(content));
    });

    // THEN: Should stream response
    expect(chunks.length).toBeGreaterThan(0);
  });

  it('should_handle_tool_call_error', async () => {
    // GIVEN: Tool call fails
    mockClient.callTool.mockRejectedValue(new Error('Tool failed'));

    const { result } = renderHook(() => useMCPTools());

    // WHEN/THEN: Should throw error
    await expect(
      act(async () => {
        await result.current.callTool('agent_chat', {});
      })
    ).rejects.toThrow('Tool failed');
  });

  it('should_find_tool_by_name', () => {
    // WHEN: Hook is rendered
    const { result } = renderHook(() => useMCPTools());

    // THEN: Should find tool
    const tool = result.current.findTool('agent_chat');
    expect(tool?.name).toBe('agent_chat');
  });

  it('should_return_undefined_for_unknown_tool', () => {
    // WHEN: Looking for unknown tool
    const { result } = renderHook(() => useMCPTools());

    // THEN: Should return undefined
    const tool = result.current.findTool('unknown_tool');
    expect(tool).toBeUndefined();
  });
});
