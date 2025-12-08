/**
 * Vitest Type Declarations
 *
 * Extends Vitest's matchers with @testing-library/jest-dom matchers
 * and provides Node.js global types for test environment.
 */

import type { TestingLibraryMatchers } from '@testing-library/jest-dom/matchers';

declare module 'vitest' {
  interface Assertion<T = any> extends TestingLibraryMatchers<T, void> {}
  interface AsymmetricMatchersContaining extends TestingLibraryMatchers<any, void> {}
}

// Declare globalThis properties for test environment
declare global {
  // eslint-disable-next-line no-var
  var ResizeObserver: typeof ResizeObserver;
  // eslint-disable-next-line no-var
  var IntersectionObserver: typeof IntersectionObserver;
  // eslint-disable-next-line no-var
  var DOMRect: {
    fromRect: (rect?: DOMRectInit) => DOMRect;
  };
  // eslint-disable-next-line no-var
  var PointerEvent: typeof PointerEvent;
}

export {};
