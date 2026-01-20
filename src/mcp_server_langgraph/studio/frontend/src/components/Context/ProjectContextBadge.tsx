/**
 * ProjectContextBadge Component
 *
 * Badge indicator showing when project context is active.
 * Features:
 * - Visible only when project has context file
 * - Shows context file path
 * - Click to open context panel
 * - Tooltip on hover
 * - Loading indicator
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on GEMINI.md, AGENTS.md, CLAUDE.md patterns.
 */

import { useState } from "react";
import { FileText, Loader2 } from "lucide-react";

import { Button } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export type BadgeSize = "sm" | "md";

export interface ProjectContextBadgeProps {
  /** Whether project has context file */
  hasContext: boolean;
  /** Context file path */
  contextPath?: string;
  /** Whether loading */
  isLoading?: boolean;
  /** Size variant */
  size?: BadgeSize;
  /** Click handler */
  onClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Constants
// ==============================================================================

const SIZE_CLASSES: Record<
  BadgeSize,
  { badge: string; icon: number; text: string }
> = {
  sm: { badge: "px-2 py-0.5", icon: 12, text: "text-xs" },
  md: { badge: "px-2.5 py-1", icon: 14, text: "text-sm" },
};

// ==============================================================================
// Component
// ==============================================================================

export function ProjectContextBadge({
  hasContext,
  contextPath,
  isLoading = false,
  size = "md",
  onClick,
  className: _className = "",
}: ProjectContextBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Don't render if no context
  if (!hasContext) {
    return null;
  }

  const sizeClasses = SIZE_CLASSES[size];

  return (
    <div className="relative inline-flex">
      <Button
        variant="primary"
        className=".5 rounded-full bg-primary-3 bg-primary-4 text-primary-11 dark:text-primary-5 hover:bg-primary-4 dark:hover:bg-primary-a6 focus:ring-primary-7"
        type="button"
        data-testid="project-context-badge"
        data-size={size}
        onClick={onClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        aria-label={`Project context active${contextPath ? `: ${contextPath}` : ""}`}
      >
        {isLoading ? (
          <Loader2
            data-testid="loading-spinner"
            size={sizeClasses.icon}
            className="animate-spin"
          />
        ) : (
          <FileText data-testid="context-icon" size={sizeClasses.icon} />
        )}
        {contextPath && (
          <span className={`font-medium ${sizeClasses.text}`}>
            {contextPath}
          </span>
        )}
      </Button>
      {/* Tooltip */}
      {showTooltip && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-neutral-2 text-neutral-12 text-xs rounded shadow-lg whitespace-nowrap z-tooltip"
        >
          Project context active
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-12 dark:border-t-neutral-11" />
        </div>
      )}
    </div>
  );
}

export default ProjectContextBadge;
