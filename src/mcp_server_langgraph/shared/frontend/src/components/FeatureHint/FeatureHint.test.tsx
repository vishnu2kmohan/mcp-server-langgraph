/**
 * FeatureHint Component Tests
 *
 * TDD: RED phase - Write tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { FeatureHint, useFeatureDiscovery } from './FeatureHint';
import { renderHook } from '@testing-library/react';

describe('FeatureHint Component', () => {
  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders hint content', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Did you know?"
          description="You can do something cool here"
        />
      );

      expect(screen.getByText('Did you know?')).toBeInTheDocument();
      expect(screen.getByText('You can do something cool here')).toBeInTheDocument();
    });

    it('renders try it button when action provided', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
          actionLabel="Try it"
          onAction={vi.fn()}
        />
      );

      expect(screen.getByRole('button', { name: /try it/i })).toBeInTheDocument();
    });

    it('renders dismiss button', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
        />
      );

      expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument();
    });

    it('does not render when dismissed', () => {
      // Pre-set the dismissed state
      localStorage.setItem('feature_hints_dismissed', JSON.stringify(['test-feature']));

      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
        />
      );

      expect(screen.queryByText('Hint')).not.toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Interaction Tests
  // ==============================================================================

  describe('Interactions', () => {
    it('calls onAction when try it button clicked', () => {
      const onAction = vi.fn();
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
          actionLabel="Try it"
          onAction={onAction}
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /try it/i }));
      expect(onAction).toHaveBeenCalled();
    });

    it('hides hint when dismiss button clicked', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));

      expect(screen.queryByText('Hint')).not.toBeInTheDocument();
    });

    it('persists dismissal to localStorage', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
        />
      );

      fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));

      const dismissed = JSON.parse(localStorage.getItem('feature_hints_dismissed') || '[]');
      expect(dismissed).toContain('test-feature');
    });
  });

  // ==============================================================================
  // Variant Tests
  // ==============================================================================

  describe('Variants', () => {
    it('renders inline variant', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
          variant="inline"
        />
      );

      expect(screen.getByText('Hint')).toBeInTheDocument();
    });

    it('renders banner variant', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
          variant="banner"
        />
      );

      expect(screen.getByText('Hint')).toBeInTheDocument();
    });

    it('renders popover variant', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
          variant="popover"
        />
      );

      expect(screen.getByText('Hint')).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
        />
      );

      expect(screen.getByRole('complementary')).toBeInTheDocument();
    });

    it('has aria-label for dismiss button', () => {
      render(
        <FeatureHint
          featureId="test-feature"
          title="Hint"
          description="Description"
        />
      );

      expect(screen.getByRole('button', { name: /dismiss/i })).toHaveAttribute('aria-label');
    });
  });
});

// ==============================================================================
// useFeatureDiscovery Hook Tests
// ==============================================================================

describe('useFeatureDiscovery Hook', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('returns current hint from queue', () => {
    const hints = [
      { featureId: 'feature1', title: 'Hint 1', description: 'Desc 1' },
      { featureId: 'feature2', title: 'Hint 2', description: 'Desc 2' },
    ];

    const { result } = renderHook(() => useFeatureDiscovery(hints));

    expect(result.current.currentHint?.featureId).toBe('feature1');
  });

  it('skips dismissed hints', () => {
    localStorage.setItem('feature_hints_dismissed', JSON.stringify(['feature1']));

    const hints = [
      { featureId: 'feature1', title: 'Hint 1', description: 'Desc 1' },
      { featureId: 'feature2', title: 'Hint 2', description: 'Desc 2' },
    ];

    const { result } = renderHook(() => useFeatureDiscovery(hints));

    expect(result.current.currentHint?.featureId).toBe('feature2');
  });

  it('dismissHint removes hint and advances queue', () => {
    const hints = [
      { featureId: 'feature1', title: 'Hint 1', description: 'Desc 1' },
      { featureId: 'feature2', title: 'Hint 2', description: 'Desc 2' },
    ];

    const { result } = renderHook(() => useFeatureDiscovery(hints));

    act(() => {
      result.current.dismissHint('feature1');
    });

    expect(result.current.currentHint?.featureId).toBe('feature2');
  });

  it('markFeatureExplored removes hint from queue', () => {
    const hints = [
      { featureId: 'feature1', title: 'Hint 1', description: 'Desc 1' },
    ];

    const { result } = renderHook(() => useFeatureDiscovery(hints));

    act(() => {
      result.current.markFeatureExplored('feature1');
    });

    expect(result.current.currentHint).toBeNull();
  });

  it('returns null when all hints dismissed', () => {
    localStorage.setItem('feature_hints_dismissed', JSON.stringify(['feature1']));

    const hints = [
      { featureId: 'feature1', title: 'Hint 1', description: 'Desc 1' },
    ];

    const { result } = renderHook(() => useFeatureDiscovery(hints));

    expect(result.current.currentHint).toBeNull();
  });
});
