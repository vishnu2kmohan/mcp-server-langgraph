/**
 * ScopeBadge Component
 *
 * Displays a badge indicating the connection scope (user/project/session).
 * Uses design system tokens and supports reduced motion.
 *
 * @see ADR-0102 Phase 6
 */

import { Badge, type BadgeSize } from "../UI/Badge";
import { User, Users, Clock } from "lucide-react";
import type { ConnectionScope } from "@/types/connection";

/**
 * Configuration for each scope type
 */
const SCOPE_CONFIG: Record<
  ConnectionScope,
  {
    label: string;
    icon: typeof User;
    variant: "default" | "primary" | "warning";
  }
> = {
  user: {
    label: "Personal",
    icon: User,
    variant: "default",
  },
  project: {
    label: "Shared",
    icon: Users,
    variant: "primary",
  },
  session: {
    label: "Session",
    icon: Clock,
    variant: "warning",
  },
};

export interface ScopeBadgeProps {
  /** The connection scope to display */
  scope: ConnectionScope;
  /** Size of the badge */
  size?: BadgeSize;
  /** Additional CSS classes */
  className?: string;
}

/**
 * ScopeBadge - Displays a connection scope indicator
 *
 * Visual representation of connection access level:
 * - user (Personal): Only accessible by owner
 * - project (Shared): Accessible by project members
 * - session (Session): Ephemeral, current session only
 */
export function ScopeBadge({ scope, size = "md", className }: ScopeBadgeProps) {
  const config = SCOPE_CONFIG[scope];
  const IconComponent = config.icon;

  return (
    <Badge
      data-testid="scope-badge"
      data-scope={scope}
      variant={config.variant}
      size={size}
      icon={<IconComponent className="h-3 w-3" aria-hidden="true" />}
      className={className}
      aria-label={`${config.label} scope`}
    >
      {config.label}
    </Badge>
  );
}
