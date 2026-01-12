/**
 * Textarea Component
 *
 * A consistent, accessible textarea component with multiple variants and sizes.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 * Aligned with the shared design system tokens.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "../../utils/cn";

/**
 * Textarea variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const textareaVariants = cva(
  // Base styles
  [
    "block rounded-lg border bg-white transition-colors duration-fast",
    "placeholder:text-neutral-400 dark:placeholder:text-neutral-500",
    "focus:outline-none focus:ring-2 focus:ring-offset-0",
    "dark:bg-neutral-800",
  ],
  {
    variants: {
      variant: {
        default: [
          "border-neutral-300 dark:border-neutral-600",
          "text-neutral-900 dark:text-neutral-100",
          "focus:border-primary-500 focus:ring-primary-500/20",
          "dark:focus:border-primary-400 dark:focus:ring-primary-400/20",
        ],
        error: [
          "border-error-500 dark:border-error-400",
          "text-neutral-900 dark:text-neutral-100",
          "focus:border-error-500 focus:ring-error-500/20",
          "dark:focus:border-error-400 dark:focus:ring-error-400/20",
        ],
        success: [
          "border-success-500 dark:border-success-400",
          "text-neutral-900 dark:text-neutral-100",
          "focus:border-success-500 focus:ring-success-500/20",
          "dark:focus:border-success-400 dark:focus:ring-success-400/20",
        ],
      },
      size: {
        sm: "p-2 text-xs",
        md: "p-3 text-sm",
        lg: "p-4 text-base",
      },
      resize: {
        none: "resize-none",
        vertical: "resize-y",
        horizontal: "resize-x",
        both: "resize",
      },
      disabled: {
        true: "cursor-not-allowed opacity-50 bg-neutral-100 dark:bg-neutral-900",
        false: "",
      },
      fullWidth: {
        true: "w-full",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      resize: "vertical",
      disabled: false,
      fullWidth: true,
    },
  },
);

export type TextareaVariant = NonNullable<
  VariantProps<typeof textareaVariants>["variant"]
>;
export type TextareaSize = NonNullable<
  VariantProps<typeof textareaVariants>["size"]
>;
export type TextareaResize = NonNullable<
  VariantProps<typeof textareaVariants>["resize"]
>;

export interface TextareaProps
  extends
    Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "size">,
    Omit<VariantProps<typeof textareaVariants>, "disabled" | "fullWidth"> {
  /** Make the textarea take full width of its container */
  fullWidth?: boolean;
}

/**
 * Textarea component with consistent styling
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      variant,
      size,
      resize,
      fullWidth = true,
      disabled,
      rows = 3,
      className,
      ...props
    },
    ref,
  ) => {
    return (
      <textarea
        ref={ref}
        rows={rows}
        disabled={disabled}
        className={cn(
          textareaVariants({
            variant,
            size,
            resize,
            disabled: !!disabled,
            fullWidth,
          }),
          className,
        )}
        {...props}
      />
    );
  },
);

Textarea.displayName = "Textarea";
