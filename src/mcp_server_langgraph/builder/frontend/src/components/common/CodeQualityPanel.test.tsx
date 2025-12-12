/**
 * Tests for CodeQualityPanel Component
 *
 * TDD: Tests written FIRST before implementation
 *
 * Displays code quality metrics for generated workflow code.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CodeQualityPanel } from './CodeQualityPanel';

describe('CodeQualityPanel Component', () => {
  const defaultMetrics = {
    linesOfCode: 45,
    nodeCount: 5,
    edgeCount: 4,
    complexity: 'low' as const,
  };

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders the panel with title', () => {
      render(<CodeQualityPanel {...defaultMetrics} />);
      expect(screen.getByText(/code quality/i)).toBeInTheDocument();
    });

    it('displays lines of code metric', () => {
      render(<CodeQualityPanel {...defaultMetrics} />);
      expect(screen.getByText('45')).toBeInTheDocument();
      expect(screen.getByText(/lines/i)).toBeInTheDocument();
    });

    it('displays node count metric', () => {
      render(<CodeQualityPanel {...defaultMetrics} />);
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText(/nodes/i)).toBeInTheDocument();
    });

    it('displays edge count metric', () => {
      render(<CodeQualityPanel {...defaultMetrics} />);
      expect(screen.getByText('4')).toBeInTheDocument();
      expect(screen.getByText(/edges/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Complexity Display Tests
  // ==============================================================================

  describe('Complexity Display', () => {
    it('shows low complexity with green indicator', () => {
      render(<CodeQualityPanel {...defaultMetrics} complexity="low" />);
      const complexityBadge = screen.getByTestId('complexity-badge');
      expect(complexityBadge).toHaveClass('bg-green-100');
      expect(screen.getByText(/low/i)).toBeInTheDocument();
    });

    it('shows medium complexity with yellow indicator', () => {
      render(<CodeQualityPanel {...defaultMetrics} complexity="medium" />);
      const complexityBadge = screen.getByTestId('complexity-badge');
      expect(complexityBadge).toHaveClass('bg-yellow-100');
      expect(screen.getByText(/medium/i)).toBeInTheDocument();
    });

    it('shows high complexity with red indicator', () => {
      render(<CodeQualityPanel {...defaultMetrics} complexity="high" />);
      const complexityBadge = screen.getByTestId('complexity-badge');
      expect(complexityBadge).toHaveClass('bg-red-100');
      expect(screen.getByText(/high/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Empty State Tests
  // ==============================================================================

  describe('Empty State', () => {
    it('shows empty state when no code generated', () => {
      render(<CodeQualityPanel linesOfCode={0} nodeCount={0} edgeCount={0} complexity="low" />);
      expect(screen.getByText(/no code generated/i)).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Lint Warnings Tests
  // ==============================================================================

  describe('Lint Warnings', () => {
    it('shows lint warning count when provided', () => {
      render(<CodeQualityPanel {...defaultMetrics} lintWarnings={3} />);
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText(/warnings/i)).toBeInTheDocument();
    });

    it('shows zero warnings when none provided', () => {
      render(<CodeQualityPanel {...defaultMetrics} lintWarnings={0} />);
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has accessible heading', () => {
      render(<CodeQualityPanel {...defaultMetrics} />);
      expect(screen.getByRole('heading', { name: /code quality/i })).toBeInTheDocument();
    });

    it('has region role for panel', () => {
      render(<CodeQualityPanel {...defaultMetrics} />);
      expect(screen.getByRole('region')).toBeInTheDocument();
    });
  });
});
