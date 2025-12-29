/**
 * Custom test utilities for React Testing Library
 *
 * Provides a custom render function that wraps components with
 * necessary providers (MCPHost, theme, etc.)
 */

import React, { ReactElement, ReactNode } from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

/**
 * Provider wrapper for tests
 *
 * Wraps components with all necessary context providers.
 * Add new providers here as they are created.
 */
interface ProvidersProps {
  children: ReactNode;
}

function AllProviders({ children }: ProvidersProps): ReactElement {
  // Add context providers here as they are created
  // e.g., <MCPHostProvider><ThemeProvider>{children}</ThemeProvider></MCPHostProvider>
  return <>{children}</>;
}

/**
 * Custom render options extending Testing Library options
 */
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  /**
   * Initial route for router testing (future use)
   */
  route?: string;
}

/**
 * Custom render function that wraps components with providers
 *
 * @param ui - React element to render
 * @param options - Render options
 * @returns Render result with user event instance
 *
 * @example
 * ```tsx
 * const { user, getByText } = renderWithProviders(<MyComponent />);
 * await user.click(getByText('Submit'));
 * ```
 */
function renderWithProviders(
  ui: ReactElement,
  options?: CustomRenderOptions
): RenderResult & { user: ReturnType<typeof userEvent.setup> } {
  const user = userEvent.setup();

  return {
    user,
    ...render(ui, { wrapper: AllProviders, ...options }),
  };
}

/**
 * Create a mock function with type safety
 */
export function createMockFn<T extends (...args: unknown[]) => unknown>(): T {
  return vi.fn() as unknown as T;
}

/**
 * Wait for a condition to be true
 *
 * @param condition - Function that returns true when condition is met
 * @param timeout - Maximum time to wait in ms (default: 1000)
 * @param interval - Check interval in ms (default: 50)
 */
export async function waitForCondition(
  condition: () => boolean,
  timeout = 1000,
  interval = 50
): Promise<void> {
  const startTime = Date.now();
  while (!condition()) {
    if (Date.now() - startTime > timeout) {
      throw new Error('Timeout waiting for condition');
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
}

/**
 * Create a deferred promise for async testing
 */
export function createDeferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
} {
  let resolve: (value: T) => void = () => {};
  let reject: (reason?: unknown) => void = () => {};

  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return { promise, resolve, reject };
}

/**
 * Mock fetch response helper
 */
export function mockFetchResponse<T>(data: T, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Mock NDJSON stream response for MCP StreamableHTTP
 */
export function mockNDJSONStream(chunks: object[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;

  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        const chunk = JSON.stringify(chunks[index]) + '\n';
        controller.enqueue(encoder.encode(chunk));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

// Re-export everything from Testing Library
export * from '@testing-library/react';
export { userEvent };

// Export custom render as default render
export { renderWithProviders as render };
