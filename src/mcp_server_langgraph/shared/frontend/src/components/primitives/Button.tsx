/**
 * Button Component (Shared Primitive)
 *
 * Accessible button with CVA variants for consistent styling.
 * Designed for WCAG 2.2 AA compliance with focus-visible and aria support.
 *
 * @module @mcp-server-langgraph/shared-frontend/primitives
 */

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';

/**
 * Button variants using CVA for type-safe, consistent styling
 */
export const buttonVariants = cva(
  // Base styles
  [
    'inline-flex items-center justify-center font-medium rounded-md',
    'transition-colors duration-150',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
  ],
  {
    variants: {
      variant: {
        primary: [
          'bg-primary-600 text-white',
          'hover:bg-primary-700 active:bg-primary-800',
          'focus-visible:ring-primary-500',
          'dark:bg-primary-500 dark:hover:bg-primary-400',
        ],
        secondary: [
          'bg-gray-100 text-gray-900',
          'hover:bg-gray-200 active:bg-gray-300',
          'focus-visible:ring-gray-300',
          'dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700',
        ],
        ghost: [
          'bg-transparent text-gray-700',
          'hover:bg-gray-100 active:bg-gray-200',
          'focus-visible:ring-gray-300',
          'dark:text-gray-300 dark:hover:bg-gray-800',
        ],
        danger: [
          'bg-error-600 text-white',
          'hover:bg-error-700 active:bg-error-800',
          'focus-visible:ring-error-500',
        ],
        success: [
          'bg-success-600 text-white',
          'hover:bg-success-700 active:bg-success-800',
          'focus-visible:ring-success-500',
        ],
        outline: [
          'bg-transparent border border-gray-300 text-gray-700',
          'hover:bg-gray-50 active:bg-gray-100',
          'focus-visible:ring-gray-300',
          'dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800',
        ],
      },
      size: {
        sm: 'h-8 px-3 text-xs gap-1.5',
        md: 'h-10 px-4 text-sm gap-2',
        lg: 'h-12 px-6 text-base gap-2.5',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
      fullWidth: false,
    },
  }
);

/**
 * Loading spinner SVG component
 */
const LoadingSpinner = () => (
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
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Whether the button is in a loading state */
  loading?: boolean;
  /** Icon to display before the text */
  leftIcon?: ReactNode;
  /** Icon to display after the text */
  rightIcon?: ReactNode;
}

/**
 * Accessible button component with consistent styling
 *
 * @example
 * ```tsx
 * <Button variant="primary" size="md">Click me</Button>
 * <Button variant="danger" loading>Deleting...</Button>
 * <Button leftIcon={<PlusIcon />}>Add Item</Button>
 * ```
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      fullWidth,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, fullWidth, className }))}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        aria-disabled={isDisabled || undefined}
        {...props}
      >
        {loading && <LoadingSpinner />}
        {!loading && leftIcon && (
          <span className="shrink-0" aria-hidden="true">
            {leftIcon}
          </span>
        )}
        {children}
        {rightIcon && (
          <span className="shrink-0" aria-hidden="true">
            {rightIcon}
          </span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
