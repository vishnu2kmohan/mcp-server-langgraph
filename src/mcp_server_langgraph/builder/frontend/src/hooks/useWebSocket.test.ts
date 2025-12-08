/**
 * Tests for WebSocket Hook with Auto-Reconnect
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from './useWebSocket';

// ==============================================================================
// Mock WebSocket
// ==============================================================================

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 10);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  });

  // Helper to simulate incoming messages
  simulateMessage(data: any) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  // Helper to simulate connection error
  simulateError() {
    this.onerror?.(new Event('error'));
  }

  // Helper to simulate unexpected close
  simulateUnexpectedClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1006 }));
  }
}

describe('useWebSocket Hook', () => {
  let mockWebSocketInstance: MockWebSocket | null = null;

  beforeEach(() => {
    vi.useFakeTimers();
    mockWebSocketInstance = null;

    // Mock WebSocket constructor
    vi.stubGlobal('WebSocket', class extends MockWebSocket {
      constructor(url: string) {
        super(url);
        mockWebSocketInstance = this;
      }
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    mockWebSocketInstance = null;
  });

  // ==============================================================================
  // Return Type Tests
  // ==============================================================================

  describe('Return Type', () => {
    it('returns expected properties and methods', () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      expect(result.current).toHaveProperty('isConnected');
      expect(result.current).toHaveProperty('isConnecting');
      expect(result.current).toHaveProperty('lastMessage');
      expect(result.current).toHaveProperty('connectionError');
      expect(result.current).toHaveProperty('sendMessage');
      expect(result.current).toHaveProperty('connect');
      expect(result.current).toHaveProperty('disconnect');
      expect(result.current).toHaveProperty('reconnectAttempts');
    });
  });

  // ==============================================================================
  // Connection Tests
  // ==============================================================================

  describe('Connection', () => {
    it('creates WebSocket connection on mount', async () => {
      renderHook(() => useWebSocket('ws://localhost:8001'));

      expect(mockWebSocketInstance).not.toBeNull();
      expect(mockWebSocketInstance?.url).toBe('ws://localhost:8001');
    });

    it('sets isConnecting to true while connecting', () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      expect(result.current.isConnecting).toBe(true);
      expect(result.current.isConnected).toBe(false);
    });

    it('sets isConnected to true when connection opens', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      // Fast-forward past the connection timeout
      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.isConnected).toBe(true);
      expect(result.current.isConnecting).toBe(false);
    });

    it('closes connection on unmount', async () => {
      const { unmount } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      unmount();

      expect(mockWebSocketInstance?.close).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Message Handling Tests
  // ==============================================================================

  describe('Message Handling', () => {
    it('updates lastMessage when message received', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      const testMessage = { type: 'test', data: 'hello' };

      await act(async () => {
        mockWebSocketInstance?.simulateMessage(testMessage);
      });

      expect(result.current.lastMessage).toEqual(testMessage);
    });

    it('calls onMessage callback when provided', async () => {
      const onMessage = vi.fn();
      renderHook(() =>
        useWebSocket('ws://localhost:8001', { onMessage })
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      const testMessage = { type: 'test', data: 'hello' };

      await act(async () => {
        mockWebSocketInstance?.simulateMessage(testMessage);
      });

      expect(onMessage).toHaveBeenCalledWith(testMessage);
    });

    it('sendMessage sends data through WebSocket', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      const testData = { action: 'test' };

      act(() => {
        result.current.sendMessage(testData);
      });

      expect(mockWebSocketInstance?.send).toHaveBeenCalledWith(
        JSON.stringify(testData)
      );
    });
  });

  // ==============================================================================
  // Auto-Reconnect Tests
  // ==============================================================================

  describe('Auto-Reconnect', () => {
    it('attempts to reconnect after unexpected close', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001', { reconnectInterval: 1000 })
      );

      // Initial connection
      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.isConnected).toBe(true);

      // Simulate unexpected close - reconnect attempt increments immediately
      await act(async () => {
        mockWebSocketInstance?.simulateUnexpectedClose();
      });

      expect(result.current.isConnected).toBe(false);
      // Reconnect attempt is incremented on close (schedules reconnect)
      expect(result.current.reconnectAttempts).toBe(1);
    });

    it('uses exponential backoff for reconnection attempts', async () => {
      // Track how many WebSocket instances are created (to verify reconnect attempts)
      let wsInstanceCount = 0;

      vi.stubGlobal('WebSocket', class extends MockWebSocket {
        constructor(url: string) {
          super(url);
          wsInstanceCount++;
          mockWebSocketInstance = this;
          // Don't auto-connect for this test - we control the timing
        }
      });

      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001', {
          reconnectInterval: 1000,
          maxReconnectAttempts: 5,
        })
      );

      // Initial connection creates first WebSocket
      expect(wsInstanceCount).toBe(1);

      // Simulate initial connection
      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      // First close - schedules reconnect at 1000ms (base interval * 2^0)
      await act(async () => {
        mockWebSocketInstance?.simulateUnexpectedClose();
      });
      expect(result.current.reconnectAttempts).toBe(1);

      // After 1000ms, second WebSocket should be created
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });
      expect(wsInstanceCount).toBe(2);

      // Second close - schedules reconnect at 2000ms (base interval * 2^1)
      await act(async () => {
        mockWebSocketInstance?.simulateUnexpectedClose();
      });
      expect(result.current.reconnectAttempts).toBe(2);

      // After 2000ms, third WebSocket should be created
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });
      expect(wsInstanceCount).toBe(3);
    });

    it('stops reconnecting after max attempts', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001', {
          reconnectInterval: 100,
          maxReconnectAttempts: 3,
        })
      );

      // Initial connection
      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      // Simulate multiple disconnections
      for (let i = 0; i < 5; i++) {
        await act(async () => {
          mockWebSocketInstance?.simulateUnexpectedClose();
          vi.advanceTimersByTime(100 * Math.pow(2, i));
        });
      }

      // Should stop at max attempts
      expect(result.current.reconnectAttempts).toBeLessThanOrEqual(3);
    });

    it('does not reconnect when autoReconnect is false', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001', { autoReconnect: false })
      );

      // Initial connection
      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      // Simulate unexpected close
      await act(async () => {
        mockWebSocketInstance?.simulateUnexpectedClose();
      });

      // Advance timer
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      expect(result.current.reconnectAttempts).toBe(0);
    });

    it('resets reconnect attempts on successful connection', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001', { reconnectInterval: 100 })
      );

      // Initial connection
      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.isConnected).toBe(true);
      expect(result.current.reconnectAttempts).toBe(0);

      // Simulate disconnect
      await act(async () => {
        mockWebSocketInstance?.simulateUnexpectedClose();
      });

      expect(result.current.reconnectAttempts).toBe(1);

      // Wait for reconnect timer and new connection
      await act(async () => {
        vi.advanceTimersByTime(100); // reconnect timer
        vi.advanceTimersByTime(20);  // connection time
      });

      // Attempts should reset to 0 on successful connection
      expect(result.current.reconnectAttempts).toBe(0);
      expect(result.current.isConnected).toBe(true);
    });
  });

  // ==============================================================================
  // Error Handling Tests
  // ==============================================================================

  describe('Error Handling', () => {
    it('sets connectionError on WebSocket error', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      await act(async () => {
        mockWebSocketInstance?.simulateError();
      });

      expect(result.current.connectionError).not.toBeNull();
    });

    it('calls onError callback when provided', async () => {
      const onError = vi.fn();
      renderHook(() =>
        useWebSocket('ws://localhost:8001', { onError })
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      await act(async () => {
        mockWebSocketInstance?.simulateError();
      });

      expect(onError).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Manual Control Tests
  // ==============================================================================

  describe('Manual Control', () => {
    it('connect method creates new connection', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001', { autoConnect: false })
      );

      // Should not connect automatically
      expect(mockWebSocketInstance).toBeNull();

      act(() => {
        result.current.connect();
      });

      // Should now have a connection
      expect(mockWebSocketInstance).not.toBeNull();
    });

    it('disconnect method closes connection', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001')
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        result.current.disconnect();
      });

      expect(mockWebSocketInstance?.close).toHaveBeenCalled();
      expect(result.current.isConnected).toBe(false);
    });

    it('disconnect prevents auto-reconnect', async () => {
      const { result } = renderHook(() =>
        useWebSocket('ws://localhost:8001', { reconnectInterval: 100 })
      );

      await act(async () => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        result.current.disconnect();
      });

      // Advance timer
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      // Should not have attempted to reconnect
      expect(result.current.reconnectAttempts).toBe(0);
    });
  });
});
