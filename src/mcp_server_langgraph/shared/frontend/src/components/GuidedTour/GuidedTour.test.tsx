/**
 * GuidedTour Component Tests
 *
 * TDD: RED phase - Write tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GuidedTour, type TourStep } from './GuidedTour';

const mockSteps: TourStep[] = [
  {
    id: 'step1',
    title: 'Welcome',
    content: 'Welcome to the application!',
    target: '#welcome-element',
  },
  {
    id: 'step2',
    title: 'Create Agent',
    content: 'Click here to create your first agent.',
    target: '#create-agent-btn',
  },
  {
    id: 'step3',
    title: 'Run Your Agent',
    content: 'Run your agent to see results.',
    target: '#run-btn',
  },
];

describe('GuidedTour Component', () => {
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
    it('renders when isOpen is true', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByText('Welcome')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(<GuidedTour steps={mockSteps} isOpen={false} onClose={vi.fn()} />);

      expect(screen.queryByText('Welcome')).not.toBeInTheDocument();
    });

    it('renders step title', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByText('Welcome')).toBeInTheDocument();
    });

    it('renders step content', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByText('Welcome to the application!')).toBeInTheDocument();
    });

    it('renders step indicator', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByText('1 of 3')).toBeInTheDocument();
    });

    it('renders next button', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
    });

    it('renders back button on non-first step', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} initialStep={1} />);

      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
    });

    it('does not render back button on first step', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.queryByRole('button', { name: /back/i })).not.toBeInTheDocument();
    });

    it('renders finish button on last step', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} initialStep={2} />);

      expect(screen.getByRole('button', { name: /finish/i })).toBeInTheDocument();
    });

    it('renders skip button', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Navigation Tests
  // ==============================================================================

  describe('Navigation', () => {
    it('advances to next step when next clicked', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      expect(screen.getByText('Create Agent')).toBeInTheDocument();
      expect(screen.getByText('2 of 3')).toBeInTheDocument();
    });

    it('goes back when back clicked', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} initialStep={1} />);

      fireEvent.click(screen.getByRole('button', { name: /back/i }));

      expect(screen.getByText('Welcome')).toBeInTheDocument();
      expect(screen.getByText('1 of 3')).toBeInTheDocument();
    });

    it('calls onClose when finish clicked', () => {
      const onClose = vi.fn();
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={onClose} initialStep={2} />);

      fireEvent.click(screen.getByRole('button', { name: /finish/i }));

      expect(onClose).toHaveBeenCalled();
    });

    it('calls onClose when skip clicked', () => {
      const onClose = vi.fn();
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={onClose} />);

      fireEvent.click(screen.getByRole('button', { name: /skip/i }));

      expect(onClose).toHaveBeenCalled();
    });

    it('calls onStepChange when navigating', () => {
      const onStepChange = vi.fn();
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} onStepChange={onStepChange} />);

      fireEvent.click(screen.getByRole('button', { name: /next/i }));

      expect(onStepChange).toHaveBeenCalledWith(1, mockSteps[1]);
    });

    it('calls onComplete when tour finished', () => {
      const onComplete = vi.fn();
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} onComplete={onComplete} initialStep={2} />);

      fireEvent.click(screen.getByRole('button', { name: /finish/i }));

      expect(onComplete).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Progress Dots Tests
  // ==============================================================================

  describe('Progress Dots', () => {
    it('renders progress dots for each step', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      const dots = screen.getAllByRole('button', { name: /step \d/i });
      expect(dots).toHaveLength(3);
    });

    it('highlights current step dot', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      const dots = screen.getAllByRole('button', { name: /step \d/i });
      expect(dots[0]).toHaveAttribute('aria-current', 'step');
    });

    it('navigates when dot clicked', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      const dots = screen.getAllByRole('button', { name: /step \d/i });
      fireEvent.click(dots[2]);

      expect(screen.getByText('Run Your Agent')).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Persistence Tests
  // ==============================================================================

  describe('Persistence', () => {
    it('persists tour completion to localStorage', () => {
      const onComplete = vi.fn();
      render(
        <GuidedTour
          steps={mockSteps}
          isOpen={true}
          onClose={vi.fn()}
          onComplete={onComplete}
          tourId="test-tour"
          initialStep={2}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /finish/i }));

      const completed = JSON.parse(localStorage.getItem('tours_completed') || '[]');
      expect(completed).toContain('test-tour');
    });

    it('does not show if previously completed', () => {
      localStorage.setItem('tours_completed', JSON.stringify(['test-tour']));

      render(
        <GuidedTour
          steps={mockSteps}
          isOpen={true}
          onClose={vi.fn()}
          tourId="test-tour"
        />
      );

      expect(screen.queryByText('Welcome')).not.toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has dialog role', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has aria-modal attribute', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    });

    it('has aria-labelledby pointing to title', () => {
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={vi.fn()} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby');
    });

    it('escape key closes tour', () => {
      const onClose = vi.fn();
      render(<GuidedTour steps={mockSteps} isOpen={true} onClose={onClose} />);

      fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

      expect(onClose).toHaveBeenCalled();
    });
  });
});
