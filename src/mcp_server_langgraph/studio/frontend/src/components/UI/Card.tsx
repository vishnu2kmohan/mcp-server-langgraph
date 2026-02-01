/**
 * Card Component
 *
 * A flexible card component with composable subcomponents.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 * Aligned with the shared design system tokens.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "../../utils/cn";

/**
 * Card variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const cardVariants = cva(
  // Base styles
  "rounded-lg",
  {
    variants: {
      variant: {
        default: ["border border-neutral-5 bg-neutral-1"],
        elevated: ["border border-neutral-5 bg-neutral-1 shadow-elevated"],
        ghost: [
          "border border-transparent bg-transparent",
          "dark:bg-transparent",
        ],
      },
      padding: {
        none: "p-0",
        sm: "p-3",
        md: "p-4",
        lg: "p-6",
      },
      interactive: {
        true: [
          "cursor-pointer transition-all duration-fast",
          "hover:shadow-soft hover:border-neutral-5",
          "dark:hover:border-neutral-6",
        ],
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      padding: "md",
      interactive: false,
    },
  },
);

export type CardVariant = NonNullable<
  VariantProps<typeof cardVariants>["variant"]
>;
export type CardPadding = NonNullable<
  VariantProps<typeof cardVariants>["padding"]
>;

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

/**
 * Card component with consistent styling
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant, padding, interactive, className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          cardVariants({ variant, padding, interactive }),
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
        "-m-4 mb-4 p-4 border-b border-neutral-5",
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
      className={cn("text-lg font-semibold text-neutral-12", className)}
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
    <div className={cn("text-neutral-11", className)} {...props}>
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
        "-m-4 mt-4 p-4 border-t border-neutral-5",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
