/**
 * AttributionBadge Component
 *
 * Displays attribution status for artifacts in the canvas.
 * Three-state system:
 * - AI-generated: Created by AI, not modified by user
 * - User-modified: Originally AI-generated but edited by user
 * - User-created: Created by user from scratch
 *
 * Design System Compliance:
 * - Uses Radix color scale (insight, primary, neutral)
 * - Follows WCAG 2.2 AA contrast requirements
 */

import { Sparkles, Pencil, User } from "lucide-react";
import type { EditMetadata, AttributionType } from "../types/artifacts";
import { getAttributionType } from "../types/artifacts";

interface AttributionBadgeProps {
  /** Edit metadata to derive attribution type */
  metadata?: EditMetadata;
  /** Compact mode shows only icon */
  compact?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * Attribution configuration for each state
 */
const ATTRIBUTION_CONFIG: Record<
  AttributionType,
  {
    icon: React.ComponentType<{ className?: string; "data-testid"?: string }>;
    testId: string;
    label: string;
    className: string;
  }
> = {
  "ai-generated": {
    icon: Sparkles,
    testId: "sparkles-icon",
    label: "AI-generated",
    className: "bg-insight-3 text-insight-11 border-insight-6",
  },
  "user-modified": {
    icon: Pencil,
    testId: "pencil-icon",
    label: "User-modified",
    className: "bg-primary-3 text-primary-11 border-primary-6",
  },
  "user-created": {
    icon: User,
    testId: "user-icon",
    label: "User-created",
    className: "bg-neutral-2 text-neutral-11 border-neutral-6",
  },
};

export function AttributionBadge({
  metadata,
  compact = false,
  className = "",
}: AttributionBadgeProps) {
  const attributionType = getAttributionType(metadata);
  const config = ATTRIBUTION_CONFIG[attributionType];
  const Icon = config.icon;

  const baseCompactClasses = "inline-flex items-center justify-center p-1 rounded-full";
  const baseFullClasses = "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium";

  if (compact) {
    return (
      <span
        className={`${baseCompactClasses} ${config.className} ${className}`.trim()}
        aria-label={config.label}
      >
        <Icon className="w-3 h-3" data-testid={config.testId} />
      </span>
    );
  }

  return (
    <span
      className={`${baseFullClasses} ${config.className} ${className}`.trim()}
      data-testid="attribution-badge"
    >
      <Icon className="w-3 h-3" data-testid={config.testId} />
      {config.label}
    </span>
  );
}

export default AttributionBadge;
