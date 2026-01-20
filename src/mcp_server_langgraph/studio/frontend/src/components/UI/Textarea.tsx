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
    "block rounded-lg border bg-neutral-1 transition-colors duration-fast",
    "placeholder:text-neutral-9 dark:placeholder:text-neutral-10",
    "focus:outline-none focus:ring-2 focus:ring-offset-0",
  ],
  {
    variants: {
      variant: {
        default: [
          "border-neutral-5",
          "text-neutral-12",
          "focus:border-primary-9 focus:ring-primary-a3",
          "dark:focus:border-primary-7 dark:focus:ring-primary-a3",
        ],
        error: [
          "border-error-9 dark:border-error-7",
          "text-neutral-12",
          "focus:border-error-9 focus:ring-error-a3",
          "dark:focus:border-error-7 dark:focus:ring-error-a3",
        ],
        success: [
          "border-success-9 dark:border-success-7",
          "text-neutral-12",
          "focus:border-success-9 focus:ring-success-a3",
          "dark:focus:border-success-7 dark:focus:ring-success-a3",
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
        true: "cursor-not-allowed opacity-50 bg-neutral-2",
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
