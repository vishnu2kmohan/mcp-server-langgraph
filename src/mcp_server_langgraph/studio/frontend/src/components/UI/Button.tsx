/**
 * Button Component
 *
 * A consistent, accessible button component with multiple variants.
 * Aligned with the shared design system tokens.
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "danger"
  | "success"
  | "outline";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual variant of the button */
  variant?: ButtonVariant;
  /** Size of the button */
  size?: ButtonSize;
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
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Get variant-specific classes
 */
function getVariantClasses(variant: ButtonVariant): string {
  const variants: Record<ButtonVariant, string> = {
    primary: cn(
      "bg-brand-primary text-white",
      "hover:bg-primary-600 active:bg-primary-700",
      "focus:ring-brand-primary",
      "dark:bg-primary-600 dark:hover:bg-primary-500",
    ),
    secondary: cn(
      "bg-gray-100 dark:bg-gray-800 text-gray-900",
      "hover:bg-gray-200 dark:bg-gray-700 active:bg-gray-300 dark:bg-gray-600",
      "focus:ring-gray-300",
      "dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700",
    ),
    ghost: cn(
      "bg-transparent text-gray-700 dark:text-gray-200",
      "hover:bg-gray-100 dark:bg-gray-800 active:bg-gray-200 dark:bg-gray-700",
      "focus:ring-gray-300",
      "dark:text-gray-300 dark:hover:bg-gray-800",
    ),
    danger: cn(
      "bg-error-500 text-white",
      "hover:bg-error-600 active:bg-error-700",
      "focus:ring-error-500",
    ),
    success: cn(
      "bg-success-500 text-white",
      "hover:bg-success-600 active:bg-success-700",
      "focus:ring-success-500",
    ),
    outline: cn(
      "bg-transparent border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200",
      "hover:bg-gray-50 active:bg-gray-100 dark:bg-gray-800",
      "focus:ring-gray-300",
      "dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800",
    ),
  };
  return variants[variant];
}

/**
 * Get size-specific classes
 */
function getSizeClasses(size: ButtonSize): string {
  const sizes: Record<ButtonSize, string> = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2 text-sm gap-2",
    lg: "px-6 py-3 text-base gap-2.5",
  };
  return sizes[size];
}

/**
 * Button component with consistent styling
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
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
          // Base styles
          "inline-flex items-center justify-center font-medium rounded-md",
          "transition-colors duration-fast",
          "focus:outline-none focus:ring-2 focus:ring-offset-2",
          // Variant styles
          getVariantClasses(variant),
          // Size styles
          getSizeClasses(size),
          // State modifiers
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
