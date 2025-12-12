/**
 * Tests for MetricsDashboard Component
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MetricsDashboard, type DashboardData } from './MetricsDashboard';

const mockDashboardData: DashboardData = {
  builder: {
    period: '7d',
    nps_score_avg: 8.5,
    task_success_rate: 0.85,
    total_tasks_started: 100,
    total_tasks_completed: 85,
    total_tasks_errored: 15,
    avg_session_duration_ms: 180000,
    total_interactions: 500,
    top_features: { code_generation: 50, dark_mode: 30 },
    new_users_count: 10,
  },
  playground: {
    period: '7d',
    nps_score_avg: 9.0,
    task_success_rate: 0.92,
    total_tasks_started: 200,
    total_tasks_completed: 184,
    total_tasks_errored: 16,
    avg_session_duration_ms: 240000,
    total_interactions: 800,
    top_features: { mcp_tools: 80, prompt_explorer: 60 },
    new_users_count: 15,
  },
  total_metrics_count: 300,
  total_events_count: 1300,
  generated_at: '2024-01-01T12:00:00Z',
};

describe('MetricsDashboard Component', () => {
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn().mockResolvedValue(mockDashboardData);
  });

  // ==============================================================================
  // Loading State Tests
  // ==============================================================================

  describe('Loading State', () => {
    it('shows loading skeleton while fetching data', async () => {
      const pendingFetch = vi.fn(() => new Promise(() => {})); // Never resolves

      render(<MetricsDashboard fetchDashboard={pendingFetch} />);

      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Data Display Tests
  // ==============================================================================

  describe('Data Display', () => {
    it('renders dashboard title', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/heart metrics dashboard/i)).toBeInTheDocument();
      });
    });

    it('displays builder metrics card', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/builder/i)).toBeInTheDocument();
      });
    });

    it('displays playground metrics card', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/playground/i)).toBeInTheDocument();
      });
    });

    it('displays NPS scores', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/8.5/)).toBeInTheDocument(); // Builder NPS
        expect(screen.getByText(/9.0/)).toBeInTheDocument(); // Playground NPS
      });
    });

    it('displays task success rates', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/85%/)).toBeInTheDocument();
        expect(screen.getByText(/92%/)).toBeInTheDocument();
      });
    });

    it('displays total metrics and events count', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/total metrics/i)).toBeInTheDocument();
        expect(screen.getByText(/total events/i)).toBeInTheDocument();
        // 300 appears in metrics count and 1,300 in events count
        expect(screen.getAllByText(/300/).length).toBeGreaterThanOrEqual(1);
      });
    });

    it('displays generated timestamp', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/last updated/i)).toBeInTheDocument();
      });
    });
  });

  // ==============================================================================
  // Refresh Tests
  // ==============================================================================

  describe('Refresh', () => {
    it('has refresh button', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });
    });

    it('fetches new data on refresh', async () => {
      const user = userEvent.setup();
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /refresh/i }));

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  // ==============================================================================
  // Error Handling Tests
  // ==============================================================================

  describe('Error Handling', () => {
    it('shows error message when fetch fails', async () => {
      const failingFetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

      render(<MetricsDashboard fetchDashboard={failingFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
      });
    });

    it('shows retry button on error', async () => {
      const failingFetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

      render(<MetricsDashboard fetchDashboard={failingFetch} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });
  });

  // ==============================================================================
  // Metrics Detail Tests
  // ==============================================================================

  describe('Metrics Details', () => {
    it('displays session duration in readable format', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        // 180000ms = 3 minutes, 240000ms = 4 minutes
        expect(screen.getByText(/3.*min/i)).toBeInTheDocument();
      });
    });

    it('displays top features', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByText(/code generation/i)).toBeInTheDocument();
      });
    });

    it('displays new users count', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        // Multiple "New Users" labels appear (one in each app card)
        expect(screen.getAllByText(/new users/i).length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has accessible headings', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /heart metrics/i })).toBeInTheDocument();
      });
    });

    it('has accessible region landmarks', async () => {
      render(<MetricsDashboard fetchDashboard={mockFetch} />);

      await waitFor(() => {
        expect(screen.getByRole('region', { name: /builder metrics/i })).toBeInTheDocument();
        expect(screen.getByRole('region', { name: /playground metrics/i })).toBeInTheDocument();
      });
    });
  });
});
