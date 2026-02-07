/**
 * SupportBadge Component
 *
 * Displays support level badges (managed, premium, community, custom)
 * using the design system Badge component with semantic colors.
 *
 * @see SQLGlot Phase 6
 */

import { Badge } from "@/components/UI";
import {
  CheckCircle,
  Star,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../../utils/cn";

export type SupportLevel = "managed" | "premium" | "community" | "custom";

const SUPPORT_BADGES: Record<
  SupportLevel,
  { label: string; icon: LucideIcon; colorClasses: string }
> = {
  managed: {
    label: "Managed",
    icon: CheckCircle,
    colorClasses: "bg-success-3 text-success-11 border border-success-6",
  },
  premium: {
    label: "Premium",
    icon: Star,
    colorClasses: "bg-warning-3 text-warning-11 border border-warning-6",
  },
  community: {
    label: "Community",
    icon: Users,
    colorClasses: "bg-primary-3 text-primary-11 border border-primary-6",
  },
  custom: {
    label: "Custom",
    icon: Wrench,
    colorClasses: "bg-neutral-3 text-neutral-11 border border-neutral-6",
  },
};

export interface SupportBadgeProps {
  /** The support level to display */
  level: SupportLevel;
  /** Additional CSS classes */
  className?: string;
}

/**
 * SupportBadge - Displays a support level indicator
 *
 * Visual representation of support tier:
 * - managed: Fully supported by platform team
 * - premium: Premium support with SLA
 * - community: Community-maintained
 * - custom: Custom/user-provided
 */
export function SupportBadge({ level, className }: SupportBadgeProps) {
  const config = SUPPORT_BADGES[level];
  const Icon = config.icon;

  return (
    <Badge
      size="sm"
      pill
      icon={<Icon className="h-3 w-3" />}
      className={cn(config.colorClasses, className)}
      data-testid={`support-badge-${level}`}
    >
      {config.label}
    </Badge>
  );
}
