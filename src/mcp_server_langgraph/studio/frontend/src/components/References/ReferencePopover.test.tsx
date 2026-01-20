/**
 * Tests for ReferencePopover component
 *
 * TDD: Tests written first per project guidelines.
 * WCAG 2.2 AA compliance verified.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import _userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { ReferencePopover } from './ReferencePopover';
import type { ResolvedReference } from '@/types/references';

// Mock navigator.clipboard globally
const mockWriteText = vi.fn();

beforeEach(() => {
  mockWriteText.mockClear();
  mockWriteText.mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: mockWriteText },
    writable: true,
    configurable: true,
  });
});

// Test fixtures
const createToolReference = (overrides: Partial<ResolvedReference> = {}): ResolvedReference => ({
  type: 'tool',
  qualifier: 'filesystem',
  id: 'read_file',
  displayName: 'Read File Tool',
  description: 'Reads a file from the filesystem',
  status: 'valid',
  metadata: {
    connectionId: 'conn-uuid-123',
    inputSchema: { path: { type: 'string' } },
  },
  ...overrides,
});

const createSkillReference = (overrides: Partial<ResolvedReference> = {}): ResolvedReference => ({
  type: 'skill',
  qualifier: 'code-review',
  id: 'code-review',
  displayName: 'Code Review',
  description: 'Reviews code for quality and best practices',
  status: 'valid',
  metadata: {
    tags: ['review', 'quality', 'linting'],
    version: '1.2.0',
  },
  ...overrides,
});

const createArtifactReference = (overrides: Partial<ResolvedReference> = {}): ResolvedReference => ({
  type: 'artifact',
  qualifier: 'chart-123',
  id: 'chart-123',
  displayName: 'Sales Chart',
  description: 'Monthly sales performance chart',
  status: 'valid',
  metadata: {
    contentType: 'image/svg+xml',
  },
  ...overrides,
});

const renderWithRouter = (ui: React.ReactElement) => {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
};

describe('ReferencePopover', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  describe('rendering', () => {
    it('should return null when closed', () => {
      const ref = createToolReference();
      const { container } = renderWithRouter(
        <ReferencePopover reference={ref} isOpen={false} onClose={() => {}} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should render when open', () => {
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should display the reference display name', () => {
      const ref = createToolReference({ displayName: 'Custom Tool Name' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByText('Custom Tool Name')).toBeInTheDocument();
    });

    it('should display the reference type badge', () => {
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByText('tool')).toBeInTheDocument();
    });

    it('should display the description when available', () => {
      const ref = createToolReference({ description: 'A powerful file reading tool' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByText('A powerful file reading tool')).toBeInTheDocument();
    });

    it('should not display description section when undefined', () => {
      const ref = createToolReference({ description: undefined });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      // Should still render without the description paragraph
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.queryByText('A powerful')).not.toBeInTheDocument();
    });
  });

  describe('metadata display', () => {
    it('should show parameter count for tools with inputSchema', () => {
      const ref = createToolReference({
        metadata: {
          inputSchema: { path: {}, encoding: {}, mode: {} },
        },
      });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByText(/Parameters:/)).toBeInTheDocument();
      expect(screen.getByText(/3 defined/)).toBeInTheDocument();
    });

    it('should show tags for skills', () => {
      const ref = createSkillReference({
        metadata: { tags: ['testing', 'automation', 'ci'] },
      });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByText(/Tags:/)).toBeInTheDocument();
      expect(screen.getByText(/testing, automation, ci/)).toBeInTheDocument();
    });

    it('should not show metadata section for artifacts', () => {
      const ref = createArtifactReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      // Artifacts don't show inputSchema or tags sections
      expect(screen.queryByText(/Parameters:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Tags:/)).not.toBeInTheDocument();
    });
  });

  describe('copy functionality', () => {
    it('should copy tool reference syntax on button click', async () => {
      const ref = createToolReference({
        qualifier: 'fs',
        id: 'read',
      });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const copyButton = screen.getByRole('button', { name: /copy reference syntax/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith('[[tool:fs:read]]');
      });
    });

    it('should copy skill reference syntax correctly', async () => {
      const ref = createSkillReference({ id: 'analyze' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const copyButton = screen.getByRole('button', { name: /copy reference syntax/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith('[[skill:analyze]]');
      });
    });

    it('should copy artifact reference syntax correctly', async () => {
      const ref = createArtifactReference({ id: 'chart-456' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const copyButton = screen.getByRole('button', { name: /copy reference syntax/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockWriteText).toHaveBeenCalledWith('[[artifact:chart-456]]');
      });
    });

    it('should show "Copied" feedback after copying', async () => {
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const copyButton = screen.getByRole('button', { name: /copy reference syntax/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(screen.getByText('Copied')).toBeInTheDocument();
      });
    });

    it('should revert to "Copy" after timeout', async () => {
      vi.useFakeTimers();
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const copyButton = screen.getByRole('button', { name: /copy reference syntax/i });

      await act(async () => {
        fireEvent.click(copyButton);
        // Allow promise to resolve
        await Promise.resolve();
      });

      expect(screen.getByText('Copied')).toBeInTheDocument();

      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      expect(screen.getByText('Copy')).toBeInTheDocument();
    });
  });

  describe('deep linking', () => {
    it('should show deep link for valid tool references', () => {
      const ref = createToolReference({
        status: 'valid',
        metadata: { connectionId: 'conn-abc' },
      });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const link = screen.getByRole('link', { name: /view in connections/i });
      expect(link).toHaveAttribute('href', '/connections?selected=conn-abc&tab=capabilities');
    });

    it('should show deep link for valid skill references', () => {
      const ref = createSkillReference({ status: 'valid' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const link = screen.getByRole('link', { name: /view in skills/i });
      expect(link).toHaveAttribute('href', '/skills?skill=code-review');
    });

    it('should show deep link for valid artifact references', () => {
      const ref = createArtifactReference({ status: 'valid', id: 'my-artifact' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const link = screen.getByRole('link', { name: /view in artifacts/i });
      expect(link).toHaveAttribute('href', '/artifacts?artifact=my-artifact');
    });

    it('should NOT show deep link for not_found references', () => {
      const ref = createToolReference({ status: 'not_found' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.queryByRole('link', { name: /view in/i })).not.toBeInTheDocument();
    });

    it('should NOT show deep link for unauthorized references', () => {
      const ref = createSkillReference({ status: 'unauthorized' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.queryByRole('link', { name: /view in/i })).not.toBeInTheDocument();
    });

    it('should use fallback connections URL when connectionId is missing', () => {
      const ref = createToolReference({
        status: 'valid',
        metadata: {}, // No connectionId
      });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const link = screen.getByRole('link', { name: /view in connections/i });
      expect(link).toHaveAttribute('href', '/connections');
    });
  });

  describe('close button', () => {
    it('should call onClose when close button is clicked', () => {
      const onClose = vi.fn();
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={onClose} />
      );

      const closeButton = screen.getByRole('button', { name: /close popover/i });
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('accessibility', () => {
    it('should have dialog role', () => {
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should have aria-label with display name', () => {
      const ref = createToolReference({ displayName: 'My Special Tool' });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-label', 'My Special Tool details');
    });

    it('should have accessible close button', () => {
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const closeButton = screen.getByRole('button', { name: /close popover/i });
      expect(closeButton).toBeInTheDocument();
    });

    it('should have accessible copy button', () => {
      const ref = createToolReference();
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      const copyButton = screen.getByRole('button', { name: /copy reference syntax/i });
      expect(copyButton).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('should handle memory references (Phase 4)', () => {
      const ref: ResolvedReference = {
        type: 'memory',
        qualifier: 'note-123',
        id: 'note-123',
        displayName: 'Meeting Notes',
        description: 'Notes from the team meeting',
        status: 'valid',
      };
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByText('Meeting Notes')).toBeInTheDocument();
      expect(screen.getByText('memory')).toBeInTheDocument();
    });

    it('should handle plan references (Phase 4)', () => {
      const ref: ResolvedReference = {
        type: 'plan',
        qualifier: 'plan-456',
        id: 'plan-456',
        displayName: 'Refactoring Plan',
        description: 'Plan for refactoring the authentication module',
        status: 'valid',
      };
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      expect(screen.getByText('Refactoring Plan')).toBeInTheDocument();
      expect(screen.getByText('plan')).toBeInTheDocument();
    });

    it('should handle empty metadata gracefully', () => {
      const ref = createToolReference({ metadata: undefined });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      // Should render without crashing
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.queryByText(/Parameters:/)).not.toBeInTheDocument();
    });

    it('should handle empty tags array for skills', () => {
      const ref = createSkillReference({ metadata: { tags: [] } });
      renderWithRouter(
        <ReferencePopover reference={ref} isOpen={true} onClose={() => {}} />
      );

      // Empty tags should not show the tags section (or show empty)
      // Implementation shows tags only when array has items
      expect(screen.queryByText(/Tags:/)).not.toBeInTheDocument();
    });
  });
});
