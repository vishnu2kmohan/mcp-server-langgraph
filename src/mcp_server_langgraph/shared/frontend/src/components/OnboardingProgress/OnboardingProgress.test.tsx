/**
 * OnboardingProgress Component Tests
 *
 * TDD: RED phase - Write tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { OnboardingProgress, useOnboarding, type OnboardingStep } from './OnboardingProgress';
import { renderHook } from '@testing-library/react';

const mockSteps: OnboardingStep[] = [
  { id: 'step1', title: 'Create your first agent', description: 'Start by creating an agent' },
  { id: 'step2', title: 'Connect a tool', description: 'Add tools to your agent' },
  { id: 'step3', title: 'Run your agent', description: 'Execute your first agent run' },
];

describe('OnboardingProgress Component', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders progress title', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByText('Getting Started')).toBeInTheDocument();
    });

    it('renders all step titles', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByText('Create your first agent')).toBeInTheDocument();
      expect(screen.getByText('Connect a tool')).toBeInTheDocument();
      expect(screen.getByText('Run your agent')).toBeInTheDocument();
    });

    it('renders step descriptions', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByText('Start by creating an agent')).toBeInTheDocument();
    });

    it('renders progress indicator', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByText('0 of 3 completed')).toBeInTheDocument();
    });

    it('shows completion percentage', () => {
      localStorage.setItem('onboarding_completed', JSON.stringify(['step1']));

      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByText('1 of 3 completed')).toBeInTheDocument();
    });

    it('renders dismiss button', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Interaction Tests
  // ==============================================================================

  describe('Interactions', () => {
    it('marks step as complete when clicked', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      const firstStep = screen.getByText('Create your first agent').closest('button');
      fireEvent.click(firstStep!);

      expect(screen.getByText('1 of 3 completed')).toBeInTheDocument();
    });

    it('persists completed steps to localStorage', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      const firstStep = screen.getByText('Create your first agent').closest('button');
      fireEvent.click(firstStep!);

      const completed = JSON.parse(localStorage.getItem('onboarding_completed') || '[]');
      expect(completed).toContain('step1');
    });

    it('calls onStepComplete when step completed', () => {
      const onStepComplete = vi.fn();
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
          onStepComplete={onStepComplete}
        />
      );

      const firstStep = screen.getByText('Create your first agent').closest('button');
      fireEvent.click(firstStep!);

      expect(onStepComplete).toHaveBeenCalledWith('step1');
    });

    it('calls onAllComplete when all steps done', () => {
      localStorage.setItem('onboarding_completed', JSON.stringify(['step1', 'step2']));
      const onAllComplete = vi.fn();

      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
          onAllComplete={onAllComplete}
        />
      );

      const lastStep = screen.getByText('Run your agent').closest('button');
      fireEvent.click(lastStep!);

      expect(onAllComplete).toHaveBeenCalled();
    });

    it('hides when dismissed', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));

      expect(screen.queryByText('Getting Started')).not.toBeInTheDocument();
    });

    it('calls onDismiss when dismissed', () => {
      const onDismiss = vi.fn();
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
          onDismiss={onDismiss}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));

      expect(onDismiss).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Visual State Tests
  // ==============================================================================

  describe('Visual States', () => {
    it('shows checkmark for completed steps', () => {
      localStorage.setItem('onboarding_completed', JSON.stringify(['step1']));

      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      const firstStepButton = screen.getByText('Create your first agent').closest('button');
      expect(firstStepButton).toHaveAttribute('aria-checked', 'true');
    });

    it('shows empty circle for incomplete steps', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      const firstStepButton = screen.getByText('Create your first agent').closest('button');
      expect(firstStepButton).toHaveAttribute('aria-checked', 'false');
    });

    it('shows progress bar with correct width', () => {
      localStorage.setItem('onboarding_completed', JSON.stringify(['step1']));

      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '33');
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has proper region role', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByRole('region')).toBeInTheDocument();
    });

    it('has aria-label on region', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      expect(screen.getByRole('region')).toHaveAttribute('aria-label', 'Getting Started');
    });

    it('steps are keyboard accessible', () => {
      render(
        <OnboardingProgress
          steps={mockSteps}
          title="Getting Started"
        />
      );

      const firstStep = screen.getByText('Create your first agent').closest('button');
      expect(firstStep).toHaveAttribute('type', 'button');
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

  afterEach(() => {
    localStorage.clear();
  });

  it('returns completion status for steps', () => {
    const { result } = renderHook(() => useOnboarding(mockSteps));

    expect(result.current.isCompleted('step1')).toBe(false);
    expect(result.current.isCompleted('step2')).toBe(false);
  });

  it('loads completed steps from localStorage', () => {
    localStorage.setItem('onboarding_completed', JSON.stringify(['step1']));

    const { result } = renderHook(() => useOnboarding(mockSteps));

    expect(result.current.isCompleted('step1')).toBe(true);
    expect(result.current.isCompleted('step2')).toBe(false);
  });

  it('completeStep marks step as done', () => {
    const { result } = renderHook(() => useOnboarding(mockSteps));

    act(() => {
      result.current.completeStep('step1');
    });

    expect(result.current.isCompleted('step1')).toBe(true);
  });

  it('returns progress percentage', () => {
    const { result } = renderHook(() => useOnboarding(mockSteps));

    expect(result.current.progress).toBe(0);

    act(() => {
      result.current.completeStep('step1');
    });

    expect(result.current.progress).toBeCloseTo(33.33, 0);
  });

  it('returns count of completed steps', () => {
    localStorage.setItem('onboarding_completed', JSON.stringify(['step1', 'step2']));

    const { result } = renderHook(() => useOnboarding(mockSteps));

    expect(result.current.completedCount).toBe(2);
    expect(result.current.totalCount).toBe(3);
  });

  it('isAllComplete returns true when all done', () => {
    localStorage.setItem('onboarding_completed', JSON.stringify(['step1', 'step2', 'step3']));

    const { result } = renderHook(() => useOnboarding(mockSteps));

    expect(result.current.isAllComplete).toBe(true);
  });

  it('reset clears all completed steps', () => {
    localStorage.setItem('onboarding_completed', JSON.stringify(['step1', 'step2']));

    const { result } = renderHook(() => useOnboarding(mockSteps));

    act(() => {
      result.current.reset();
    });

    expect(result.current.completedCount).toBe(0);
    expect(localStorage.getItem('onboarding_completed')).toBe('[]');
  });
});
