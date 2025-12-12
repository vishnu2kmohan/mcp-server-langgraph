/**
 * Tests for WelcomeModal Component
 *
 * TDD: Tests written FIRST before implementation
 *
 * Builder-specific onboarding with feature highlights.
 * Implements HEART Framework "Adoption" dimension.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { renderHook, act } from '@testing-library/react';
import { WelcomeModal, useOnboarding } from './WelcomeModal';

describe('WelcomeModal Component', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders welcome title', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      expect(screen.getByText(/welcome to.*builder/i)).toBeInTheDocument();
    });

    it('renders first feature slide', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      expect(screen.getByText(/add nodes/i)).toBeInTheDocument();
    });

    it('renders progress dots for all slides', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      const dots = screen.getAllByRole('button', { name: /go to slide/i });
      expect(dots).toHaveLength(4);
    });

    it('does not render when onboarding already completed', () => {
      localStorage.setItem('builder_onboarding_complete', 'true');
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      expect(screen.queryByText(/welcome to.*builder/i)).not.toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Navigation Tests
  // ==============================================================================

  describe('Navigation', () => {
    it('navigates to next slide when Next is clicked', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      fireEvent.click(screen.getByText('Next'));
      expect(screen.getByText(/connect nodes/i)).toBeInTheDocument();
    });

    it('navigates back when Back is clicked', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      fireEvent.click(screen.getByText('Next')); // Go to slide 2
      fireEvent.click(screen.getByText('Back')); // Go back to slide 1
      expect(screen.getByText(/add nodes/i)).toBeInTheDocument();
    });

    it('does not show Back button on first slide', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      expect(screen.queryByText('Back')).not.toBeInTheDocument();
    });

    it('navigates via progress dots', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      fireEvent.click(screen.getByLabelText('Go to slide 3'));
      expect(screen.getByText(/configure/i)).toBeInTheDocument();
    });

    it('shows Get Started on last slide', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      // Navigate through all slides
      fireEvent.click(screen.getByText('Next')); // Slide 2
      fireEvent.click(screen.getByText('Next')); // Slide 3
      fireEvent.click(screen.getByText('Next')); // Slide 4 (last)
      expect(screen.getByText('Get Started')).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Completion Tests
  // ==============================================================================

  describe('Completion', () => {
    it('calls onComplete when Get Started is clicked', () => {
      const onComplete = vi.fn();
      render(<WelcomeModal onComplete={onComplete} onSkip={vi.fn()} />);

      // Navigate to last slide and complete
      fireEvent.click(screen.getByText('Next'));
      fireEvent.click(screen.getByText('Next'));
      fireEvent.click(screen.getByText('Next'));
      fireEvent.click(screen.getByText('Get Started'));

      expect(onComplete).toHaveBeenCalled();
    });

    it('saves completion to localStorage when finished', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);

      fireEvent.click(screen.getByText('Next'));
      fireEvent.click(screen.getByText('Next'));
      fireEvent.click(screen.getByText('Next'));
      fireEvent.click(screen.getByText('Get Started'));

      expect(localStorage.getItem('builder_onboarding_complete')).toBe('true');
    });

    it('calls onSkip when Skip tour is clicked', () => {
      const onSkip = vi.fn();
      render(<WelcomeModal onComplete={vi.fn()} onSkip={onSkip} />);

      fireEvent.click(screen.getByText('Skip tour'));

      expect(onSkip).toHaveBeenCalled();
    });

    it('saves completion to localStorage when skipped', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);

      fireEvent.click(screen.getByText('Skip tour'));

      expect(localStorage.getItem('builder_onboarding_complete')).toBe('true');
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has dialog role with modal attribute', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
    });

    it('has accessible label for dialog', () => {
      render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
      expect(screen.getByRole('dialog', { name: /welcome/i })).toBeInTheDocument();
    });
  });
});

// ==============================================================================
// useOnboarding Hook Tests
// ==============================================================================

describe('useOnboarding Hook', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns false when onboarding not completed', () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasCompletedOnboarding).toBe(false);
  });

  it('returns true when onboarding completed', () => {
    localStorage.setItem('builder_onboarding_complete', 'true');
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasCompletedOnboarding).toBe(true);
  });

  it('resets onboarding', () => {
    localStorage.setItem('builder_onboarding_complete', 'true');
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.resetOnboarding();
    });

    expect(localStorage.getItem('builder_onboarding_complete')).toBeNull();
    expect(result.current.hasCompletedOnboarding).toBe(false);
  });

  it('completes onboarding', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.completeOnboarding();
    });

    expect(localStorage.getItem('builder_onboarding_complete')).toBe('true');
    expect(result.current.hasCompletedOnboarding).toBe(true);
  });
});
