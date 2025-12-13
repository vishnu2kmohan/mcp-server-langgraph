/**
 * useTraceWebSocket Hook Tests
 *
 * TDD tests for the trace WebSocket hook.
 * Tests cover:
 * - Connection management
 * - Message handling
 * - Span updates
 * - Event processing
 * - Reconnection logic
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useTraceWebSocket } from './useTraceWebSocket';
import type { TraceSpan, TraceEvent } from './useTraceWebSocket';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];

  url: string;
  readyState: number = WebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string): void {
    // Mock send
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper to simulate receiving a message
  simulateMessage(data: object): void {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper to simulate connection open
  simulateOpen(): void {
    this.readyState = WebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  // Helper to simulate error
  simulateError(): void {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

describe('useTraceWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('Initial State', () => {
    it('should start with empty spans array', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      expect(result.current.spans).toEqual([]);
    });

    it('should start with empty events array', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      expect(result.current.events).toEqual([]);
    });

    it('should start disconnected', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      expect(result.current.isConnected).toBe(false);
    });

    it('should provide connect function', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      expect(typeof result.current.connect).toBe('function');
    });

    it('should provide disconnect function', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      expect(typeof result.current.disconnect).toBe('function');
    });

    it('should provide clearTraces function', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      expect(typeof result.current.clearTraces).toBe('function');
    });
  });

  describe('Connection', () => {
    it('should connect when connect() is called', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      expect(MockWebSocket.instances.length).toBe(1);
    });

    it('should use default URL when not provided', () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];
      expect(ws.url).toContain('/api/v1/mcp/ws');
    });

    it('should use custom URL when provided', () => {
      const { result } = renderHook(() => useTraceWebSocket({ url: '/custom/ws' }));

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];
      expect(ws.url).toContain('/custom/ws');
    });

    it('should include session ID in URL when provided', () => {
      const { result } = renderHook(() => useTraceWebSocket({ sessionId: 'test-session' }));

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];
      expect(ws.url).toContain('test-session');
    });

    it('should set isConnected to true on connection open', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });
    });

    it('should auto-connect when autoConnect is true', () => {
      renderHook(() => useTraceWebSocket({ autoConnect: true }));

      expect(MockWebSocket.instances.length).toBe(1);
    });
  });

  describe('Disconnection', () => {
    it('should disconnect when disconnect() is called', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        result.current.disconnect();
      });

      expect(ws.readyState).toBe(WebSocket.CLOSED);
    });

    it('should set isConnected to false on disconnect', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        result.current.disconnect();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
      });
    });
  });

  describe('Span Handling', () => {
    it('should add new span on $/trace/span message', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      const spanMessage = {
        method: '$/trace/span',
        params: {
          traceId: 'trace-1',
          spanId: 'span-1',
          name: 'Test Span',
          startTime: '2024-01-15T10:00:00Z',
          status: 'UNSET',
          attributes: {},
        },
      };

      act(() => {
        ws.simulateMessage(spanMessage);
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(1);
        expect(result.current.spans[0].spanId).toBe('span-1');
        expect(result.current.spans[0].name).toBe('Test Span');
      });
    });

    it('should update existing span when span with same ID received', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Add initial span
      act(() => {
        ws.simulateMessage({
          method: '$/trace/span',
          params: {
            traceId: 'trace-1',
            spanId: 'span-1',
            name: 'Test Span',
            startTime: '2024-01-15T10:00:00Z',
            status: 'UNSET',
            attributes: {},
          },
        });
      });

      // Update the span
      act(() => {
        ws.simulateMessage({
          method: '$/trace/span',
          params: {
            traceId: 'trace-1',
            spanId: 'span-1',
            name: 'Test Span',
            startTime: '2024-01-15T10:00:00Z',
            endTime: '2024-01-15T10:00:05Z',
            status: 'OK',
            attributes: {},
          },
        });
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(1);
        expect(result.current.spans[0].status).toBe('OK');
        expect(result.current.spans[0].endTime).toBe('2024-01-15T10:00:05Z');
      });
    });

    it('should handle parent-child span relationships', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Add parent span
      act(() => {
        ws.simulateMessage({
          method: '$/trace/span',
          params: {
            traceId: 'trace-1',
            spanId: 'parent-span',
            name: 'Parent',
            startTime: '2024-01-15T10:00:00Z',
            status: 'UNSET',
            attributes: {},
          },
        });
      });

      // Add child span
      act(() => {
        ws.simulateMessage({
          method: '$/trace/span',
          params: {
            traceId: 'trace-1',
            spanId: 'child-span',
            parentSpanId: 'parent-span',
            name: 'Child',
            startTime: '2024-01-15T10:00:01Z',
            status: 'UNSET',
            attributes: {},
          },
        });
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(2);
        const childSpan = result.current.spans.find(s => s.spanId === 'child-span');
        expect(childSpan?.parentSpanId).toBe('parent-span');
      });
    });
  });

  describe('Event Handling', () => {
    it('should add event on $/trace/event message', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      const eventMessage = {
        method: '$/trace/event',
        params: {
          spanId: 'span-1',
          name: 'Log Event',
          timestamp: '2024-01-15T10:00:02Z',
          attributes: { message: 'Something happened' },
        },
      };

      act(() => {
        ws.simulateMessage(eventMessage);
      });

      await waitFor(() => {
        expect(result.current.events.length).toBe(1);
        expect(result.current.events[0].name).toBe('Log Event');
      });
    });
  });

  describe('Clear Traces', () => {
    it('should clear all spans and events when clearTraces() is called', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Add some data
      act(() => {
        ws.simulateMessage({
          method: '$/trace/span',
          params: {
            traceId: 'trace-1',
            spanId: 'span-1',
            name: 'Test',
            startTime: '2024-01-15T10:00:00Z',
            status: 'OK',
            attributes: {},
          },
        });
        ws.simulateMessage({
          method: '$/trace/event',
          params: {
            spanId: 'span-1',
            name: 'Event',
            timestamp: '2024-01-15T10:00:01Z',
            attributes: {},
          },
        });
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(1);
        expect(result.current.events.length).toBe(1);
      });

      act(() => {
        result.current.clearTraces();
      });

      expect(result.current.spans).toEqual([]);
      expect(result.current.events).toEqual([]);
    });
  });

  describe('Error Handling', () => {
    it('should set isConnected to false on error', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        ws.simulateError();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
      });

      consoleSpy.mockRestore();
    });

    it('should handle malformed JSON messages gracefully', async () => {
      const { result } = renderHook(() => useTraceWebSocket());

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      act(() => {
        result.current.connect();
      });

      const ws = MockWebSocket.instances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Send malformed JSON
      act(() => {
        if (ws.onmessage) {
          ws.onmessage(new MessageEvent('message', { data: 'not valid json' }));
        }
      });

      // Should not crash, just log error
      expect(consoleSpy).toHaveBeenCalled();
      expect(result.current.spans).toEqual([]);

      consoleSpy.mockRestore();
    });
  });
});
