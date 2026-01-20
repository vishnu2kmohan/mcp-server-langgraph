/**
 * ConnectorCard Component
 *
 * A card component for displaying connector templates in the directory view.
 * Uses Motion for smooth hover animations per ADR-0102.
 *
 * @see ADR-0102 - Connections Page Redesign
 */

import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/utils/cn";
import { cardHoverVariants } from "@/design-system/micro-interactions";
import { Button } from "@/components/UI";
import type { ConnectionTemplateCamelCase } from "@/types/connectionTemplate";

// ============================================================================
// Types
// ============================================================================

export interface ConnectorCardProps {
  /** The connection template to display */
  template: ConnectionTemplateCamelCase;
  /** Callback when Connect button is clicked */
  onConnect: (template: ConnectionTemplateCamelCase) => void;
  /** Whether this connector is already connected */
  isConnected?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Icon Mapping
// ============================================================================

const getIconEmoji = (icon: string): string => {
  const iconMap: Record<string, string> = {
    github: "🐙",
    gitlab: "🦊",
    slack: "💬",
    discord: "🎮",
    notion: "📝",
    jira: "📋",
    linear: "📐",
    folder: "📁",
    database: "🗄️",
    key: "🔑",
    lock: "🔒",
    custom: "⚙️",
  };
  return iconMap[icon] || "🔌";
};

// ============================================================================
// Auth Type Display
// ============================================================================

const getAuthTypeLabel = (authType: string): string => {
  const labels: Record<string, string> = {
    oauth2: "OAuth2",
    api_key: "API Key",
    none: "No Auth",
  };
  return labels[authType] || authType;
};

const getAuthTypeBadgeClass = (authType: string): string => {
  const classes: Record<string, string> = {
    oauth2: "bg-primary-3 text-primary-11",
    api_key:
      "bg-warning-3 text-warning-11",
    none: "bg-neutral-2 text-neutral-11",
  };
  return classes[authType] || classes.none;
};

// ============================================================================
// Component
// ============================================================================

export function ConnectorCard({
  template,
  onConnect,
  isConnected = false,
  className,
}: ConnectorCardProps) {
  const prefersReducedMotion = useReducedMotion();

  // Use reduced motion variants if user prefers
  const variants = prefersReducedMotion ? undefined : cardHoverVariants;

  return (
    <motion.article
      className={cn(
        "relative flex flex-col rounded-lg border bg-neutral-1 p-4",
        "border-neutral-6",
        "transition-shadow duration-fast",
        className
      )}
      variants={variants}
      initial="rest"
      whileHover="hover"
      whileTap="pressed"
      aria-label={`${template.name} connector`}
    >
      {/* Connected Badge */}
      {isConnected && (
        <div className="absolute -top-2 -right-2">
          <span className="inline-flex items-center rounded-full bg-success-3 px-2.5 py-0.5 text-xs font-medium text-success-11">
            Connected
          </span>
        </div>
      )}

      {/* Header with Icon and Name */}
      <div className="mb-3 flex items-center gap-3">
        <span
          className="text-3xl"
          role="img"
          aria-label={`${template.icon} icon`}
          data-testid="connector-icon"
        >
          {getIconEmoji(template.icon)}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-neutral-12">
            {template.name}
          </h3>
        </div>
      </div>

      {/* Description */}
      <p className="mb-4 line-clamp-2 flex-1 text-sm text-neutral-11">
        {template.description}
      </p>

      {/* Badges */}
      <div className="mb-4 flex flex-wrap gap-2">
        {/* Auth Type Badge */}
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            getAuthTypeBadgeClass(template.authType)
          )}
        >
          {getAuthTypeLabel(template.authType)}
        </span>

        {/* Category Badge */}
        <span className="inline-flex items-center rounded-full bg-neutral-2 px-2 py-0.5 text-xs font-medium text-neutral-11">
          {template.category}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between gap-2">
        <Button
          variant={isConnected ? "secondary" : "primary"}
          size="sm"
          onClick={() => onConnect(template)}
          disabled={isConnected}
          className="flex-1"
        >
          {isConnected ? "Connected" : "Connect"}
        </Button>

        {template.documentationUrl && (
          <a
            href={template.documentationUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium",
              "text-neutral-11 hover:bg-neutral-2 hover:text-neutral-12",
              
              "transition-colors duration-fast"
            )}
            aria-label="Docs (opens in new tab)"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
            Docs
          </a>
        )}
      </div>
    </motion.article>
  );
}

export default ConnectorCard;
