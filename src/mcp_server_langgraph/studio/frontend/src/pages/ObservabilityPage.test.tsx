/**
 * ObservabilityPage Tests
 *
 * TDD tests for the observability page.
 * Tests cover:
 * - Tab navigation
 * - Traces display
 * - Logs display
 * - Metrics display
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ObservabilityPage } from './ObservabilityPage';

// Mock fetch
global.fetch = vi.fn();

describe('ObservabilityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock successful API response
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        traces: [
          { id: '1', name: 'chat/completion', duration: 1234, status: 'success', timestamp: new Date().toISOString(), spans: 5 },
          { id: '2', name: 'tools/execute', duration: 567, status: 'success', timestamp: new Date(Date.now() - 60000).toISOString(), spans: 3 },
          { id: '3', name: 'workflow/run', duration: 2345, status: 'running', timestamp: new Date(Date.now() - 120000).toISOString(), spans: 8 },
        ],
      }),
    });
  });

  describe('Header', () => {
    it('should display page title', () => {
      render(<ObservabilityPage />);

      expect(screen.getByText('Observability')).toBeInTheDocument();
    });

    it('should display page description', () => {
      render(<ObservabilityPage />);

      expect(screen.getByText(/Monitor traces, logs, and metrics/)).toBeInTheDocument();
    });

    it('should have refresh button', () => {
      render(<ObservabilityPage />);

      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });
  });

  describe('Tabs', () => {
    it('should have Traces tab', () => {
      render(<ObservabilityPage />);

      expect(screen.getByText('Traces')).toBeInTheDocument();
    });

    it('should have Logs tab', () => {
      render(<ObservabilityPage />);

      expect(screen.getByText('Logs')).toBeInTheDocument();
    });

    it('should have Metrics tab', () => {
      render(<ObservabilityPage />);

      expect(screen.getByText('Metrics')).toBeInTheDocument();
    });

    it('should switch to Logs tab when clicked', async () => {
      render(<ObservabilityPage />);

      // Wait for initial load
      await waitFor(() => {
        expect(screen.queryByText('chat/completion')).toBeInTheDocument();
      }, { timeout: 1000 });

      fireEvent.click(screen.getByText('Logs'));

      // Should show logs content
      await waitFor(() => {
        expect(screen.getByText('Session started')).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner initially', () => {
      render(<ObservabilityPage />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('API Integration', () => {
    it('should call traces API on mount', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/observability/traces'),
          expect.objectContaining({ method: 'GET' })
        );
      });
    });

    it('should handle API errors', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
      });

      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load traces/i)).toBeInTheDocument();
      });
    });
  });

  describe('Traces Tab', () => {
    it('should display traces after loading', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText('chat/completion')).toBeInTheDocument();
      }, { timeout: 1000 });
    });

    it('should show trace status badges', async () => {
      render(<ObservabilityPage />);

      // Wait for loading to complete first
      await waitFor(() => {
        expect(screen.getByText('chat/completion')).toBeInTheDocument();
      }, { timeout: 2000 });

      // Now check for status badge - there are multiple traces, one with "success"
      expect(screen.getAllByText('success').length).toBeGreaterThan(0);
    });

    it('should show trace duration', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/1234ms/)).toBeInTheDocument();
      }, { timeout: 1000 });
    });

    it('should show span count', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.getByText(/5 spans/)).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });

  describe('Logs Tab', () => {
    it('should display coming soon badge for logs', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.queryByText('chat/completion')).toBeInTheDocument();
      }, { timeout: 1000 });

      fireEvent.click(screen.getByText('Logs'));

      await waitFor(() => {
        expect(screen.getByText(/Coming Soon/i)).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });

  describe('Metrics Tab', () => {
    it('should display coming soon badge for metrics', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.queryByText('chat/completion')).toBeInTheDocument();
      }, { timeout: 1000 });

      fireEvent.click(screen.getByText('Metrics'));

      await waitFor(() => {
        expect(screen.getByText(/Coming Soon/i)).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });
});
