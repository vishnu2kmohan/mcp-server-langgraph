/**
 * Card Component Tests
 *
 * TDD: RED phase - Write tests first
 * Focus on accessibility (WCAG 2.2 AA compliance)
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './Card';

expect.extend(toHaveNoViolations);

describe('Card Component', () => {
  // ==============================================================================
  // Accessibility Tests (jest-axe)
  // ==============================================================================

  describe('Accessibility', () => {
    it('should have no accessibility violations in default state', async () => {
      const { container } = render(
        <Card>
          <CardContent>Card content</CardContent>
        </Card>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no accessibility violations with full composition', async () => {
      const { container } = render(
        <Card>
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
          </CardHeader>
          <CardContent>Card content goes here</CardContent>
          <CardFooter>
            <button>Action</button>
          </CardFooter>
        </Card>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no accessibility violations for all variants', async () => {
      const variants = ['default', 'elevated', 'ghost'] as const;

      for (const variant of variants) {
        const { container } = render(
          <Card variant={variant}>
            <CardContent>{variant} card</CardContent>
          </Card>
        );
        const results = await axe(container);
        expect(results).toHaveNoViolations();
      }
    });

    it('should have no accessibility violations when interactive', async () => {
      const { container } = render(
        <Card interactive onClick={() => {}}>
          <CardContent>Clickable card</CardContent>
        </Card>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('CardTitle renders as h3 for proper heading hierarchy', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Title</CardTitle>
          </CardHeader>
        </Card>
      );
      const title = screen.getByRole('heading', { level: 3 });
      expect(title).toBeInTheDocument();
      expect(title).toHaveTextContent('Title');
    });
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders Card with children', () => {
      render(<Card data-testid="card">Content</Card>);
      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('renders CardHeader with children', () => {
      render(
        <Card>
          <CardHeader data-testid="header">Header content</CardHeader>
        </Card>
      );
      expect(screen.getByTestId('header')).toBeInTheDocument();
    });

    it('renders CardTitle with children', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>My Title</CardTitle>
          </CardHeader>
        </Card>
      );
      expect(screen.getByText('My Title')).toBeInTheDocument();
    });

    it('renders CardContent with children', () => {
      render(
        <Card>
          <CardContent data-testid="content">Main content</CardContent>
        </Card>
      );
      expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('renders CardFooter with children', () => {
      render(
        <Card>
          <CardFooter data-testid="footer">Footer content</CardFooter>
        </Card>
      );
      expect(screen.getByTestId('footer')).toBeInTheDocument();
    });

    it('renders full card composition', () => {
      render(
        <Card data-testid="card">
          <CardHeader>
            <CardTitle>Title</CardTitle>
          </CardHeader>
          <CardContent>Content</CardContent>
          <CardFooter>
            <button>Action</button>
          </CardFooter>
        </Card>
      );

      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Variant Tests
  // ==============================================================================

  describe('Variants', () => {
    it('applies default variant classes', () => {
      render(<Card data-testid="card">Default</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('border');
      expect(card).toHaveClass('bg-white');
    });

    it('applies elevated variant classes', () => {
      render(<Card variant="elevated" data-testid="card">Elevated</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('shadow-lg');
    });

    it('applies ghost variant classes', () => {
      render(<Card variant="ghost" data-testid="card">Ghost</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('bg-transparent');
    });
  });

  // ==============================================================================
  // Padding Tests
  // ==============================================================================

  describe('Padding', () => {
    it('applies medium padding by default', () => {
      render(<Card data-testid="card">Content</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('p-4');
    });

    it('applies no padding when padding is none', () => {
      render(<Card padding="none" data-testid="card">Content</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('p-0');
    });

    it('applies small padding', () => {
      render(<Card padding="sm" data-testid="card">Content</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('p-3');
    });

    it('applies large padding', () => {
      render(<Card padding="lg" data-testid="card">Content</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('p-6');
    });
  });

  // ==============================================================================
  // Interactive Tests
  // ==============================================================================

  describe('Interactive', () => {
    it('applies interactive classes when interactive is true', () => {
      render(<Card interactive data-testid="card">Interactive</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('cursor-pointer');
    });

    it('responds to click events when interactive', () => {
      const onClick = vi.fn();
      render(<Card interactive onClick={onClick} data-testid="card">Clickable</Card>);
      fireEvent.click(screen.getByTestId('card'));
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('does not have cursor-pointer when not interactive', () => {
      render(<Card data-testid="card">Not Interactive</Card>);
      const card = screen.getByTestId('card');
      expect(card).not.toHaveClass('cursor-pointer');
    });
  });

  // ==============================================================================
  // Custom Class Tests
  // ==============================================================================

  describe('Custom Classes', () => {
    it('merges custom className with Card', () => {
      render(<Card className="custom-card" data-testid="card">Content</Card>);
      const card = screen.getByTestId('card');
      expect(card).toHaveClass('custom-card');
      expect(card).toHaveClass('rounded-lg'); // Still has base class
    });

    it('merges custom className with CardHeader', () => {
      render(
        <Card>
          <CardHeader className="custom-header" data-testid="header">Header</CardHeader>
        </Card>
      );
      expect(screen.getByTestId('header')).toHaveClass('custom-header');
    });

    it('merges custom className with CardTitle', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle className="custom-title">Title</CardTitle>
          </CardHeader>
        </Card>
      );
      expect(screen.getByText('Title')).toHaveClass('custom-title');
    });

    it('merges custom className with CardContent', () => {
      render(
        <Card>
          <CardContent className="custom-content" data-testid="content">Content</CardContent>
        </Card>
      );
      expect(screen.getByTestId('content')).toHaveClass('custom-content');
    });

    it('merges custom className with CardFooter', () => {
      render(
        <Card>
          <CardFooter className="custom-footer" data-testid="footer">Footer</CardFooter>
        </Card>
      );
      expect(screen.getByTestId('footer')).toHaveClass('custom-footer');
    });
  });

  // ==============================================================================
  // Ref Forwarding Tests
  // ==============================================================================

  describe('Ref Forwarding', () => {
    it('forwards ref to Card element', () => {
      const ref = { current: null };
      render(<Card ref={ref}>Content</Card>);
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });
  });
});
