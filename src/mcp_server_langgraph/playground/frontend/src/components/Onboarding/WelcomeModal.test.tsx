/**
 * WelcomeModal Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WelcomeModal, useOnboarding } from './WelcomeModal';
import { renderHook, act } from '@testing-library/react';

describe('WelcomeModal', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should_render_welcome_title', () => {
    render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
    expect(screen.getByText('Welcome to the Playground')).toBeInTheDocument();
  });

  it('should_render_first_feature', () => {
    render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);
    expect(screen.getByText('Chat with AI Agents')).toBeInTheDocument();
  });

  it('should_navigate_to_next_slide', () => {
    render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);

    fireEvent.click(screen.getByText('Next'));

    expect(screen.getByText('Explore MCP Tools')).toBeInTheDocument();
  });

  it('should_navigate_back_to_previous_slide', () => {
    render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);

    // Go to second slide
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByText('Explore MCP Tools')).toBeInTheDocument();

    // Go back
    fireEvent.click(screen.getByText('Back'));
    expect(screen.getByText('Chat with AI Agents')).toBeInTheDocument();
  });

  it('should_show_get_started_on_last_slide', () => {
    render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);

    // Navigate through all slides
    fireEvent.click(screen.getByText('Next')); // Slide 2
    fireEvent.click(screen.getByText('Next')); // Slide 3
    fireEvent.click(screen.getByText('Next')); // Slide 4 (last)

    expect(screen.getByText('Get Started')).toBeInTheDocument();
  });

  it('should_call_onComplete_when_finished', () => {
    const onComplete = vi.fn();
    render(<WelcomeModal onComplete={onComplete} onSkip={vi.fn()} />);

    // Navigate to last slide and complete
    fireEvent.click(screen.getByText('Next'));
    fireEvent.click(screen.getByText('Next'));
    fireEvent.click(screen.getByText('Next'));
    fireEvent.click(screen.getByText('Get Started'));

    expect(onComplete).toHaveBeenCalled();
    // Verify the value was saved
    expect(localStorage.getItem('playground_onboarding_complete')).toBe('true');
  });

  it('should_call_onSkip_when_skipped', () => {
    const onSkip = vi.fn();
    render(<WelcomeModal onComplete={vi.fn()} onSkip={onSkip} />);

    fireEvent.click(screen.getByText('Skip tour'));

    expect(onSkip).toHaveBeenCalled();
    expect(localStorage.getItem('playground_onboarding_complete')).toBe('true');
  });

  it('should_render_progress_dots', () => {
    render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);

    // Should have 4 progress dots
    const dots = screen.getAllByRole('button', { name: /Go to slide/ });
    expect(dots).toHaveLength(4);
  });

  it('should_navigate_via_progress_dots', () => {
    render(<WelcomeModal onComplete={vi.fn()} onSkip={vi.fn()} />);

    // Click on third dot
    fireEvent.click(screen.getByLabelText('Go to slide 3'));

    expect(screen.getByText('Browse Resources')).toBeInTheDocument();
  });
});

describe('useOnboarding', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should_return_false_when_not_completed', () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasCompletedOnboarding).toBe(false);
  });

  it('should_return_true_when_completed', () => {
    localStorage.setItem('playground_onboarding_complete', 'true');

    const { result } = renderHook(() => useOnboarding());
    expect(result.current.hasCompletedOnboarding).toBe(true);
  });

  it('should_reset_onboarding', () => {
    localStorage.setItem('playground_onboarding_complete', 'true');

    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.resetOnboarding();
    });

    expect(localStorage.getItem('playground_onboarding_complete')).toBeNull();
    expect(result.current.hasCompletedOnboarding).toBe(false);
  });

  it('should_complete_onboarding', () => {
    const { result } = renderHook(() => useOnboarding());

    act(() => {
      result.current.completeOnboarding();
    });

    expect(localStorage.getItem('playground_onboarding_complete')).toBe('true');
    expect(result.current.hasCompletedOnboarding).toBe(true);
  });
});
