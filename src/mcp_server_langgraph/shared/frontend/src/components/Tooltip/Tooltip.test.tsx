/**
 * Tooltip Component Tests
 *
 * TDD: RED phase - Write tests first
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from './Tooltip';

describe('Tooltip Component', () => {
  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders trigger element', () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      expect(screen.getByText('Hover me')).toBeInTheDocument();
    });

    it('does not show tooltip content initially', () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      expect(screen.queryByText('Tooltip content')).not.toBeInTheDocument();
    });

    it('shows tooltip content on hover', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      fireEvent.mouseEnter(screen.getByText('Hover me'));

      await waitFor(() => {
        expect(screen.getByText('Tooltip content')).toBeInTheDocument();
      });
    });

    it('hides tooltip content on mouse leave', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      const trigger = screen.getByText('Hover me');
      fireEvent.mouseEnter(trigger);

      await waitFor(() => {
        expect(screen.getByText('Tooltip content')).toBeInTheDocument();
      });

      fireEvent.mouseLeave(trigger);

      await waitFor(() => {
        expect(screen.queryByText('Tooltip content')).not.toBeInTheDocument();
      });
    });
  });

  // ==============================================================================
  // Accessibility Tests
  // ==============================================================================

  describe('Accessibility', () => {
    it('has correct ARIA attributes on trigger', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      const trigger = screen.getByText('Hover me');
      fireEvent.mouseEnter(trigger);

      await waitFor(() => {
        expect(trigger).toHaveAttribute('aria-describedby');
      });
    });

    it('tooltip content has role tooltip', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      fireEvent.mouseEnter(screen.getByText('Hover me'));

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toBeInTheDocument();
      });
    });

    it('shows tooltip on focus for keyboard users', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button>Focus me</button>
            </TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      const button = screen.getByRole('button', { name: 'Focus me' });
      fireEvent.focus(button);

      await waitFor(() => {
        expect(screen.getByText('Tooltip content')).toBeInTheDocument();
      });
    });
  });

  // ==============================================================================
  // Positioning Tests
  // ==============================================================================

  describe('Positioning', () => {
    it('supports side prop for positioning', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent side="bottom">Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      fireEvent.mouseEnter(screen.getByText('Hover me'));

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toBeInTheDocument();
      });
    });

    it('supports align prop for alignment', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent align="start">Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      fireEvent.mouseEnter(screen.getByText('Hover me'));

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toBeInTheDocument();
      });
    });
  });

  // ==============================================================================
  // Delay Tests
  // ==============================================================================

  describe('Delay', () => {
    it('supports custom delay before showing', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      // With 0 delay, tooltip should show immediately on hover
      fireEvent.mouseEnter(screen.getByText('Hover me'));

      await waitFor(() => {
        expect(screen.getByText('Tooltip content')).toBeInTheDocument();
      });
    });
  });

  // ==============================================================================
  // Styling Tests
  // ==============================================================================

  describe('Styling', () => {
    it('applies custom className to content', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent className="custom-tooltip">Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      fireEvent.mouseEnter(screen.getByText('Hover me'));

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toHaveClass('custom-tooltip');
      });
    });

    it('supports dark mode styling', async () => {
      render(
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger>Hover me</TooltipTrigger>
            <TooltipContent variant="dark">Tooltip content</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );

      fireEvent.mouseEnter(screen.getByText('Hover me'));

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toBeInTheDocument();
      });
    });
  });
});
