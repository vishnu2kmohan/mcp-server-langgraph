/**
 * AdminDashboardPage Tests
 *
 * TDD tests for the admin dashboard page.
 * Tests cover:
 * - Loading state
 * - System health display
 * - HEART metrics display
 * - Error handling
 * - Refresh functionality
 * - Status indicators
 * - API fallbacks
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

    it('should set degraded status on error', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('degraded')).toBeInTheDocument();
      });
    });
  });

  describe('Dashboard Header', () => {
    it('should display dashboard title', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
      });
    });

    it('should have refresh button', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeInTheDocument();
      });
    });
  });

  describe('Refresh Functionality', () => {
    it('should call refresh when button clicked', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeInTheDocument();
      });

      const refreshButton = screen.getByText('Refresh');
      fireEvent.click(refreshButton);

      // Verify fetch was called again (initial load + refresh)
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(4); // 2 initial + 2 refresh
      });
    });

    it('should show loading state during refresh', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Refresh')).toBeInTheDocument();
      });

      // Create a delayed response for refresh
      let resolveHealth: (value: unknown) => void;
      const healthPromise = new Promise((resolve) => {
        resolveHealth = resolve;
      });

      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
        if (url.includes('/api/v1/health')) {
          return healthPromise;
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        });
      });

      const refreshButton = screen.getByText('Refresh');
      fireEvent.click(refreshButton);

      // Should show loading
      await waitFor(() => {
        expect(document.querySelector('.animate-spin')).toBeInTheDocument();
      });

      // Resolve the promise
      resolveHealth!({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy' }),
      });

      await waitFor(() => {
        expect(screen.getByText('System Health')).toBeInTheDocument();
      });
    });
  });

  describe('System Health Extended', () => {
    it('should show uptime percentage', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('99.9%')).toBeInTheDocument();
      });
    });

    it('should show active users label', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Active Users')).toBeInTheDocument();
      });
    });

    it('should show uptime label', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Uptime')).toBeInTheDocument();
      });
    });

    it('should show error rate label', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Error Rate')).toBeInTheDocument();
      });
    });

    it('should display healthy status', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('healthy')).toBeInTheDocument();
      });
    });

    it('should display status label', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Status')).toBeInTheDocument();
      });
    });
  });

  describe('HEART Metrics Extended', () => {
    it('should show adoption metric', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Adoption')).toBeInTheDocument();
      });
    });

    it('should show retention metric', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Retention')).toBeInTheDocument();
      });
    });

    it('should display metric values with percentages', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        // Check happiness value (72%)
        expect(screen.getByText('72%')).toBeInTheDocument();
        // Check engagement value (85%)
        expect(screen.getByText('85%')).toBeInTheDocument();
      });
    });

    it('should display all five HEART metrics', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('Happiness')).toBeInTheDocument();
        expect(screen.getByText('Engagement')).toBeInTheDocument();
        expect(screen.getByText('Adoption')).toBeInTheDocument();
        expect(screen.getByText('Retention')).toBeInTheDocument();
        expect(screen.getByText('Task Success')).toBeInTheDocument();
      });
    });
  });

  describe('API Fallback', () => {
    it('should use mock data when health API returns !ok', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
        if (url.includes('/api/v1/health')) {
          return Promise.resolve({
            ok: false,
            json: () => Promise.resolve({}),
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

      render(<AdminDashboardPage />);

      await waitFor(() => {
        // Should still display with fallback data
        expect(screen.getByText('System Health')).toBeInTheDocument();
        expect(screen.getByText('42')).toBeInTheDocument(); // Fallback active users
      });
    });

    it('should use mock data when metrics API returns !ok', async () => {
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
            ok: false,
            json: () => Promise.resolve({}),
          });
        }
        return Promise.resolve({ ok: false });
      });

      render(<AdminDashboardPage />);

      await waitFor(() => {
        // Should still display with fallback HEART data
        expect(screen.getByText('HEART Metrics')).toBeInTheDocument();
        expect(screen.getByText('72%')).toBeInTheDocument(); // Fallback happiness
      });
    });
  });

  describe('Degraded Status', () => {
    it('should display degraded status when API returns degraded', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
        if (url.includes('/api/v1/health')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'degraded',
              uptime: 95.0,
              activeUsers: 10,
              activeSessions: 3,
              errorRate: 5.0,
            }),
          });
        }
        if (url.includes('/api/v1/metrics/heart')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              happiness: 50,
              engagement: 40,
              adoption: 30,
              retention: 20,
              taskSuccess: 60,
            }),
          });
        }
        return Promise.resolve({ ok: false });
      });

      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('degraded')).toBeInTheDocument();
      });
    });

    it('should handle unhealthy status from API', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
        if (url.includes('/api/v1/health')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'unhealthy',
              uptime: 50.0,
              activeUsers: 0,
              activeSessions: 0,
              errorRate: 50.0,
            }),
          });
        }
        if (url.includes('/api/v1/metrics/heart')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              happiness: 10,
              engagement: 10,
              adoption: 10,
              retention: 10,
              taskSuccess: 10,
            }),
          });
        }
        return Promise.resolve({ ok: false });
      });

      render(<AdminDashboardPage />);

      await waitFor(() => {
        // unhealthy maps to degraded in the component logic
        expect(screen.getByText('degraded')).toBeInTheDocument();
      });
    });
  });

  describe('Data Loading', () => {
    it('should fetch health and metrics on mount', async () => {
      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith('/api/v1/health');
        expect(global.fetch).toHaveBeenCalledWith('/api/v1/metrics/heart');
      });
    });

    it('should display data from API response', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
        if (url.includes('/api/v1/health')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              status: 'healthy',
              uptime: 88.5,
              activeUsers: 100,
              activeSessions: 25,
              errorRate: 2.5,
            }),
          });
        }
        if (url.includes('/api/v1/metrics/heart')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              happiness: 90,
              engagement: 95,
              adoption: 80,
              retention: 75,
              taskSuccess: 98,
            }),
          });
        }
        return Promise.resolve({ ok: false });
      });

      render(<AdminDashboardPage />);

      await waitFor(() => {
        expect(screen.getByText('100')).toBeInTheDocument(); // activeUsers
        expect(screen.getByText('88.5%')).toBeInTheDocument(); // uptime
        expect(screen.getByText('2.5%')).toBeInTheDocument(); // errorRate
        expect(screen.getByText('90%')).toBeInTheDocument(); // happiness
      });
    });
  });
});
