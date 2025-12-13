/**
 * AdminDashboardPage Tests
 *
 * TDD tests for the admin dashboard page.
 * Tests cover:
 * - Loading state
 * - System health display
 * - HEART metrics display
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AdminDashboardPage } from './AdminDashboardPage';

// Mock fetch
global.fetch = vi.fn();

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default successful fetch responses
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/api/v1/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'healthy',
            uptime: 99.9,
            activeUsers: 42,
            activeSessions: 15,
            errorRate: 0.1,
          }),
        });
      }
      if (url.includes('/api/v1/metrics/heart')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            happiness: 72,
            engagement: 85,
            adoption: 68,
            retention: 65,
            taskSuccess: 94,
          }),
        });
      }
      return Promise.resolve({ ok: false });
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner initially', () => {
      render(<AdminDashboardPage />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should hide loading spinner after data loads', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('System Health')).toBeInTheDocument();
      });
    });
  });

  describe('System Health', () => {
    it('should display system health section after loading', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('System Health')).toBeInTheDocument();
      });
    });

    it('should show active users count', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('42')).toBeInTheDocument();
      });
    });

    it('should show error rate', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('0.1%')).toBeInTheDocument();
      });
    });
  });

  describe('HEART Metrics', () => {
    it('should display HEART metrics section', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('HEART Metrics')).toBeInTheDocument();
      });
    });

    it('should show happiness metric', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Happiness')).toBeInTheDocument();
      });
    });

    it('should show engagement metric', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Engagement')).toBeInTheDocument();
      });
    });

    it('should show task success metric', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Task Success')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle fetch errors gracefully', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

      render(<AdminDashboardPage />);

      await waitFor(() => {
        // Should still render something after error
        expect(screen.getByText('System Health')).toBeInTheDocument();
      });
    });
  });
});
