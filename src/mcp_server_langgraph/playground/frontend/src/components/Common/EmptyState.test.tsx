/**
 * EmptyState Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EmptyState } from './EmptyState';

describe('EmptyState', () => {
  it('should_render_title', () => {
    render(<EmptyState title="No items found" />);
    expect(screen.getByText('No items found')).toBeInTheDocument();
  });

  it('should_render_description', () => {
    render(<EmptyState title="No items" description="Create your first item to get started" />);
    expect(screen.getByText('Create your first item to get started')).toBeInTheDocument();
  });

  it('should_render_icon_when_provided', () => {
    const TestIcon = () => <svg data-testid="custom-icon" />;
    render(<EmptyState title="Empty" icon={<TestIcon />} />);
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('should_render_action_button_when_provided', () => {
    const onAction = vi.fn();
    render(
      <EmptyState
        title="No sessions"
        actionLabel="Create Session"
        onAction={onAction}
      />
    );

    const button = screen.getByRole('button', { name: 'Create Session' });
    expect(button).toBeInTheDocument();

    fireEvent.click(button);
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it('should_not_render_button_without_action', () => {
    render(<EmptyState title="Empty" actionLabel="Click me" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('should_render_suggestions_when_provided', () => {
    const suggestions = ['Try this first', 'Or this', 'Maybe this'];
    render(<EmptyState title="No results" suggestions={suggestions} />);

    expect(screen.getByText('Try:')).toBeInTheDocument();
    suggestions.forEach((suggestion) => {
      expect(screen.getByText(suggestion)).toBeInTheDocument();
    });
  });

  it('should_apply_variant_styles_for_default', () => {
    render(<EmptyState title="Empty" variant="default" />);
    const container = screen.getByText('Empty').closest('[data-testid="empty-state"]');
    expect(container).toHaveClass('bg-gray-50');
  });

  it('should_apply_variant_styles_for_compact', () => {
    render(<EmptyState title="Empty" variant="compact" />);
    const container = screen.getByText('Empty').closest('[data-testid="empty-state"]');
    expect(container).toHaveClass('py-4');
  });

  it('should_apply_variant_styles_for_large', () => {
    render(<EmptyState title="Empty" variant="large" />);
    const container = screen.getByText('Empty').closest('[data-testid="empty-state"]');
    expect(container).toHaveClass('py-16');
  });

  it('should_apply_custom_className', () => {
    render(<EmptyState title="Empty" className="custom-class" />);
    const container = screen.getByText('Empty').closest('[data-testid="empty-state"]');
    expect(container).toHaveClass('custom-class');
  });

  it('should_render_with_accessible_region', () => {
    render(<EmptyState title="No data" />);
    expect(screen.getByRole('region')).toBeInTheDocument();
  });
});
