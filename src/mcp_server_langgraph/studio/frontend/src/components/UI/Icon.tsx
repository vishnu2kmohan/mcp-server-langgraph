/**
 * Icon Component
 *
 * Wrapper for Lucide icons with standardized sizing and accessibility.
 * Provides consistent icon sizes across the application and proper ARIA attributes.
 *
 * Size Reference:
 * - xs: 12px (badges, tiny indicators)
 * - sm: 14px (inline text, compact)
 * - md: 16px (buttons, inputs - default)
 * - lg: 20px (navigation, sidebar)
 * - xl: 24px (headers, dialogs)
 * - 2xl: 32px (empty states)
 * - 3xl: 48px (hero sections)
 *
 * Accessibility:
 * - Decorative icons: aria-hidden="true" (default)
 * - Meaningful icons: Provide aria-label, gets role="img"
 *
 * @example
 * // Decorative icon (text provides meaning)
 * <Button>
 *   <Icon icon={Download} />
 *   Download Report
 * </Button>
 *
 * @example
 * // Icon-only button (button provides meaning)
 * <Button aria-label="Delete item" variant="icon">
 *   <Icon icon={Trash2} />
 * </Button>
 *
 * @example
 * // Meaningful icon (standalone, no surrounding text)
 * <Icon icon={CheckCircle} aria-label="Success" className="text-success-9" />
 */

import { forwardRef } from "react";
import type { LucideIcon, LucideProps } from "lucide-react";
import { cn } from "@/utils/cn";

// =============================================================================
// Types
// =============================================================================

export type IconSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | "3xl";

export interface IconProps extends Omit<LucideProps, "ref"> {
  /** The Lucide icon component to render */
  icon: LucideIcon;
  /** Icon size preset */
  size?: IconSize;
  /** Accessible label for meaningful icons */
  "aria-label"?: string;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Size Mapping
// =============================================================================

/**
 * Maps size tokens to Tailwind width/height classes.
 * All sizes are based on the 4px grid system.
 */
const sizeClasses: Record<IconSize, string> = {
  xs: "w-3 h-3", // 12px
  sm: "w-3.5 h-3.5", // 14px
  md: "w-4 h-4", // 16px
  lg: "w-5 h-5", // 20px
  xl: "w-6 h-6", // 24px
  "2xl": "w-8 h-8", // 32px
  "3xl": "w-12 h-12", // 48px
};

// =============================================================================
// Component
// =============================================================================

export const Icon = forwardRef<SVGSVGElement, IconProps>(
  (
    {
      icon: IconComponent,
      size = "md",
      "aria-label": ariaLabel,
      className,
      ...props
    },
    ref,
  ) => {
    // Determine if icon is decorative or meaningful
    const isDecorative = !ariaLabel;

    return (
      <IconComponent
        ref={ref}
        className={cn(sizeClasses[size], "shrink-0", className)}
        aria-hidden={isDecorative}
        aria-label={ariaLabel}
        role={isDecorative ? undefined : "img"}
        {...props}
      />
    );
  },
);

Icon.displayName = "Icon";

export default Icon;
