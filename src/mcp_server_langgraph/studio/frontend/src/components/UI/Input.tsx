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
        sm: "px-3 py-1.5 text-xs",
        md: "px-4 py-2 text-sm",
        lg: "px-4 py-2.5 text-base",
      },
      disabled: {
        true: "cursor-not-allowed opacity-50 bg-neutral-2",
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
          <div className="absolute left-3 pointer-events-none text-neutral-9">
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
          <div className="absolute right-3 pointer-events-none text-neutral-9">
            {rightIcon}
          </div>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
