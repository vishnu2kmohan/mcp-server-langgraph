/**
 * useStreamingChat Hook Tests
 *
 * Tests for streaming chat hook using Server-Sent Events (SSE).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useStreamingChat } from './useStreamingChat';

// Mock EventSource
class MockEventSource {
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onopen: ((event: Event) => void) | null = null;
  public readyState: number = 0;
  public url: string;

  constructor(url: string) {
    this.url = url;
    this.readyState = 0; // CONNECTING
  }

  close() {
    this.readyState = 2; // CLOSED
  }
}

describe('useStreamingChat', () => {
  let mockEventSource: MockEventSource;

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock EventSource globally
    mockEventSource = new MockEventSource('');
    vi.stubGlobal(
      'EventSource',
      vi.fn((url: string) => {
        mockEventSource.url = url;
        return mockEventSource;
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('Initial State', () => {
    it('should start with empty state', () => {
      const { result } = renderHook(() => useStreamingChat());

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.streamingContent).toBe('');
      expect(result.current.error).toBeNull();
    });
  });

  describe('Starting Stream', () => {
    it('should set isStreaming to true when starting stream', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      expect(result.current.isStreaming).toBe(true);
    });

    it('should create EventSource with correct URL', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello World');
      });

      expect(mockEventSource.url).toContain('/api/v1/chat/completions/stream');
      expect(mockEventSource.url).toContain('session_id=session-123');
      expect(mockEventSource.url).toContain('message=Hello%20World');
    });

    it('should reset content when starting new stream', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'First message');
      });

      // Simulate receiving content
      act(() => {
        mockEventSource.onmessage?.({
          data: JSON.stringify({ content: 'Response' }),
        } as MessageEvent);
      });

      expect(result.current.streamingContent).toBe('Response');

      // Start new stream
      act(() => {
        result.current.startStream('session-123', 'Second message');
      });

      expect(result.current.streamingContent).toBe('');
    });

    it('should close previous stream when starting new one', () => {
      const { result } = renderHook(() => useStreamingChat());
      const closeSpy = vi.spyOn(mockEventSource, 'close');

      act(() => {
        result.current.startStream('session-123', 'First');
      });

      const firstEventSource = mockEventSource;

      // Create new mock for second stream
      const secondEventSource = new MockEventSource('');
      vi.stubGlobal(
        'EventSource',
        vi.fn(() => secondEventSource)
      );

      act(() => {
        result.current.startStream('session-123', 'Second');
      });

      expect(closeSpy).toHaveBeenCalled();
    });
  });

  describe('Receiving Messages', () => {
    it('should accumulate streamed content', async () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      // Simulate receiving chunks
      act(() => {
        mockEventSource.onmessage?.({
          data: JSON.stringify({ content: 'Hi ' }),
        } as MessageEvent);
      });

      expect(result.current.streamingContent).toBe('Hi ');

      act(() => {
        mockEventSource.onmessage?.({
          data: JSON.stringify({ content: 'there!' }),
        } as MessageEvent);
      });

      expect(result.current.streamingContent).toBe('Hi there!');
    });

    it('should handle [DONE] message and close stream', async () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      act(() => {
        mockEventSource.onmessage?.({
          data: JSON.stringify({ content: 'Response' }),
        } as MessageEvent);
      });

      expect(result.current.isStreaming).toBe(true);

      // Simulate stream completion
      act(() => {
        mockEventSource.onmessage?.({
          data: '[DONE]',
        } as MessageEvent);
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.streamingContent).toBe('Response');
    });

    it('should handle non-JSON messages gracefully', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      // Send invalid JSON
      act(() => {
        mockEventSource.onmessage?.({
          data: 'invalid json',
        } as MessageEvent);
      });

      // Should not crash or add content
      expect(result.current.streamingContent).toBe('');
      expect(result.current.error).toBeNull();
    });

    it('should handle messages without content field', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      // Send message without content
      act(() => {
        mockEventSource.onmessage?.({
          data: JSON.stringify({ type: 'metadata' }),
        } as MessageEvent);
      });

      expect(result.current.streamingContent).toBe('');
    });
  });

  describe('Error Handling', () => {
    it('should set error on stream error', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      // Simulate error
      act(() => {
        mockEventSource.onerror?.({} as Event);
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.error).toBe('Stream connection failed');
    });

    it('should close connection on error', () => {
      const { result } = renderHook(() => useStreamingChat());
      const closeSpy = vi.spyOn(mockEventSource, 'close');

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      act(() => {
        mockEventSource.onerror?.({} as Event);
      });

      expect(closeSpy).toHaveBeenCalled();
    });
  });

  describe('Stopping Stream', () => {
    it('should stop streaming when stopStream is called', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      expect(result.current.isStreaming).toBe(true);

      act(() => {
        result.current.stopStream();
      });

      expect(result.current.isStreaming).toBe(false);
    });

    it('should close EventSource when stopStream is called', () => {
      const { result } = renderHook(() => useStreamingChat());
      const closeSpy = vi.spyOn(mockEventSource, 'close');

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      act(() => {
        result.current.stopStream();
      });

      expect(closeSpy).toHaveBeenCalled();
    });

    it('should handle stopStream when no stream is active', () => {
      const { result } = renderHook(() => useStreamingChat());

      // Should not throw
      expect(() => {
        act(() => {
          result.current.stopStream();
        });
      }).not.toThrow();
    });
  });

  describe('Clearing Content', () => {
    it('should clear content when clearContent is called', () => {
      const { result } = renderHook(() => useStreamingChat());

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      act(() => {
        mockEventSource.onmessage?.({
          data: JSON.stringify({ content: 'Response' }),
        } as MessageEvent);
      });

      expect(result.current.streamingContent).toBe('Response');

      act(() => {
        result.current.clearContent();
      });

      expect(result.current.streamingContent).toBe('');
      expect(result.current.error).toBeNull();
    });
  });

  describe('Cleanup', () => {
    it('should close EventSource on unmount', () => {
      const { result, unmount } = renderHook(() => useStreamingChat());
      const closeSpy = vi.spyOn(mockEventSource, 'close');

      act(() => {
        result.current.startStream('session-123', 'Hello');
      });

      unmount();

      expect(closeSpy).toHaveBeenCalled();
    });
  });
});
