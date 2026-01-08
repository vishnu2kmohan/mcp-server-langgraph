/**
 * Card Component
 *
 * A flexible card component with composable subcomponents.
 * Aligned with the shared design system tokens.
 */

import { forwardRef, type HTMLAttributes } from "react";

export type CardVariant = "default" | "elevated" | "ghost";
export type CardPadding = "none" | "sm" | "md" | "lg";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Visual variant of the card */
  variant?: CardVariant;
  /** Padding size */
  padding?: CardPadding;
  /** Whether the card is interactive (hoverable/clickable) */
  interactive?: boolean;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Get variant-specific classes
 */
function getVariantClasses(variant: CardVariant): string {
  const variants: Record<CardVariant, string> = {
    default: cn(
      "border border-gray-200 dark:border-gray-700 bg-white",
      "dark:border-gray-700 dark:bg-gray-900",
    ),
    elevated: cn(
      "border border-gray-100 bg-white shadow-elevated",
      "dark:border-gray-700 dark:bg-gray-900",
    ),
    ghost: cn(
      "border border-transparent bg-transparent",
      "dark:bg-transparent",
    ),
  };
  return variants[variant];
}

/**
 * Get padding-specific classes
 */
function getPaddingClasses(padding: CardPadding): string {
  const paddings: Record<CardPadding, string> = {
    none: "p-0",
    sm: "p-3",
    md: "p-4",
    lg: "p-6",
  };
  return paddings[padding];
}

/**
 * Card component with consistent styling
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      variant = "default",
      padding = "md",
      interactive = false,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          // Base styles
          "rounded-lg",
          // Variant styles
          getVariantClasses(variant),
          // Padding styles
          getPaddingClasses(padding),
          // Interactive styles
          interactive &&
            cn(
              "cursor-pointer transition-all duration-fast",
              "hover:shadow-soft hover:border-gray-300 dark:border-gray-600",
              "dark:hover:border-gray-600",
            ),
          className,
        )}
        {...props}
      >
        {children}
      </div>
    );
  },
);

Card.displayName = "Card";

/**
 * CardHeader - Container for card title and actions
 */
export type CardHeaderProps = HTMLAttributes<HTMLDivElement>;

export function CardHeader({ className, children, ...props }: CardHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4",
        "-m-4 mb-4 p-4 border-b border-gray-100",
        "dark:border-gray-800",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * CardTitle - Heading for the card
 */
export type CardTitleProps = HTMLAttributes<HTMLHeadingElement>;

export function CardTitle({ className, children, ...props }: CardTitleProps) {
  return (
    <h3
      className={cn(
        "text-lg font-semibold text-gray-900",
        "dark:text-gray-100",
        className,
      )}
      {...props}
    >
      {children}
    </h3>
  );
}

/**
 * CardContent - Main content area of the card
 */
export type CardContentProps = HTMLAttributes<HTMLDivElement>;

export function CardContent({
  className,
  children,
  ...props
}: CardContentProps) {
  return (
    <div
      className={cn("text-gray-600 dark:text-gray-400", className)}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * CardFooter - Container for card actions
 */
export type CardFooterProps = HTMLAttributes<HTMLDivElement>;

export function CardFooter({ className, children, ...props }: CardFooterProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-2",
        "-m-4 mt-4 p-4 border-t border-gray-100",
        "dark:border-gray-800",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
