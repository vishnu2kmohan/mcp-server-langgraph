/**
 * Shared fixtures for useRealtimeSync tests
 *
 * Provides MockWebSocket class, mock token validation, and helper functions
 * shared across all useRealtimeSync test shards.
 */
import { vi } from "vitest";
import { act } from "@testing-library/react";

/**
 * Mock WebSocket implementation for testing
 */
export class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateRawMessage(data: string) {
    this.onmessage?.({ data });
  }

  simulateClose(code = 1006) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code });
  }

  simulateError(event: unknown) {
    this.onerror?.(event);
  }

  static instances: MockWebSocket[] = [];
  static reset() {
    MockWebSocket.instances = [];
  }
  static getLastInstance(): MockWebSocket | undefined {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }
}

/**
 * Mock implementation of ensureValidTokenForWebSocket
 */
export const mockEnsureValidTokenForWebSocket = vi.fn();

/**
 * Helper to wait for proactive token validation promise to resolve.
 * The new createConnection() calls ensureValidTokenForWebSocket().then(...)
 * which is async, so we need to flush promises before accessing WebSocket.
 */
export async function waitForTokenValidation() {
  await act(async () => {
    await Promise.resolve();
  });
}
