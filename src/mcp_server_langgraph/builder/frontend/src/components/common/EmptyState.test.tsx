/**
 * EmptyState Component Tests
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EmptyState, EmptyCanvas, EmptyCodePanel, ConnectionError } from './EmptyState';

describe('EmptyState', () => {
  describe('Base EmptyState', () => {
    it('renders title', () => {
      render(<EmptyState title="No items" />);
      expect(screen.getByText('No items')).toBeInTheDocument();
    });

    it('renders description', () => {
      render(<EmptyState title="No items" description="Add some items to get started" />);
      expect(screen.getByText('Add some items to get started')).toBeInTheDocument();
    });

    it('renders icon when provided', () => {
      const Icon = () => <svg data-testid="icon" />;
      render(<EmptyState title="No items" icon={<Icon />} />);
      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('renders action button when provided', () => {
      const handleClick = vi.fn();
      render(
        <EmptyState
          title="No items"
          actionLabel="Add Item"
          onAction={handleClick}
        />
      );
      expect(screen.getByRole('button', { name: /add item/i })).toBeInTheDocument();
    });

    it('calls onAction when button is clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(
        <EmptyState
          title="No items"
          actionLabel="Add Item"
          onAction={handleClick}
        />
      );

      await user.click(screen.getByRole('button', { name: /add item/i }));
      expect(handleClick).toHaveBeenCalled();
    });

    it('applies custom className', () => {
      render(<EmptyState title="No items" className="custom-class" />);
      expect(screen.getByTestId('empty-state')).toHaveClass('custom-class');
    });
  });

  describe('EmptyCanvas', () => {
    it('renders empty canvas message', () => {
      render(<EmptyCanvas />);
      expect(screen.getByText(/drag nodes/i)).toBeInTheDocument();
    });

    it('has get started action', () => {
      render(<EmptyCanvas />);
      expect(screen.getByText(/get started/i)).toBeInTheDocument();
    });
  });

  describe('EmptyCodePanel', () => {
    it('renders empty code panel message', () => {
      render(<EmptyCodePanel />);
      expect(screen.getByText(/no code generated/i)).toBeInTheDocument();
    });

    it('shows instruction to generate code', () => {
      render(<EmptyCodePanel />);
      expect(screen.getByText(/add nodes.*generate/i)).toBeInTheDocument();
    });
  });

  describe('ConnectionError', () => {
    it('renders error message', () => {
      render(<ConnectionError />);
      expect(screen.getByText(/unable to connect/i)).toBeInTheDocument();
    });

    it('has retry action', () => {
      const handleRetry = vi.fn();
      render(<ConnectionError onRetry={handleRetry} />);
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', async () => {
      const user = userEvent.setup();
      const handleRetry = vi.fn();
      render(<ConnectionError onRetry={handleRetry} />);

      await user.click(screen.getByRole('button', { name: /retry/i }));
      expect(handleRetry).toHaveBeenCalled();
    });
  });
});
