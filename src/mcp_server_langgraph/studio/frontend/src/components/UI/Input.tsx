/**
 * Input Component
 *
 * A consistent, accessible input component with multiple variants and sizes.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 * Aligned with the shared design system tokens.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../utils/cn";

/**
 * Input variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const inputVariants = cva(
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
        sm: "px-3 py-1.5 text-xs",
        md: "px-4 py-2 text-sm",
        lg: "px-4 py-2.5 text-base",
      },
      disabled: {
        true: "cursor-not-allowed opacity-50 bg-neutral-100 dark:bg-neutral-900",
        false: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      disabled: false,
    },
  },
);

export type InputVariant = NonNullable<
  VariantProps<typeof inputVariants>["variant"]
>;
export type InputSize = NonNullable<VariantProps<typeof inputVariants>["size"]>;

export interface InputProps
  extends
    Omit<InputHTMLAttributes<HTMLInputElement>, "size">,
    Omit<VariantProps<typeof inputVariants>, "disabled"> {
  /** Icon to display on the left side */
  leftIcon?: ReactNode;
  /** Icon to display on the right side */
  rightIcon?: ReactNode;
  /** Make the input take full width of its container */
  fullWidth?: boolean;
}

/**
 * Input component with consistent styling
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      variant,
      size,
      leftIcon,
      rightIcon,
      fullWidth = true,
      disabled,
      className,
      type = "text",
      ...props
    },
    ref,
  ) => {
    return (
      <div
        className={cn(
          "relative inline-flex items-center",
          fullWidth && "w-full",
        )}
      >
        {/* Left icon */}
        {leftIcon && (
          <div className="absolute left-3 pointer-events-none text-neutral-400 dark:text-neutral-500">
            {leftIcon}
          </div>
        )}

        {/* Input element */}
        <input
          ref={ref}
          type={type}
          disabled={disabled}
          className={cn(
            inputVariants({ variant, size, disabled: !!disabled }),
            leftIcon ? "pl-10" : undefined,
            rightIcon ? "pr-10" : undefined,
            fullWidth ? "w-full" : undefined,
            className,
          )}
          {...props}
        />

        {/* Right icon */}
        {rightIcon && (
          <div className="absolute right-3 pointer-events-none text-neutral-400 dark:text-neutral-500">
            {rightIcon}
          </div>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
