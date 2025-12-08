/**
 * Tests for Session Timeout Warning Component
 *
 * TDD: Tests written FIRST before implementation
 *
 * This component displays a warning banner/modal when the session
 * is about to expire, with countdown and refresh option.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { SessionTimeoutWarning } from './SessionTimeoutWarning';

describe('SessionTimeoutWarning Component', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // Helper to advance timers inside act()
  const advanceTimers = async (ms: number) => {
    await act(async () => {
      vi.advanceTimersByTime(ms);
    });
  };

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('does not render when session is not in warning state', () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('renders warning when session enters warning state', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      // Advance to warning state (past 30s threshold)
      await advanceTimers(35000);

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('displays remaining time in warning', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      // Advance to 25 seconds remaining
      await advanceTimers(35000);

      // Should show ~25 seconds remaining as "0:25" or similar
      expect(screen.getByText(/0:2[0-9]/)).toBeInTheDocument();
    });

    it('displays warning title', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      await advanceTimers(35000);

      // Check for the specific heading in warning state
      expect(screen.getByRole('heading', { name: /session expiring soon/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Refresh Action Tests
  // ==============================================================================

  describe('Refresh Action', () => {
    it('has a refresh/continue button', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      await advanceTimers(35000);

      expect(screen.getByRole('button', { name: /continue|refresh|extend/i })).toBeInTheDocument();
    });

    it('hides warning when refresh button is clicked', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      await advanceTimers(35000);

      expect(screen.getByRole('alert')).toBeInTheDocument();

      const refreshButton = screen.getByRole('button', { name: /continue|refresh|extend/i });

      await act(async () => {
        refreshButton.click();
      });

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('calls onRefresh callback when refresh button is clicked', async () => {
      const onRefresh = vi.fn();

      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
          onRefresh={onRefresh}
        />
      );

      await advanceTimers(35000);

      expect(screen.getByRole('alert')).toBeInTheDocument();

      const refreshButton = screen.getByRole('button', { name: /continue|refresh|extend/i });

      await act(async () => {
        refreshButton.click();
      });

      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  // ==============================================================================
  // Expiration Tests
  // ==============================================================================

  describe('Expiration', () => {
    it('calls onExpire callback when session expires', async () => {
      const onExpire = vi.fn();

      render(
        <SessionTimeoutWarning
          sessionDuration={5000}
          warningThreshold={3000}
          onExpire={onExpire}
        />
      );

      // Advance past session expiration
      await advanceTimers(6000);

      expect(onExpire).toHaveBeenCalledTimes(1);
    });

    it('shows expired message when session expires', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={5000}
          warningThreshold={3000}
        />
      );

      await advanceTimers(6000);

      // Check for the specific "Session Expired" heading
      expect(screen.getByRole('heading', { name: /session expired/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Styling/Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has appropriate ARIA role', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      await advanceTimers(35000);

      const alert = screen.getByRole('alert');
      expect(alert).toBeInTheDocument();
    });

    it('has visible focus on refresh button', async () => {
      render(
        <SessionTimeoutWarning
          sessionDuration={60000}
          warningThreshold={30000}
        />
      );

      await advanceTimers(35000);

      const button = screen.getByRole('button', { name: /continue|refresh|extend/i });
      expect(button).toBeInTheDocument();

      // Focus on the button directly
      button.focus();
      expect(button).toHaveFocus();
    });
  });
});
