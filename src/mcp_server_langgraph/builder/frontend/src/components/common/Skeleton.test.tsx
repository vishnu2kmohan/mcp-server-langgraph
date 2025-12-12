/**
 * Skeleton Component Tests for Visual Workflow Builder
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Skeleton,
  SkeletonCard,
  SkeletonList,
  SkeletonText,
  SkeletonWorkflowNode,
  SkeletonCodeBlock,
} from './Skeleton';

describe('Skeleton', () => {
  it('renders with animate-pulse class', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('animate-pulse');
  });

  it('accepts custom width and height', () => {
    render(<Skeleton width={100} height={50} data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toHaveStyle({ width: '100px', height: '50px' });
  });

  it('accepts string width and height', () => {
    render(<Skeleton width="50%" height="2rem" data-testid="skeleton" />);
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toHaveStyle({ width: '50%', height: '2rem' });
  });

  it('has aria-hidden for accessibility', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveAttribute('aria-hidden', 'true');
  });

  it('applies custom className', () => {
    render(<Skeleton className="custom-class" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('custom-class');
  });

  it('applies text variant with rounded corners', () => {
    render(<Skeleton variant="text" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('rounded');
  });

  it('applies circular variant', () => {
    render(<Skeleton variant="circular" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('rounded-full');
  });

  it('applies rounded variant', () => {
    render(<Skeleton variant="rounded" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('rounded-lg');
  });
});

describe('SkeletonCard', () => {
  it('renders avatar and text lines', () => {
    render(<SkeletonCard />);
    const lines = screen.getAllByTestId('skeleton-line');
    expect(lines.length).toBeGreaterThan(1);
  });

  it('has presentation role', () => {
    render(<SkeletonCard />);
    expect(screen.getByRole('presentation')).toBeInTheDocument();
  });
});

describe('SkeletonList', () => {
  it('renders default 3 items', () => {
    render(<SkeletonList />);
    const items = screen.getAllByRole('presentation');
    expect(items).toHaveLength(3);
  });

  it('accepts lines prop for item count', () => {
    render(<SkeletonList count={5} />);
    const items = screen.getAllByRole('presentation');
    expect(items).toHaveLength(5);
  });
});

describe('SkeletonText', () => {
  it('renders multiple text lines', () => {
    render(<SkeletonText />);
    expect(screen.getByTestId('skeleton-text')).toBeInTheDocument();
  });

  it('accepts lines prop', () => {
    render(<SkeletonText lines={4} />);
    const lines = screen.getAllByTestId('skeleton-line');
    expect(lines).toHaveLength(4);
  });
});

describe('SkeletonWorkflowNode', () => {
  it('renders workflow node placeholder', () => {
    render(<SkeletonWorkflowNode />);
    expect(screen.getByTestId('skeleton-workflow-node')).toBeInTheDocument();
  });

  it('has presentation role', () => {
    render(<SkeletonWorkflowNode />);
    expect(screen.getByRole('presentation')).toBeInTheDocument();
  });

  it('applies node shape styling', () => {
    render(<SkeletonWorkflowNode />);
    const node = screen.getByTestId('skeleton-workflow-node');
    expect(node).toHaveClass('rounded-lg');
  });
});

describe('SkeletonCodeBlock', () => {
  it('renders code block placeholder', () => {
    render(<SkeletonCodeBlock />);
    expect(screen.getByTestId('skeleton-code-block')).toBeInTheDocument();
  });

  it('renders multiple code lines', () => {
    render(<SkeletonCodeBlock />);
    const lines = screen.getAllByTestId('skeleton-code-line');
    expect(lines.length).toBeGreaterThan(3);
  });

  it('accepts lines prop', () => {
    render(<SkeletonCodeBlock lines={10} />);
    const codeLines = screen.getAllByTestId('skeleton-code-line');
    expect(codeLines).toHaveLength(10);
  });
});
