/**
 * SaveAsWorkflowButton Tests
 *
 * TDD tests for the workflow bootstrap button.
 * Tests cover:
 * - Button rendering
 * - API call on click
 * - Loading state
 * - Success message
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { SaveAsWorkflowButton } from './SaveAsWorkflowButton';

// Mock fetch
global.fetch = vi.fn();

describe('SaveAsWorkflowButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers(); // Ensure real timers are used by default
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        workflow_id: 'workflow-123',
        name: 'My Workflow'
      }),
    });
  });

  afterEach(() => {
    vi.useRealTimers(); // Clean up timers after each test
  });

  describe('Rendering', () => {
    it('should render button', () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      expect(screen.getByRole('button', { name: /Save as Workflow/i })).toBeInTheDocument();
    });

    it('should display button text', () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      expect(screen.getByText(/Save as Workflow/i)).toBeInTheDocument();
    });
  });

  describe('API Call', () => {
    it('should call bootstrap API on click', async () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/v1/sessions/session-123/bootstrap-workflow',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
            }),
          })
        );
      });
    });

    it('should include session ID in API call', async () => {
      render(<SaveAsWorkflowButton sessionId="test-session-456" />);

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('test-session-456'),
          expect.any(Object)
        );
      });
    });
  });

  describe('Loading State', () => {
    it('should be disabled during processing', async () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(button).toBeDisabled();
    });

    it('should show loading spinner during API call', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() =>
        new Promise((resolve) => setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ workflow_id: 'workflow-123', name: 'My Workflow' }),
        }), 100))
      );

      render(<SaveAsWorkflowButton sessionId="session-123" />);

      fireEvent.click(screen.getByRole('button'));

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should re-enable button after successful API call', async () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      await waitFor(() => {
        expect(button).not.toBeDisabled();
      });
    });
  });

  describe('Success State', () => {
    it('should show success message after creation', async () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByText(/Workflow Created/i)).toBeInTheDocument();
      });
    });

    it('should display workflow name in success message', async () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        expect(screen.getByText(/My Workflow/i)).toBeInTheDocument();
      });
    });

    it('should show link to workflow on success', async () => {
      render(<SaveAsWorkflowButton sessionId="session-123" />);

      fireEvent.click(screen.getByRole('button'));

      await waitFor(() => {
        const link = screen.getByRole('link', { name: /View Workflow/i });
        expect(link).toBeInTheDocument();
        expect(link).toHaveAttribute('href', '/studio/workflows?id=workflow-123');
      });
    });

    it('should auto-dismiss success message after delay', async () => {
      vi.useFakeTimers();

      render(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole('button'));
        // Let the fetch promise resolve
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(screen.getByText(/Workflow Created/i)).toBeInTheDocument();

      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      expect(screen.queryByText(/Workflow Created/i)).not.toBeInTheDocument();

      vi.useRealTimers();
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ detail: 'Error creating workflow' }),
      });

      render(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole('button'));
      });

      await waitFor(() => {
        expect(screen.getByText(/Failed to Create Workflow/i)).toBeInTheDocument();
      });
    });

    it('should display error message from API', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ detail: 'Custom error message' }),
      });

      render(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole('button'));
      });

      await waitFor(() => {
        expect(screen.getByText(/Custom error message/i)).toBeInTheDocument();
      });
    });

    it('should re-enable button after error', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ detail: 'Error' }),
      });

      render(<SaveAsWorkflowButton sessionId="session-123" />);

      const button = screen.getByRole('button');
      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(button).not.toBeDisabled();
      });
    });

    it('should allow retry after error', async () => {
      let callCount = 0;
      (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({
            ok: false,
            json: () => Promise.resolve({ detail: 'Error' }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ workflow_id: 'workflow-123', name: 'My Workflow' }),
        });
      });

      render(<SaveAsWorkflowButton sessionId="session-123" />);

      // First click fails
      await act(async () => {
        fireEvent.click(screen.getByRole('button'));
      });

      await waitFor(() => {
        expect(screen.getByText(/Failed to Create Workflow/i)).toBeInTheDocument();
      });

      // Second click succeeds
      await act(async () => {
        fireEvent.click(screen.getByRole('button'));
      });

      await waitFor(() => {
        expect(screen.getByText(/Workflow Created/i)).toBeInTheDocument();
      });
    });

    it('should handle network errors', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Network error')
      );

      render(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole('button'));
      });

      await waitFor(() => {
        expect(screen.getByText(/Network error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Disabled State', () => {
    it('should not call API when disabled', () => {
      render(<SaveAsWorkflowButton sessionId="session-123" disabled />);

      const button = screen.getByRole('button');
      fireEvent.click(button);

      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should show disabled styling when disabled', () => {
      render(<SaveAsWorkflowButton sessionId="session-123" disabled />);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });
});
