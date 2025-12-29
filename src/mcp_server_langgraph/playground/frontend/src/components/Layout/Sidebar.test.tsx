/**
 * Sidebar Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Sidebar } from './Sidebar';

describe('Sidebar', () => {
  it('should_render_children', () => {
    render(
      <Sidebar>
        <div data-testid="child">Content</div>
      </Sidebar>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('should_have_aside_role', () => {
    render(<Sidebar>Content</Sidebar>);
    const aside = screen.getByRole('complementary');
    expect(aside).toBeInTheDocument();
  });

  it('should_have_proper_width', () => {
    render(<Sidebar>Content</Sidebar>);
    const aside = screen.getByRole('complementary');
    expect(aside).toHaveClass('w-80');
  });

  it('should_be_collapsible', () => {
    const onToggle = vi.fn();
    render(
      <Sidebar collapsed={false} onToggle={onToggle}>
        Content
      </Sidebar>
    );

    const toggleButton = screen.getByRole('button', { name: /collapse/i });
    fireEvent.click(toggleButton);
    expect(onToggle).toHaveBeenCalled();
  });

  it('should_render_collapsed_state', () => {
    render(<Sidebar collapsed>Content</Sidebar>);
    const aside = screen.getByRole('complementary');
    expect(aside).toHaveClass('w-16');
  });

  it('should_render_title_when_provided', () => {
    render(<Sidebar title="Sessions">Content</Sidebar>);
    expect(screen.getByText('Sessions')).toBeInTheDocument();
  });
});
