/**
 * Tests for NPSSurvey Component
 *
 * TDD: Tests written FIRST before implementation
 *
 * Net Promoter Score survey for measuring user satisfaction.
 * Scale: 0-10, where 0-6 = Detractors, 7-8 = Passives, 9-10 = Promoters
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NPSSurvey } from './NPSSurvey';

describe('NPSSurvey Component', () => {
  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders NPS question', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      expect(screen.getByText(/how likely/i)).toBeInTheDocument();
    });

    it('renders custom question when provided', () => {
      render(<NPSSurvey onSubmit={() => {}} question="Rate your experience" />);
      expect(screen.getByText(/rate your experience/i)).toBeInTheDocument();
    });

    it('renders score buttons 0 to 10', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      for (let i = 0; i <= 10; i++) {
        expect(screen.getByRole('button', { name: String(i) })).toBeInTheDocument();
      }
    });

    it('shows scale labels for ends', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      expect(screen.getByText(/not likely/i)).toBeInTheDocument();
      expect(screen.getByText(/extremely likely/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Interaction Tests
  // ==============================================================================

  describe('Interactions', () => {
    it('highlights selected score with promoter color for 9-10', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      const button9 = screen.getByRole('button', { name: '9' });
      fireEvent.click(button9);
      expect(button9).toHaveClass('bg-green-600');
    });

    it('highlights selected score with passive color for 7-8', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      const button7 = screen.getByRole('button', { name: '7' });
      fireEvent.click(button7);
      expect(button7).toHaveClass('bg-yellow-500');
    });

    it('highlights selected score with detractor color for 0-6', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      const button3 = screen.getByRole('button', { name: '3' });
      fireEvent.click(button3);
      expect(button3).toHaveClass('bg-red-500');
    });

    it('disables submit button without selection', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      const submitButton = screen.getByRole('button', { name: /submit/i });
      expect(submitButton).toBeDisabled();
    });

    it('enables submit button after selection', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      fireEvent.click(screen.getByRole('button', { name: '7' }));
      const submitButton = screen.getByRole('button', { name: /submit/i });
      expect(submitButton).not.toBeDisabled();
    });
  });

  // ==============================================================================
  // Submission Tests
  // ==============================================================================

  describe('Submission', () => {
    it('calls onSubmit with selected score', () => {
      const onSubmit = vi.fn();
      render(<NPSSurvey onSubmit={onSubmit} />);
      fireEvent.click(screen.getByRole('button', { name: '9' }));
      fireEvent.click(screen.getByRole('button', { name: /submit/i }));
      expect(onSubmit).toHaveBeenCalledWith(9);
    });

    it('calls onDismiss when skip is clicked', () => {
      const onDismiss = vi.fn();
      render(<NPSSurvey onSubmit={() => {}} onDismiss={onDismiss} />);
      fireEvent.click(screen.getByRole('button', { name: /skip/i }));
      expect(onDismiss).toHaveBeenCalled();
    });

    it('does not render skip button when onDismiss is not provided', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      expect(screen.queryByRole('button', { name: /skip/i })).not.toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has accessible fieldset with group role', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      expect(screen.getByRole('group', { name: /nps survey/i })).toBeInTheDocument();
    });

    it('has aria-pressed attribute on score buttons', () => {
      render(<NPSSurvey onSubmit={() => {}} />);
      const button5 = screen.getByRole('button', { name: '5' });
      expect(button5).toHaveAttribute('aria-pressed', 'false');
      fireEvent.click(button5);
      expect(button5).toHaveAttribute('aria-pressed', 'true');
    });
  });
});
