/**
 * Button Component
 *
 * A consistent, accessible button component with multiple variants.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 * Aligned with the shared design system tokens.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "../../utils/cn";

/**
 * Button variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const buttonVariants = cva(
  // Base styles
  [
    "inline-flex items-center justify-center font-medium rounded-md",
    "transition-colors duration-fast",
    "focus:outline-none focus:ring-2 focus:ring-offset-2",
  ],
  {
    variants: {
      variant: {
        primary: [
          "bg-brand-primary text-white",
          "hover:bg-primary-10 active:bg-primary-11",
          "focus:ring-brand-primary",
          "dark:bg-primary-10 dark:hover:bg-primary-9",
        ],
        secondary: [
          "bg-neutral-2 text-neutral-12",
          "hover:bg-neutral-3 active:bg-neutral-3",
          "focus:ring-neutral-6",
        ],
        ghost: [
          "bg-transparent text-neutral-11",
          "hover:bg-neutral-2 active:bg-neutral-3",
          "focus:ring-neutral-6",
        ],
        danger: [
          "bg-error-9 text-white",
          "hover:bg-error-10 active:bg-error-11",
          "focus:ring-error-7",
        ],
        success: [
          "bg-success-9 text-white",
          "hover:bg-success-10 active:bg-success-11",
          "focus:ring-success-7",
        ],
        warning: [
          "bg-warning-9 text-neutral-12",
          "hover:bg-warning-9 active:bg-warning-10",
          "focus:ring-warning-7",
        ],
        outline: [
          "bg-transparent border border-neutral-5",
          "text-neutral-11",
          "hover:bg-neutral-1 active:bg-neutral-2",
          "focus:ring-neutral-6",
        ],
      },
      size: {
        sm: "px-3 py-1.5 text-xs gap-1.5",
        md: "px-4 py-2 text-sm gap-2",
        lg: "px-6 py-3 text-base gap-2.5",
        icon: "p-2 h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export type ButtonVariant = NonNullable<
  VariantProps<typeof buttonVariants>["variant"]
>;
export type ButtonSize = NonNullable<
  VariantProps<typeof buttonVariants>["size"]
>;

export interface ButtonProps
  extends
    ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Whether the button is in a loading state */
  loading?: boolean;
  /** Icon to display before the text */
  leftIcon?: ReactNode;
  /** Icon to display after the text */
  rightIcon?: ReactNode;
  /** Full width button */
  fullWidth?: boolean;
}

/**
 * Button component with consistent styling
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant,
      size,
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          buttonVariants({ variant, size }),
          isDisabled && "opacity-50 cursor-not-allowed",
          fullWidth && "w-full",
          className,
        )}
        {...props}
      >
        {/* Loading spinner */}
        {loading && (
          <svg
            className="animate-spin -ml-1 h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {/* Left icon */}
        {!loading && leftIcon && (
          <span className="shrink-0" aria-hidden="true">
            {leftIcon}
          </span>
        )}
        {/* Button text */}
        {children}
        {/* Right icon */}
        {rightIcon && (
          <span className="shrink-0" aria-hidden="true">
            {rightIcon}
          </span>
        )}
      </button>
    );
  },
);

Button.displayName = "Button";
