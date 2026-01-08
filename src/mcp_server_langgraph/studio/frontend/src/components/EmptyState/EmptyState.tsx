/**
 * EmptyState Component
 *
 * A standardized empty state component implementing the Fogg Behavior Model:
 * - Motivation: Why the user should take action
 * - Ability: How easy the action is (optional)
 * - Trigger: CTA button or action to perform
 *
 * @example
 * <EmptyState
 *   context="sessions"
 *   title="No sessions yet"
 *   motivation="Start a conversation to unlock AI-powered workflows"
 *   ability="Takes less than a minute"
 *   trigger={<Button onClick={handleNewSession}>Start Chat</Button>}
 * />
 */

import React from "react";
import {
  MessageSquare,
  FolderOpen,
  GitBranch,
  Activity,
  MessageCircle,
  FileText,
  Bell,
  Plug,
  Loader2,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../../utils/cn";

/**
 * Supported empty state contexts - maps to different features/pages
 */
export type EmptyStateContext =
  | "sessions"
  | "projects"
  | "workflows"
  | "traces"
  | "messages"
  | "files"
  | "alerts"
  | "connections";

/**
 * EmptyState display variants
 */
export type EmptyStateVariant = "default" | "compact" | "inline";

/**
 * EmptyState component props implementing Fogg Behavior Model
 */
export interface EmptyStateProps {
  /** Context determines the default icon */
  context: EmptyStateContext;
  /** Main title - what's empty */
  title: string;
  /** Motivation - why the user should act (Fogg: Motivation) */
  motivation: string;
  /** Optional description providing more context */
  description?: string;
  /** Optional ability indicator - how easy it is (Fogg: Ability) */
  ability?: string;
  /** Primary CTA trigger (Fogg: Trigger) */
  trigger: React.ReactNode;
  /** Optional secondary CTA */
  secondaryTrigger?: React.ReactNode;
  /** Custom icon to override context default */
  icon?: React.ReactNode;
  /** Display variant */
  variant?: EmptyStateVariant;
  /** Loading state - hides trigger and shows spinner */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Custom test ID */
  testId?: string;
}

/**
 * Context to icon mapping
 */
const CONTEXT_ICONS: Record<EmptyStateContext, LucideIcon> = {
  sessions: MessageSquare,
  projects: FolderOpen,
  workflows: GitBranch,
  traces: Activity,
  messages: MessageCircle,
  files: FileText,
  alerts: Bell,
  connections: Plug,
};

/**
 * Variant-specific styles
 */
const VARIANT_STYLES: Record<EmptyStateVariant, string> = {
  default: "py-12 px-6",
  compact: "py-6 px-4",
  inline: "py-4 px-3",
};

const ICON_SIZES: Record<EmptyStateVariant, number> = {
  default: 48,
  compact: 36,
  inline: 24,
};

const TITLE_STYLES: Record<EmptyStateVariant, string> = {
  default: "text-lg font-medium",
  compact: "text-base font-medium",
  inline: "text-sm font-medium",
};

const TEXT_STYLES: Record<EmptyStateVariant, string> = {
  default: "text-sm mt-2",
  compact: "text-sm mt-1",
  inline: "text-xs mt-1",
};

/**
 * EmptyState - A Fogg-model-aware empty state component
 *
 * Provides consistent empty state UX across the application with:
 * - Context-aware icons
 * - Motivation messaging
 * - Optional ability indicators
 * - Clear call-to-action triggers
 */
export function EmptyState({
  context,
  title,
  motivation,
  description,
  ability,
  trigger,
  secondaryTrigger,
  icon,
  variant = "default",
  isLoading = false,
  className,
  testId,
}: EmptyStateProps): React.ReactElement {
  const IconComponent = CONTEXT_ICONS[context];
  const iconSize = ICON_SIZES[variant];

  return (
    <div
      role="region"
      aria-label={`Empty state: ${title}`}
      data-testid={testId ?? `empty-state-${context}`}
      data-context={context}
      data-variant={variant}
      className={cn(
        "flex flex-col items-center justify-center text-center",
        VARIANT_STYLES[variant],
        className,
      )}
    >
      {/* Icon */}
      <div
        data-testid="empty-state-icon"
        aria-hidden="true"
        className="mb-4 text-gray-400 dark:text-gray-400"
      >
        {icon ?? <IconComponent size={iconSize} className="opacity-50" />}
      </div>

      {/* Title */}
      <h3
        className={cn(
          "text-gray-900 dark:text-gray-100",
          TITLE_STYLES[variant],
        )}
      >
        {title}
      </h3>

      {/* Description (optional) */}
      {description && (
        <p
          className={cn(
            "text-gray-600 dark:text-gray-400 max-w-md",
            TEXT_STYLES[variant],
          )}
        >
          {description}
        </p>
      )}

      {/* Motivation (Fogg Model) */}
      <p
        className={cn("text-gray-500 dark:text-gray-400", TEXT_STYLES[variant])}
      >
        {motivation}
      </p>

      {/* Ability indicator (Fogg Model - optional) */}
      {ability && (
        <p
          className={cn(
            "text-gray-400 dark:text-gray-400 italic",
            TEXT_STYLES[variant],
          )}
        >
          {ability}
        </p>
      )}

      {/* Loading or Trigger (Fogg Model) */}
      {isLoading ? (
        <div
          data-testid="empty-state-loading"
          className="mt-4 flex items-center gap-2 text-gray-500 dark:text-gray-400"
        >
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      ) : (
        <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
          {trigger}
          {secondaryTrigger}
        </div>
      )}
    </div>
  );
}

export default EmptyState;
