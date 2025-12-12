/**
 * Tests for ValidationBadge Component
 *
 * TDD: Tests written FIRST before implementation
 *
 * Displays workflow validation status with visual indicators.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ValidationBadge } from './ValidationBadge';

describe('ValidationBadge Component', () => {
  // ==============================================================================
  // Valid State Tests
  // ==============================================================================

  describe('Valid State', () => {
    it('renders valid status with checkmark icon', () => {
      render(<ValidationBadge status="valid" />);
      expect(screen.getByTestId('validation-badge')).toBeInTheDocument();
      expect(screen.getByText(/valid/i)).toBeInTheDocument();
    });

    it('applies green styling for valid status', () => {
      render(<ValidationBadge status="valid" />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveClass('bg-green-100');
    });
  });

  // ==============================================================================
  // Warning State Tests
  // ==============================================================================

  describe('Warning State', () => {
    it('renders warning status with warning count', () => {
      render(<ValidationBadge status="warning" warningCount={3} />);
      expect(screen.getByText(/3 warnings/i)).toBeInTheDocument();
    });

    it('applies yellow styling for warning status', () => {
      render(<ValidationBadge status="warning" warningCount={1} />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveClass('bg-yellow-100');
    });

    it('uses singular warning for count of 1', () => {
      render(<ValidationBadge status="warning" warningCount={1} />);
      expect(screen.getByText(/1 warning$/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Error State Tests
  // ==============================================================================

  describe('Error State', () => {
    it('renders error status with error count', () => {
      render(<ValidationBadge status="error" errorCount={2} />);
      expect(screen.getByText(/2 errors/i)).toBeInTheDocument();
    });

    it('applies red styling for error status', () => {
      render(<ValidationBadge status="error" errorCount={1} />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveClass('bg-red-100');
    });

    it('uses singular error for count of 1', () => {
      render(<ValidationBadge status="error" errorCount={1} />);
      expect(screen.getByText(/1 error$/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Validating State Tests
  // ==============================================================================

  describe('Validating State', () => {
    it('renders validating status with spinner', () => {
      render(<ValidationBadge status="validating" />);
      expect(screen.getByText(/validating/i)).toBeInTheDocument();
    });

    it('applies blue styling for validating status', () => {
      render(<ValidationBadge status="validating" />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveClass('bg-blue-100');
    });
  });

  // ==============================================================================
  // Size Variants Tests
  // ==============================================================================

  describe('Size Variants', () => {
    it('renders small size', () => {
      render(<ValidationBadge status="valid" size="sm" />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveClass('text-xs');
    });

    it('renders medium size by default', () => {
      render(<ValidationBadge status="valid" />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveClass('text-sm');
    });

    it('renders large size', () => {
      render(<ValidationBadge status="valid" size="lg" />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveClass('text-base');
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has role status for screen readers', () => {
      render(<ValidationBadge status="valid" />);
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has aria-label describing the status', () => {
      render(<ValidationBadge status="error" errorCount={2} />);
      const badge = screen.getByTestId('validation-badge');
      expect(badge).toHaveAttribute('aria-label', expect.stringContaining('2 errors'));
    });
  });
});
