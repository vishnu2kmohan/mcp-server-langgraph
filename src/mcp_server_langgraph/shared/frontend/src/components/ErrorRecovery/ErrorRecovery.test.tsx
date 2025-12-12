/**
 * ErrorRecovery Component Tests
 *
 * TDD: RED phase - Write tests first
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorRecovery, classifyError, getRecoverySuggestions } from './ErrorRecovery';

describe('ErrorRecovery Component', () => {
  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders error message', () => {
      render(
        <ErrorRecovery
          error={new Error('A specific error occurred')}
          onRetry={vi.fn()}
        />
      );

      expect(screen.getByText('A specific error occurred')).toBeInTheDocument();
    });

    it('renders error title based on error type', () => {
      render(
        <ErrorRecovery
          error={new Error('Network error')}
          errorType="network"
          onRetry={vi.fn()}
        />
      );

      expect(screen.getByText(/connection problem/i)).toBeInTheDocument();
    });

    it('renders recovery suggestions', () => {
      render(
        <ErrorRecovery
          error={new Error('Failed to connect')}
          errorType="network"
          onRetry={vi.fn()}
        />
      );

      expect(screen.getByText(/check your internet connection/i)).toBeInTheDocument();
    });

    it('renders retry button', () => {
      render(
        <ErrorRecovery
          error={new Error('Failed')}
          onRetry={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('renders dismiss button when onDismiss provided', () => {
      render(
        <ErrorRecovery
          error={new Error('Failed')}
          onRetry={vi.fn()}
          onDismiss={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Interaction Tests
  // ==============================================================================

  describe('Interactions', () => {
    it('calls onRetry when retry button clicked', () => {
      const onRetry = vi.fn();
      render(
        <ErrorRecovery
          error={new Error('Failed')}
          onRetry={onRetry}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /retry/i }));
      expect(onRetry).toHaveBeenCalled();
    });

    it('calls onDismiss when dismiss button clicked', () => {
      const onDismiss = vi.fn();
      render(
        <ErrorRecovery
          error={new Error('Failed')}
          onRetry={vi.fn()}
          onDismiss={onDismiss}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
      expect(onDismiss).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Error Classification Tests
  // ==============================================================================

  describe('classifyError', () => {
    it('classifies network errors', () => {
      expect(classifyError(new Error('NetworkError'))).toBe('network');
      expect(classifyError(new Error('Failed to fetch'))).toBe('network');
      expect(classifyError(new Error('net::ERR_CONNECTION_REFUSED'))).toBe('network');
    });

    it('classifies timeout errors', () => {
      expect(classifyError(new Error('Request timeout'))).toBe('timeout');
      expect(classifyError(new Error('ETIMEDOUT'))).toBe('timeout');
    });

    it('classifies authentication errors', () => {
      expect(classifyError(new Error('401 Unauthorized'))).toBe('auth');
      expect(classifyError(new Error('403 Forbidden'))).toBe('auth');
      expect(classifyError(new Error('Invalid token'))).toBe('auth');
    });

    it('classifies validation errors', () => {
      expect(classifyError(new Error('Validation failed'))).toBe('validation');
      expect(classifyError(new Error('Invalid input'))).toBe('validation');
    });

    it('classifies server errors', () => {
      expect(classifyError(new Error('500 Internal Server Error'))).toBe('server');
      expect(classifyError(new Error('503 Service Unavailable'))).toBe('server');
    });

    it('returns unknown for unclassified errors', () => {
      expect(classifyError(new Error('Random error'))).toBe('unknown');
    });
  });

  // ==============================================================================
  // Recovery Suggestions Tests
  // ==============================================================================

  describe('getRecoverySuggestions', () => {
    it('provides network error suggestions', () => {
      const suggestions = getRecoverySuggestions('network');
      expect(suggestions).toContain('Check your internet connection');
      expect(suggestions.length).toBeGreaterThan(0);
    });

    it('provides timeout suggestions', () => {
      const suggestions = getRecoverySuggestions('timeout');
      expect(suggestions.some(s => s.toLowerCase().includes('wait'))).toBe(true);
    });

    it('provides auth suggestions', () => {
      const suggestions = getRecoverySuggestions('auth');
      expect(suggestions.some(s => s.toLowerCase().includes('log'))).toBe(true);
    });

    it('provides validation suggestions', () => {
      const suggestions = getRecoverySuggestions('validation');
      expect(suggestions.some(s => s.toLowerCase().includes('check'))).toBe(true);
    });

    it('provides server error suggestions', () => {
      const suggestions = getRecoverySuggestions('server');
      expect(suggestions.some(s => s.toLowerCase().includes('try again'))).toBe(true);
    });

    it('provides generic suggestions for unknown errors', () => {
      const suggestions = getRecoverySuggestions('unknown');
      expect(suggestions.length).toBeGreaterThan(0);
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has alert role for error messages', () => {
      render(
        <ErrorRecovery
          error={new Error('Error')}
          onRetry={vi.fn()}
        />
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('has proper aria-live for announcements', () => {
      render(
        <ErrorRecovery
          error={new Error('Error')}
          onRetry={vi.fn()}
        />
      );

      expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive');
    });
  });

  // ==============================================================================
  // Variant Tests
  // ==============================================================================

  describe('Variants', () => {
    it('supports inline variant', () => {
      render(
        <ErrorRecovery
          error={new Error('Error')}
          onRetry={vi.fn()}
          variant="inline"
        />
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('supports modal variant', () => {
      render(
        <ErrorRecovery
          error={new Error('Error')}
          onRetry={vi.fn()}
          variant="modal"
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('supports toast variant', () => {
      render(
        <ErrorRecovery
          error={new Error('Error')}
          onRetry={vi.fn()}
          variant="toast"
        />
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});
