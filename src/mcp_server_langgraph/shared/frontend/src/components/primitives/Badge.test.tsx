/**
 * Badge Component Tests
 *
 * TDD: RED phase - Write tests first
 * Focus on accessibility (WCAG 2.2 AA compliance)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { Badge } from './Badge';

expect.extend(toHaveNoViolations);

describe('Badge Component', () => {
  // ==============================================================================
  // Accessibility Tests (jest-axe)
  // ==============================================================================

  describe('Accessibility', () => {
    it('should have no accessibility violations in default state', async () => {
      const { container } = render(<Badge>Default</Badge>);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no accessibility violations for all variants', async () => {
      const variants = ['default', 'primary', 'success', 'warning', 'error', 'outline'] as const;

      for (const variant of variants) {
        const { container } = render(<Badge variant={variant}>{variant}</Badge>);
        const results = await axe(container);
        expect(results).toHaveNoViolations();
      }
    });

    it('should have no accessibility violations with icon', async () => {
      const Icon = () => <span aria-hidden="true">★</span>;
      const { container } = render(<Badge icon={<Icon />}>Featured</Badge>);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('icon should be aria-hidden', () => {
      const Icon = () => <span data-testid="icon">★</span>;
      render(<Badge icon={<Icon />}>Featured</Badge>);
      const iconWrapper = screen.getByTestId('icon').parentElement;
      expect(iconWrapper).toHaveAttribute('aria-hidden', 'true');
    });
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders with children', () => {
      render(<Badge>Status</Badge>);
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('renders with icon', () => {
      const Icon = () => <span data-testid="icon">★</span>;
      render(<Badge icon={<Icon />}>Featured</Badge>);
      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('renders as span element', () => {
      render(<Badge>Status</Badge>);
      const badge = screen.getByText('Status');
      expect(badge.tagName).toBe('SPAN');
    });
  });

  // ==============================================================================
  // Variant Tests
  // ==============================================================================

  describe('Variants', () => {
    it('applies default variant classes', () => {
      render(<Badge>Default</Badge>);
      const badge = screen.getByText('Default');
      expect(badge).toHaveClass('bg-gray-100');
    });

    it('applies primary variant classes', () => {
      render(<Badge variant="primary">Primary</Badge>);
      const badge = screen.getByText('Primary');
      expect(badge).toHaveClass('bg-primary-100');
    });

    it('applies success variant classes', () => {
      render(<Badge variant="success">Success</Badge>);
      const badge = screen.getByText('Success');
      expect(badge).toHaveClass('bg-success-100');
    });

    it('applies warning variant classes', () => {
      render(<Badge variant="warning">Warning</Badge>);
      const badge = screen.getByText('Warning');
      expect(badge).toHaveClass('bg-warning-100');
    });

    it('applies error variant classes', () => {
      render(<Badge variant="error">Error</Badge>);
      const badge = screen.getByText('Error');
      expect(badge).toHaveClass('bg-error-100');
    });

    it('applies outline variant classes', () => {
      render(<Badge variant="outline">Outline</Badge>);
      const badge = screen.getByText('Outline');
      expect(badge).toHaveClass('bg-transparent');
      expect(badge).toHaveClass('border');
    });
  });

  // ==============================================================================
  // Size Tests
  // ==============================================================================

  describe('Sizes', () => {
    it('applies medium size by default', () => {
      render(<Badge>Medium</Badge>);
      const badge = screen.getByText('Medium');
      expect(badge).toHaveClass('text-sm');
    });

    it('applies small size', () => {
      render(<Badge size="sm">Small</Badge>);
      const badge = screen.getByText('Small');
      expect(badge).toHaveClass('text-xs');
    });

    it('applies large size', () => {
      render(<Badge size="lg">Large</Badge>);
      const badge = screen.getByText('Large');
      expect(badge).toHaveClass('text-base');
    });
  });

  // ==============================================================================
  // Pill Shape Tests
  // ==============================================================================

  describe('Pill Shape', () => {
    it('applies rounded-md by default (not pill)', () => {
      render(<Badge>Normal</Badge>);
      const badge = screen.getByText('Normal');
      expect(badge).toHaveClass('rounded-md');
    });

    it('applies rounded-full when pill is true', () => {
      render(<Badge pill>Pill</Badge>);
      const badge = screen.getByText('Pill');
      expect(badge).toHaveClass('rounded-full');
    });
  });

  // ==============================================================================
  // Custom Class Tests
  // ==============================================================================

  describe('Custom Classes', () => {
    it('merges custom className with variant classes', () => {
      render(<Badge className="custom-class">Custom</Badge>);
      const badge = screen.getByText('Custom');
      expect(badge).toHaveClass('custom-class');
      expect(badge).toHaveClass('bg-gray-100'); // Still has variant class
    });
  });
});
