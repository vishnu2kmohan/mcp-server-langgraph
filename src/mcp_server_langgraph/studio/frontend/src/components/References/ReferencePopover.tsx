/**
 * ReferencePopover component
 *
 * Shows expanded details for a reference when hovering/clicking on ReferenceChip.
 * Provides:
 * - Full description
 * - Copy reference syntax button
 * - Deep link to relevant page (e.g., Connections for tools)
 */

import { useState } from 'react';
import { Link } from 'react-router';
import { Copy, ExternalLink, Check } from 'lucide-react';
import { Button } from '@/components/UI';
import type { ResolvedReference, ReferenceType } from '@/types/references';

export interface ReferencePopoverProps {
  /** The resolved reference to display */
  reference: ResolvedReference;
  /** Whether the popover is currently open */
  isOpen: boolean;
  /** Callback when close is requested */
  onClose: () => void;
}

/**
 * Build the [[type:qualifier:id]] syntax string for copying.
 */
function buildReferenceSyntax(ref: ResolvedReference): string {
  if (ref.type === 'tool') {
    return `[[tool:${ref.qualifier}:${ref.id}]]`;
  }
  return `[[${ref.type}:${ref.id}]]`;
}

/**
 * Get the deep link URL for navigating to the reference's detail page.
 */
function getDeepLinkUrl(ref: ResolvedReference): string | null {
  switch (ref.type) {
    case 'tool':
      // Navigate to Connections page with connection selected
      if (ref.metadata?.connectionId) {
        return `/connections?selected=${ref.metadata.connectionId}&tab=capabilities`;
      }
      return '/connections';
    case 'skill':
      return `/skills?skill=${ref.id}`;
    case 'artifact':
      return `/artifacts?artifact=${ref.id}`;
    default:
      return null;
  }
}

/**
 * Get the deep link label based on reference type.
 */
function getDeepLinkLabel(type: ReferenceType): string {
  switch (type) {
    case 'tool':
      return 'View in Connections';
    case 'skill':
      return 'View in Skills';
    case 'artifact':
      return 'View in Artifacts';
    default:
      return 'View Details';
  }
}

/**
 * ReferencePopover displays detailed information about a reference.
 */
export function ReferencePopover({
  reference,
  isOpen,
  onClose,
}: ReferencePopoverProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) {
    return null;
  }

  const syntax = buildReferenceSyntax(reference);
  const deepLinkUrl = getDeepLinkUrl(reference);
  const deepLinkLabel = getDeepLinkLabel(reference.type);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(syntax);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for browsers without clipboard API
      console.error('Failed to copy to clipboard');
    }
  };

  return (
    <div
      className="absolute z-50 w-72 p-3 bg-neutral-1 border border-neutral-6 rounded-lg shadow-lg"
      role="dialog"
      aria-label={`${reference.displayName} details`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-neutral-12">
          {reference.displayName}
        </h4>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="p-0.5 min-w-0"
          aria-label="Close popover"
        >
          &times;
        </Button>
      </div>

      {/* Type badge */}
      <div className="mb-2">
        <span className="text-xs text-neutral-11 uppercase tracking-wide">
          {reference.type}
        </span>
      </div>

      {/* Description */}
      {reference.description && (
        <p className="text-sm text-neutral-11 mb-3">
          {reference.description}
        </p>
      )}

      {/* Metadata display for tools */}
      {reference.type === 'tool' && reference.metadata?.inputSchema && (
        <div className="text-xs text-neutral-10 mb-3">
          <span className="font-medium">Parameters: </span>
          {Object.keys(reference.metadata.inputSchema).length} defined
        </div>
      )}

      {/* Metadata display for skills */}
      {reference.type === 'skill' &&
        reference.metadata?.tags &&
        (reference.metadata.tags as string[]).length > 0 && (
          <div className="text-xs text-neutral-10 mb-3">
            <span className="font-medium">Tags: </span>
            {(reference.metadata.tags as string[]).join(', ')}
          </div>
        )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-neutral-6">
        {/* Copy button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          aria-label="Copy reference syntax"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 mr-1" />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 mr-1" />
              Copy
            </>
          )}
        </Button>

        {/* Deep link */}
        {deepLinkUrl && reference.status === 'valid' && (
          <Link
            to={deepLinkUrl}
            className="inline-flex items-center gap-1 text-xs text-primary-11 hover:text-primary-12"
          >
            {deepLinkLabel}
            <ExternalLink className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  );
}
