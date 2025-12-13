/**
 * CostPage Tests
 *
 * TDD tests for the cost tracking dashboard page.
 * Tests cover:
 * - Loading state
 * - Cost summary display
 * - Cost by model display
 * - Period selector
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { CostPage } from './CostPage';

// Mock fetch
global.fetch = vi.fn();

describe('CostPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/api/v1/cost/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            total_cost: 125.50,
            total_tokens: 500000,
            period: 'week',
          }),
        });
      }
      if (url.includes('/api/v1/cost/by-model')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            models: [
              { model: 'gpt-4', cost: 75.00, tokens: 200000 },
              { model: 'gpt-3.5-turbo', cost: 50.50, tokens: 300000 },
            ],
          }),
        });
      }
      return Promise.resolve({ ok: false });
    });
  });

  describe('Header', () => {
    it('should display page title', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText('Cost Dashboard')).toBeInTheDocument();
      });
    });

    it('should display page description', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Track and analyze LLM usage costs/i)).toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner initially', () => {
      render(<CostPage />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should hide loading spinner after data loads', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
      });
    });
  });

  describe('Cost Summary', () => {
    it('should display total cost', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/\$125\.50/)).toBeInTheDocument();
      });
    });

    it('should display total tokens', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/500,000/)).toBeInTheDocument();
      });
    });

    it('should display period label', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/week/i)).toBeInTheDocument();
      });
    });
  });

  describe('Cost by Model', () => {
    it('should display cost by model section heading', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Cost by Model/i)).toBeInTheDocument();
      });
    });

    it('should display model names', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText('gpt-4')).toBeInTheDocument();
        expect(screen.getByText('gpt-3.5-turbo')).toBeInTheDocument();
      });
    });

    it('should display model costs', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/\$75\.00/)).toBeInTheDocument();
        expect(screen.getByText(/\$50\.50/)).toBeInTheDocument();
      });
    });

    it('should display model token counts', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/200,000/)).toBeInTheDocument();
        expect(screen.getByText(/300,000/)).toBeInTheDocument();
      });
    });
  });

  describe('Period Selector', () => {
    it('should have period selector dropdown', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });

    it('should have day option', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Day/i)).toBeInTheDocument();
      });
    });

    it('should have week option', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Week/i)).toBeInTheDocument();
      });
    });

    it('should have month option', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Month/i)).toBeInTheDocument();
      });
    });

    it('should fetch new data when period changes', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText('Cost Dashboard')).toBeInTheDocument();
      });

      const select = screen.getByRole('combobox');
      fireEvent.change(select, { target: { value: 'day' } });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('period=day'),
          expect.any(Object)
        );
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message when API fails', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
      });

      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load cost summary/i)).toBeInTheDocument();
      });
    });

    it('should show retry button on error', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
      });

      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Retry/i)).toBeInTheDocument();
      });
    });

    it('should retry fetching data when retry button is clicked', async () => {
      let callCount = 0;
      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({ ok: false, statusText: 'Error' });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            total_cost: 125.50,
            total_tokens: 500000,
            period: 'week',
          }),
        });
      });

      render(<CostPage />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load cost data/i)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText(/Retry/i));

      await waitFor(() => {
        expect(screen.getByText(/\$125\.50/)).toBeInTheDocument();
      });
    });
  });

  describe('API Integration', () => {
    it('should call cost summary API on mount', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/cost/summary'),
          expect.objectContaining({ method: 'GET' })
        );
      });
    });

    it('should call cost by model API on mount', async () => {
      render(<CostPage />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/cost/by-model'),
          expect.objectContaining({ method: 'GET' })
        );
      });
    });
  });
});
