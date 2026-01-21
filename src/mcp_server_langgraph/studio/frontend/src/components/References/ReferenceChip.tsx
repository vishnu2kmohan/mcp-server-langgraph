/**
 * ReferenceChip component
 *
 * Renders an inline chip for [[type:qualifier:id]] markdown references.
 * Shows type-specific icon, resolved display name, and popover on hover.
 */

import { forwardRef } from 'react';
import { cva } from 'class-variance-authority';
import { Wrench, Sparkles, FileCode, Brain, ListTodo } from 'lucide-react';
import { Tooltip, Button } from '@/components/UI';
import { useReferenceResolver } from '@/contexts/ReferenceResolverContext';
import { getReferenceKey } from '@/types/references';
import type { ReferenceType, ReferenceStatus, ReferenceChipProps } from '@/types/references';
import { cn } from '@/utils/cn';

/**
 * Chip style variants based on reference type and status.
 */
const chipVariants = cva(
  'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium transition-opacity',
  {
    variants: {
      type: {
        tool: 'bg-primary-3 text-primary-11',
        skill: 'bg-success-3 text-success-11',
        artifact: 'bg-neutral-3 text-neutral-11',
        memory: 'bg-info-3 text-info-11',
        plan: 'bg-warning-3 text-warning-11',
      },
      status: {
        valid: 'cursor-pointer hover:opacity-80',
        not_found: 'opacity-50 line-through cursor-not-allowed',
        unauthorized: 'opacity-50 cursor-not-allowed',
        loading: 'animate-pulse',
      },
    },
    defaultVariants: {
      type: 'tool',
      status: 'valid',
    },
  }
);

/**
 * Icons for each reference type.
 */
const referenceIcons: Record<ReferenceType, typeof Wrench> = {
  tool: Wrench,
  skill: Sparkles,
  artifact: FileCode,
  memory: Brain,
  plan: ListTodo,
};

/**
 * Accessible labels for reference types.
 */
const typeLabels: Record<ReferenceType, string> = {
  tool: 'Tool reference',
  skill: 'Skill reference',
  artifact: 'Artifact reference',
  memory: 'Memory reference',
  plan: 'Plan reference',
};

/**
 * ReferenceChip component for rendering inline reference chips.
 *
 * Features:
 * - Type-specific icons (Wrench for tools, Sparkles for skills, FileCode for artifacts)
 * - Type-specific colors (primary for tools, success for skills, neutral for artifacts)
 * - Status-based styling (opacity, line-through for not_found, etc.)
 * - Tooltip with description on hover
 * - Keyboard accessible
 */
export const ReferenceChip = forwardRef<HTMLButtonElement, ReferenceChipProps>(
  function ReferenceChip(
    { type, qualifier, id, label, connectionId: _connectionId },
    ref
  ) {
    // Get resolved reference from context
    const { resolvedRefs, isLoading } = useReferenceResolver();
    const key = getReferenceKey({ type, qualifier, id });
    const resolved = resolvedRefs.get(key);

    // Determine display text
    const displayName = label || resolved?.displayName || id;

    // Determine status for styling
    let status: ReferenceStatus = 'valid';
    if (isLoading && !resolved) {
      status = 'loading';
    } else if (resolved) {
      status = resolved.status;
    }

    // Get the appropriate icon
    const Icon = referenceIcons[type];

    // Build aria-label
    const ariaLabel =
      type === 'tool'
        ? `${typeLabels[type]}: ${qualifier}:${id}`
        : `${typeLabels[type]}: ${id}`;

    // Tooltip content
    const tooltipContent = resolved?.description || 'Loading...';

    const chip = (
      <Button
      variant="primary"
      ref={ref}
      type="button"
      className={cn(chipVariants({ type, status }))}
      aria-label={ariaLabel}
      disabled={status === 'not_found' || status === 'unauthorized'}>
        <Icon className="w-3 h-3" aria-hidden="true" />
        <span>{displayName}</span>
      </Button>
    );

    // Wrap with tooltip if we have content to show
    if (resolved?.description || status === 'loading') {
      return (
        <Tooltip content={tooltipContent}>
          {chip}
        </Tooltip>
      );
    }

    return chip;
  }
);

export type { ReferenceChipProps };
