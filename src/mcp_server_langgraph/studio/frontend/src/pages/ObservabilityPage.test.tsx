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

describe('ObservabilityPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
    it('should display logs after loading', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.queryByText('chat/completion')).toBeInTheDocument();
      }, { timeout: 1000 });

      fireEvent.click(screen.getByText('Logs'));

      await waitFor(() => {
        expect(screen.getByText('Session started')).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });

  describe('Metrics Tab', () => {
    it('should display metrics after loading', async () => {
      render(<ObservabilityPage />);

      await waitFor(() => {
        expect(screen.queryByText('chat/completion')).toBeInTheDocument();
      }, { timeout: 1000 });

      fireEvent.click(screen.getByText('Metrics'));

      await waitFor(() => {
        expect(screen.getByText('Requests / min')).toBeInTheDocument();
        expect(screen.getByText('Avg Response Time')).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });
});
