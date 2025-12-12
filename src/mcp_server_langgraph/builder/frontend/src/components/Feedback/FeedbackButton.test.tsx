/**
 * Tests for FeedbackButton Component
 *
 * TDD: Tests written FIRST before implementation
 *
 * Floating feedback button with quick satisfaction rating
 * for HEART Framework "Happiness" dimension.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FeedbackButton, type FeedbackData } from './FeedbackButton';

describe('FeedbackButton Component', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders floating feedback button', () => {
      render(<FeedbackButton />);

      const button = screen.getByRole('button', { name: /give feedback/i });
      expect(button).toBeInTheDocument();
    });

    it('renders in bottom-right position by default', () => {
      render(<FeedbackButton />);

      const button = screen.getByRole('button', { name: /give feedback/i });
      expect(button.closest('div')).toHaveClass('right-4');
    });

    it('renders in bottom-left position when specified', () => {
      render(<FeedbackButton position="bottom-left" />);

      const button = screen.getByRole('button', { name: /give feedback/i });
      expect(button.closest('div')).toHaveClass('left-4');
    });
  });

  // ==============================================================================
  // Interaction Tests
  // ==============================================================================

  describe('Interactions', () => {
    it('opens feedback panel when button is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      const button = screen.getByRole('button', { name: /give feedback/i });
      await user.click(button);

      expect(screen.getByText(/how's your experience/i)).toBeInTheDocument();
    });

    it('closes feedback panel when button is clicked again', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      // Open
      const button = screen.getByRole('button', { name: /give feedback/i });
      await user.click(button);
      expect(screen.getByText(/how's your experience/i)).toBeInTheDocument();

      // Close
      await user.click(screen.getByRole('button', { name: /close feedback/i }));
      expect(screen.queryByText(/how's your experience/i)).not.toBeInTheDocument();
    });

    it('shows 5 emoji rating buttons', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      await user.click(screen.getByRole('button', { name: /give feedback/i }));

      const ratingButtons = screen.getAllByRole('button', { name: /(happy|unhappy|neutral)/i });
      expect(ratingButtons).toHaveLength(5);
    });

    it('highlights selected rating', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      await user.click(screen.getByRole('button', { name: /give feedback/i }));

      const happyButton = screen.getByRole('button', { name: /^happy$/i });
      await user.click(happyButton);

      expect(happyButton).toHaveClass('ring-2');
    });

    it('shows comment textarea after selecting rating', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      await user.click(screen.getByRole('button', { name: /give feedback/i }));
      await user.click(screen.getByRole('button', { name: /^happy$/i }));

      expect(screen.getByPlaceholderText(/additional feedback/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Submission Tests
  // ==============================================================================

  describe('Submission', () => {
    it('calls onSubmit with feedback data', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const onSubmit = vi.fn();
      render(<FeedbackButton onSubmit={onSubmit} />);

      await user.click(screen.getByRole('button', { name: /give feedback/i }));
      await user.click(screen.getByRole('button', { name: /very happy/i }));
      await user.type(screen.getByPlaceholderText(/additional feedback/i), 'Great tool!');
      await user.click(screen.getByRole('button', { name: /submit feedback/i }));

      expect(onSubmit).toHaveBeenCalledTimes(1);
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          rating: 5,
          comment: 'Great tool!',
          timestamp: expect.any(String),
          page: expect.any(String),
        })
      );
    });

    it('shows thank you message after submission', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      await user.click(screen.getByRole('button', { name: /give feedback/i }));
      await user.click(screen.getByRole('button', { name: /^happy$/i }));
      await user.click(screen.getByRole('button', { name: /submit feedback/i }));

      expect(screen.getByText(/thanks for your feedback/i)).toBeInTheDocument();
    });

    it('auto-closes panel after submission', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      await user.click(screen.getByRole('button', { name: /give feedback/i }));
      await user.click(screen.getByRole('button', { name: /^happy$/i }));
      await user.click(screen.getByRole('button', { name: /submit feedback/i }));

      // Verify thank you message is shown
      expect(screen.getByText(/thanks for your feedback/i)).toBeInTheDocument();

      // Advance timers to trigger auto-close
      await vi.advanceTimersByTimeAsync(2500);

      // Panel should be closed
      expect(screen.queryByText(/thanks for your feedback/i)).not.toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has accessible labels for rating buttons', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      await user.click(screen.getByRole('button', { name: /give feedback/i }));

      expect(screen.getByRole('button', { name: /very unhappy/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /very happy/i })).toBeInTheDocument();
    });

    it('has aria-expanded attribute on toggle button', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<FeedbackButton />);

      const button = screen.getByRole('button', { name: /give feedback/i });
      expect(button).toHaveAttribute('aria-expanded', 'false');

      await user.click(button);
      expect(screen.getByRole('button', { name: /close feedback/i })).toHaveAttribute('aria-expanded', 'true');
    });
  });
});
