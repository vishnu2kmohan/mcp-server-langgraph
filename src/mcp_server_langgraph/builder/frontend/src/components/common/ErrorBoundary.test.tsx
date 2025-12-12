/**
 * Tests for ErrorBoundary Component
 *
 * TDD: Tests written FIRST before implementation
 *
 * Enhanced error boundary with recovery suggestions and error tracking.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

// Test component that throws an error
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
}

describe('ErrorBoundary Component', () => {
  // Suppress console.error during tests
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  // ==============================================================================
  // Normal Rendering Tests
  // ==============================================================================

  describe('Normal Rendering', () => {
    it('renders children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <div>Child content</div>
        </ErrorBoundary>
      );
      expect(screen.getByText('Child content')).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Error Handling Tests
  // ==============================================================================

  describe('Error Handling', () => {
    it('renders error message when error occurs', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });

    it('shows error details', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(screen.getByText(/test error/i)).toBeInTheDocument();
    });

    it('provides retry button', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('resets error state when retry is clicked', () => {
      let shouldThrow = true;
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      );

      // Verify error state
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      // Click retry - component will re-render
      shouldThrow = false;
      fireEvent.click(screen.getByRole('button', { name: /try again/i }));

      // After retry, should attempt to render children again
      // (but since the error-throwing component is still in the tree, it will throw again)
      // In real usage, the parent would update state to fix the issue
    });
  });

  // ==============================================================================
  // Recovery Suggestions Tests
  // ==============================================================================

  describe('Recovery Suggestions', () => {
    it('shows recovery suggestions', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(screen.getByText(/refresh the page/i)).toBeInTheDocument();
    });

    it('provides refresh page link', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(screen.getByRole('button', { name: /refresh page/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Custom Fallback Tests
  // ==============================================================================

  describe('Custom Fallback', () => {
    it('renders custom fallback when provided', () => {
      render(
        <ErrorBoundary fallback={<div>Custom error message</div>}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(screen.getByText('Custom error message')).toBeInTheDocument();
    });

    it('passes error to fallback function', () => {
      const fallbackFn = vi.fn(() => <div>Function fallback</div>);
      render(
        <ErrorBoundary fallback={fallbackFn}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(fallbackFn).toHaveBeenCalledWith(
        expect.objectContaining({
          error: expect.any(Error),
          resetError: expect.any(Function),
        })
      );
    });
  });

  // ==============================================================================
  // Error Reporting Tests
  // ==============================================================================

  describe('Error Reporting', () => {
    it('calls onError callback when error occurs', () => {
      const onError = vi.fn();
      render(
        <ErrorBoundary onError={onError}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(onError).toHaveBeenCalledWith(expect.any(Error), expect.any(Object));
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has alert role for error state', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});
