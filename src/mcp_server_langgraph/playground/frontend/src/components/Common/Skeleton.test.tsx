/**
 * Skeleton Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton, SkeletonCard, SkeletonList, SkeletonText } from './Skeleton';

describe('Skeleton', () => {
  it('should_render_base_skeleton', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
  });

  it('should_apply_custom_className', () => {
    render(<Skeleton className="custom-class" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('custom-class');
  });

  it('should_have_animate_pulse_class', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('animate-pulse');
  });

  it('should_apply_width_and_height', () => {
    render(<Skeleton width="100px" height="50px" data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toHaveStyle({ width: '100px', height: '50px' });
  });

  it('should_apply_rounded_variant', () => {
    render(<Skeleton variant="rounded" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('rounded-lg');
  });

  it('should_apply_circular_variant', () => {
    render(<Skeleton variant="circular" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('rounded-full');
  });
});

describe('SkeletonCard', () => {
  it('should_render_card_skeleton', () => {
    render(<SkeletonCard />);
    expect(screen.getByRole('presentation')).toBeInTheDocument();
  });

  it('should_contain_multiple_skeleton_lines', () => {
    render(<SkeletonCard />);
    const skeletons = screen.getAllByTestId('skeleton-line');
    expect(skeletons.length).toBeGreaterThan(1);
  });
});

describe('SkeletonList', () => {
  it('should_render_default_3_items', () => {
    render(<SkeletonList />);
    const items = screen.getAllByRole('presentation');
    expect(items).toHaveLength(3);
  });

  it('should_render_specified_count', () => {
    render(<SkeletonList count={5} />);
    const items = screen.getAllByRole('presentation');
    expect(items).toHaveLength(5);
  });
});

describe('SkeletonText', () => {
  it('should_render_text_skeleton', () => {
    render(<SkeletonText />);
    expect(screen.getByTestId('skeleton-text')).toBeInTheDocument();
  });

  it('should_render_multiple_lines', () => {
    render(<SkeletonText lines={4} />);
    const lines = screen.getAllByTestId('skeleton-line');
    expect(lines).toHaveLength(4);
  });
});
